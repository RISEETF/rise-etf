"""Import a selected KRX Portfolio Deposit File CSV; no login automation.

The observed CSV has no parent ETF/date. A browser-observed receipt is mandatory;
the hash binds bytes, not independent proof of the operator's date assertion.
Raw holdings stay in var/. Only acquisition/quality metadata may be exported.
"""
import argparse
import datetime as dt
import hashlib
import json
import re
import sqlite3
from pathlib import Path
from zoneinfo import ZoneInfo
from collect_krx_etf import write_json_atomic
from import_etf_provider_export import read_rows, provider_number

HEADER = ['종목코드', '구성종목명', '주식수(계약수)', '평가금액', '시가총액', '시가총액 구성비중']
SOURCE = 'https://data.krx.co.kr/contents/MDC/MDI/mdiLoader/index.cmd?menuId=MDC0201030108'
CASH_CODES = {'KRD010010001', 'CASH00000001'}


def inspect(path, receipt, queue):
    path = Path(path)
    if path.suffix.lower() != '.csv' or not 0 < path.stat().st_size <= 10 * 1024 * 1024:
        raise ValueError('PDF_FILE_INVALID')
    raw = path.read_bytes()
    if receipt.get('sha256') != hashlib.sha256(raw).hexdigest():
        raise ValueError('PDF_HASH_MISMATCH')
    if (receipt.get('source_url') != SOURCE or receipt.get('date_basis') != 'BROWSER_OBSERVED_QUERY'
            or receipt.get('quantity_unit') != '주(계약)' or receipt.get('amount_unit') != '원'):
        raise ValueError('PDF_RECEIPT_INVALID')
    day = dt.date.fromisoformat(receipt['observation_date'])
    retrieved = dt.datetime.fromisoformat(receipt['retrieved_at'])
    now = dt.datetime.now(dt.timezone.utc)
    if (receipt['observation_date'] != day.isoformat() or retrieved.tzinfo is None or retrieved > now + dt.timedelta(minutes=5)
            or day > retrieved.astimezone(ZoneInfo('Asia/Seoul')).date()):
        raise ValueError('PDF_DATE_INVALID')
    if queue.get('schema') != 'ETF_INVESTIGATION_QUEUE_V1':
        raise ValueError('PDF_QUEUE_INVALID')
    matches = [i for i in queue['items'] if i['ticker'] == receipt.get('ticker')
               and i['name'] == receipt.get('name') and i['observation_date'] == day.isoformat()
               and i['pdf_request']['requested_date'] == day.isoformat()]
    if len(matches) != 1 or queue['observation_date'] != day.isoformat():
        raise ValueError('PDF_REQUEST_MISMATCH')
    rows, encoding = read_rows(path)
    if not rows or rows[0] != HEADER:
        raise ValueError('PDF_SCHEMA_UNSUPPORTED')
    records, seen = [], set()
    for row in rows[1:]:
        if not any(v.strip() for v in row):
            continue
        if len(row) != 6:
            raise ValueError('PDF_ROW_WIDTH_INVALID')
        code, name = row[0].strip(), row[1].strip()
        if not re.fullmatch(r'[0-9A-Z]{6,12}', code) or code in seen or not name:
            raise ValueError('PDF_CONSTITUENT_INVALID')
        seen.add(code)
        nums = [provider_number(v) for v in row[2:]]
        if nums[3] is not None and not 0 <= nums[3] <= 100:
            raise ValueError('PDF_WEIGHT_INVALID')
        records.append(dict(zip(['code','name','quantity','valuation_krw','market_value_krw','weight_pct'],
                                [code,name] + nums)))
    if not records or type(receipt.get('row_count')) is not int or len(records) != receipt['row_count']:
        raise ValueError('PDF_ROW_COUNT_MISMATCH')
    securities = [r for r in records if r['code'] not in CASH_CODES]
    if not securities:
        raise ValueError('PDF_NO_SECURITIES')
    missing_weights = sum(r['weight_pct'] is None for r in securities)
    # Even complete weights do not establish a causal explanation of the alert.
    summary = {'ticker': receipt['ticker'], 'name': receipt['name'],
               'observation_date': day.isoformat(), 'retrieved_at': retrieved.astimezone(dt.timezone.utc).isoformat(),
               'source': 'KRX_PDF', 'source_url': SOURCE, 'sha256': receipt['sha256'],
               'date_basis': receipt['date_basis'], 'row_count': len(records),
               'security_count': len(securities), 'cash_related_rows': len(records)-len(securities),
               'missing_security_weights': missing_weights,
               'state': 'PDF_ACQUIRED_PARTIAL' if missing_weights else 'PDF_ACQUIRED',
               'attribution_verified': False,
               'limitation': '구성내역 확보 · 비중 누락으로 기여도 분석 보류' if missing_weights else
                             '구성내역 확보 · 이상신호 원인 분석은 별도 검증 필요'}
    return {'schema': 'KRX_PDF_IMPORT_V1', 'receipt': receipt, 'encoding': encoding,
            'summary': summary, 'records': records}


def ingest(path, receipt, queue, output, public_receipts=None):
    output = Path(output)
    status_path = output / 'status.json'
    prior = json.loads(status_path.read_text()) if status_path.exists() else {}
    stamp = dt.datetime.now(dt.timezone.utc).isoformat()
    try:
        doc = inspect(path, receipt, queue)
        # One identity includes query context because CSV itself has no ETF/date.
        key = hashlib.sha256(f"{receipt['ticker']}:{receipt['observation_date']}:{receipt['sha256']}".encode()).hexdigest()
        raw_path = output / 'raw' / receipt['sha256'] / 'original.csv'
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw = Path(path).read_bytes()
        if hashlib.sha256(raw).hexdigest() != receipt['sha256']:
            raise ValueError('PDF_FILE_CHANGED_DURING_IMPORT')
        if raw_path.exists():
            if raw_path.read_bytes() != raw:
                raise ValueError('PDF_ARCHIVE_COLLISION')
        else:
            with raw_path.open('xb') as f:
                f.write(raw)
        with sqlite3.connect(output / 'holdings.sqlite') as db:
            db.execute('''CREATE TABLE IF NOT EXISTS pdf_imports
                (id TEXT PRIMARY KEY, ticker TEXT, observation_date TEXT,
                 retrieved_at TEXT, document TEXT)''')
            db.execute('INSERT OR IGNORE INTO pdf_imports VALUES (?,?,?,?,?)',
                       (key, receipt['ticker'], receipt['observation_date'], doc['summary']['retrieved_at'],
                        json.dumps(doc, ensure_ascii=False)))
            db.commit()
            doc = json.loads(db.execute('SELECT document FROM pdf_imports WHERE id=?', (key,)).fetchone()[0])
            if public_receipts:
                # Merge by ticker/date; retain previous public acquisitions even
                # when this workstation has imported only a subset of private DBs.
                p = Path(public_receipts)
                old = json.loads(p.read_text()) if p.exists() else {'schema':'KRX_PDF_RECEIPTS_V1','items':[]}
                if old.get('schema') != 'KRX_PDF_RECEIPTS_V1':
                    raise ValueError('PDF_PUBLIC_SCHEMA_INVALID')
                items = {(i['ticker'],i['observation_date']): i for i in old['items']}
                for (payload,) in db.execute('SELECT document FROM pdf_imports ORDER BY retrieved_at,id'):
                    item = json.loads(payload)['summary']; pair = (item['ticker'],item['observation_date'])
                    if pair not in items or dt.datetime.fromisoformat(items[pair]['retrieved_at']) <= dt.datetime.fromisoformat(item['retrieved_at']):
                        items[pair] = item
                write_json_atomic(p, {'schema':'KRX_PDF_RECEIPTS_V1','items':[items[k] for k in sorted(items)]})
        write_json_atomic(status_path, {'status':'SUCCESS','last_success_at':stamp,'attempted_at':stamp,'import_id':key})
        return doc['summary']
    except Exception as exc:
        write_json_atomic(status_path, {'status':'FAILED','last_success_at':prior.get('last_success_at'),
                                       'attempted_at':stamp,'reason':str(exc),'prior_imports_preserved':True})
        raise


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('csv'); p.add_argument('--receipt', required=True)
    p.add_argument('--queue', default='data/etf_investigations/latest.json')
    p.add_argument('--output', default='var/etf-pdf')
    p.add_argument('--public-receipts', help='Optional metadata-only publication; never exports constituent rows')
    args = p.parse_args()
    print(json.dumps(ingest(Path(args.csv), json.loads(Path(args.receipt).read_text()),
                           json.loads(Path(args.queue).read_text()), Path(args.output), args.public_receipts), ensure_ascii=False))


if __name__ == '__main__':
    main()

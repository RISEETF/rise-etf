"""Dated RISE market view from the existing KRX ledger (no new collection)."""
import argparse
import calendar
import datetime as dt
import hashlib
import json
import math
import sqlite3
from pathlib import Path
from zoneinfo import ZoneInfo
from collect_krx_etf import write_json_atomic

PERIODS = ('1D', '1W', '1M', '3M', 'YTD')


def target_date(day, period):
    if period == '1D':
        target = day - dt.timedelta(days=1)
        while target.weekday() > 4:
            target -= dt.timedelta(days=1)
        return target
    if period == '1W':
        return day - dt.timedelta(days=7)
    if period == 'YTD':
        return dt.date(day.year-1, 12, 31)
    month = day.year * 12 + day.month - 1 - (1 if period == '1M' else 3)
    year, month = divmod(month, 12)
    return dt.date(year, month+1, min(day.day, calendar.monthrange(year, month+1)[1]))


def period_return(history, day, period, market_dates):
    target = target_date(day, period)
    candidates = [d for d in market_dates if d <= target.isoformat()]
    base = max(candidates) if candidates else None
    result = {'pct': None, 'target_date': target.isoformat(), 'base_date': base,
              'end_date': day.isoformat(), 'status': 'INSUFFICIENT_HISTORY'}
    # 1D never silently bridges an absent weekday. Other periods expose both endpoints.
    tolerance = 0 if period == '1D' else 7
    if not base or (target-dt.date.fromisoformat(base)).days > tolerance:
        return result
    prior = history.get(base, {}).get('close')
    current = history.get(day.isoformat(), {}).get('close')
    if not prior or not current:
        return result
    result.update(pct=round((current/prior-1)*100, 4), status='PRICE_RETURN_UNADJUSTED')
    return result


def build(db_path, receipt, inventory, today):
    day = dt.date.fromisoformat(receipt['observation_date'])
    if receipt.get('status') != 'SUCCESS' or not 0 <= (today-day).days <= 7:
        raise ValueError('INVALID_COLLECTION_RECEIPT')
    if (inventory.get('source_id') != 'KRX_OPEN_API_ETF_DAILY' or
        inventory['observed_on'] != day.isoformat() or inventory['raw_sha256'] != receipt['raw_sha256']):
        raise ValueError('INVENTORY_RECEIPT_MISMATCH')
    observed = [r for r in inventory['products'] if r.get('status', 'OBSERVED') == 'OBSERVED']
    codes = [r['code'] for r in observed]
    if len(set(codes)) != len(codes) or len(codes) != inventory['observed_count']:
        raise ValueError('INVENTORY_COUNT_MISMATCH')
    with sqlite3.connect(f'file:{Path(db_path).resolve()}?mode=ro', uri=True) as db:
        db.row_factory = sqlite3.Row
        if db.execute('select max(observation_date) from snapshots').fetchone()[0] != day.isoformat():
            raise ValueError('DATABASE_RECEIPT_DATE_MISMATCH')
        count = db.execute('select count(distinct ticker) from snapshots where observation_date=?', (day.isoformat(),)).fetchone()[0]
        if count != receipt['record_count']:
            raise ValueError('DATABASE_RECEIPT_COUNT_MISMATCH')
        market_dates = [r[0] for r in db.execute('select distinct observation_date from snapshots where field=?', ('close',))]
        rows = db.execute('''select * from (select *, row_number() over
          (partition by observation_date,ticker,field order by retrieved_at desc,rowid desc) as rank
          from snapshots where ticker in (''' + ','.join('?' for _ in codes) + ')) where rank=1', codes).fetchall()
    series, names = {}, {}
    for row in rows:
        value = row['value']
        if not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
            raise ValueError('INVALID_DATABASE_VALUE')
        series.setdefault(row['ticker'], {}).setdefault(row['observation_date'], {})[row['field']] = value
        if row['observation_date'] == day.isoformat():
            names[row['ticker']] = row['name']
    products = []
    for product in observed:
        code = product['code']
        if names.get(code) != product['name']:
            raise ValueError('DATABASE_INVENTORY_IDENTITY_MISMATCH')
        history = series[code]
        values = history[day.isoformat()]
        close, nav = values.get('close'), values.get('nav')
        products.append({'code': code, 'name': product['name'],
            'close': close, 'nav': nav, 'volume': values.get('volume'),
            'trading_value': values.get('trading_value'), 'net_assets': values.get('net_assets'),
            'nav_gap_pct': round((close/nav-1)*100, 4) if close and nav else None,
            'returns': {p: period_return(history, day, p, market_dates) for p in PERIODS},
            'investor_flows': {'status': 'SOURCE_NOT_CONNECTED', 'observation_date': None,
                'individual_net_krw': None, 'institution_net_krw': None, 'foreign_net_krw': None}})
    return {'schema': 'RISE_MARKET_METRICS_V1', 'source': 'KRX_OPEN_API_ETF_DAILY',
        'source_url': 'https://openapi.krx.co.kr/contents/OPP/INFO/service/OPPINFO004.cmd',
        'observation_date': day.isoformat(), 'source_retrieved_at': receipt['retrieved_at'],
        'source_raw_sha256': receipt['raw_sha256'], 'count': len(products),
        'history_start': min(market_dates), 'history_observation_count': len(market_dates),
        'return_basis': 'UNADJUSTED_CLOSE_EXCLUDING_DISTRIBUTIONS', 'products': products,
        'limitations': ['종가 등락률이며 분배금 재투자 총수익률이 아닙니다. 분할·병합도 미조정입니다.',
            '1W는 7일 전, 1M·3M은 달력 월, YTD는 전년 말 기준입니다. 상세에 실제 비교일을 표시합니다.',
            '비교 기준일 이전 7일 내 관측이 없거나 해당 종목 값이 없으면 미산정합니다. 1D는 직전 평일 누락 시 미산정합니다.',
            '투자자별 순매수는 별도 원천 연결 전 미제공합니다. 거래량·순자산 변화로 대체하지 않습니다.',
            'NAV와 국내 종가의 평가시점 차이로 해외 ETF 괴리율 해석에 주의가 필요합니다.']}


def publish(document, output):
    output = Path(output)
    if output.exists() and json.loads(output.read_text())['observation_date'] > document['observation_date']:
        raise ValueError('METRICS_DATE_REGRESSION')
    digest = hashlib.sha256(json.dumps(document, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    history = output.parent/'history'/document['observation_date']/f'{digest}.json'
    if not history.exists():
        write_json_atomic(history, document)
    write_json_atomic(output, document)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--db', default='var/krx_etf.sqlite')
    p.add_argument('--receipt', default='var/krx-output/receipt.json')
    p.add_argument('--inventory', default='data/quality/krx_rise_inventory.json')
    p.add_argument('--output', default='data/etf_market/latest.json')
    args = p.parse_args()
    status = Path(args.output).parent/'status.json'
    stamp = dt.datetime.now(dt.timezone.utc).isoformat()
    prior = json.loads(status.read_text()) if status.exists() else {}
    try:
        doc = build(args.db, json.loads(Path(args.receipt).read_text()),
                    json.loads(Path(args.inventory).read_text()), dt.datetime.now(ZoneInfo('Asia/Seoul')).date())
        publish(doc, args.output)
        write_json_atomic(status, {'status': 'SUCCESS', 'last_success_at': stamp,
            'attempted_at': stamp, 'observation_date': doc['observation_date']})
        print(json.dumps({'status': 'SUCCESS', 'count': doc['count'], 'observation_date': doc['observation_date']}))
    except Exception as exc:
        write_json_atomic(status, {'status': 'FAILED', 'attempted_at': stamp,
            'last_success_at': prior.get('last_success_at'), 'reason': type(exc).__name__, 'last_good_preserved': True})
        raise

if __name__ == '__main__':
    main()

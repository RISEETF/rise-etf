"""Dated Naver ETF snapshots and investor net quantities; secondary to KRX."""
import datetime as dt
import hashlib
import json
import math
import re
import sqlite3
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
LIST = 'https://finance.naver.com/api/sise/etfItemList.nhn'
DETAIL = 'https://m.stock.naver.com/api/stock/{}/integration'

def num(v):
    if v is None or str(v).strip() in ('', '-', 'N/A'):
        return None
    n = float(str(v).replace(',', ''))
    if not math.isfinite(n):
        raise ValueError('NONFINITE')
    return n

def listing(d):
    if d.get('resultCode') != 'success':
        raise ValueError('BAD_LIST')
    rows, seen = [], set()
    for r in d['result']['etfItemList']:
        c = r['itemcode']
        if not re.fullmatch('[0-9A-Z]{6}', c) or c in seen or not isinstance(r['itemname'], str):
            raise ValueError('BAD_IDENTITY')
        seen.add(c)
        rows.append(dict(code=c, name=r['itemname'], price_krw=num(r.get('nowVal')),
            change_pct=num(r.get('changeRate')), volume_shares=num(r.get('quant')),
            nav_krw=num(r.get('nav')), observation_date=None))
    if not rows:
        raise ValueError('EMPTY_LIST')
    return rows

def flows(d, code, today):
    if d.get('itemCode') != code or d.get('stockEndType') != 'etf':
        raise ValueError('BAD_IDENTITY')
    out, seen = [], set()
    for r in d.get('dealTrendInfos', []):
        day = dt.datetime.strptime(r['bizdate'], '%Y%m%d').date()
        if r.get('itemCode') != code or day > today or day in seen:
            raise ValueError('BAD_DATE_OR_IDENTITY')
        seen.add(day)
        out.append(dict(code=code, name=d['stockName'], observation_date=str(day),
            foreign_net_shares=num(r.get('foreignerPureBuyQuant')),
            institution_net_shares=num(r.get('organPureBuyQuant')),
            individual_net_shares=num(r.get('individualPureBuyQuant')),
            close_krw=num(r.get('closePrice'))))
    if not out:
        raise ValueError('EMPTY_FLOWS')
    return out

def write(path, doc):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(doc, ensure_ascii=False, indent=2)+'\n')
    temp.replace(path)

def request(url, folder):
    with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent':'RISE-Research/1.0'}), timeout=25) as r:
        raw = r.read(5000001)
    if len(raw)>5000000:
        raise ValueError('TOO_LARGE')
    sha = hashlib.sha256(raw).hexdigest()
    for encoding in ('utf-8','euc-kr'):
        try:
            doc = json.loads(raw.decode(encoding))
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ValueError('ENCODING')
    # Preserve decoded public response and original-byte digest.
    write(folder/'raw'/(sha+'.json'), {'url':url,'raw_sha256':sha,'response':doc})
    return doc, {'url':url,'raw_sha256':sha}

def database(folder, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE IF NOT EXISTS snapshots(id TEXT PRIMARY KEY,retrieved_at TEXT,document TEXT)')
        db.execute('CREATE TABLE IF NOT EXISTS flows(snapshot_id TEXT,code TEXT,observation_date TEXT,document TEXT,PRIMARY KEY(snapshot_id,code,observation_date))')
        for p in sorted((folder/'history').glob('*/*.json')):
            raw = p.read_text(); d = json.loads(raw)
            key = hashlib.sha256(raw.encode()).hexdigest()
            db.execute('INSERT OR IGNORE INTO snapshots VALUES(?,?,?)',(key,d['retrieved_at'],raw))
            for r in d['flows']:
                db.execute('INSERT OR IGNORE INTO flows VALUES(?,?,?,?)',(key,r['code'],r['observation_date'],json.dumps(r,ensure_ascii=False)))
        db.commit()

def publish(folder, doc):
    key = hashlib.sha256(json.dumps(doc,sort_keys=True).encode()).hexdigest()
    write(folder/'history'/doc['capture_date_kst']/(key+'.json'),doc)
    write(folder/'attempt.json',doc)
    # Partial attempts are archived, but cannot replace the complete snapshot.
    if doc['status']=='SUCCESS':
        write(folder/'latest.json',doc)
    write(folder/'status.json', {'status':doc['status'],'attempted_at':doc['retrieved_at'],
        'etf_count':len(doc['products']),'flow_etf_count':len({r['code'] for r in doc['flows']}),
        'failure_count':len(doc['failures']),'retained_previous':doc['status']!='SUCCESS'})

def main():
    folder=ROOT/'data/naver_etf'
    now=dt.datetime.now(dt.timezone.utc)
    today=now.astimezone(ZoneInfo('Asia/Seoul')).date()
    products=[]; records=[]; sources=[]; failures=[]
    try:
        d, source=request(LIST,folder); sources.append(source); products=listing(d)
        targets=[r for r in products if r['name'].startswith('RISE ')]
        if not targets: raise ValueError('NO_RISE')
        def collect(r):
            time.sleep(.5)
            d,s=request(DETAIL.format(r['code']),folder)
            return flows(d,r['code'],today),s
        with ThreadPoolExecutor(max_workers=3) as pool:
            jobs={pool.submit(collect,r):r['code'] for r in targets}
            for job in as_completed(jobs):
                try:
                    rows,source=job.result();records.extend(rows);sources.append(source)
                except Exception as exc:
                    failures.append({'code':jobs[job],'reason':type(exc).__name__})
    except Exception as exc:
        failures.append({'code':None,'reason':type(exc).__name__})
    state='SUCCESS' if not failures and records else 'PARTIAL' if records else 'FAILED'
    doc={'schema':'NAVER_ETF_DAILY_V1','status':state,'retrieved_at':now.isoformat(),
         'capture_date_kst':str(today),'products':products,
         'flows':sorted(records,key=lambda r:(r['code'],r['observation_date'])),
         'sources':sorted(sources,key=lambda r:r['url']),'failures':failures,
         'limitations':['목록은 조회 시점 스냅샷, 시장 기준일 미제공','수급은 순매수 수량(주), 금액·설정환매와 다름','KRX를 대체하지 않는 보조자료']}
    publish(folder,doc)
    database(folder,ROOT/'var/naver_etf.sqlite')
    if state!='SUCCESS': raise SystemExit(1)

if __name__=='__main__':
    main()

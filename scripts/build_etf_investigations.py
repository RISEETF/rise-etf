"""Bounded research triage from validated KRX observations; never a trading signal.

No web login or PDF download is attempted. Missing holdings always remain pending.
"""
import argparse
import datetime as dt
import hashlib
import json
import math
import sqlite3
from pathlib import Path
from statistics import mean
from zoneinfo import ZoneInfo
from collect_krx_etf import write_json_atomic

RULES = {'version': 'ETF_TRIAGE_RESEARCH_V1', 'price_abs_pct': 5,
         'nav_gap_abs_pct': 2, 'volume_multiple': 3, 'baseline_sessions': 20,
         'daily_limit': 5, 'status': 'UNCALIBRATED_RESEARCH_ONLY'}


def build(db_path, receipt, today):
    day = receipt['observation_date']
    age = (today - dt.date.fromisoformat(day)).days
    if receipt.get('status') != 'SUCCESS' or not 0 <= age <= 7:
        raise ValueError('INVALID_COLLECTION_RECEIPT')
    with sqlite3.connect(f'file:{Path(db_path).resolve()}?mode=ro', uri=True) as db:
        db.row_factory = sqlite3.Row
        if db.execute('select max(observation_date) from snapshots').fetchone()[0] != day:
            raise ValueError('DATABASE_RECEIPT_DATE_MISMATCH')
        dates = [r[0] for r in db.execute(
            'select distinct observation_date from snapshots where observation_date<=? order by observation_date desc limit 21', (day,))]
        rows = db.execute('''select * from (
          select *, row_number() over(partition by observation_date,ticker,field
          order by retrieved_at desc, rowid desc) as rank from snapshots
          where observation_date>=? and observation_date<=?) where rank=1''', (dates[-1], day)).fetchall()
    series, names = {}, {}
    for r in rows:
        value = r['value']
        if not isinstance(value, (float,int)) or not math.isfinite(value) or value < 0:
            raise ValueError('INVALID_DATABASE_VALUE')
        series.setdefault(r['ticker'], {}).setdefault(r['observation_date'], {})[r['field']] = value
        if r['observation_date'] == day:
            names[r['ticker']] = r['name']
    if len(names) != receipt['record_count']:
        raise ValueError('DATABASE_RECEIPT_COUNT_MISMATCH')
    candidates, coverage = [], {'price': 0, 'nav_gap': 0, 'volume': 0}
    previous = dates[1] if len(dates)>1 else None
    for ticker in sorted(names):
        history = series[ticker]; current = history[day]; prior = history.get(previous, {})
        signals = []
        if current.get('close', 0)>0 and prior.get('close', 0)>0:
            change = (current['close']/prior['close']-1)*100
            coverage['price'] += 1
            if abs(change)>=RULES['price_abs_pct']:
                signals.append({'kind':'PRICE_MOVE', 'value':round(change,4), 'unit':'%', 'prior_date':previous})
        if current.get('close',0)>0 and current.get('nav',0)>0:
            gap = (current['close']/current['nav']-1)*100
            coverage['nav_gap'] += 1
            if abs(gap)>=RULES['nav_gap_abs_pct']:
                signals.append({'kind':'NAV_GAP', 'value':round(gap,4), 'unit':'%'})
        # Require all 20 preceding market observation dates; never include today.
        volumes = [history.get(d,{}).get('volume') for d in dates[1:]]
        if len(volumes)==20 and all(v is not None for v in volumes) and mean(volumes)>0 and current.get('volume') is not None:
            coverage['volume'] += 1
            multiple = current['volume']/mean(volumes)
            if multiple>=RULES['volume_multiple']:
                signals.append({'kind':'VOLUME_SPIKE','value':round(multiple,4),'unit':'x','baseline_sessions':20})
        if signals:
            candidates.append({'ticker':ticker, 'name':names[ticker], 'observation_date':day,
                'signals':signals, 'state':'PDF_PENDING', 'holdings_verified':False,
                'pdf_request':{'ticker':ticker,'requested_date':day,'source':'KRX',
                    'instruction':'KRX 로그인 → ETF PDF → 종목코드·기준일 선택 → 다운로드'}})
    thresholds={'PRICE_MOVE':5,'NAV_GAP':2,'VOLUME_SPIKE':3}
    candidates.sort(key=lambda r:(-len(r['signals']),-max(abs(s['value'])/thresholds[s['kind']] for s in r['signals']),r['ticker']))
    return {'schema':'ETF_INVESTIGATION_QUEUE_V1','rules':RULES,'source':'KRX_OPEN_API_ETF_DAILY',
        'observation_date':day,'source_retrieved_at':receipt['retrieved_at'],
        'source_raw_sha256':receipt['raw_sha256'],'screened_count':len(names),
        'metric_coverage':coverage,'candidate_count':len(candidates),
        'deferred_count':max(0,len(candidates)-RULES['daily_limit']),
        'items':candidates[:RULES['daily_limit']],
        'limitations':['조사 우선순위용 임시 기준이며 검증된 매매신호가 아닙니다.',
          '가격은 비조정 종가입니다. 분배·분할·병합·레버리지 및 시장 전체 변동을 먼저 확인하세요.',
          '해외자산 NAV와 국내 종가의 시차는 괴리의 원인이 될 수 있습니다.',
          '거래량 증가를 투자자 순유입으로 해석하지 않습니다. PDF 확보 전 구성자산 원인은 미확인입니다.']}


def publish(document, output):
    output=Path(output)
    if output.exists() and json.loads(output.read_text())['observation_date']>document['observation_date']:
        raise ValueError('QUEUE_DATE_REGRESSION')
    digest=hashlib.sha256(json.dumps(document,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
    history=output.parent/'history'/document['observation_date']/f'{digest}.json'
    if not history.exists(): write_json_atomic(history,document)
    write_json_atomic(output,document)


def main():
    p=argparse.ArgumentParser();p.add_argument('--db',default='var/krx_etf.sqlite')
    p.add_argument('--receipt',default='var/krx-output/receipt.json')
    p.add_argument('--output',default='data/etf_investigations/latest.json')
    args=p.parse_args(); status=Path(args.output).parent/'status.json'
    stamp=dt.datetime.now(dt.timezone.utc).isoformat()
    try:
        receipt=json.loads(Path(args.receipt).read_text())
        doc=build(args.db,receipt,dt.datetime.now(ZoneInfo('Asia/Seoul')).date())
        publish(doc,args.output)
        write_json_atomic(status,{'status':'SUCCESS','attempted_at':stamp,'last_success_at':stamp,'observation_date':doc['observation_date']})
        print(json.dumps({'status':'SUCCESS','screened':doc['screened_count'],'candidates':doc['candidate_count'],'selected':len(doc['items'])}))
    except Exception as exc:
        prior=json.loads(status.read_text()) if status.exists() else {}
        write_json_atomic(status,{'status':'FAILED','attempted_at':stamp,'last_success_at':prior.get('last_success_at'),'reason':type(exc).__name__,'last_good_preserved':True})
        raise

if __name__=='__main__':main()

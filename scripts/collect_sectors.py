#!/usr/bin/env python3
"""Collect sector candidates separately from the integrated RS selection pool."""
import datetime as dt
import json
import statistics
import time
from zoneinfo import ZoneInfo
from collect_overseas import capture_overseas
from update_daily import ROOT, write_json

def summarize(records, groups, now, horizon=30):
    today = now.astimezone(ZoneInfo('America/New_York')).date().isoformat()
    prices = {code: {r['date']: r for r in rec.get('observations', []) if r['date'] < today}
              for code, rec in records.items() if rec.get('status') == 'CAPTURED'}
    requested = ['SPY'] + [g[k] for g in groups for k in ('primary', 'peer')]
    common = set.intersection(*(set(prices.get(c, {})) for c in requested))
    end = max(common) if common else None
    target = (dt.date.fromisoformat(end)-dt.timedelta(days=horizon)).isoformat() if end else None
    starts = [d for d in common if target and (dt.date.fromisoformat(target)-dt.timedelta(days=7)).isoformat() <= d <= target]
    start = max(starts) if starts else None
    rows = []
    for group in groups:
        for role in ('primary', 'peer'):
            code = group[role]
            rec = records.get(code, {})
            p = prices.get(code, {})
            row = {'sector':group['name'], 'code':code, 'role':role, 'status':rec.get('status','NOT_ATTEMPTED'),
                   'last_date':max(p) if p else None, 'return_pct':None, 'rs_vs_spy_pct':None,
                   'median_close_times_volume_usd':None, 'volume_sessions':0,
                   'source_sha256':rec.get('source_sha256'), 'error':rec.get('error')}
            volume_days = sorted(d for d in common if end and d <= end)[-20:]
            row['volume_sessions'] = len(volume_days)
            if len(volume_days) == 20:
                row['median_close_times_volume_usd'] = statistics.median(p[d]['close']*p[d]['volume'] for d in volume_days)
            if start and end:
                splits = [e for c in (code,'SPY') for e in records[c].get('events',[])
                          if e['kind']=='SPLIT' and start < e['date'] <= end]
                if splits:
                    row['comparison_status']='SPLIT_IN_WINDOW'
                else:
                    gross = p[end]['close']/p[start]['close']
                    benchmark = prices['SPY'][end]['close']/prices['SPY'][start]['close']
                    row.update(return_pct=100*(gross-1), rs_vs_spy_pct=100*(gross/benchmark-1),
                               comparison_status='RESEARCH_PRICE_ONLY')
            else:
                row['comparison_status']='COMMON_PERIOD_UNAVAILABLE'
            rows.append(row)
    return {'schema_version':1, 'calendar_days':horizon, 'built_at':now.isoformat(), 'start_date':start,'end_date':end,
            'requested_count':len(requested), 'captured_count':len(prices), 'rows':rows,
            'currency':'USD', 'production_eligible':False,
            'note':'모든 후보와 SPY의 동일 날짜 비교. 분배금 미반영 종가 수익률. 종가×거래량은 거래대금 근사치이며 호가 스프레드·추적오차가 아님.'}

def publish_result(result, directory):
    """Keep a complete comparable snapshot when a later attempt is unusable."""
    directory.mkdir(parents=True, exist_ok=True)
    good = (result['captured_count'] == result['requested_count']
            and result.get('start_date') and result.get('end_date'))
    write_json(directory/'attempt.json', result)
    write_json(directory/'status.json', {
        'status': 'SUCCESS' if good else 'FAILED',
        'attempted_at': result['built_at'],
        'captured_count': result['captured_count'],
        'requested_count': result['requested_count'],
        'reason': None if good else 'INCOMPLETE_OR_UNALIGNED_CAPTURE',
        'display_policy': 'LAST_COMPLETE_SNAPSHOT',
    })
    if good or not (directory/'latest.json').exists():
        write_json(directory/'latest.json', result)
    return bool(good)

def main():
    now=dt.datetime.now(dt.timezone.utc)
    groups=json.loads((ROOT/'data/universe/discovery.json').read_text())['groups']['EQUITY_SECTORS']
    config=json.loads((ROOT/'data/overseas_sources.json').read_text())
    config['url_template']=config['url_template'].replace('range=2y','range=6mo')
    records={}
    for code in ['SPY']+[g[k] for g in groups for k in ('primary','peer')]:
        item={'code':code,'name':code,'market':'US_LISTED','currency':'USD','instrument_type':'ETF','timezone':'America/New_York','exclude_current_session':True}
        rec=capture_overseas(ROOT/'data/sector_series',config,item,now=now)
        records[code]=rec
        if rec.get('http_status') in (401,403,429):
            break
        time.sleep(0.5)
    result=summarize(records,groups,now)
    result["windows"] = [summarize(records,groups,now,horizon) for horizon in (7,30,90)]
    published = publish_result(result, ROOT/'data/sector_series')
    print(json.dumps({'captured':result['captured_count'],'requested':result['requested_count'],'end':result['end_date']}))
    return 0 if published else 1
if __name__=='__main__':
    raise SystemExit(main())

#!/usr/bin/env python3
"""Exploratory close-price relative strength, separate from validated selection."""
import argparse
import datetime as dt
import math
from pathlib import Path
import json
from query_asof import snapshot, timestamp
from update_daily import ROOT, write_json


def calculate(data, instruments, horizons=(7, 30, 60), benchmark='US_LISTED:SPY'):
    cutoff = timestamp(data['decision_time_utc'])
    if data['status'] != 'CAPTURE_TIME_FILTER_ONLY':
        raise ValueError('Expected captured vintage snapshot')
    configs = {r['market']+':'+r['code']: r for r in instruments}
    if len(configs) != len(instruments) or benchmark not in configs:
        raise ValueError('Duplicate instrument or missing benchmark')
    if any(r['currency'] not in ('USD', 'KRW') for r in instruments):
        raise ValueError('Unsupported currency')
    def observations(rows, field):
        result = {}
        for row in rows:
            day = row['observation_date']
            value = row[field]
            if day in result or not math.isfinite(value) or value <= 0:
                raise ValueError('Duplicate date or invalid value')
            if dt.date.fromisoformat(day) > cutoff.date():
                continue
            result[day] = value
        return result
    captured = {}
    for item in data['prices']:
        key = item['instrument_id']
        if key in captured:
            raise ValueError('Duplicate instrument snapshot')
        if timestamp(item['capture']['retrieved_at']) > cutoff:
            raise ValueError('Capture after cutoff')
        captured[key] = item
    prices = {key: observations(captured[key]['prices'], 'close') if key in captured else {} for key in configs}
    fx_data = data.get('fx')
    if fx_data and fx_data['capture']['source_id'] != 'ECB_REFERENCE':
        raise ValueError('Expected ECB reference FX source')
    if fx_data and timestamp(fx_data['capture']['retrieved_at']) > cutoff:
        raise ValueError('FX capture after cutoff')
    fx = observations([r for r in fx_data['observations'] if r['base']=='USD' and r['quote']=='KRW'], 'rate') if fx_data else {}
    common = set(fx)
    for rows in prices.values():
        common &= set(rows)
    end = max(common) if common else None
    result = {'schema_version': 1, 'status': 'EXPLORATORY_PRICE_RS',
              'decision_time_utc': cutoff.isoformat(), 'benchmark': benchmark,
              'price_field': 'close', 'fx_basis': 'ECB_REFERENCE_NOT_CLOSE',
              'production_eligible': False, 'representative_selection_changed': False,
              'endpoint_rule': 'SAME_DATE_INTERSECTION_ALL_REQUESTED_PRICES_AND_FX',
              'latest_common_date': end,
              'source_age_calendar_days': (cutoff.date()-dt.date.fromisoformat(end)).days if end else None,
              'sources': [{'instrument_id': k, 'name': c['name'], 'currency': c['currency'],
                           'capture': captured[k]['capture'] if k in captured else None,
                           'latest_price_date': max(prices[k]) if prices[k] else None} for k,c in configs.items()],
              'fx_capture': fx_data['capture'] if fx_data else None,
              'windows': [],
              'limits': ['Close-price changes, not total returns; distributions are not reinvested.',
                         'Domestic adjustment basis is unconfirmed; provider close corporate-action handling is not independently verified.',
                         'Same date labels are not simultaneous closes; no benchmark T-1 shift is applied.',
                         'ECB reference rates are not closing or executable rates. No forward fill.',
                         'Ranks describe this pilot pool, not the market or approved representatives.',
                         'Historical rows are a captured vintage, not historical publication-time backtests.']}
    for days in horizons:
        if not isinstance(days, int) or days <= 0:
            raise ValueError('Horizon must be a positive calendar-day count')
        window = {'calendar_days': days, 'start_date': None, 'end_date': end, 'rows': [], 'status': 'INSUFFICIENT_COMMON_DATA'}
        result['windows'].append(window)
        if not end:
            continue
        target = dt.date.fromisoformat(end)-dt.timedelta(days=days)
        starts = [d for d in common if 0 <= (target-dt.date.fromisoformat(d)).days <= 7]
        if not starts:
            continue
        start = max(starts)
        window.update(start_date=start, actual_calendar_days=(dt.date.fromisoformat(end)-dt.date.fromisoformat(start)).days)
        # Split handling is not independently verified; conservatively withhold the pool.
        splits = [key for key in configs if any(e['kind']=='SPLIT' and start < e['observation_date'] <= end
                  for e in captured[key].get('corporate_actions', []))]
        if splits:
            window.update(status='KNOWN_SPLIT_IN_WINDOW', split_instruments=splits)
            continue
        gross = {}
        for key, config in configs.items():
            local = prices[key][end]/prices[key][start]
            fx_gross = fx[end]/fx[start] if config['currency']=='USD' else 1.0
            gross[key] = (local, local*fx_gross, fx_gross)
        rows = []
        for key, (local, krw, fx_gross) in gross.items():
            rows.append({'instrument_id':key, 'name':configs[key]['name'], 'currency':configs[key]['currency'],
                         'local_return_pct':100*(local-1), 'krw_return_pct':100*(krw-1),
                         'fx_return_pct':100*(fx_gross-1),
                         'local_rs_vs_spy_pct':100*(local/gross[benchmark][0]-1),
                         'krw_rs_vs_spy_pct':100*(krw/gross[benchmark][1]-1),
                         'start_close':prices[key][start], 'end_close':prices[key][end],
                         'start_fx':fx[start] if configs[key]['currency']=='USD' else 1,
                         'end_fx':fx[end] if configs[key]['currency']=='USD' else 1})
        for row in rows:
            for basis in ('local', 'krw'):
                row[basis+'_rank'] = 1+sum(round(other[basis+'_return_pct'],10)>round(row[basis+'_return_pct'],10) for other in rows)
        window.update(status='CALCULATED_RESEARCH_ONLY', rows=sorted(rows,key=lambda r:(r['krw_rank'],r['instrument_id'])))
    return result


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', default=str(ROOT/'var/research.sqlite'))
    parser.add_argument('--cutoff', help='Timezone-aware timestamp; defaults to current UTC time')
    parser.add_argument('--output', default=str(ROOT/'data/research/rs.json'))
    args=parser.parse_args()
    instruments=json.loads((ROOT/'data/series_sources.json').read_text())['price_instruments']+json.loads((ROOT/'data/overseas_sources.json').read_text())['instruments']
    result=calculate(snapshot(args.db,args.cutoff or dt.datetime.now(dt.timezone.utc).isoformat()),instruments)
    write_json(Path(args.output),result)
    print(json.dumps({'status':result['status'],'end':result['latest_common_date'],
                      'windows':[{'days':w['calendar_days'],'status':w['status'],'rows':len(w['rows'])} for w in result['windows']]}))

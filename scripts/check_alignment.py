#!/usr/bin/env python3
"""Diagnose date-label overlap; never approve simultaneous market observations."""
import argparse
import datetime as dt
import json
from pathlib import Path
from query_asof import snapshot


def diagnose(data, instrument_ids, start, end):
    first, last = dt.date.fromisoformat(start), dt.date.fromisoformat(end)
    if first > last or len(instrument_ids) < 2 or len(set(instrument_ids)) != len(instrument_ids):
        raise ValueError('Use an ordered date interval and at least two distinct instrument IDs')
    if data['rs_status'] != 'BLOCKED' or data['status'] != 'CAPTURE_TIME_FILTER_ONLY':
        raise ValueError('Expected a capture-time research snapshot')
    def dates(rows):
        values = [r['observation_date'] for r in rows]
        if len(values) != len(set(values)):
            raise ValueError('Duplicate observation date')
        return {value for value in values if first <= dt.date.fromisoformat(value) <= last}
    by_id = {}
    for item in data['prices']:
        if item['instrument_id'] in by_id:
            raise ValueError('Duplicate instrument snapshot')
        by_id[item['instrument_id']] = item
    sets = {key: dates(by_id[key]['prices']) if key in by_id else set() for key in instrument_ids}
    union = set().union(*sets.values())
    common = set.intersection(*sets.values())
    fx = data.get('fx')
    fx_dates = dates([r for r in fx['observations'] if r['base'] == 'USD' and r['quote'] == 'KRW']) if fx else set()
    records = []
    for key, values in sets.items():
        capture = by_id[key]['capture'] if key in by_id else None
        records.append({'instrument_id': key, 'capture_id': capture['capture_id'] if capture else None,
                        'retrieved_at': capture['retrieved_at'] if capture else None,
                        'observation_count': len(values), 'first_date': min(values) if values else None,
                        'last_date': max(values) if values else None,
                        'absent_dates_relative_to_price_union': sorted(union - values)})
    return {'status': 'DATE_LABEL_DIAGNOSTIC_ONLY', 'decision_time_utc': data['decision_time_utc'],
            'window': {'start': start, 'end': end}, 'instruments': records,
            'missing_instruments': [key for key in instrument_ids if key not in by_id],
            'price_union_count': len(union), 'common_price_dates': sorted(common),
            'fx_capture_id': fx['capture']['capture_id'] if fx else None,
            'fx_pair': 'USD/KRW', 'fx_observation_count': len(fx_dates),
            'common_price_and_fx_dates': sorted(common & fx_dates),
            'common_price_dates_without_fx': sorted(common - fx_dates),
            'simultaneity_verified': False, 'rs_status': 'BLOCKED', 'ranking': None,
            'blockers': ['SESSION_CLOSE_FINALITY_UNVERIFIED', 'EXCHANGE_CALENDARS_UNVERIFIED',
                         'BENCHMARK_LAG_AND_FX_FIXING_UNRESOLVED', 'TOTAL_RETURN_COMPARABILITY_UNVERIFIED'],
            'limits': ['Absent dates are relative to observed price dates, not an exchange holiday calendar.',
                       'Matching date labels do not prove matching information times.',
                       'No fill, date shift, FX conversion or return calculation is performed.',
                       'USD/KRW coverage is diagnostic only; the query does not infer currency exposure.']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', default=str(Path(__file__).resolve().parents[1] / 'var/research.sqlite'))
    parser.add_argument('--cutoff', required=True)
    parser.add_argument('--instrument', action='append', required=True)
    parser.add_argument('--start', required=True)
    parser.add_argument('--end', required=True)
    args = parser.parse_args()
    print(json.dumps(diagnose(snapshot(args.db, args.cutoff), args.instrument, args.start, args.end), ensure_ascii=False))

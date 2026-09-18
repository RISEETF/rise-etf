#!/usr/bin/env python3
"""Read coherent captured vintages available by an explicit decision cutoff."""
import argparse
import datetime as dt
import json
from pathlib import Path
import sqlite3


def timestamp(value):
    result = dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError('An explicit timezone offset is required')
    return result.astimezone(dt.timezone.utc)


def snapshot(db_path, cutoff):
    decision_time = timestamp(cutoff)
    connection = sqlite3.connect(Path(db_path).resolve().as_uri() + '?mode=ro', uri=True)
    connection.row_factory = sqlite3.Row
    try:
        available = {}
        for row in connection.execute("SELECT * FROM captures WHERE status='CAPTURED'"):
            captured = timestamp(row['retrieved_at'])
            if captured <= decision_time:
                available[row['capture_id']] = (captured, dict(row))
        # Select whole snapshots, never patch missing rows with an older capture.
        chosen = {}
        for row in connection.execute('SELECT DISTINCT instrument_id,capture_id FROM prices'):
            if row['capture_id'] not in available:
                continue
            key = (available[row['capture_id']][0], row['capture_id'])
            if row['instrument_id'] not in chosen or key > chosen[row['instrument_id']][0]:
                chosen[row['instrument_id']] = (key, row['capture_id'])
        prices = []
        for instrument, (_, capture_id) in sorted(chosen.items()):
            capture = available[capture_id][1]
            rows = [dict(r) for r in connection.execute(
                'SELECT * FROM prices WHERE capture_id=? AND instrument_id=? ORDER BY observation_date',
                (capture_id, instrument))]
            events = [dict(r) for r in connection.execute(
                'SELECT * FROM corporate_actions WHERE capture_id=? AND instrument_id=? ORDER BY observation_date,event_id',
                (capture_id, instrument))]
            prices.append({'instrument_id': instrument, 'capture': capture, 'prices': rows,
                           'corporate_actions': events, 'rs_eligible': False})
        fx_ids = {r[0] for r in connection.execute('SELECT DISTINCT capture_id FROM fx')}
        fx_candidates = [(available[cid][0], cid) for cid in fx_ids if cid in available]
        fx = None
        if fx_candidates:
            _, cid = max(fx_candidates)
            fx = {'capture': available[cid][1], 'observations': [dict(r) for r in connection.execute(
                'SELECT * FROM fx WHERE capture_id=? ORDER BY observation_date,base,quote', (cid,))]}
        return {'decision_time_utc': decision_time.isoformat(), 'status': 'CAPTURE_TIME_FILTER_ONLY',
                'selection_rule': 'LATEST_SUCCESSFUL_NONEMPTY_SNAPSHOT_PER_INSTRUMENT',
                'prices': prices, 'fx': fx, 'rs_status': 'BLOCKED', 'ranking': None,
                'limits': ['Retrieval time is not original publication time.',
                           'Current names, memberships and representative selections are not backdated.',
                           'Missing rows are not filled from earlier snapshots; failed attempts are not described by this query.',
                           'Session close finality and cross-market/FX alignment remain unverified.',
                           'These are captured research vintages, not a validated historical investment universe.']}
    finally:
        connection.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', default=str(Path(__file__).resolve().parents[1] / 'var/research.sqlite'))
    parser.add_argument('--cutoff', required=True, help='ISO timestamp including timezone offset')
    args = parser.parse_args()
    print(json.dumps(snapshot(args.db, args.cutoff), ensure_ascii=False))

"""Fetch only missing return endpoints using the existing authenticated collector.

Does not change the current inventory/receipt or manufacture a daily time series.
All successful raw responses and revisions are preserved in the existing ledger.
"""
import argparse
import datetime as dt
import hashlib
import json
import os
import sqlite3
import tempfile
from pathlib import Path
from collect_krx_etf import fetch_latest, validate_completeness, accumulate, write_json_atomic, safe_reason
from build_etf_market_metrics import target_date


def backfill(db_path, receipt, auth_key, output):
    if receipt.get('status') != 'SUCCESS' or not auth_key:
        raise ValueError('BASELINE_SOURCE_UNAVAILABLE')
    day = dt.date.fromisoformat(receipt['observation_date'])
    stamp = dt.datetime.now(dt.timezone.utc).isoformat()
    output = Path(output)
    with sqlite3.connect(db_path) as db:
        if db.execute('select max(observation_date) from snapshots').fetchone()[0] != day.isoformat():
            raise ValueError('BASELINE_CURRENT_DATE_MISMATCH')
        db.execute('''create table if not exists return_baseline_requests
          (target_date text primary key, observation_date text not null,
           raw_sha256 text not null, retrieved_at text not null)''')
        cached = {r[0] for r in db.execute('select target_date from return_baseline_requests')}
        dates = {r[0] for r in db.execute('select distinct observation_date from snapshots')}
    results = []
    # Four bounded endpoint requests; collector permits at most eight calendar-date attempts each.
    for period in ('1W', '1M', '3M', 'YTD'):
        target = target_date(day, period)
        result = {'period': period, 'target_date': target.isoformat()}
        if target.isoformat() in cached or target.isoformat() in dates:
            results.append(dict(result, status='ALREADY_CAPTURED'))
            continue
        try:
            # A closed-market date can return identities with all prices empty.
            # Keep the collector's eight-date bound and validate before accepting a date.
            with tempfile.TemporaryDirectory() as tmp:
                raw, fetched = fetch_latest(auth_key, target, snapshot_validator=lambda snapshot, requested:
                    validate_completeness(Path(tmp)/'no_prior.sqlite', snapshot, requested))
            snapshot = fetched['snapshot']
            if not 0 <= (target-dt.date.fromisoformat(snapshot['page_date'])).days <= 7:
                raise ValueError('BASELINE_DATE_INVALID')
            digest = hashlib.sha256(raw).hexdigest()
            raw_path = output/snapshot['page_date']/f'{digest}.json'
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            if not raw_path.exists():raw_path.write_bytes(raw)
            # Retain even rejected raw responses for diagnosis, never in the price view.
            # Historical universe size must not be compared with today's larger universe.
            with tempfile.TemporaryDirectory() as tmp:
                validate_completeness(Path(tmp)/'no_prior.sqlite', snapshot, target)
            delta = accumulate(Path(db_path), snapshot, digest, stamp)
            with sqlite3.connect(db_path) as db:
                db.execute('insert or replace into return_baseline_requests values(?,?,?,?)',
                           (target.isoformat(), snapshot['page_date'], digest, stamp))
            results.append(dict(result, status='SUCCESS', observation_date=snapshot['page_date'],
                                raw_sha256=digest, record_count=len(snapshot['records']), delta=delta))
        except Exception as exc:
            # Never publish raw exception strings, URLs with keys, or request headers.
            results.append(dict(result, status='FAILED', reason=safe_reason(exc),
                                **({'quality': exc.quality_evidence} if hasattr(exc, 'quality_evidence') else {})))
    return {'status': 'PARTIAL' if any(r['status']=='FAILED' for r in results) else 'SUCCESS',
            'attempted_at': stamp, 'current_observation_date': day.isoformat(), 'items': results,
            'scope': 'RETURN_ENDPOINTS_ONLY_NOT_CONTINUOUS_HISTORY'}


if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('--db',default='var/krx_etf.sqlite')
    p.add_argument('--receipt',default='var/krx-output/receipt.json')
    p.add_argument('--output',default='var/krx-output/baselines')
    p.add_argument('--status',default='data/etf_market/baseline_status.json')
    a=p.parse_args()
    result=backfill(a.db,json.loads(Path(a.receipt).read_text()),os.environ.get('KRX_AUTH_KEY','').strip(),a.output)
    write_json_atomic(a.status,result)
    print(json.dumps(result))

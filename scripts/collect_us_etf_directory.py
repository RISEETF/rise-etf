#!/usr/bin/env python3
"""Nasdaq directory snapshots: ETF-flagged securities, not a verified fund universe."""
import argparse
import csv
import datetime as dt
import hashlib
import io
import json
from pathlib import Path
import sqlite3
import urllib.request
from zoneinfo import ZoneInfo
from process_etf_provider_inbox import atomic, private_output

FILES = ('nasdaqlisted', 'otherlisted')
BASE = 'https://www.nasdaqtrader.com/dynamic/SymDir/'
MAX_BYTES = 5_000_000


def parse(raw, kind, today):
    lines = raw.decode('utf-8-sig').strip().splitlines()
    if not lines or not lines[-1].startswith('File Creation Time: '):
        raise ValueError('MISSING_CREATION_FOOTER')
    stamp = lines[-1].split('|')[0].removeprefix('File Creation Time: ').strip()
    created = dt.datetime.strptime(stamp, '%m%d%Y%H:%M')
    age = (today - created.date()).days
    if age < 0 or age > 7:
        raise ValueError('FUTURE_OR_STALE_DIRECTORY')
    reader = csv.DictReader(io.StringIO('\n'.join(lines[:-1])), delimiter='|')
    symbol = 'Symbol' if kind == 'nasdaqlisted' else 'ACT Symbol'
    required = {symbol, 'Security Name', 'ETF', 'Test Issue'}
    if kind == 'otherlisted': required.add('Exchange')
    if not required.issubset(reader.fieldnames or []):
        raise ValueError('DIRECTORY_SCHEMA_CHANGED')
    result, seen = [], set()
    for row in reader:
        if None in row or any(v is None for v in row.values()):
            raise ValueError('MALFORMED_ROW')
        ticker = row[symbol].strip()
        if not ticker or ticker in seen or not row['Security Name'].strip():
            raise ValueError('EMPTY_OR_DUPLICATE_SECURITY')
        seen.add(ticker)
        if row['ETF'] not in ('Y', 'N') or row['Test Issue'] not in ('Y', 'N'):
            raise ValueError('INVALID_FLAG')
        if row['ETF'] == 'Y' and row['Test Issue'] == 'N':
            result.append({'symbol': ticker, 'name': row['Security Name'],
                           'exchange': 'Q' if kind == 'nasdaqlisted' else row['Exchange'],
                           'source_file': kind, 'source_row': row})
    if not result: raise ValueError('EMPTY_ETF_DIRECTORY')
    return {'file_created_local': created.isoformat(), 'timezone': None,
            'directory_date': created.date().isoformat(), 'rows': result}


def fetch(kind):
    with urllib.request.urlopen(BASE + kind + '.txt', timeout=30) as response:
        raw = response.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES: raise ValueError('FILE_TOO_LARGE')
    return raw


def run(output, loader=fetch, clock=None):
    output = private_output(Path(output)); output.mkdir(parents=True, exist_ok=True)
    now = clock or dt.datetime.now(dt.timezone.utc)
    today = now.astimezone(ZoneInfo('America/New_York')).date()
    status_path = output/'status.json'
    old = json.loads(status_path.read_text()) if status_path.exists() else {}
    status = {'attempted_at': now.isoformat(), 'last_success_at': old.get('last_success_at'),
              'status': 'FAILED', 'source': BASE, 'scope': 'ETF_FLAGGED_DIRECTORY_SECURITIES'}
    try:
        with sqlite3.connect(output/'history.sqlite', timeout=30) as db:
            db.execute('CREATE TABLE IF NOT EXISTS snapshots (digest TEXT PRIMARY KEY, received TEXT, payload TEXT)')
            db.execute('CREATE TABLE IF NOT EXISTS state (id INTEGER PRIMARY KEY CHECK(id=1), digest TEXT)')
            db.execute('BEGIN IMMEDIATE')
            parsed, hashes = {}, {}
            for kind in FILES:
                raw = loader(kind)
                if len(raw) > MAX_BYTES: raise ValueError('FILE_TOO_LARGE')
                digest = hashlib.sha256(raw).hexdigest(); hashes[kind] = digest
                archive = output/'raw'/digest/(kind+'.txt'); archive.parent.mkdir(parents=True, exist_ok=True)
                if archive.exists() and archive.read_bytes() != raw: raise ValueError('RAW_HASH_CONFLICT')
                if not archive.exists(): archive.write_bytes(raw)
                parsed[kind] = parse(raw, kind, today)
            dates = {p['directory_date'] for p in parsed.values()}
            if len(dates) != 1: raise ValueError('SOURCE_DATES_DIFFER')
            rows = sorted([r for p in parsed.values() for r in p['rows']], key=lambda r:r['symbol'])
            keyed = {r['symbol']: r for r in rows}
            if len(keyed) != len(rows): raise ValueError('CROSS_FILE_DUPLICATE')
            digest = hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()
            previous = db.execute('SELECT payload FROM snapshots JOIN state USING(digest) WHERE id=1').fetchone()
            prior = json.loads(previous[0]) if previous else None
            date = next(iter(dates))
            if prior and date < prior['directory_date']: raise ValueError('DIRECTORY_DATE_REGRESSION')
            before = {r['symbol']:r for r in prior['rows']} if prior else {}
            if prior and len(rows) < len(before)*0.8: raise ValueError('LARGE_UNIVERSE_DROP_REVIEW_REQUIRED')
            payload = {'digest':digest, 'retrieved_at_utc':now.isoformat(), 'directory_date':date,
                       'source_metadata':{k:{f:v for f,v in p.items() if f!='rows'} for k,p in parsed.items()},
                       'source_hashes':hashes, 'count':len(rows), 'rows':rows,
                       'scope':'ETF_FLAGGED_DIRECTORY_SECURITIES', 'price_data_available':False,
                       'changes': {'baseline':prior is None, 'added_candidates':sorted(keyed.keys()-before.keys()) if prior else [],
                                   'missing_candidates':sorted(before.keys()-keyed.keys()),
                                   'changed':sorted(k for k in keyed.keys()&before.keys() if keyed[k]!=before[k])}}
            duplicate = db.execute('SELECT 1 FROM snapshots WHERE digest=?',(digest,)).fetchone() is not None
            db.execute('INSERT OR IGNORE INTO snapshots VALUES (?,?,?)',(digest,now.isoformat(),json.dumps(payload,ensure_ascii=False)))
            db.execute('INSERT OR REPLACE INTO state VALUES (1,?)',(digest,))
            db.commit()
            latest = db.execute('SELECT payload FROM snapshots JOIN state USING(digest) WHERE id=1').fetchone()[0]
        atomic(output/'latest.json',latest+'\n')
        status.update(status='SUCCESS', last_success_at=now.isoformat(), count=len(rows),
                      directory_date=date, duplicate=duplicate, digest=digest)
    except Exception as error:
        status['error'] = f'{type(error).__name__}: {error}'
    receipt = json.dumps(status,ensure_ascii=False,indent=2)+'\n'
    atomic(output/'runs'/(now.strftime('%Y%m%dT%H%M%S%fZ')+'.json'),receipt)
    atomic(status_path,receipt)
    return status


if __name__ == '__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--output',default='var/us_etf_directory')
    args=parser.parse_args(); result=run(args.output)
    print(json.dumps(result,ensure_ascii=False,indent=2)); raise SystemExit(0 if result['status']=='SUCCESS' else 1)

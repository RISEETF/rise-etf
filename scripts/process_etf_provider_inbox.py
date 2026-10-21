#!/usr/bin/env python3
"""Private local provider inbox. No network, credentials, or public data writes."""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import time
import uuid

from import_etf_provider_export import (MAX_BYTES, EXTENSIONS, read_rows,
    normalize_funetf_kr, inspect_funetf_kr)

REPO = Path(__file__).resolve().parents[1]


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def atomic(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=path.parent, prefix='.tmp-')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            stream.write(content)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def write_json(path, value):
    atomic(path, json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n')


def private_output(path):
    path = path.resolve()
    if path.is_relative_to(REPO) and not path.is_relative_to(REPO/'var'):
        raise ValueError('OUTPUT_MUST_BE_PRIVATE_VAR_OR_OUTSIDE_REPOSITORY')
    return path


def connect(output):
    connection = sqlite3.connect(output/'provider.sqlite')
    connection.execute('PRAGMA foreign_keys=ON')
    connection.executescript('''
      CREATE TABLE IF NOT EXISTS captures (
        digest TEXT PRIMARY KEY, retrieved_at TEXT NOT NULL, observation_date TEXT,
        screen_date TEXT, source TEXT NOT NULL, market TEXT NOT NULL,
        row_count INTEGER NOT NULL, metadata TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS observations (
        digest TEXT REFERENCES captures(digest), code TEXT, payload TEXT NOT NULL,
        PRIMARY KEY(digest, code));
      CREATE TABLE IF NOT EXISTS reconciliations (
        digest TEXT REFERENCES captures(digest), krx_hash TEXT, payload TEXT NOT NULL,
        PRIMARY KEY(digest, krx_hash));
      CREATE TABLE IF NOT EXISTS changes (
        digest TEXT REFERENCES captures(digest), previous_digest TEXT, payload TEXT NOT NULL,
        PRIMARY KEY(digest, previous_digest));
    ''')
    return connection


def metadata_for(path):
    sidecar = path.with_suffix(path.suffix+'.json')
    meta = json.loads(sidecar.read_text()) if sidecar.exists() else {}
    allowed = {'source', 'market', 'retrieved_at_utc', 'observation_date', 'screen_date'}
    if set(meta) - allowed:
        raise ValueError('UNSUPPORTED_METADATA_FIELDS_NO_CREDENTIALS_ALLOWED')
    if meta.get('source', 'funetf') != 'funetf' or meta.get('market', 'KR') != 'KR':
        raise ValueError('UNVERIFIED_PROVIDER_OR_MARKET_SCHEMA')
    for field in ('observation_date', 'screen_date'):
        if meta.get(field) and dt.date.fromisoformat(meta[field]) > dt.datetime.now(dt.timezone.utc).date()+dt.timedelta(days=1):
            raise ValueError('FUTURE_SOURCE_DATE')
    stamp = meta.get('retrieved_at_utc') or dt.datetime.fromtimestamp(path.stat().st_mtime, dt.timezone.utc).isoformat()
    parsed = dt.datetime.fromisoformat(stamp)
    if parsed.tzinfo is None or parsed > dt.datetime.now(dt.timezone.utc)+dt.timedelta(minutes=5):
        raise ValueError('INVALID_RETRIEVAL_TIMESTAMP')
    return {'source':'funetf', 'market':'KR', 'retrieved_at_utc':parsed.astimezone(dt.timezone.utc).isoformat(),
            'observation_date':meta.get('observation_date'), 'screen_date':meta.get('screen_date')}


def latest_capture(db):
    return db.execute('SELECT digest FROM captures ORDER BY COALESCE(observation_date, substr(retrieved_at,1,10)) DESC, retrieved_at DESC, digest DESC LIMIT 1').fetchone()


def payloads(db, digest):
    return {code:json.loads(body) for code, body in db.execute('SELECT code,payload FROM observations WHERE digest=? ORDER BY code', (digest,))}


def delta(previous, current):
    return {'new_in_provider':sorted(current.keys()-previous.keys()),
            'missing_in_provider':sorted(previous.keys()-current.keys()),
            'changed':[{ 'code':code,
                         'fields':[k for k in current[code] if current[code][k] != previous[code].get(k)]}
                       for code in sorted(current.keys() & previous.keys()) if current[code] != previous[code]],
            'lifecycle_status':'NOT_INFERRED_FROM_PROVIDER_ABSENCE'}


def process_file(path, inventory, output, db):
    if path.suffix.lower() not in EXTENSIONS or not 0 < path.stat().st_size <= MAX_BYTES:
        raise ValueError('FILE_INVALID')
    raw = path.read_bytes(); digest = hashlib.sha256(raw).hexdigest()
    raw_dir = output/'raw'/digest; raw_dir.mkdir(parents=True, exist_ok=True)
    raw_path = raw_dir/('original'+path.suffix.lower())
    if raw_path.exists():
        if hashlib.sha256(raw_path.read_bytes()).hexdigest() != digest:
            raise ValueError('ARCHIVE_HASH_MISMATCH')
    else:
        raw_path.write_bytes(raw)
    meta = metadata_for(path)
    # Validation consumes the immutable capture, not a possibly changing inbox file.
    report = inspect_funetf_kr(raw_path, inventory, meta['observation_date'])
    report['screen_date'] = meta['screen_date']
    records = normalize_funetf_kr(read_rows(raw_path)[0])
    old = db.execute('SELECT metadata FROM captures WHERE digest=?', (digest,)).fetchone()
    if old:
        known = json.loads(old[0])
        if (known['observation_date'], known['screen_date']) != (meta['observation_date'], meta['screen_date']):
            raise ValueError('DUPLICATE_FILE_DATE_CONFLICT')
    previous = latest_capture(db)
    with db:
        if not old:
            db.execute('INSERT INTO captures VALUES (?,?,?,?,?,?,?,?)',
                (digest, meta['retrieved_at_utc'], meta['observation_date'], meta['screen_date'],
                 'funetf', 'KR', len(records), json.dumps(meta, ensure_ascii=False)))
            db.executemany('INSERT INTO observations VALUES (?,?,?)',
                [(digest,r['code'],json.dumps(r, ensure_ascii=False, allow_nan=False)) for r in records])
            # Baseline and backfill are not new-listing events.
            if previous and latest_capture(db)[0] == digest:
                changes = delta(payloads(db, previous[0]), {r['code']:r for r in records})
                db.execute('INSERT INTO changes VALUES (?,?,?)',
                           (digest, previous[0], json.dumps(changes, ensure_ascii=False)))
        db.execute('INSERT OR IGNORE INTO reconciliations VALUES (?,?,?)',
                   (digest, inventory['raw_sha256'], json.dumps(report, ensure_ascii=False)))
    return {'file':path.name, 'status':'DUPLICATE' if old else 'IMPORTED', 'sha256':digest,
            'rows':len(records), 'reconciliation':report}


def render_private(db, output):
    current = latest_capture(db)
    if not current:
        return False
    digest = current[0]
    row = db.execute('SELECT metadata FROM captures WHERE digest=?',(digest,)).fetchone()
    reports = [json.loads(r[0]) for r in db.execute('SELECT payload FROM reconciliations WHERE digest=?',(digest,))]
    report = max(reports, key=lambda r:r['krx_observation_date'])
    change = db.execute('SELECT payload FROM changes WHERE digest=?',(digest,)).fetchone()
    document = {'schema':'RISE_PRIVATE_PROVIDER_V1', 'metadata':json.loads(row[0]), 'sha256':digest, 'reconciliation':report,
                'records':list(payloads(db,digest).values()),
                'changes':json.loads(change[0]) if change else None,
                'capture_count':db.execute('SELECT count(*) FROM captures').fetchone()[0]}
    encoded = json.dumps(document, ensure_ascii=False, allow_nan=False).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
    page = (REPO/'templates/provider_private.html').read_text().replace('__PROVIDER_DATA__',encoded)
    atomic(output/'index.html',page)
    atomic(output/'portal.json',encoded+'\n')
    return True


def run(inbox, output, inventory_path):
    output = private_output(output); output.mkdir(parents=True,exist_ok=True)
    # Exclusive creation also protects against two scheduled local watchers.
    lock = output/'.processing.lock'
    try:
        fd = os.open(lock, os.O_CREAT|os.O_EXCL|os.O_WRONLY, 0o600)
    except FileExistsError:
        raise RuntimeError('INBOX_ALREADY_RUNNING_OR_STALE_LOCK')
    os.close(fd)
    status_path = output/'status.json'
    previous = json.loads(status_path.read_text()) if status_path.exists() else {}
    receipt = {'run_id':uuid.uuid4().hex, 'started_at_utc':now(), 'status':'FAILED',
               'last_success_at_utc':previous.get('last_success_at_utc'),
               'files':[], 'public_publication':False}
    db = None
    try:
        if not inbox.is_dir():
            raise ValueError('INBOX_DIRECTORY_MISSING')
        inventory = json.loads(inventory_path.read_text())
        db = connect(output)
        for path in sorted(inbox.iterdir()):
            if path.name.startswith('~$') or path.suffix.lower() not in EXTENSIONS or not path.is_file():
                continue
            try:
                receipt['files'].append(process_file(path, inventory, output, db))
            except Exception as exc:
                # Never expose arbitrary cell content or authentication material in receipts.
                receipt['files'].append({'file':path.name,'status':'FAILED', 'reason':type(exc).__name__+':'+str(exc).split(':')[0][:100]})
        receipt['private_page_updated'] = render_private(db,output)
        failed = any(r['status']=='FAILED' for r in receipt['files'])
        receipt['status'] = 'PARTIAL' if failed and any(r['status']!='FAILED' for r in receipt['files']) else 'FAILED' if failed else 'SUCCESS' if receipt['files'] else 'NO_FILES'
        if receipt['status'] == 'SUCCESS':
            receipt['last_success_at_utc'] = now()
    except Exception as exc:
        receipt['reason'] = type(exc).__name__+':'+str(exc).split(':')[0][:100]
    finally:
        if db is not None:
            db.close()
        receipt['finished_at_utc'] = now()
        try:
            write_json(output/'runs'/(receipt['run_id']+'.json'),receipt)
            write_json(status_path,receipt)
        finally:
            lock.unlink()
    return receipt


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--inbox',type=Path,default=REPO/'var/provider_inbox')
    parser.add_argument('--output',type=Path,default=REPO/'var/provider_private')
    parser.add_argument('--krx-inventory',type=Path,default=REPO/'data/quality/krx_rise_inventory.json')
    parser.add_argument('--watch',action='store_true')
    parser.add_argument('--interval',type=int,default=60)
    args=parser.parse_args()
    if args.interval<10:
        parser.error('interval must be at least 10 seconds')
    while True:
        result=run(args.inbox,args.output,args.krx_inventory)
        print(json.dumps({'status':result['status'],'files':len(result['files']),
                          'last_success_at_utc':result['last_success_at_utc']},ensure_ascii=False),flush=True)
        if not args.watch:
            return 0 if result['status'] in ('SUCCESS','NO_FILES') else 1
        time.sleep(args.interval)

if __name__=='__main__':
    raise SystemExit(main())

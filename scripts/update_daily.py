#!/usr/bin/env python3
"""Capture source responses without converting retrieval time into a market date."""
import base64
import datetime as dt
import hashlib
import json
import math
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
SOURCE_URL = 'https://finance.naver.com/api/sise/etfItemList.nhn'

def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temporary.replace(path)

def validate_snapshot(data):
    dt.date.fromisoformat(data['date'])
    rows = data.get('items')
    if not isinstance(rows, list) or not rows:
        raise ValueError('Snapshot must contain items')
    codes = set()
    for row in rows:
        if not isinstance(row, list) or len(row) != 20:
            raise ValueError('Expected 20 fields per legacy item')
        code = str(row[0])
        if code in codes:
            raise ValueError('Duplicate instrument code: ' + code)
        codes.add(code)
    return data

def archive_snapshot(data_dir):
    """Preserve baseline under its own date. Never overwrite an existing vintage."""
    source = data_dir / 'latest.json'
    data = validate_snapshot(json.loads(source.read_text(encoding='utf-8')))
    target = data_dir / (data['date'] + '.json')
    if not target.exists():
        write_json(target, data)
    snapshots = []
    for path in sorted(data_dir.glob('????-??-??.json'), reverse=True):
        item = validate_snapshot(json.loads(path.read_text(encoding='utf-8')))
        if path.stem != item['date']:
            raise ValueError('Snapshot filename/date mismatch')
        snapshots.append({'date': item['date'], 'path': path.name})
    write_json(data_dir / 'manifest.json', {'snapshots': snapshots})

def normalize_quotes(payload):
    rows = payload.get('result', {}).get('etfItemList')
    if not isinstance(rows, list) or not rows:
        raise ValueError('Empty or invalid provider response')
    quotes, codes = [], set()
    for row in rows:
        code = str(row.get('itemcode', '')).strip()
        price = row.get('nowVal')
        if not code or code in codes or isinstance(price, bool) or not isinstance(price, (int, float)) or not math.isfinite(price) or price <= 0:
            raise ValueError('Invalid or duplicate quote')
        codes.add(code)
        quotes.append({'code': code, 'price': price, 'currency': 'KRW',
                       'observation_date': None, 'quality': 'OBSERVATION_DATE_UNCONFIRMED'})
    return quotes

def collect(data_dir, fetcher, now=None):
    now = now or dt.datetime.now(dt.timezone.utc)
    run_id = now.strftime('%Y%m%dT%H%M%S%fZ')
    status = {'retrieved_at': now.isoformat(), 'source_url': SOURCE_URL,
              'observation_date': None, 'published_to_portal': False}
    try:
        raw = fetcher()
        digest = hashlib.sha256(raw).hexdigest()
        raw_path = data_dir / 'raw' / 'naver' / (digest + '.json')
        write_json(raw_path, {'sha256': digest, 'raw_base64': base64.b64encode(raw).decode('ascii')})
        try:
            decoded = raw.decode('utf-8')
        except UnicodeDecodeError:
            decoded = raw.decode('cp949')
        payload = json.loads(decoded)
        quotes = normalize_quotes(payload)
        status.update(status='CAPTURED_UNVERIFIED', quote_count=len(quotes), sha256=digest,
                      reason='Provider observation date is not established; baseline is unchanged.')
        write_json(data_dir / 'observations' / (run_id + '.json'), {**status, 'quotes': quotes})
    except Exception as exc:
        status.update(status='FAILED', reason=type(exc).__name__ + ': ' + str(exc))
    write_json(data_dir / 'runs' / (run_id + '.json'), status)
    write_json(data_dir / 'collection_status.json', status)
    return status

def fetch_source():
    request = urllib.request.Request(SOURCE_URL, headers={'User-Agent': 'RISE-research/0.1'})
    with urllib.request.urlopen(request, timeout=20) as response:
        return response.read()

def main():
    data_dir = ROOT / 'data'
    archive_snapshot(data_dir)
    status = collect(data_dir, fetch_source)
    print(json.dumps(status, ensure_ascii=False))
    return 1 if status['status'] == 'FAILED' else 0

if __name__ == '__main__':
    raise SystemExit(main())

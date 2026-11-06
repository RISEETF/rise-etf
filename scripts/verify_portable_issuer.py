"""Validate a portable issuer capture offline; never publish or replace the master."""
import argparse
import base64
import datetime as dt
import hashlib
import json
from pathlib import Path
from update_official_master import FINDER_URL, LIST_URL, extract_overview, parse_catalog

def decode(value):
    return base64.b64decode(value, validate=True).decode('utf-8-sig')

def verify(bundle):
    if bundle['format'] != 'KBAM_PORTABLE_V1' or bundle['finder_url'] != FINDER_URL:
        raise ValueError('Unexpected source')
    start, end = [dt.datetime.fromisoformat(bundle[k]) for k in ('started_at', 'captured_at')]
    if not start.tzinfo or not end.tzinfo or not dt.timedelta(0) <= end-start <= dt.timedelta(hours=1):
        raise ValueError('Invalid capture interval')
    total, day = extract_overview(decode(bundle['overview_b64']))
    if dt.date.fromisoformat(day) > end.astimezone(dt.timezone(dt.timedelta(hours=9))).date():
        raise ValueError('Future source date')
    pages = []
    if not 1 <= len(bundle['pages']) <= 100:
        raise ValueError('Invalid page count')
    for n, entry in enumerate(bundle['pages'], 1):
        if entry['url'] != f'{LIST_URL}?page={n}':
            raise ValueError('Unexpected API page')
        pages.append({'url': entry['url'], 'body': decode(entry['body_b64'])})
    products, pending = parse_catalog(json.dumps({'format':'KBAM_ETF_API_V1','pages':pages}))
    if total <= 0 or len(products)+len(pending) != total:
        raise ValueError('Finder and API count disagree')
    return {'effective_date':day,'finder_count':total,'verified_codes':len(products),
            'pending_codes':len(pending),'master_updated':False}

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture', type=Path)
    raw = parser.parse_args().capture.read_bytes()
    print(json.dumps(dict(verify(json.loads(raw)),capture_sha256=hashlib.sha256(raw).hexdigest())))

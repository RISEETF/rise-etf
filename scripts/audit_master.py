"""Reconcile legacy names against a preserved provider response; not official approval."""
import base64
from collections import Counter
import hashlib
import json
from pathlib import Path
from update_daily import ROOT, write_json

def reconcile(legacy, provider):
    by_code = {str(q['itemcode']): q for q in provider}
    results = []
    for row in legacy:
        code, name = str(row[0]), str(row[1])
        match = by_code.get(code)
        actual = match['itemname'] if match else None
        if not match:
            status = 'NOT_FOUND_IN_CAPTURE'
        elif not actual.startswith('RISE '):
            status = 'PROVIDER_BRAND_MISMATCH'
        elif ''.join(name.split()) != ''.join(actual.split()):
            status = 'NAME_MISMATCH'
        else:
            status = 'NAME_CODE_MATCH_UNVERIFIED'
        results.append({'code': code, 'legacy_name': name, 'provider_name': actual, 'status': status})
    return results

def main():
    capture = json.loads((ROOT/'data/collection_status.json').read_text())
    digest = capture['sha256']
    source = ROOT/'data/raw/naver'/f'{digest}.json'
    raw = base64.b64decode(json.loads(source.read_text())['raw_base64'])
    if hashlib.sha256(raw).hexdigest() != digest:
        raise ValueError('Source digest mismatch')
    try: text = raw.decode('utf-8')
    except UnicodeDecodeError: text = raw.decode('cp949')
    quotes = json.loads(text)['result']['etfItemList']
    legacy = json.loads((ROOT/'data/latest.json').read_text())['items']
    records = reconcile(legacy, quotes)
    counts = dict(Counter(r['status'] for r in records))
    result = {'status':'BLOCKED_PENDING_OFFICIAL_MASTER', 'source_url':capture['source_url'],
              'source_sha256':digest, 'retrieved_at':capture['retrieved_at'],
              'observation_date':None, 'legacy_count':len(legacy),
              'provider_rise_count':sum(q['itemname'].startswith('RISE ') for q in quotes),
              'counts':counts,'records':records}
    write_json(ROOT/'data/quality/master_audit.json', result)
    lines = ['# ETF master reconciliation', '',
             'Stored provider response comparison only. NOT official instrument verification.',
             'No legacy values were replaced. Missing codes are not proof of delisting.',
             'Name/code matches do not validate fees, pension eligibility or performance.', '',
             f'Legacy rows: {len(legacy)}; provider RISE rows: {result["provider_rise_count"]}.', '',
             '| Result | Count |','|---|---:|']
    lines += [f'| {key} | {value} |' for key,value in counts.items()]
    lines += ['', '| Code | Legacy name | Provider name | Result |', '|---|---|---|---|']
    lines += [f'| {r["code"]} | {r["legacy_name"]} | {r["provider_name"] or "—"} | {r["status"]} |' for r in records]
    (ROOT/'MASTER_AUDIT.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps(counts))

if __name__ == '__main__': main()

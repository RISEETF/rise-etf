"""Bounded acquisition experiment, not a production holdings importer.

Only the KRX shortlist's RISE entries are requested. Raw JSON stays in runtime
artifacts; HTTP success never promotes holdings, dates, weights or attribution.
"""
import argparse
import datetime as dt
import hashlib
import json
import re
import urllib.error
import urllib.request
from pathlib import Path
from collect_krx_etf import write_json_atomic


def probe(queue, master, output):
    if queue.get('schema') != 'ETF_INVESTIGATION_QUEUE_V1' or not isinstance(queue.get('items'), list) or len(queue['items']) > 5:
        raise ValueError('INVALID_SHORTLIST')
    products = {r['code']: r for r in master['products']}
    output = Path(output);output.mkdir(parents=True, exist_ok=True)
    results = []
    for item in queue['items']:
        code = item['ticker']
        if not re.fullmatch('[0-9A-Z]{6}', code):raise ValueError('INVALID_TICKER')
        product = products.get(code)
        result = {'ticker': code, 'requested_observation_date': queue['observation_date'],
                  'status': 'ISSUER_ADAPTER_NOT_VERIFIED', 'holdings_verified': False}
        if product and product['name'] == item['name'] and re.fullmatch('[a-zA-Z0-9]+', product['detail_id']):
            url = f"https://kbam.co.kr/api/products/etfs/{product['detail_id']}/holdings"
            result['candidate_url'] = url
            try:
                req = urllib.request.Request(url, headers={'User-Agent': 'RISE-Research-Collector/1.0'})
                with urllib.request.urlopen(req, timeout=20) as response:
                    raw = response.read(5_000_001)
                    if len(raw)>5_000_000:raise ValueError('RESPONSE_TOO_LARGE')
                    data = json.loads(raw)
                digest = hashlib.sha256(raw).hexdigest()
                (output/f'{code}-{digest}.json').write_bytes(raw)
                result.update(status='JSON_RECEIVED_UNVALIDATED', raw_sha256=digest,
                    shape=list(data.keys()) if isinstance(data,dict) else type(data).__name__)
            except urllib.error.HTTPError as exc:
                result.update(status='HTTP_ERROR', http_status=exc.code)
            except Exception as exc:
                result.update(status='FETCH_FAILED', reason=type(exc).__name__)
        results.append(result)
    report = {'schema': 'TARGETED_HOLDINGS_PROBE_V1', 'attempted_at': dt.datetime.now(dt.timezone.utc).isoformat(),
        'queue_observation_date': queue['observation_date'], 'items': results,
        'production_enabled': False, 'note': 'Validate identity, actual date, units, scope and source terms before enabling accumulation.'}
    write_json_atomic(output/'probe.json', report)
    return report


if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('--queue',default='data/etf_investigations/latest.json')
    p.add_argument('--master',default='data/master/latest.json');p.add_argument('--output',default='var/holdings-probe')
    a=p.parse_args();print(json.dumps(probe(json.loads(Path(a.queue).read_text()),json.loads(Path(a.master).read_text()),a.output),ensure_ascii=False))

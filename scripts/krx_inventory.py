"""Exchange-observed RISE inventory; absence never assigns legal delisting."""
import re
import unicodedata


def build_inventory(snapshot, receipt, previous=None):
    previous = previous or {}
    day = snapshot['page_date']
    if (receipt['status'] != 'SUCCESS' or receipt['observation_date'] != day
            or receipt['record_count'] != len(snapshot['records'])):
        raise ValueError('KRX_INVENTORY_RECEIPT_MISMATCH')
    if previous.get('observed_on', '') > day:
        raise ValueError('KRX_INVENTORY_DATE_REGRESSION')
    current = {}
    seen = set()
    for row in snapshot['records']:
        code = row['ticker']
        if code in seen or not re.fullmatch(r'[0-9A-Z]{6}', code):
            raise ValueError('KRX_INVENTORY_IDENTITY_INVALID')
        seen.add(code)
        # A brand token boundary avoids matching unrelated names containing RISE.
        if re.match(r'^RISE\s+', unicodedata.normalize('NFKC', row['name']).strip()):
            current[code] = row['name']
    if not current:
        raise ValueError('KRX_INVENTORY_EMPTY')
    old = {p['code']: p for p in previous.get('products', [])}
    events = list(previous.get('recent_changes', []))
    products = []
    for code in sorted(set(old) | set(current)):
        prior = old.get(code)
        if code in current:
            item = {'code': code, 'name': current[code], 'status': 'OBSERVED',
                    'first_observed_on': prior['first_observed_on'] if prior else day,
                    'last_observed_on': day}
            kind = ('FIRST_OBSERVED' if prior is None else
                    'REOBSERVED' if prior['status'] != 'OBSERVED' else
                    'NAME_CHANGED' if prior['name'] != current[code] else None)
        else:
            item = dict(prior, status='NOT_OBSERVED')
            kind = 'NOT_OBSERVED' if prior['status'] == 'OBSERVED' else None
        products.append(item)
        # Initial capture is a baseline, not a mass new-listing event.
        if kind and previous:
            event = {'observed_on': day, 'code': code, 'type': kind,
                     'name': item['name'], 'previous_name': prior['name'] if prior else None}
            if event not in events:
                events.append(event)
    return {'schema_version': 1, 'source_id': 'KRX_OPEN_API_ETF_DAILY',
            'observed_on': day, 'retrieved_at': receipt['retrieved_at'],
            'raw_sha256': receipt['raw_sha256'], 'observed_count': len(current),
            'baseline_on': previous.get('baseline_on', day),
            'products': products, 'recent_changes': events[-200:], 'change_history_limit': 200,
            'legal_lifecycle_status': 'NOT_ASSIGNED',
            'note': 'Brand-filtered daily observations. First observation is not listing; absence is not delisting.'}

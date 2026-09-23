"""Compare issuer identities against one complete KRX daily snapshot.

Daily trading observations establish presence, never legal listing/delisting dates.
Name-only matches remain candidates and do not overwrite issuer identities.
"""
from collections import Counter, defaultdict
import datetime as dt
import re
import unicodedata


def name_key(value):
    return ''.join(unicodedata.normalize('NFKC', value).split()).casefold()


def reconcile(master, snapshot, receipt):
    products = master['products'] + master.get('pending_products', [])
    known_codes = {p['code'] for p in master['products']}
    if (master.get('source_product_count', master['instrument_count']) != len(products)
            or master['instrument_count'] != len(master['products'])
            or len({p['detail_id'] for p in products}) != len(products)
            or len(known_codes) != len(master['products'])
            or any(not re.fullmatch(r'[0-9A-Z]{6}', c or '') for c in known_codes)
            or any(p['code'] is not None for p in master.get('pending_products', []))):
        raise ValueError('ISSUER_MASTER_IDENTITY_INVALID')
    if receipt['status'] != 'SUCCESS' or receipt['observation_date'] != snapshot['page_date']:
        raise ValueError('KRX_RECEIPT_MISMATCH')
    if receipt['record_count'] != len(snapshot['records']):
        raise ValueError('KRX_RECEIPT_COUNT_MISMATCH')
    dt.date.fromisoformat(snapshot['page_date'])
    by_code = {}; by_name = defaultdict(list)
    for item in snapshot['records']:
        code = item['ticker']
        if code in by_code:
            raise ValueError('KRX_DUPLICATE_IDENTITY')
        by_code[code] = item
        by_name[name_key(item['name'])].append(item)
    rows = []; claimed = set()
    for product in sorted(products, key=lambda p: p['detail_id']):
        dt.date.fromisoformat(product['listed_on'])
        code = product['code']; match = by_code.get(code)
        row = {'detail_id': product['detail_id'], 'issuer_code': code,
               'issuer_name': product['name'], 'issuer_listed_on': product['listed_on'],
               'krx_code': None, 'krx_name': None, 'candidate_codes': []}
        if match:
            claimed.add(code)
            row.update(krx_code=code, krx_name=match['name'])
            row['status'] = ('MATCHED_CODE_NAME' if name_key(product['name']) == name_key(match['name'])
                             else 'NAME_DIFFERENCE')
        elif product['listed_on'] > snapshot['page_date']:
            row['status'] = 'LISTED_AFTER_KRX_DATE'
        elif code is not None:
            row['status'] = 'NOT_OBSERVED'
        else:
            candidates = by_name.get(name_key(product['name']), [])
            row['candidate_codes'] = [r['ticker'] for r in candidates]
            if (len(candidates) == 1 and re.fullmatch(r'[0-9A-Z]{6}', candidates[0]['ticker'])
                    and candidates[0]['ticker'] not in known_codes):
                row['status'] = 'CODE_PENDING_NAME_CANDIDATE'
                row.update(krx_code=candidates[0]['ticker'], krx_name=candidates[0]['name'])
            elif candidates:
                row['status'] = 'IDENTITY_REVIEW_REQUIRED'
            else:
                row['status'] = 'NO_NAME_CANDIDATE'
        rows.append(row)
    # Candidate names are deliberately not treated as confirmed code matches.
    unmapped = [{'code': p['ticker'], 'name': p['name']} for p in snapshot['records']
                if p['name'].startswith('RISE ') and p['ticker'] not in claimed]
    return {
        'schema_version': 1, 'status': 'KRX_DAILY_IDENTITY_COMPARISON',
        'source_role': 'PRIMARY_EXCHANGE_OBSERVATION',
        'source_url': 'https://data-dbg.krx.co.kr/svc/apis/etp/etf_bydd_trd',
        'observed_on': snapshot['page_date'], 'retrieved_at': receipt['retrieved_at'],
        'raw_sha256': receipt['raw_sha256'], 'krx_market_count': len(snapshot['records']),
        'issuer_effective_date': master['effective_date'], 'issuer_source_sha256': master['source_sha256'],
        'issuer_product_count': len(products), 'counts': dict(Counter(r['status'] for r in rows)),
        'rows': rows, 'krx_rise_without_confirmed_issuer_code': sorted(unmapped, key=lambda r:r['code']),
        'legal_lifecycle_status': 'NOTICE_VERIFICATION_NOT_CONNECTED',
        'note': 'Presence is an exchange observation. Absence is not delisting. Name-only codes require identity review.',
    }

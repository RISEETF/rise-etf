#!/usr/bin/env python3
"""Build a non-ranking exposure candidate registry from the collection pilot."""
import hashlib
import json
import datetime as dt
from urllib.parse import urlparse
from pathlib import Path
from update_daily import ROOT, write_json


def build(data_dir):
    data_dir = Path(data_dir)
    paths = ['universe/policy.json', 'series_sources.json', 'overseas_sources.json']
    raw = {path: (data_dir / path).read_bytes() for path in paths}
    policy, domestic, overseas = (json.loads(raw[path]) for path in paths)
    evidence_path = 'universe/issuer_evidence.json'
    evidence_records = []
    if (data_dir / evidence_path).exists():
        raw[evidence_path] = (data_dir / evidence_path).read_bytes()
        evidence_records = json.loads(raw[evidence_path])['records']
    evidence_ids = set()
    allowed_hosts = {'US_LISTED:SPY': 'www.ssga.com', 'US_LISTED:IEF': 'www.ishares.com'}
    links = {(g['id'], key) for g in policy['groups'] for key in g['candidates']}
    for record in evidence_records:
        url = urlparse(record['source_url'])
        if (record['evidence_id'] in evidence_ids or
            (record['group_id'], record['instrument_id']) not in links or
            url.scheme != 'https' or url.hostname != allowed_hosts.get(record['instrument_id']) or
            url.username or url.password or record['status'] != 'PARTIAL_OFFICIAL_OBJECTIVE_CHECK' or
            record['rs_eligible'] is not False):
            raise ValueError('Invalid issuer evidence identity, source or scope')
        accessed = dt.date.fromisoformat(record['accessed_date'])
        if record['source_as_of'] and dt.date.fromisoformat(record['source_as_of']) > accessed:
            raise ValueError('Source date follows access date')
        evidence_ids.add(record['evidence_id'])
    if policy['status'] != 'RESEARCH_PROPOSAL' or policy['activation_date'] is not None:
        raise ValueError('Activation requires a separately reviewed selection implementation')
    instruments = {}
    for row in domestic['price_instruments'] + overseas['instruments']:
        key = row['market'] + ':' + row['code']
        if key in instruments:
            raise ValueError('Duplicate instrument identity')
        instruments[key] = row
    groups, group_ids, members = [], set(), set()
    for group in policy['groups']:
        if group['id'] in group_ids or group['scope'] not in ('MARKET', 'SECTOR', 'COMPANY', 'THEME'):
            raise ValueError('Duplicate group or invalid scope')
        group_ids.add(group['id'])
        candidates, group_members = [], set()
        for key in group['candidates']:
            if key not in instruments or key in group_members:
                raise ValueError('Unknown or duplicate instrument within group')
            group_members.add(key)
            members.add(key)
            # Evidence is exposure-specific; unreviewed values cannot clear a gate.
            missing = list(policy['required_evidence'])
            candidates.append({'instrument_id': key, 'name': instruments[key]['name'],
                               'currency': instruments[key]['currency'], 'missing_evidence': missing,
                               'issuer_evidence': [r for r in evidence_records if r['instrument_id'] == key and r['group_id'] == group['id']],
                               'exposure_relationship_status': 'PROPOSED_NOT_VERIFIED',
                               'rs_eligible': False})
        groups.append({**group, 'candidates': candidates, 'selected_instrument_id': None,
                       'selection_status': 'UNSELECTED' if candidates else 'DATA_GAP',
                       'overview_votes': 0,
                       'aggregation_status': 'NOT_IMPLEMENTED_NO_CROSS_GROUP_SUM',
                       'max_primary_representatives_per_group': 1})
    result = {'policy_version': policy['version'], 'status': 'CANDIDATE_GROUPS_ONLY',
              'rs_status': 'BLOCKED', 'ranking': None, 'activation_date': None,
              'source_sha256': {path: hashlib.sha256(value).hexdigest() for path, value in raw.items()},
              'groups': groups, 'unmapped_instruments': sorted(set(instruments) - members),
              'selection_order': policy['selection_order'],
              'candidate_link_count': sum(len(g['candidates']) for g in groups),
              'gap_group_count': sum(not g['candidates'] for g in groups),
              'candidate_count': len(members), 'selected_count': 0}
    result['issuer_evidence_count'] = len(evidence_records)
    write_json(data_dir / 'universe/status.json', result)
    return result


if __name__ == '__main__':
    result = build(ROOT / 'data')
    print(json.dumps({'groups': len(result['groups']), 'candidates': result['candidate_count'],
                      'selected': result['selected_count']}))

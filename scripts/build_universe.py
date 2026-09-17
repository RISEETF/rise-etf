#!/usr/bin/env python3
"""Build a non-ranking exposure candidate registry from the collection pilot."""
import hashlib
import json
from pathlib import Path
from update_daily import ROOT, write_json


def build(data_dir):
    data_dir = Path(data_dir)
    paths = ['universe/policy.json', 'series_sources.json', 'overseas_sources.json']
    raw = {path: (data_dir / path).read_bytes() for path in paths}
    policy, domestic, overseas = (json.loads(raw[path]) for path in paths)
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
        if group['id'] in group_ids or group['scope'] not in ('MARKET', 'SECTOR', 'COMPANY'):
            raise ValueError('Duplicate group or invalid scope')
        group_ids.add(group['id'])
        if not group['candidates']:
            raise ValueError('Empty exposure group')
        candidates = []
        for key in group['candidates']:
            if key not in instruments or key in members:
                raise ValueError('Unknown or multiply counted instrument')
            members.add(key)
            evidence = policy['evidence'].get(key, {})
            # This version cannot promote a candidate, even if somebody adds evidence.
            missing = [field for field in policy['required_evidence'] if not evidence.get(field)]
            candidates.append({'instrument_id': key, 'name': instruments[key]['name'],
                               'currency': instruments[key]['currency'], 'missing_evidence': missing,
                               'rs_eligible': False})
        groups.append({**group, 'candidates': candidates, 'selected_instrument_id': None,
                       'selection_status': 'UNSELECTED', 'overview_votes': 0,
                       'max_overview_votes_after_validation': 0 if group['scope'] == 'COMPANY' else 1})
    result = {'policy_version': policy['version'], 'status': 'CANDIDATE_GROUPS_ONLY',
              'rs_status': 'BLOCKED', 'ranking': None, 'activation_date': None,
              'source_sha256': {path: hashlib.sha256(value).hexdigest() for path, value in raw.items()},
              'groups': groups, 'unmapped_instruments': sorted(set(instruments) - members),
              'selection_order': policy['selection_order'],
              'candidate_count': len(members), 'selected_count': 0}
    write_json(data_dir / 'universe/status.json', result)
    return result


if __name__ == '__main__':
    result = build(ROOT / 'data')
    print(json.dumps({'groups': len(result['groups']), 'candidates': result['candidate_count'],
                      'selected': result['selected_count']}))

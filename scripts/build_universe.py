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
    write_json(data_dir / 'universe/status.json', result)
    return result


if __name__ == '__main__':
    result = build(ROOT / 'data')
    print(json.dumps({'groups': len(result['groups']), 'candidates': result['candidate_count'],
                      'selected': result['selected_count']}))

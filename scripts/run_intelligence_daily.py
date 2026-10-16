#!/usr/bin/env python3
"""Run existing engines, prepare evidence, and publish only a current FULL package."""
import argparse
from datetime import datetime, timezone, date
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from uuid import uuid4
from zoneinfo import ZoneInfo

from update_intelligence_portal import publish, read_json, write_json
from validate_intelligence_snapshot import validate

ENGINES = ('build_gclri_signals.py', 'build_signal_episodes.py',
           'build_regime_gate.py', 'build_validation_status.py')
INPUTS = ('data/gclri/latest.json', 'data/signals/signal_registry.json',
          'data/episodes/episode_registry.json', 'data/regime/channel_registry.json')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare_input(root, now):
    market = read_json(root / INPUTS[0])
    today = now.astimezone(ZoneInfo('Asia/Seoul')).date()
    gaps = []
    built = datetime.fromisoformat(market['built_at_utc'])
    if built.utcoffset() is None or not 0 <= (now - built).total_seconds() <= 36 * 3600:
        gaps.append('MARKET_BUILD_NOT_CURRENT')
    if market.get('status') != 'SUCCESS' or not market.get('series'):
        gaps.append('MARKET_COLLECTION_INCOMPLETE')
    for key, row in market.get('series', {}).items():
        try:
            age = (today - date.fromisoformat(row['observation_date'])).days
            if row.get('data_state') != 'CURRENT' or not 0 <= age <= row['stale_after_days']:
                gaps.append('STALE_OR_UNAVAILABLE:' + key)
        except (KeyError, TypeError, ValueError):
            gaps.append('INVALID_OBSERVATION:' + key)
    return {'schema_version': '1.0', 'asof_date': today.isoformat(),
            'prepared_at_utc': now.isoformat(), 'publication_blockers': gaps,
            'source_hashes': {p: digest(root / p) for p in INPUTS},
            'market': market,
            'signals': read_json(root / 'data/signals/latest.json'),
            'episodes': read_json(root / 'data/episodes/latest.json'),
            'regime_gate': read_json(root / 'data/regime/gate_latest.json'),
            'validation': read_json(root / 'data/validation/v1_status.json'),
            'note': 'Research inputs only. No new regime, confidence, ETF recommendation or FULL report is inferred.'}


def check_package(package, inputs, root):
    errors = list(inputs['publication_blockers'])
    if not all((package / name).is_file() for name in ('snapshot.json', 'report.txt', 'evidence.json')):
        return errors + ['FULL_INPUT_PACKAGE_MISSING']
    snapshot = read_json(package / 'snapshot.json')
    evidence = read_json(package / 'evidence.json')
    errors.extend(validate(snapshot))
    if snapshot.get('snapshot_type') != 'FULL':
        errors.append('EXPLICIT_FULL_SNAPSHOT_REQUIRED')
    if snapshot.get('asof_date') != inputs['asof_date'] or evidence.get('asof_date') != inputs['asof_date']:
        errors.append('PACKAGE_DATE_MISMATCH')
    if evidence.get('source_hashes') != inputs['source_hashes']:
        errors.append('SOURCE_VINTAGE_MISMATCH')
    for name in ('snapshot.json', 'report.txt'):
        if evidence.get('content_hashes', {}).get(name) != digest(package / name):
            errors.append('CONTENT_HASH_MISMATCH:' + name)
    references = evidence.get('external_evidence')
    if not isinstance(references, list) or not references:
        errors.append('EXTERNAL_EVIDENCE_MISSING')
    else:
        for item in references:
            if not isinstance(item, dict) or not all(isinstance(item.get(k), str) and item[k].strip()
                    for k in ('url', 'observation_date', 'claim')):
                errors.append('EXTERNAL_EVIDENCE_INVALID')
                continue
            try:
                observed = date.fromisoformat(item['observation_date'])
                if observed > date.fromisoformat(inputs['asof_date']) or not item['url'].startswith('https://'):
                    raise ValueError()
            except ValueError:
                errors.append('EXTERNAL_EVIDENCE_INVALID')
    # Preserve authorization boundaries: publication does not promote research rules.
    if snapshot.get('production_eligible', False) is not False:
        errors.append('PRODUCTION_PROMOTION_NOT_AUTHORIZED')
    gate = snapshot.get('regime_history_update', {})
    if gate.get('transition_gate_crossed') is not False or snapshot.get('regime_change_status') == 'ACTIVE':
        errors.append('REGIME_PROMOTION_NOT_AUTHORIZED')
    prior = read_json(root / 'intelligence/data/latest.json')
    if snapshot.get('current_regime') != prior.get('current_regime'):
        errors.append('REGIME_CHANGE_REQUIRES_REVIEW')
    known = {(x.get('name'), x.get('to')) for x in read_json(root / 'intelligence/data/framework_history.json')}
    if any((x.get('name'), x.get('status')) not in known for x in snapshot.get('framework_updates', [])):
        errors.append('FRAMEWORK_CHANGE_REQUIRES_REVIEW')
    return errors


def run(root, now=None, engine_runner=None):
    root = Path(root).resolve()
    now = now or datetime.now(timezone.utc)
    run_key = os.environ.get('GITHUB_RUN_ID', 'local-' + uuid4().hex)
    attempt = os.environ.get('GITHUB_RUN_ATTEMPT', '1')
    if not all(c.isalnum() or c in '-_' for c in run_key + attempt):
        raise ValueError('invalid run identity')
    receipt = {'schema_version': '1.0', 'started_at_utc': now.isoformat(),
               'run_id': run_key, 'run_attempt': attempt, 'status': 'FAILED', 'stages': {},
               'note': 'Checkout execution only. Git push and Pages deployment are separate outcomes.'}
    try:
        for script in ENGINES:
            receipt['stages'][script] = 'RUNNING'
            if engine_runner:
                engine_runner(script)
            else:
                subprocess.run([sys.executable, str(root / 'scripts' / script)], cwd=root, check=True)
            receipt['stages'][script] = 'SUCCESS'
        inputs = prepare_input(root, now)
        write_json(root / 'data/intelligence/daily_input.json', inputs)
        package = root / 'intelligence/inbox' / inputs['asof_date']
        blockers = check_package(package, inputs, root)
        if os.environ.get('UPSTREAM_CONCLUSION', '') not in {'', 'success'}:
            blockers.append('UPSTREAM_COLLECTION_FAILED')
        receipt['blockers'] = blockers
        if blockers:
            receipt['status'] = 'BLOCKED'
            receipt['stages']['publication'] = 'BLOCKED'
        else:
            evidence = read_json(package / 'evidence.json')
            receipt['publication'] = publish(package / 'snapshot.json', package / 'report.txt',
                                             root / 'intelligence', evidence.get('revision_reason'))
            receipt['stages']['publication'] = 'SUCCESS'
            receipt['status'] = 'PUBLISHED' if receipt['publication']['content_changed'] else 'UNCHANGED'
    except Exception as exc:
        receipt['error'] = type(exc).__name__ + ': ' + str(exc)
        for stage, outcome in receipt['stages'].items():
            if outcome == 'RUNNING':
                receipt['stages'][stage] = 'FAILED'
    receipt['finished_at_utc'] = datetime.now(timezone.utc).isoformat()
    write_json(root / 'data/operations/runs' / f'intelligence-{run_key}-{attempt}.json', receipt)
    write_json(root / 'data/operations/intelligence.json', receipt)
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', default=str(Path(__file__).resolve().parents[1]))
    args = parser.parse_args()
    result = run(args.root)
    print(json.dumps(result, ensure_ascii=False))
    sys.exit(0 if result['status'] in {'PUBLISHED', 'UNCHANGED'} else 2)

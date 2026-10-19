#!/usr/bin/env python3
"""Run existing engines, prepare evidence, and publish only a current FULL package."""
import argparse
from datetime import datetime, timezone, date
import hashlib
import json
import math
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
          'data/episodes/episode_registry.json', 'data/regime/channel_registry.json',
          'data/gclri/series_registry.json', 'data/signals/latest.json',
          'data/episodes/latest.json', 'data/regime/gate_latest.json',
          'data/validation/v1_status.json', 'data/quality/krx_rise_inventory.json',
          'data/gclri/history.json', 'data/signals/history.json',
          'data/episodes/history.json', 'data/regime/gate_history.json')


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
    registry = {row['id']: row for row in read_json(root / 'data/gclri/series_registry.json')['series']}
    for key in sorted(set(registry) - set(market.get('series', {}))):
        gaps.append('REQUIRED_SERIES_MISSING:' + key)
    for key, row in market.get('series', {}).items():
        try:
            age = (today - date.fromisoformat(row['observation_date'])).days
            if row.get('data_state') != 'CURRENT' or not 0 <= age <= registry[key]['stale_after_days']:
                gaps.append('STALE_OR_UNAVAILABLE:' + key)
            value = row.get('value')
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                gaps.append('INVALID_VALUE:' + key)
        except (KeyError, TypeError, ValueError):
            gaps.append('INVALID_OBSERVATION:' + key)
    signals = read_json(root / 'data/signals/latest.json')
    episodes = read_json(root / 'data/episodes/latest.json')
    gate = read_json(root / 'data/regime/gate_latest.json')
    for name, source, upstream in (
        ('SIGNALS', signals.get('source_gclri_built_at_utc'), market.get('built_at_utc')),
        ('EPISODES', episodes.get('source_signal_built_at_utc'), signals.get('built_at_utc')),
        ('GATE', gate.get('source_episode_built_at_utc'), episodes.get('built_at_utc')),
    ):
        if not source or source != upstream:
            gaps.append('DERIVED_VINTAGE_MISMATCH:' + name)
    return {'schema_version': '1.0', 'asof_date': today.isoformat(),
            'prepared_at_utc': now.isoformat(), 'publication_blockers': gaps,
            'source_hashes': {p: digest(root / p) for p in INPUTS},
            'market': market,
            'signals': signals,
            'episodes': episodes,
            'regime_gate': gate,
            'series_registry': registry,
            'rise_inventory': read_json(root / 'data/quality/krx_rise_inventory.json'),
            'validation': read_json(root / 'data/validation/v1_status.json'),
            'note': 'Research inputs only. No new regime, confidence, ETF recommendation or FULL report is inferred.'}


def check_package(package, inputs, root):
    errors = list(inputs['publication_blockers'])
    if not all((package / name).is_file() for name in ('snapshot.json', 'report.txt', 'evidence.json')):
        return errors + ['FULL_INPUT_PACKAGE_MISSING']
    snapshot = read_json(package / 'snapshot.json')
    evidence = read_json(package / 'evidence.json')
    if snapshot.get('schema_version') == '1.1':
        from build_intelligence_full import coverage, compose
        errors = coverage(inputs)[0]
        expected, narrative, refs = compose(inputs, read_json(root / 'intelligence/data/latest.json'))
        if snapshot != expected or (package / 'report.txt').read_text(encoding='utf-8') != narrative:
            errors.append('AUTOMATIC_REPORT_EVIDENCE_MISMATCH')
        if evidence.get('external_evidence') != refs:
            errors.append('AUTOMATIC_REPORT_REFERENCES_MISMATCH')
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


def run(root, now=None, engine_runner=None, publish_prepared=False, auto_report=False):
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
            if publish_prepared:
                receipt['stages'][script] = 'REUSED_FOR_REVIEWED_PACKAGE'
                continue
            receipt['stages'][script] = 'RUNNING'
            if engine_runner:
                engine_runner(script)
            else:
                subprocess.run([sys.executable, str(root / 'scripts' / script)], cwd=root, check=True)
            receipt['stages'][script] = 'SUCCESS'
        inputs = prepare_input(root, now)
        if os.environ.get('UPSTREAM_CONCLUSION', '') not in {'', 'success'}:
            inputs['publication_blockers'].append('UPSTREAM_COLLECTION_FAILED')
        write_json(root / 'data/intelligence/daily_input.json', inputs)
        from build_intelligence_research import build, save
        receipt['stages']['research_draft'] = 'RUNNING'
        receipt['research_draft'] = save(root, build(inputs))
        receipt['stages']['research_draft'] = 'SUCCESS'
        package = root / 'intelligence/inbox' / inputs['asof_date']
        if auto_report and not publish_prepared and not package.exists():
            from build_intelligence_full import coverage, generate
            hard_blockers, exclusions = coverage(inputs)
            receipt['coverage_exclusions'] = exclusions
            if not hard_blockers:
                receipt['stages']['full_report'] = 'RUNNING'
                package = generate(root, inputs)
                receipt['generated_package'] = str(package.relative_to(root))
                receipt['stages']['full_report'] = 'SUCCESS'
        blockers = check_package(package, inputs, root)
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
    parser.add_argument('--publish-prepared', action='store_true',
                        help='Validate and publish an already computed/reviewed vintage without rerunning engines')
    args = parser.parse_args()
    result = run(args.root, publish_prepared=args.publish_prepared, auto_report=True)
    print(json.dumps(result, ensure_ascii=False))
    sys.exit(0 if result['status'] in {'PUBLISHED', 'UNCHANGED'} else 2)

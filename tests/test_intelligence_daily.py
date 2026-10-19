import json
from datetime import datetime, timezone
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import run_intelligence_daily as daily

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 10, 16, 6, tzinfo=timezone.utc)


class DailyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        shutil.copytree(ROOT / 'intelligence', self.root / 'intelligence')
        for path in daily.INPUTS + ('data/signals/latest.json', 'data/episodes/latest.json',
                                  'data/regime/gate_latest.json', 'data/validation/v1_status.json'):
            target = self.root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / path, target)
        self.market = daily.read_json(self.root / daily.INPUTS[0])
        self.market['built_at_utc'] = NOW.isoformat()
        for row in self.market['series'].values():
            row.update(observation_date='2026-10-15', data_state='CURRENT')
        daily.write_json(self.root / daily.INPUTS[0], self.market)
        upstream = self.market['built_at_utc']
        for path, field in (('data/signals/latest.json', 'source_gclri_built_at_utc'),
                            ('data/episodes/latest.json', 'source_signal_built_at_utc'),
                            ('data/regime/gate_latest.json', 'source_episode_built_at_utc')):
            row = daily.read_json(self.root / path)
            row[field] = upstream
            daily.write_json(self.root / path, row)
            upstream = row['built_at_utc']
        self.before = {str(p.relative_to(self.root)): p.read_bytes()
                       for p in (self.root / 'intelligence').rglob('*') if p.is_file()}

    def assert_preserved(self):
        for path, content in self.before.items():
            self.assertEqual((self.root / path).read_bytes(), content)

    def package(self):
        inputs = daily.prepare_input(self.root, NOW)
        package = self.root / 'intelligence/inbox/2026-10-16'
        package.mkdir(parents=True)
        snapshot = daily.read_json(ROOT / 'intelligence/data/daily/2026-09-22.json')
        snapshot.update(asof_date='2026-10-16', snapshot_type='FULL', framework_updates=[],
                        current_regime=daily.read_json(self.root / 'intelligence/data/latest.json')['current_regime'])
        snapshot['regime_history_update']['transition_gate_crossed'] = False
        snapshot['regime_change_status'] = 'NONE'
        daily.write_json(package / 'snapshot.json', snapshot)
        (package / 'report.txt').write_text('Synthetic test narrative only')
        evidence = {'asof_date': '2026-10-16', 'source_hashes': inputs['source_hashes'],
                    'content_hashes': {n: daily.digest(package / n) for n in ('snapshot.json', 'report.txt')},
                    'external_evidence': [{'url': 'https://example.org/source', 'observation_date': '2026-10-15', 'claim': 'Test evidence'}]}
        daily.write_json(package / 'evidence.json', evidence)
        return package, inputs

    def test_missing_package_blocks_but_records_all_engines(self):
        called = []
        result = daily.run(self.root, NOW, called.append)
        self.assertEqual(called, list(daily.ENGINES))
        self.assertEqual(result['status'], 'BLOCKED')
        self.assertIn('FULL_INPUT_PACKAGE_MISSING', result['blockers'])
        self.assertTrue((self.root / 'data/operations/intelligence.json').exists())
        self.assert_preserved()

    def test_engine_failure_is_recorded_and_stops_chain(self):
        def fail(script):
            raise RuntimeError('injected')
        result = daily.run(self.root, NOW, fail)
        self.assertEqual(result['status'], 'FAILED')
        self.assertEqual(result['stages'], {daily.ENGINES[0]: 'FAILED'})
        self.assert_preserved()

    def test_staleness_is_recomputed_not_trusted(self):
        self.market['series']['DGS10']['observation_date'] = '2026-09-01'
        daily.write_json(self.root / daily.INPUTS[0], self.market)
        inputs = daily.prepare_input(self.root, NOW)
        self.assertIn('STALE_OR_UNAVAILABLE:DGS10', inputs['publication_blockers'])

    def test_successful_package_publishes_and_repeat_is_unchanged(self):
        self.package()
        self.assertEqual(daily.run(self.root, NOW, lambda _: None)['status'], 'PUBLISHED')
        self.assertEqual(daily.run(self.root, NOW, lambda _: None)['status'], 'UNCHANGED')

    def test_source_change_blocks_reviewed_package(self):
        package, _ = self.package()
        self.market['series']['DGS10']['value'] += 1
        daily.write_json(self.root / daily.INPUTS[0], self.market)
        errors = daily.check_package(package, daily.prepare_input(self.root, NOW), self.root)
        self.assertIn('SOURCE_VINTAGE_MISMATCH', errors)

    def test_report_change_invalidates_evidence(self):
        package, inputs = self.package()
        (package / 'report.txt').write_text('Different text')
        self.assertIn('CONTENT_HASH_MISMATCH:report.txt', daily.check_package(package, inputs, self.root))

    def test_summary_and_promotion_are_blocked(self):
        package, inputs = self.package()
        snapshot = daily.read_json(package / 'snapshot.json')
        snapshot.update(snapshot_type='SUMMARY_ONLY', production_eligible=True, current_regime='NEW')
        daily.write_json(package / 'snapshot.json', snapshot)
        errors = daily.check_package(package, inputs, self.root)
        self.assertIn('EXPLICIT_FULL_SNAPSHOT_REQUIRED', errors)
        self.assertIn('PRODUCTION_PROMOTION_NOT_AUTHORIZED', errors)
        self.assertIn('REGIME_CHANGE_REQUIRES_REVIEW', errors)

    def test_failed_upstream_blocks_even_with_valid_package(self):
        self.package()
        with patch.dict('os.environ', {'UPSTREAM_CONCLUSION': 'failure'}):
            result = daily.run(self.root, NOW, lambda _: None)
        self.assertEqual(result['status'], 'BLOCKED')
        self.assertIn('UPSTREAM_COLLECTION_FAILED', result['blockers'])
        self.assert_preserved()

    def test_required_series_cannot_disappear(self):
        del self.market['series']['DGS10']
        daily.write_json(self.root / daily.INPUTS[0], self.market)
        self.assertIn('REQUIRED_SERIES_MISSING:DGS10', daily.prepare_input(self.root, NOW)['publication_blockers'])

    def test_payload_cannot_relax_registry_freshness(self):
        self.market['series']['DGS10'].update(observation_date='2026-09-01', stale_after_days=999)
        daily.write_json(self.root / daily.INPUTS[0], self.market)
        self.assertIn('STALE_OR_UNAVAILABLE:DGS10', daily.prepare_input(self.root, NOW)['publication_blockers'])

    def test_invalid_values_fail_closed(self):
        for value in (None, True, float('nan'), float('inf'), '5.1'):
            with self.subTest(value=value):
                self.market['series']['DGS10']['value'] = value
                daily.write_json(self.root / daily.INPUTS[0], self.market)
                self.assertIn('INVALID_VALUE:DGS10', daily.prepare_input(self.root, NOW)['publication_blockers'])

    def test_derived_results_are_bound_to_reviewed_package(self):
        package, _ = self.package()
        path = self.root / 'data/signals/latest.json'
        signal = daily.read_json(path)
        signal['signals'][0]['direction'] = 'CHANGED'
        daily.write_json(path, signal)
        self.assertIn('SOURCE_VINTAGE_MISMATCH', daily.check_package(package, daily.prepare_input(self.root, NOW), self.root))

    def test_mixed_engine_vintages_block(self):
        path = self.root / 'data/signals/latest.json'
        signal = daily.read_json(path)
        signal['source_gclri_built_at_utc'] = '2026-09-01T00:00:00+00:00'
        daily.write_json(path, signal)
        self.assertIn('DERIVED_VINTAGE_MISMATCH:SIGNALS', daily.prepare_input(self.root, NOW)['publication_blockers'])

    def research_input(self):
        inputs = daily.prepare_input(self.root, NOW)
        row = inputs['market']['series']['DGS10']
        inputs['signals']['signals'] = [{
            'signal_id': 'SIG-RATE-001', 'signal_state': 'ACTIVE_CANDIDATE', 'direction': 'DOWN',
            'strongest_series': 'DGS10', 'details': [{'series_id': 'DGS10',
                'observation_date': row['observation_date'], 'latest_value': row['value']}]}]
        inputs['rise_inventory'] = {'observed_on': '2026-10-15', 'products': [
            {'code': 'TEST01', 'name': 'RISE 미국채 테스트', 'status': 'OBSERVED', 'last_observed_on': '2026-10-15'}]}
        return inputs

    def test_research_is_distinct_from_full_and_repeatable(self):
        from build_intelligence_research import build, save
        inputs = self.research_input()
        draft = build(inputs)
        self.assertFalse(draft['publication_eligible'])
        self.assertFalse(draft['production_eligible'])
        self.assertNotIn('regime_confidence', draft)
        self.assertEqual(draft['rise_research_candidates'][0]['basis'], 'NAME_ONLY_UNVERIFIED_EXPOSURE')
        first = save(self.root, draft)
        self.assertEqual(first, save(self.root, build(inputs)))
        inputs['market']['series']['DGS10']['value'] += 0.1
        second = save(self.root, build(inputs))
        self.assertNotEqual(first['path'], second['path'])
        self.assertTrue((self.root / first['path'] / 'report.md').exists())
        self.assert_preserved()

    def test_stale_research_never_creates_marketing_candidates(self):
        from build_intelligence_research import build
        inputs = self.research_input()
        inputs['publication_blockers'] = ['STALE_OR_UNAVAILABLE:DTWEXBGS']
        draft = build(inputs)
        self.assertFalse(draft['rise_research_candidates'])
        self.assertFalse(draft['gate_observation']['usable'])
        self.assertTrue(all(not s['usable_for_research'] for s in draft['signals']))

    def test_stale_or_mismatched_signal_detail_is_not_usable(self):
        from build_intelligence_research import build
        inputs = self.research_input()
        inputs['signals']['signals'][0]['details'][0]['observation_date'] = '2026-09-01'
        self.assertFalse(build(inputs)['rise_research_candidates'])
        inputs = self.research_input()
        inputs['market']['series']['DGS10']['observation_date'] = '2026-09-01'
        self.assertFalse(next(r for r in build(inputs)['observations'] if r['series_id']=='DGS10')['fresh_for_report'])
        self.assertFalse(build(inputs)['rise_research_candidates'])

    def test_stale_inventory_is_not_a_current_candidate(self):
        from build_intelligence_research import build
        inputs = self.research_input()
        inputs['rise_inventory']['observed_on'] = '2026-09-01'
        self.assertFalse(build(inputs)['rise_research_candidates'])

    def test_blocked_run_still_produces_reviewable_draft(self):
        result = daily.run(self.root, NOW, lambda _: None)
        self.assertEqual(result['status'], 'BLOCKED')
        self.assertEqual(result['stages']['research_draft'], 'SUCCESS')
        report = self.root / result['research_draft']['path'] / 'report.md'
        self.assertIn('정식 보고서 아님', report.read_text())
        self.assert_preserved()

    def test_prepared_publication_reuses_exact_reviewed_vintage(self):
        self.package()
        def fail(_):
            raise AssertionError('must not recompute reviewed outputs')
        result = daily.run(self.root, NOW, fail, publish_prepared=True)
        self.assertEqual(result['status'], 'PUBLISHED')
        self.assertEqual(result['stages'][daily.ENGINES[0]], 'REUSED_FOR_REVIEWED_PACKAGE')

    def test_prepared_publication_still_rejects_changed_outputs(self):
        self.package()
        path = self.root / 'data/validation/v1_status.json'
        value = daily.read_json(path)
        value['validation_state'] = 'CHANGED'
        daily.write_json(path, value)
        result = daily.run(self.root, NOW, publish_prepared=True)
        self.assertEqual(result['status'], 'BLOCKED')
        self.assertIn('SOURCE_VINTAGE_MISMATCH', result['blockers'])
        self.assert_preserved()

if __name__ == '__main__':
    unittest.main()

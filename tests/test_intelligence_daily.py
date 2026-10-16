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

if __name__ == '__main__':
    unittest.main()

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import update_intelligence_portal as publisher

ROOT = Path(__file__).resolve().parents[1]


class TestPublication(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.portal = self.root / 'portal'
        self.snapshot = self.root / 'snapshot.json'
        self.narrative = self.root / 'report.txt'
        self.data = json.loads((ROOT / 'intelligence/data/daily/2026-09-22.json').read_text())
        self.snapshot.write_text(json.dumps(self.data))
        self.narrative.write_text('Original narrative')
        self.run_publish()

    def run_publish(self, reason=None):
        return publisher.publish(self.snapshot, self.narrative, self.portal, reason)

    def contents(self):
        return {str(p.relative_to(self.portal)): p.read_bytes()
                for p in self.portal.rglob('*') if p.is_file()}

    def test_idempotent(self):
        before = self.contents()
        self.assertFalse(self.run_publish()['content_changed'])
        self.assertEqual(before, self.contents())

    def test_render_failure_leaves_original(self):
        before = self.contents()
        with patch.object(publisher, 'render_report', side_effect=RuntimeError('render failed')):
            with self.assertRaises(RuntimeError):
                self.run_publish()
        self.assertEqual(before, self.contents())

    def test_missing_narrative_leaves_original(self):
        before = self.contents()
        self.narrative.unlink()
        with self.assertRaises(FileNotFoundError):
            self.run_publish()
        self.assertEqual(before, self.contents())

    def test_empty_narrative_leaves_original(self):
        before = self.contents()
        self.narrative.write_text('   ')
        with self.assertRaises(ValueError):
            self.run_publish()
        self.assertEqual(before, self.contents())

    def test_validation_failure_leaves_original(self):
        before = self.contents()
        with patch.object(publisher, 'validate_portal', side_effect=ValueError('invalid stage')):
            with self.assertRaises(ValueError):
                self.run_publish()
        self.assertEqual(before, self.contents())

    def test_swap_failure_rolls_back(self):
        before = self.contents()
        original = publisher.os.replace
        def fail_stage(src, dst):
            if '.intelligence-stage-' in str(src):
                raise OSError('injected replacement failure')
            return original(src, dst)
        with patch.object(publisher.os, 'replace', side_effect=fail_stage):
            with self.assertRaises(OSError):
                self.run_publish()
        self.assertEqual(before, self.contents())

    def test_narrative_revision_preserves_both_and_reason(self):
        before = self.contents()
        self.narrative.write_text('Revised narrative')
        with self.assertRaises(ValueError):
            self.run_publish()
        self.assertEqual(before, self.contents())
        self.run_publish('Correct explanatory wording')
        vintages = list((self.portal / 'data/vintages/2026-09-22').iterdir())
        self.assertEqual(len(vintages), 1)
        self.assertEqual((vintages[0] / 'snapshot.json').read_bytes(), before['data/daily/2026-09-22.json'])
        self.assertEqual((vintages[0] / 'report.html').read_bytes(), before['reports/2026-09-22.html'])
        self.assertEqual(json.loads((vintages[0] / 'revision.json').read_text())['reason'], 'Correct explanatory wording')
        self.assertFalse(self.run_publish()['content_changed'])
        self.narrative.write_text('Another correction')
        self.run_publish('Second correction')
        self.assertEqual(len(list((self.portal / 'data/vintages/2026-09-22').iterdir())), 2)

    def test_snapshot_repair_preserves_report_and_vintage(self):
        import shutil
        shutil.rmtree(self.portal)
        shutil.copytree(ROOT / 'intelligence', self.portal)
        day = '2026-10-27'
        # Replay the actual broken snapshot, kept as a revision vintage.
        originals = list((self.portal / 'data/vintages' / day).glob('*/snapshot.json'))
        original = next(p for p in originals if json.loads(p.read_text()).get('product_candidates'))
        data = json.loads(original.read_text())
        (self.portal / f'data/daily/{day}.json').write_bytes(original.read_bytes())
        (self.portal / 'data/latest.json').write_bytes(original.read_bytes())
        before = self.contents()
        repaired = publisher.canonical_repair_metadata(data)
        self.snapshot.write_text(json.dumps(repaired))
        result = publisher.publish(self.snapshot, None, self.portal, 'Schema repair',
                                   preserve_existing_report=True)
        self.assertTrue(result['content_changed'])
        self.assertEqual(before[f'reports/{day}.html'], (self.portal / f'reports/{day}.html').read_bytes())
        new_paths = set(self.contents()) - set(before)
        archived = next(p for p in new_paths if p.endswith('/snapshot.json'))
        self.assertEqual(before[f'data/daily/{day}.json'], self.contents()[archived])
        self.assertEqual(repaired['research_candidates'], data['product_candidates'])
        self.assertEqual(repaired['research_gaps'], data['coverage']['blockers'])
        self.assertFalse(publisher.publish(self.snapshot, None, self.portal, 'Schema repair',
                                          preserve_existing_report=True)['content_changed'])
        stable = self.contents()
        repaired['observations'][0]['value'] += 1
        self.snapshot.write_text(json.dumps(repaired))
        with self.assertRaises(ValueError):
            publisher.publish(self.snapshot, None, self.portal, 'Repair', preserve_existing_report=True)
        self.assertEqual(stable, self.contents())

    def test_snapshot_repair_requires_existing_report_and_reason(self):
        before = self.contents()
        with self.assertRaises(ValueError):
            publisher.publish(self.snapshot, None, self.portal, preserve_existing_report=True)
        self.assertEqual(before, self.contents())
        self.data['asof_date'] = '2026-09-23'
        self.snapshot.write_text(json.dumps(self.data))
        with self.assertRaises(ValueError):
            publisher.publish(self.snapshot, None, self.portal, 'Repair', preserve_existing_report=True)
        self.assertEqual(before, self.contents())

    def test_backfill_does_not_rewind_latest(self):
        latest = (self.portal / 'data/latest.json').read_bytes()
        self.data['asof_date'] = '2026-09-21'
        self.snapshot.write_text(json.dumps(self.data))
        self.run_publish()
        self.assertEqual(latest, (self.portal / 'data/latest.json').read_bytes())
        publisher.validate_portal(self.portal)

    def test_broken_archive_link_blocks_publication(self):
        (self.portal / 'reports/2026-09-22.html').unlink()
        before = self.contents()
        self.data['asof_date'] = '2026-09-23'
        self.snapshot.write_text(json.dumps(self.data))
        with self.assertRaises(FileNotFoundError):
            self.run_publish()
        self.assertEqual(before, self.contents())

    def test_concurrent_writer_is_blocked(self):
        before = self.contents()
        (self.root / '.portal.publish.lock').touch()
        with self.assertRaises(FileExistsError):
            self.run_publish()
        self.assertEqual(before, self.contents())

    def test_actual_archive(self):
        publisher.validate_portal(ROOT / 'intelligence')


if __name__ == '__main__':
    unittest.main()

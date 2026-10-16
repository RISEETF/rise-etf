import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from krx_inventory import build_inventory


class InventoryTests(unittest.TestCase):
    def build(self, records, previous=None, day='2026-10-15'):
        return build_inventory({'page_date': day, 'records': records},
                               {'status': 'SUCCESS', 'observation_date': day,
                                'record_count': len(records), 'retrieved_at': day+'T10:00:00Z',
                                'raw_sha256': 'hash'}, previous)

    def test_baseline_brand_boundary_and_dynamic_count(self):
        result = self.build([{'ticker': '111111', 'name': 'RISE A'},
                             {'ticker': '222222', 'name': 'RISE\u3000B'},
                             {'ticker': '333333', 'name': 'OTHER RISE'},
                             {'ticker': '444444', 'name': 'RISEX'}])
        self.assertEqual(result['observed_count'], 2)
        self.assertEqual(result['recent_changes'], [])

    def test_change_absence_reappearance_and_idempotency(self):
        before = self.build([{'ticker': '111111', 'name': 'RISE A'}, {'ticker': '222222', 'name': 'RISE B'}])
        records = [{'ticker': '111111', 'name': 'RISE Renamed'}, {'ticker': '333333', 'name': 'RISE C'}]
        after = self.build(records, before, '2026-10-16')
        self.assertEqual(after['observed_count'], 2)
        self.assertEqual({e['type'] for e in after['recent_changes']}, {'NAME_CHANGED','NOT_OBSERVED','FIRST_OBSERVED'})
        self.assertEqual(after, self.build(records, after, '2026-10-16'))
        returned = self.build(records+[{'ticker': '222222', 'name': 'RISE B'}], after, '2026-10-17')
        self.assertEqual(returned['recent_changes'][-1]['type'], 'REOBSERVED')
        self.assertEqual(returned['products'][1]['first_observed_on'], '2026-10-15')
        self.assertEqual(returned['legal_lifecycle_status'], 'NOT_ASSIGNED')
        self.assertFalse(any('delisted_on' in p for p in after['products']))

    def test_bad_or_regressed_capture_rejected(self):
        rows = [{'ticker': '111111', 'name': 'RISE A'}]
        previous = self.build(rows)
        with self.assertRaisesRegex(ValueError, 'REGRESSION'):
            self.build(rows, previous, '2026-10-14')
        with self.assertRaisesRegex(ValueError, 'IDENTITY'):
            self.build(rows*2)
        with self.assertRaisesRegex(ValueError, 'EMPTY'):
            self.build([{'ticker': '111111', 'name': 'OTHER A'}])

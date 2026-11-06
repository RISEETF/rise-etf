import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from build_intelligence_full import unique_rise_candidates


class TestRiseCandidateDedup(unittest.TestCase):
    def test_same_code_retains_two_signals_without_duplicate_card(self):
        base = dict(name='RISE Test', code='123456', basis='NAME_ONLY_UNVERIFIED_EXPOSURE',
                    inventory_asof='2026-11-04', required_check='공식 노출 확인')
        rows = [
            dict(base, signal_id='SIG-RATE-001', internal_discussion_topic='금리 점검'),
            dict(base, signal_id='SIG-RATE-002', internal_discussion_topic='곡선 점검'),
        ]
        result = unique_rise_candidates(rows)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['signal_id'], 'SIG-RATE-001,SIG-RATE-002')
        self.assertIn('금리 점검', result[0]['angle'])
        self.assertIn('곡선 점검', result[0]['angle'])

    def test_conflicting_metadata_fails_closed(self):
        base = dict(name='RISE Test', code='123456', basis='NAME_ONLY_UNVERIFIED_EXPOSURE',
                    inventory_asof='2026-11-04', required_check='확인', internal_discussion_topic='조사',
                    signal_id='SIG-RATE-001')
        with self.assertRaises(ValueError):
            unique_rise_candidates([base, dict(base, name='Different name')])

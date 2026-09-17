import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from build_universe import build
from update_daily import ROOT, write_json


class UniverseTests(unittest.TestCase):
    def fixture(self, root):
        for path in ('universe/policy.json','series_sources.json','overseas_sources.json'):
            write_json(root/path, json.loads((ROOT/'data'/path).read_text()))
        return json.loads((root/'universe/policy.json').read_text())

    def test_cross_listing_group_does_not_double_count_or_promote(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); self.fixture(root)
            result=build(root)
            us=next(g for g in result['groups'] if g['id']=='US_LARGE_CAP')
            self.assertEqual(len(us['candidates']),2)
            self.assertEqual(us['max_overview_votes_after_validation'],1)
            self.assertIsNone(us['selected_instrument_id'])
            self.assertEqual(result['selected_count'],0)
            self.assertIsNone(result['ranking'])
            company=next(g for g in result['groups'] if g['scope']=='COMPANY')
            self.assertEqual(company['max_overview_votes_after_validation'],0)

    def test_duplicates_unknown_and_unreviewed_activation_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); original=self.fixture(root)
            for mode in ('duplicate','unknown','activation'):
                policy=copy.deepcopy(original)
                if mode=='duplicate':policy['groups'][1]['candidates'].append(policy['groups'][0]['candidates'][0])
                elif mode=='unknown':policy['groups'][0]['candidates']=['XKRX:UNKNOWN']
                else:policy['activation_date']='2026-09-17'
                write_json(root/'universe/policy.json',policy)
                with self.assertRaises(ValueError):build(root)

    def test_new_instrument_is_unmapped_not_automatically_selected(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); self.fixture(root)
            config=json.loads((root/'overseas_sources.json').read_text())
            config['instruments'].append({**config['instruments'][0],'code':'NEW'})
            write_json(root/'overseas_sources.json',config)
            self.assertEqual(build(root)['unmapped_instruments'],['US_LISTED:NEW'])

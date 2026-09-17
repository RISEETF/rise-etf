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
            self.assertEqual(us['max_primary_representatives_per_group'],1)
            self.assertIsNone(us['selected_instrument_id'])
            self.assertEqual(result['selected_count'],0)
            self.assertIsNone(result['ranking'])
            company=next(g for g in result['groups'] if g['scope']=='COMPANY')
            self.assertEqual(company['overview_votes'],0)

    def test_duplicates_unknown_and_unreviewed_activation_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); original=self.fixture(root)
            for mode in ('duplicate','unknown','activation'):
                policy=copy.deepcopy(original)
                if mode=='duplicate':policy['groups'][0]['candidates'].append(policy['groups'][0]['candidates'][0])
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

    def test_issuer_facts_do_not_clear_selection_gates(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); self.fixture(root)
            facts=json.loads((ROOT/'data/universe/issuer_evidence.json').read_text())
            write_json(root/'universe/issuer_evidence.json', facts)
            result=build(root)
            self.assertEqual(result['issuer_evidence_count'],2)
            candidate=next(c for g in result['groups'] for c in g['candidates'] if c['instrument_id']=='US_LISTED:IEF')
            self.assertFalse(candidate['rs_eligible'])
            self.assertIn('benchmark_and_holdings',candidate['missing_evidence'])
            self.assertEqual(result['selected_count'],0)
            facts['records'][0]['rs_eligible']=True
            write_json(root/'universe/issuer_evidence.json',facts)
            with self.assertRaises(ValueError):build(root)
            facts['records'][0]['rs_eligible']=False
            facts['records'][0]['group_id']='US_TREASURY_INTERMEDIATE'
            write_json(root/'universe/issuer_evidence.json',facts)
            with self.assertRaises(ValueError):build(root)

    def test_multiple_exposures_and_empty_groups_preserve_unique_counts(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); policy=self.fixture(root)
            before=build(root)
            policy['groups'].append({'id':'TEST_LINK','label':'Synthetic overlap','scope':'THEME','candidates':['US_LISTED:AAPL']})
            policy['groups'].append({'id':'TEST_GAP','label':'Uncovered exposure','scope':'MARKET','candidates':[]})
            policy['evidence']={'US_LISTED:AAPL':{field:True for field in policy['required_evidence']}}
            write_json(root/'universe/policy.json',policy)
            after=build(root)
            self.assertEqual(after['candidate_count'],before['candidate_count'])
            self.assertEqual(after['candidate_link_count'],before['candidate_link_count']+1)
            self.assertEqual(after['gap_group_count'],before['gap_group_count']+1)
            self.assertEqual(after['groups'][-1]['selection_status'],'DATA_GAP')
            self.assertEqual(after['groups'][-2]['candidates'][0]['missing_evidence'],policy['required_evidence'])
            self.assertTrue(all(g['overview_votes']==0 for g in after['groups']))

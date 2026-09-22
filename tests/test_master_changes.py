import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from master_changes import record_changes


class MasterChangeTests(unittest.TestCase):
    def test_pending_code_resolution_preserves_membership(self):
        row={'detail_id':'44L1','code':None,'name':'RISE 신규','listed_on':'2026-09-22'}
        old={'products':[], 'pending_products':[row], 'source_sha256':'a',
             'retrieved_at':'2026-09-22T01:00:00+00:00','effective_date':'2026-09-22'}
        new={**old,'products':[{**row,'code':'123456'}],'pending_products':[],'source_sha256':'b'}
        with tempfile.TemporaryDirectory() as d:
            result=record_changes(Path(d),old,new)
            self.assertEqual([e['kind'] for e in result['events']],['CODE_UPDATED'])
            self.assertIsNone(result['events'][0]['previous_code'])
            self.assertEqual(result['source_product_count'],1)
            self.assertEqual(result['instrument_count'],1)

    def test_add_remove_rename_and_unchanged_poll(self):
        def snap(rows,sha):
            return {'products':[{'code':c,'name':n,'listed_on':'2026-09-22'} for c,n in rows],
                    'retrieved_at':'2026-09-22T01:00:00+00:00','effective_date':'2026-09-22','source_sha256':sha}
        old=snap([('111111','RISE A'),('222222','RISE B')],'old')
        new=snap([('222222','RISE 이름변경'),('333333','RISE 신규')],'new')
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            baseline=record_changes(root,None,old)
            self.assertEqual(baseline['events'],[])
            changed=record_changes(root,old,new)
            self.assertEqual({e['kind'] for e in changed['events']},{'ADDED_TO_OFFICIAL_LIST','REMOVED_FROM_OFFICIAL_LIST','NAME_CHANGED'})
            self.assertFalse(next(e for e in changed['events'] if e['code']=='111111')['delisting_confirmed'])
            unchanged=record_changes(root,new,new)
            self.assertEqual(unchanged['last_check_change_count'],0)
            self.assertEqual(len(unchanged['events']),3)
            self.assertEqual(unchanged['instrument_count'],2)

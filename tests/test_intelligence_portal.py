import json, unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from validate_intelligence_snapshot import validate
class TestIntelligencePortal(unittest.TestCase):
    def setUp(self): self.data=json.loads((Path(__file__).resolve().parents[1]/"intelligence/data/latest.json").read_text(encoding="utf-8"))
    def test_latest_is_valid(self): self.assertEqual(validate(self.data), [])
    def test_transition_gate_is_boolean(self):
        if self.data.get('snapshot_type')=='SUMMARY_ONLY': self.assertNotIn('regime_history_update',self.data)
        else: self.assertIsInstance(self.data["regime_history_update"]["transition_gate_crossed"], bool)
    def test_framework_statuses(self):
        if self.data.get('snapshot_type')=='SUMMARY_ONLY': self.assertEqual(validate(self.data),[])
        else:
            allowed={"CANDIDATE","SHADOW","VALIDATED","FROZEN"}; self.assertTrue(all(x["status"] in allowed for x in self.data["framework_updates"]))
    def test_summary_requires_explicit_type_and_cannot_fabricate_confidence(self):
        d={'snapshot_type':'SUMMARY_ONLY','asof_date':'2026-10-06','market_data_asof':'2026-10-05',
           'current_regime':'test','regime_change_status':'CHALLENGE','top_change':'test',
           'report_generated_at':'2026-10-06T07:35:00+09:00','full_report_path':'reports/2026-10-06.html'}
        self.assertEqual(validate(d),[])
        self.assertTrue(validate({k:v for k,v in d.items() if k!='snapshot_type'}))
        self.assertTrue(validate(dict(d,regime_confidence=0)))
        self.assertTrue(validate(dict(d,full_report_path='https://example.com')))
    def test_full_contract_still_rejects_missing_gate(self):
        d=json.loads((Path(__file__).resolve().parents[1]/'intelligence/data/daily/2026-09-22.json').read_text())
        self.assertEqual(validate(d),[])
        del d['regime_history_update']
        self.assertTrue(validate(d))
    def test_summary_optional_fields_pending_report_and_version(self):
        d={'schema_version':'1.0','snapshot_type':'SUMMARY_ONLY','asof_date':'2026-10-15',
           'market_data_asof':'2026-10-14','current_regime':'test','regime_change_status':'CHALLENGE',
           'top_change':'test','report_generated_at':'2026-10-15T07:00:00+09:00',
           'full_report_path':None,'report_status':'SUMMARY_ONLY_FULL_REPORT_PENDING',
           'framework_updates':[{'name':'test','status':'RESEARCH_REQUIRED'}],'production_eligible':False}
        self.assertEqual(validate(d),[])
        for change in ({'schema_version':'2.0'},{'production_eligible':True},{'production_eligible':0},
                       {'report_status':'PUBLISHED'},{'framework_updates':[None]},
                       {'key_triggers':'text'},{'report_generated_at':3},{'top_rise_matches':[{'name':False}]},
                       {'full_report_path':'reports/2026-10-15.html'}):
            with self.subTest(change=change): self.assertTrue(validate(dict(d,**change)))
    def test_archive_consistency(self):
        root=Path(__file__).resolve().parents[1]/"intelligence"; m=json.loads((root/"data/archive.json").read_text(encoding="utf-8")); self.assertIn(m["latest"],m["dates"])
        for day in m['dates']:
            d=json.loads((root/f'data/daily/{day}.json').read_text())
            self.assertEqual(validate(d),[],day)
            if d.get('full_report_path'): self.assertTrue((root/d['full_report_path']).exists(),day)
        self.assertEqual(self.data,json.loads((root/f"data/daily/{m['latest']}.json").read_text()))
if __name__=="__main__": unittest.main()

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
        if self.data.get('snapshot_type')=='SUMMARY_ONLY': self.assertNotIn('framework_updates',self.data)
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
    def test_archive_consistency(self):
        root=Path(__file__).resolve().parents[1]/"intelligence"; m=json.loads((root/"data/archive.json").read_text(encoding="utf-8")); self.assertIn(m["latest"],m["dates"])
        for d in m["dates"]: self.assertTrue((root/f"data/daily/{d}.json").exists()); self.assertTrue((root/f"reports/{d}.html").exists())
if __name__=="__main__": unittest.main()

import json, unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from validate_intelligence_snapshot import validate
class TestIntelligencePortal(unittest.TestCase):
    def setUp(self): self.data=json.loads((Path(__file__).resolve().parents[1]/"intelligence/data/latest.json").read_text(encoding="utf-8"))
    def test_latest_is_valid(self): self.assertEqual(validate(self.data), [])
    def test_transition_gate_is_boolean(self): self.assertIsInstance(self.data["regime_history_update"]["transition_gate_crossed"], bool)
    def test_framework_statuses(self):
        allowed={"CANDIDATE","SHADOW","VALIDATED","FROZEN"}; self.assertTrue(all(x["status"] in allowed for x in self.data["framework_updates"]))
    def test_archive_consistency(self):
        root=Path(__file__).resolve().parents[1]/"intelligence"; m=json.loads((root/"data/archive.json").read_text(encoding="utf-8")); self.assertIn(m["latest"],m["dates"])
        for d in m["dates"]: self.assertTrue((root/f"data/daily/{d}.json").exists()); self.assertTrue((root/f"reports/{d}.html").exists())
if __name__=="__main__": unittest.main()

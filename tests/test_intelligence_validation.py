import json, unittest
from pathlib import Path

class TestValidationFoundation(unittest.TestCase):
    def test_glossary_has_zscore(self):
        p=Path(__file__).resolve().parents[1]/"data/intelligence/glossary_ko.json"
        d=json.loads(p.read_text(encoding="utf-8"))
        self.assertTrue(any(x["term"]=="Z-score" for x in d["terms"]))

    def test_validation_output_contract(self):
        p=Path(__file__).resolve().parents[1]/"data/validation/v1_status.json"
        d=json.loads(p.read_text(encoding="utf-8"))
        self.assertIn(d["validation_state"],{"INSUFFICIENT_HISTORY","READY_FOR_HISTORICAL_CALIBRATION"})
        self.assertFalse(d["production_eligible"])

if __name__=="__main__": unittest.main()

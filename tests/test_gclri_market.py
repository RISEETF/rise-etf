import json, unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from collect_gclri_market import parse_series

class TestGCLRICollector(unittest.TestCase):
    def test_parse_fred_csv(self):
        txt="DATE,DGS10\n2026-09-24,5.10\n2026-09-25,.\n2026-09-26,5.20\n"
        rows=parse_series(txt,"DGS10")
        self.assertEqual(len(rows),2)
        self.assertEqual(rows[-1]["date"],"2026-09-26")
        self.assertAlmostEqual(rows[-1]["value"],5.20)

    def test_registry_has_unique_ids(self):
        p=Path(__file__).resolve().parents[1]/"data/gclri/series_registry.json"
        d=json.loads(p.read_text(encoding="utf-8"))
        ids=[x["id"] for x in d["series"]]
        self.assertEqual(len(ids),len(set(ids)))
        self.assertIn("SOFR",ids)
        self.assertIn("BAMLH0A0HYM2",ids)

if __name__=="__main__": unittest.main()

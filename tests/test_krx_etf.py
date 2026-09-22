import datetime as dt
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "collect_krx_etf.py"
SPEC = importlib.util.spec_from_file_location("collect_krx_etf", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class KrxEtfTest(unittest.TestCase):
    def fixture(self):
        return {"OutBlock_1": [
            {"BAS_DD": "20260918", "ISU_SRT_CD": "123456", "ISU_NM": "TEST ETF",
             "TDD_CLSPRC": "10,000", "NAV": "9,990.25", "ACC_TRDVOL": "100",
             "ACC_TRDVAL": "1,000,000", "MKTCAP": "10,000,000",
             "INVSTASST_NETASST_TOTAMT": "9,990,000", "LIST_SHRS": "1,000"},
            {"BAS_DD": "20260918", "ISU_SRT_CD": "654321", "ISU_NM": "SECOND ETF",
             "TDD_CLSPRC": "20,000", "NAV": "20,010", "ACC_TRDVOL": "200",
             "ACC_TRDVAL": "4,000,000", "MKTCAP": "20,000,000",
             "INVSTASST_NETASST_TOTAMT": "20,010,000", "LIST_SHRS": "1,000"},
        ]}

    def test_parse_and_accumulate_idempotently(self):
        raw = json.dumps(self.fixture()).encode()
        snapshot = MODULE.parse_snapshot(raw, dt.date(2026, 9, 18))
        self.assertEqual(snapshot["records"][0]["close"], 10000)
        with tempfile.TemporaryDirectory() as temp:
            db = Path(temp) / "krx.sqlite"
            first = MODULE.accumulate(db, snapshot, "hash-a", "2026-09-18T10:00:00+00:00")
            second = MODULE.accumulate(db, snapshot, "hash-b", "2026-09-18T11:00:00+00:00")
            self.assertEqual(first["new"], 14)
            self.assertEqual(second["unchanged"], 14)
            self.assertEqual(second["total"], 14)

    def test_reject_future_and_duplicate(self):
        raw = json.dumps(self.fixture()).encode()
        with self.assertRaisesRegex(ValueError, "FUTURE"):
            MODULE.parse_snapshot(raw, dt.date(2026, 9, 17))
        duplicate = self.fixture()
        duplicate["OutBlock_1"][1]["ISU_SRT_CD"] = "123456"
        with self.assertRaisesRegex(ValueError, "DUPLICATE"):
            MODULE.parse_snapshot(json.dumps(duplicate).encode(), dt.date(2026, 9, 18))

    def test_completeness_rejects_partial_and_stale_snapshots(self):
        snapshot = MODULE.parse_snapshot(json.dumps(self.fixture()).encode(), dt.date(2026, 9, 18))
        with tempfile.TemporaryDirectory() as temp:
            db = Path(temp) / "krx.sqlite"
            with self.assertRaisesRegex(ValueError, "UNIVERSE_TOO_SMALL"):
                MODULE.validate_completeness(db, snapshot, dt.date(2026, 9, 18))
            expanded = {"page_date": "2026-09-01", "records": snapshot["records"] * 250}
            with self.assertRaisesRegex(ValueError, "STALE"):
                MODULE.validate_completeness(db, expanded, dt.date(2026, 9, 18))

    def test_completeness_rejects_low_coverage_and_universe_collapse(self):
        base = self.fixture()["OutBlock_1"][0]
        rows = []
        for number in range(100000, 100600):
            row = dict(base)
            row["ISU_SRT_CD"] = str(number)
            rows.append(row)
        snapshot = MODULE.parse_snapshot(json.dumps({"OutBlock_1": rows}).encode(), dt.date(2026, 9, 18))
        with tempfile.TemporaryDirectory() as temp:
            db = Path(temp) / "krx.sqlite"
            quality = MODULE.validate_completeness(db, snapshot, dt.date(2026, 9, 18))
            self.assertEqual(quality["lag_calendar_days"], 0)
            MODULE.accumulate(db, snapshot, "hash-a", "2026-09-18T10:00:00+00:00")
            collapsed = {"page_date": "2026-09-19", "records": snapshot["records"][:500]}
            with self.assertRaisesRegex(ValueError, "UNIVERSE_COLLAPSE"):
                MODULE.validate_completeness(db, collapsed, dt.date(2026, 9, 19))
            for item in snapshot["records"][:40]:
                item["nav"] = None
            with self.assertRaisesRegex(ValueError, "FIELD_COVERAGE_LOW"):
                MODULE.validate_completeness(Path(temp) / "empty.sqlite", snapshot, dt.date(2026, 9, 18))


if __name__ == "__main__":
    unittest.main()

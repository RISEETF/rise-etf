import importlib.util
from pathlib import Path
import sys
import unittest
import base64
import gzip
import hashlib
import json
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location("master", ROOT / "scripts/update_official_master.py")
master = importlib.util.module_from_spec(spec)
spec.loader.exec_module(master)


class OfficialMasterTests(unittest.TestCase):
    def test_latest_capture_matches_preserved_overview_and_listing(self):
        snapshot = json.loads((ROOT / "data/master/latest.json").read_text())
        def source(digest):
            record = json.loads((ROOT / "data/raw/rise_finder" / f"{digest}.json").read_text())
            raw = gzip.decompress(base64.b64decode(record["content"]))
            self.assertEqual(hashlib.sha256(raw).hexdigest(), digest)
            return raw.decode()
        total, effective = master.extract_overview(source(snapshot["overview_sha256"]))
        self.assertEqual(total, snapshot["instrument_count"])
        self.assertEqual(effective, snapshot["effective_date"])
        products = master.validate_master(master.parse_products(source(snapshot["source_sha256"])), total)
        self.assertEqual(products, snapshot["products"])

    def test_daily_vintage_is_immutable_and_latest_cannot_regress(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = {"effective_date":"2026-09-11", "retrieved_at":"2026-09-11T01:00:00+00:00", "source_sha256":"a"}
            revised = {**first, "retrieved_at":"2026-09-11T02:00:00+00:00", "source_sha256":"b"}
            master.persist_master(root, first)
            master.persist_master(root, revised)
            self.assertEqual(json.loads((root / "2026-09-11.json").read_text()), first)
            self.assertEqual(json.loads((root / "latest.json").read_text()), revised)
            self.assertEqual(len(list((root / "captures").glob("*.json"))), 2)
            with self.assertRaises(ValueError):
                master.persist_master(root, {**revised, "effective_date":"2026-09-10"})
            self.assertEqual(json.loads((root / "latest.json").read_text()), revised)

    def test_preserved_official_snapshot_and_secondary_identity(self):
        snapshot = json.loads((ROOT / "data/master/2026-09-11.json").read_text())
        digest = snapshot["source_sha256"]
        envelope = json.loads((ROOT / "data/raw/rise_finder" / f"{digest}.json").read_text())
        raw = gzip.decompress(base64.b64decode(envelope["content"]))
        self.assertEqual(hashlib.sha256(raw).hexdigest(), digest)
        products = master.validate_master(master.parse_products(raw.decode()), 143)
        self.assertEqual([(p["code"], p["name"]) for p in products],
                         [(p["code"], p["name"]) for p in snapshot["products"]])
        secondary_digest = "1c2772e3d2c1ce91ca882d9bb52d20ade00b05f59362ec3c0cbdaf14648e011f"
        secondary = json.loads((ROOT / "data/raw/naver" / f"{secondary_digest}.json").read_text())
        secondary_raw = base64.b64decode(secondary["raw_base64"])
        self.assertEqual(hashlib.sha256(secondary_raw).hexdigest(), secondary_digest)
        quotes = json.loads(secondary_raw.decode("cp949"))["result"]["etfItemList"]
        result = master.reconcile_secondary_capture(products, quotes)
        self.assertEqual(result["status"], "EXACT_IDENTITY_MATCH")
        self.assertEqual(result["secondary_rise_count"], 143)
        legacy = json.loads((ROOT / "data/2026-09-10.json").read_text())["items"]
        actual = master.reconcile_legacy(products, legacy)
        from collections import Counter
        self.assertEqual(dict(Counter(row["status"] for row in actual)), {
            "IDENTITY_MATCH": 20, "OFFICIAL_NAME_MISMATCH": 4,
            "NOT_IN_OFFICIAL_CURRENT_MASTER": 124})

    def test_parser_handles_standard_and_embedded_codes(self):
        row = lambda body: '<tr data-class="dataList">' + body + '</tr>'
        fixture = row('''
          <th><span class="tag_type01">글로벌주식</span>
          <span class="tag_type02">미국</span><span class="tag_type03">개인연금</span>
          <p><a href="/prod/finderDetail/AAAA">RISE 표준</a></p>
          <span class="code">(123456)</span><div class="graph">noise</div></th>
          <td>10,000</td><td>연 0.1</td><td>-</td><td>-</td><td>-</td>
          <td>-</td><td>-</td><td>-</td><td>2020.01.02</td><td>비교</td>
        ''') + row('''
          <th><span class="tag_type01">국내주식</span>
          <p><a href="/prod/finderDetail/BBBB">RISE 예외 (0123A0)</a></p></th>
          <td>10,000</td><td>연 0.2</td><td>-</td><td>-</td><td>-</td>
          <td>-</td><td>-</td><td>-</td><td>2021.02.03</td><td>비교</td>
        ''')
        products = master.parse_products(fixture)
        self.assertEqual([p["code"] for p in products], ["123456", "0123A0"])
        self.assertEqual(products[1]["name"], "RISE 예외")
        self.assertEqual(products[0]["published_total_fee"], "연 0.1")

    def test_master_rejects_duplicates_and_count_mismatch(self):
        item = {"code": "123456", "detail_id": "A"}
        with self.assertRaises(ValueError):
            master.validate_master([item, item], 2)
        with self.assertRaises(ValueError):
            master.validate_master([item], 2)

    def test_reconciliation_uses_official_identity(self):
        products = [{"code":"123456", "name":"RISE 공식"}]
        rows = [["123456", "RISE 공식"], ["999999", "RISE 없음"]]
        states = [r["status"] for r in master.reconcile_legacy(products, rows)]
        self.assertEqual(states, ["IDENTITY_MATCH", "NOT_IN_OFFICIAL_CURRENT_MASTER"])


if __name__ == "__main__":
    unittest.main()

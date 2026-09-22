import datetime as dt
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from collect_series import parse_naver, parse_ecb, capture
from build_research_db import build
from update_daily import write_json

TODAY = dt.date(2026, 9, 16)
NOW = dt.datetime(2026, 9, 16, tzinfo=dt.timezone.utc)
PRICE = b'<protocol><chartdata symbol="148020"><item data="20260915|100|110|90|105|20"/></chartdata></protocol>'
FX = b'<Envelope><Cube><Cube time="2026-09-15"><Cube currency="USD" rate="1.25"/><Cube currency="KRW" rate="1750"/></Cube></Cube></Envelope>'


class SeriesTests(unittest.TestCase):
    def test_price_identity_future_duplicate_and_ohlc_rejected(self):
        self.assertEqual(parse_naver(PRICE,"148020",TODAY)[0]["close"],105)
        for raw in (PRICE.replace(b'148020',b'999999'), PRICE.replace(b'20260915',b'20260917'),
                    PRICE.replace(b'|110|',b'|95|'), PRICE.replace(b'</chartdata>',b'<item data="20260915|100|110|90|105|20"/></chartdata>')):
            with self.assertRaises(ValueError):
                parse_naver(raw,"148020",TODAY)

    def test_euckr_source_supported_without_changing_raw(self):
        raw = '<?xml version="1.0" encoding="EUC-KR"?><protocol><chartdata symbol="148020" name="한국"><item data="20260915|100|110|90|105|20"/></chartdata></protocol>'.encode("cp949")
        self.assertEqual(parse_naver(raw,"148020",TODAY)[0]["close"],105)

    def test_fx_cross_direction_and_missing_leg(self):
        rows = parse_ecb(FX,TODAY)
        cross = next(r for r in rows if r["base"]=="USD")
        self.assertEqual(cross["rate"],1400)
        for raw in (FX.replace(b'KRW',b'JPY'), FX.replace(b'1.25',b'NaN'), FX.replace(b'2026-09-15',b'2026-09-17')):
            with self.assertRaises(ValueError):
                parse_ecb(raw,TODAY)

    def test_database_vintages_rebuild_and_tamper_protection(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            write_json(root / "master/latest.json", {"effective_date":"2026-09-16", "products":[{"code":"148020","name":"RISE 200"}]})
            write_json(root / "master/changes.json", {"effective_date":"2026-09-16", "events":[]})
            write_json(root / "series_sources.json", {"price_instruments":[{"code":"148020","name":"RISE 200"}]})
            first=capture(root,"NAVER_CHART_CANDIDATE","https://example.test", "PRICE","148020",fetcher=lambda _:PRICE,now=NOW)
            capture(root,"NAVER_CHART_CANDIDATE","https://example.test", "PRICE","148020",fetcher=lambda _:PRICE.replace(b'|105|',b'|106|'),now=NOW+dt.timedelta(hours=1))
            capture(root,"ECB_REFERENCE","https://example.test", "FX",fetcher=lambda _:FX,now=NOW)
            db=root / "research.sqlite"
            result=build(root,db)
            self.assertFalse(result["series"][0]["rs_eligible"])
            self.assertIsNone(result["ranking"])
            self.assertEqual(result["fx"]["observations"],1)
            with sqlite3.connect(db) as connection:
                self.assertEqual(connection.execute("SELECT COUNT(*) FROM prices").fetchone()[0],2)
                self.assertEqual(connection.execute("SELECT close FROM latest_prices").fetchone()[0],106)
                value=connection.execute("SELECT close FROM prices JOIN captures USING(capture_id) WHERE retrieved_at<=?",(NOW.isoformat(),)).fetchone()[0]
                self.assertEqual(value,105)
            self.assertEqual(build(root,db)["series"][0]["observations"],1)
            preserved=db.read_bytes()
            first["observations"][0]["close"]=999
            write_json(root / "series/captures" / (first["capture_id"]+".json"),first)
            with self.assertRaises(ValueError):
                build(root,db)
            self.assertEqual(db.read_bytes(),preserved)

    def test_failure_and_capture_collision_preserve_history(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            result=capture(root,"NAVER_CHART_CANDIDATE","https://example.test","PRICE","148020",fetcher=lambda _:b'invalid',now=NOW)
            self.assertEqual(result["status"],"FAILED")
            self.assertEqual(result["observations"],[])
            with self.assertRaises(ValueError):
                capture(root,"NAVER_CHART_CANDIDATE","https://example.test","PRICE","148020",fetcher=lambda _:PRICE,now=NOW)
            stored=json.loads(next((root / "series/captures").glob("*.json")).read_text())
            self.assertEqual(stored,result)

    def test_master_removal_and_rename_preserve_price_history(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            old={"effective_date":"2026-09-15", "products":[{"code":"148020","name":"Old name"}]}
            write_json(root / "master/2026-09-15.json", old)
            write_json(root / "master/latest.json", {"effective_date":"2026-09-16","products":[]})
            write_json(root / "series_sources.json", {"price_instruments":[]})
            capture(root,"NAVER_CHART_CANDIDATE","https://example.test","PRICE","148020",fetcher=lambda _:PRICE,now=NOW)
            db=root / "research.sqlite"
            build(root,db)
            with sqlite3.connect(db) as connection:
                self.assertEqual(connection.execute("SELECT close FROM latest_prices").fetchone()[0],105)
                self.assertEqual(connection.execute("SELECT COUNT(*) FROM master_memberships WHERE is_current=1").fetchone()[0],0)
            write_json(root / "master/latest.json", {"effective_date":"2026-09-16","products":[{"code":"148020","name":"New name"}]})
            build(root,db)
            with sqlite3.connect(db) as connection:
                self.assertEqual(connection.execute("SELECT name FROM instruments").fetchone()[0],"New name")
                self.assertEqual(connection.execute("SELECT name FROM master_memberships WHERE is_current=0").fetchone()[0],"Old name")


if __name__ == "__main__":
    unittest.main()

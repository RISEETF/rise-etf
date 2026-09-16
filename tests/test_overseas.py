import datetime as dt
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from collect_overseas import parse_yahoo, audit_adjustments, capture_overseas
from build_research_db import build
from update_daily import write_json

ITEM={"code":"TEST","name":"Test equity","market":"US_LISTED","currency":"USD","instrument_type":"EQUITY","timezone":"America/New_York"}
NOW=dt.datetime(2026,9,16,tzinfo=dt.timezone.utc)
T1=int(dt.datetime(2026,9,14,13,30,tzinfo=dt.timezone.utc).timestamp())
T2=int(dt.datetime(2026,9,15,13,30,tzinfo=dt.timezone.utc).timestamp())


def fixture():
    return {"chart":{"error":None,"result":[{"meta":{"symbol":"TEST","currency":"USD","instrumentType":"EQUITY","exchangeTimezoneName":"America/New_York"},
        "timestamp":[T1,T2],"indicators":{"quote":[{"open":[100,99],"high":[101,100],"low":[99,98],"close":[100,99],"volume":[10,20]}],
        "adjclose":[{"adjclose":[99,99]}]},"events":{"dividends":{str(T2):{"date":T2,"amount":1}}}}]}}


class OverseasTests(unittest.TestCase):
    def parse(self,payload):
        return parse_yahoo(json.dumps(payload).encode(),ITEM,NOW)

    def test_identity_currency_and_array_validation(self):
        for field,value in (("symbol","OTHER"),("currency","KRW"),("exchangeTimezoneName","UTC"),("instrumentType","ETF")):
            p=fixture();p["chart"]["result"][0]["meta"][field]=value
            with self.assertRaises(ValueError):self.parse(p)
        p=fixture();p["chart"]["result"][0]["indicators"]["adjclose"][0]["adjclose"]=[1]
        with self.assertRaises(ValueError):self.parse(p)

    def test_missing_prices_are_reported_not_filled(self):
        p=fixture();p["chart"]["result"][0]["indicators"]["quote"][0]["close"][0]=None
        result=self.parse(p)
        self.assertEqual(len(result["observations"]),1)
        self.assertEqual(result["missing_dates"],["2026-09-14"])

    def test_duplicate_future_timestamp_and_nonfinite_price(self):
        for change in ("duplicate","future","nan"):
            p=fixture();r=p["chart"]["result"][0]
            if change=="duplicate":r["timestamp"][1]=T1
            elif change=="future":r["timestamp"][1]=int(NOW.timestamp())+86400
            else:r["indicators"]["adjclose"][0]["adjclose"][0]=float("nan")
            with self.assertRaises(ValueError):self.parse(p)

    def test_dividend_factor_and_no_double_split(self):
        p=fixture();result=self.parse(p)
        audit=audit_adjustments(result["observations"],result["events"])
        self.assertAlmostEqual(audit["factor_changes"][0]["cash_residual"],0)
        self.assertFalse(audit["rs_eligible"])
        p["chart"]["result"][0]["events"]["splits"]={str(T2):{"date":T2,"numerator":4,"denominator":1}}
        with_split=self.parse(p)
        self.assertEqual(with_split["observations"],result["observations"])
        self.assertEqual(audit_adjustments(with_split["observations"],with_split["events"])["split_count"],1)

    def test_same_database_and_events_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            config={"source_id":"YAHOO_CHART_CANDIDATE","url_template":"https://example.test/{code}","instruments":[ITEM]}
            write_json(root/"overseas_sources.json",config)
            write_json(root/"series_sources.json",{"price_instruments":[]})
            write_json(root/"master/latest.json",{"effective_date":"2026-09-16","products":[]})
            result=capture_overseas(root,config,ITEM,fetcher=lambda _:json.dumps(fixture()).encode(),now=NOW)
            summary=build(root,root/"research.sqlite")
            self.assertEqual(summary["series"][0]["observations"],2)
            self.assertIsNone(summary["ranking"])
            with sqlite3.connect(root/"research.sqlite") as connection:
                self.assertEqual(connection.execute("SELECT COUNT(*) FROM corporate_actions").fetchone()[0],1)
                self.assertEqual(connection.execute("SELECT adjusted_close FROM prices LIMIT 1").fetchone()[0],99)
            result["events"][0]["amount"]=2
            write_json(root/"series/captures"/(result["capture_id"]+".json"),result)
            with self.assertRaises(ValueError):build(root,root/"research.sqlite")


if __name__=="__main__":unittest.main()

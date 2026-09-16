import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from verify_apple_actions import amount_checks, split_check, load_provider

ROOT=Path(__file__).resolve().parents[1]


class AppleActionTests(unittest.TestCase):
    def test_record_date_is_not_relabelled_as_ex_date(self):
        issuer={"accessed_date":"2026-09-16","splits":[],"dividends":[
            {"record_date":"2024-11-11","payable_date":"2024-11-14","amount":.25}]}
        events=[{"kind":"DIVIDEND","date":"2024-11-08","amount":.25,"event_id":"one"}]
        result=amount_checks(events,issuer,"2024-09-16","2026-09-15")
        self.assertEqual(result["matched_amount_count"],1)
        self.assertFalse(result["checks"][0]["ex_date_verified"])
        self.assertEqual(result["checks"][0]["provider_event_date"],"2024-11-08")
        events[0]["amount"]=.3
        self.assertEqual(amount_checks(events,issuer,"2024-09-16","2026-09-15")["checks"][0]["status"],"AMOUNT_MISMATCH")

    def test_official_unadjusted_cash_is_not_compared_naively(self):
        issuer={"accessed_date":"2026-09-16","splits":[{"first_split_adjusted_trading_date":"2020-08-31","numerator":4,"denominator":1}],
                "dividends":[{"record_date":"2020-08-10","payable_date":"2020-08-13","amount":.82}]}
        event={"kind":"DIVIDEND","date":"2020-08-07","amount":.205,"event_id":"one"}
        result=amount_checks([event],issuer,"2020-08-01","2020-09-15")
        self.assertEqual(result["matched_amount_count"],1)
        self.assertEqual(result["checks"][0]["subsequent_split_divisor"],4)
        duplicate={**event,"event_id":"two"}
        self.assertEqual(amount_checks([event,duplicate],issuer,"2020-08-01","2020-09-15")["matched_amount_count"],0)

    def test_split_uses_first_trading_date_and_preserves_prices(self):
        rows=[{"date":"2020-08-28","close":125},{"date":"2020-08-31","close":130}]
        original=copy.deepcopy(rows)
        issuer={"first_split_adjusted_trading_date":"2020-08-31","faq_generic_split_date":"2020-08-28","numerator":4,"denominator":1}
        events=[{"kind":"SPLIT","date":"2020-08-31","numerator":4,"denominator":1}]
        result=split_check(rows,events,issuer)
        self.assertEqual(result["status"],"SPLIT_EVENT_DATE_AND_RATIO_MATCH")
        self.assertAlmostEqual(result["as_received_close_return"],.04)
        self.assertAlmostEqual(result["incorrect_return_if_previous_close_divided_again"],3.16)
        self.assertEqual(rows,original)
        events[0]["date"]="2020-08-28"
        self.assertEqual(split_check(rows,events,issuer)["status"],"SPLIT_EVENT_MISMATCH")

    def test_preserved_real_case_reproduces_report(self):
        data=ROOT/"data"
        issuer=json.loads((data/"validation/apple_official_extract.json").read_text())
        manifest=json.loads((data/"validation/aapl_2020/manifest.json").read_text())
        report=json.loads((data/"quality/apple_issuer_validation.json").read_text())
        self.assertEqual(hashlib.sha256((data/"validation/apple_official_extract.json").read_bytes()).hexdigest(),report["issuer_evidence_file_sha256"])
        for label,root,key in (("current_cash",data,"current_capture_id"),("historical_cash",data/"validation/aapl_2020","historical_capture_id")):
            record=load_provider(root,manifest[key],manifest["instrument_contract"])
            self.assertEqual(amount_checks(record["events"],issuer,record["first_date"],record["last_date"]),report[label])
        historical=load_provider(data/"validation/aapl_2020",manifest["historical_capture_id"],manifest["instrument_contract"])
        self.assertEqual(split_check(historical["observations"],historical["events"],issuer["splits"][0]),report["historical_split"])
        self.assertEqual(report["current_cash"]["matched_amount_count"],8)
        self.assertEqual(report["historical_cash"]["matched_amount_count"],1)
        self.assertFalse(report["rs_eligible"])


if __name__=="__main__":unittest.main()

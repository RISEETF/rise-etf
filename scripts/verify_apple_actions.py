#!/usr/bin/env python3
"""Bounded issuer-fact reconciliation, preserving record/ex-date distinctions."""
import argparse
import base64
import datetime as dt
import gzip
import hashlib
import json
from pathlib import Path
from collect_overseas import capture_overseas, parse_yahoo
from update_daily import ROOT, write_json


def amount_checks(events, issuer, first, last):
    """Seven-day windows associate candidates; they do not validate ex-dates."""
    selected=[d for d in issuer["dividends"] if first<=d["record_date"]<=last]
    checks=[]
    used=set()
    for dividend in sorted(selected,key=lambda d:d["record_date"]):
        record_date=dt.date.fromisoformat(dividend["record_date"])
        candidates=[e for e in events if e["kind"]=="DIVIDEND" and
                    0<=(record_date-dt.date.fromisoformat(e["date"])).days<=7]
        check={"issuer_record_date":dividend["record_date"],"issuer_payable_date":dividend["payable_date"],
               "issuer_unadjusted_amount":dividend["amount"],"ex_date_verified":False}
        if len(candidates)!=1 or candidates[0]["event_id"] in used:
            checks.append({**check,"status":"MISSING_OR_AMBIGUOUS_PROVIDER_EVENT"})
            continue
        event=candidates[0];used.add(event["event_id"])
        divisor=1.0
        for split in issuer["splits"]:
            if dividend["record_date"] < split["first_split_adjusted_trading_date"] <= issuer["accessed_date"]:
                divisor*=split["numerator"]/split["denominator"]
        expected=dividend["amount"]/divisor
        checks.append({**check,"provider_event_date":event["date"],"provider_amount":event["amount"],
                       "subsequent_split_divisor":divisor,"split_adjusted_expected_amount":expected,
                       "status":"AMOUNT_MATCH_ONLY" if abs(expected-event["amount"])<1e-8 else "AMOUNT_MISMATCH"})
    unmatched=[e for e in events if e["kind"]=="DIVIDEND" and e["event_id"] not in used]
    return {"checks":checks,"unmatched_provider_dividends":unmatched,
            "matched_amount_count":sum(c["status"]=="AMOUNT_MATCH_ONLY" for c in checks),
            "ex_date_status":"NOT_IN_ISSUER_SOURCE"}


def split_check(rows, events, official):
    day=official["first_split_adjusted_trading_date"]
    candidates=[e for e in events if e["kind"]=="SPLIT" and e["date"]==day]
    if len(candidates)!=1 or candidates[0]["numerator"]!=official["numerator"] or candidates[0]["denominator"]!=official["denominator"]:
        return {"status":"SPLIT_EVENT_MISMATCH","first_trading_date":day}
    index=next((i for i,r in enumerate(rows) if r["date"]==day),None)
    if index is None or index==0:
        return {"status":"PRICE_WINDOW_INCOMPLETE","first_trading_date":day}
    before,after=rows[index-1],rows[index]
    ratio=official["numerator"]/official["denominator"]
    observed_return=after["close"]/before["close"]-1
    return {"status":"SPLIT_EVENT_DATE_AND_RATIO_MATCH","first_trading_date":day,
            "ratio":ratio,"issuer_faq_generic_date":official.get("faq_generic_split_date"),
            "previous_price_date":before["date"],"previous_provider_close":before["close"],
            "split_date_provider_close":after["close"],"as_received_close_return":observed_return,
            "incorrect_return_if_previous_close_divided_again":after["close"]/(before["close"]/ratio)-1,
            "price_mutation_applied":False,"total_return_certified":False}


def load_provider(root, capture_id, instrument):
    record=json.loads((root/"series/captures"/f"{capture_id}.json").read_text())
    if record["status"]!="CAPTURED" or record["instrument_contract"]!=instrument:
        raise ValueError("Invalid AAPL capture")
    digest=record["source_sha256"]
    if len(digest)!=64 or any(c not in "0123456789abcdef" for c in digest):
        raise ValueError("Invalid raw hash")
    envelope=json.loads((root/"raw/series"/f"{digest}.json").read_text())
    raw=gzip.decompress(base64.b64decode(envelope["content"]))
    if hashlib.sha256(raw).hexdigest()!=digest:
        raise ValueError("Provider raw checksum mismatch")
    parsed=parse_yahoo(raw,instrument,dt.datetime.fromisoformat(record["retrieved_at"]))
    if parsed["observations"]!=record["observations"] or parsed["events"]!=record["events"]:
        raise ValueError("Normalized AAPL capture differs from raw")
    return record


def collect(data_dir):
    config=json.loads((data_dir/"overseas_sources.json").read_text())
    instrument=next(i for i in config["instruments"] if i["code"]=="AAPL")
    current=[]
    for path in (data_dir/"series/captures").glob("*-AAPL.json"):
        item=json.loads(path.read_text())
        if item["status"]=="CAPTURED":current.append(item)
    if not current:raise ValueError("Current AAPL capture is required")
    current=max(current,key=lambda r:r["retrieved_at"])
    start=int(dt.datetime(2020,8,1,tzinfo=dt.timezone.utc).timestamp())
    end=int(dt.datetime(2020,9,16,tzinfo=dt.timezone.utc).timestamp())
    config={**config,"url_template":f"https://query1.finance.yahoo.com/v8/finance/chart/{{code}}?period1={start}&period2={end}&interval=1d&events=div%2Csplits%2CcapitalGains&includeAdjustedClose=true"}
    root=data_dir/"validation/aapl_2020"
    historical=capture_overseas(root,config,instrument)
    if historical["status"]!="CAPTURED":
        raise ValueError(historical.get("error","Historical capture failed"))
    manifest={"current_capture_id":current["capture_id"],"historical_capture_id":historical["capture_id"],
              "instrument_contract":instrument,"scope":"VALIDATION_FIXTURE_ONLY_NOT_LIVE_UNIVERSE_HISTORY"}
    write_json(root/"manifest.json",manifest)


def verify(data_dir):
    data_dir=Path(data_dir)
    evidence_path=data_dir/"validation/apple_official_extract.json"
    evidence_raw=evidence_path.read_bytes()
    issuer=json.loads(evidence_raw)
    if issuer["amount_basis"]!="NOT_SPLIT_ADJUSTED" or issuer["symbol"]!="AAPL":
        raise ValueError("Unexpected issuer facts")
    root=data_dir/"validation/aapl_2020"
    manifest=json.loads((root/"manifest.json").read_text())
    instrument=manifest["instrument_contract"]
    current=load_provider(data_dir,manifest["current_capture_id"],instrument)
    historical=load_provider(root,manifest["historical_capture_id"],instrument)
    official=next(s for s in issuer["splits"] if s["first_split_adjusted_trading_date"]=="2020-08-31")
    report={"status":"PARTIAL_ISSUER_RECONCILIATION","rs_eligible":False,
            "issuer_source_url":issuer["source_url"],"issuer_accessed_date":issuer["accessed_date"],
            "issuer_extraction_method":issuer["extraction_method"],
            "issuer_evidence_file_sha256":hashlib.sha256(evidence_raw).hexdigest(),
            "original_issuer_html_sha256":None,
            "current_capture_id":current["capture_id"],"current_source_sha256":current["source_sha256"],
            "current_window":{"first_date":current["first_date"],"last_date":current["last_date"]},
            "historical_capture_id":historical["capture_id"],"historical_source_sha256":historical["source_sha256"],
            "current_cash":amount_checks(current["events"],issuer,current["first_date"],current["last_date"]),
            "historical_cash":amount_checks(historical["events"],issuer,historical["first_date"],historical["last_date"]),
            "historical_split":split_check(historical["observations"],historical["events"],official),
            "limitations":["Cash ex-dates not independently verified", "Manual official-page fact transcription, not automated source ingestion", "Split fixture remains outside live price coverage", "No full-market or total-return certification"]}
    write_json(data_dir/"quality/apple_issuer_validation.json",report)
    return report


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--collect",action="store_true",help="Fetch one bounded historical AAPL validation fixture")
    args=parser.parse_args()
    if args.collect:collect(ROOT/"data")
    report=verify(ROOT/"data")
    print(json.dumps({"current_cash_matches":report["current_cash"]["matched_amount_count"],
                      "historical_cash_matches":report["historical_cash"]["matched_amount_count"],
                      "split":report["historical_split"],"rs_eligible":False},ensure_ascii=False))

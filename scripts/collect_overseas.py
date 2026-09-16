#!/usr/bin/env python3
"""Capture provider close/adjusted close/events without double-adjusting splits."""
import base64
import datetime as dt
import gzip
import hashlib
import json
import urllib.error
from zoneinfo import ZoneInfo
from collect_series import fetch, positive, validate_date
from update_daily import ROOT, write_json


def parse_yahoo(raw, instrument, now):
    payload = json.loads(raw)
    chart = payload["chart"]
    if chart.get("error") or len(chart.get("result") or []) != 1:
        raise ValueError("Provider returned an error or ambiguous result")
    result = chart["result"][0]
    meta = result["meta"]
    for field, key in (("symbol","code"),("currency","currency"),("instrumentType","instrument_type"),("exchangeTimezoneName","timezone")):
        if meta.get(field) != instrument[key]:
            raise ValueError(f"Provider identity mismatch: {field}")
    zone = ZoneInfo(instrument["timezone"])
    today = now.astimezone(zone).date()
    def day(timestamp):
        if isinstance(timestamp, bool) or not isinstance(timestamp, int) or timestamp > now.timestamp():
            raise ValueError("Invalid or future source timestamp")
        return validate_date(dt.datetime.fromtimestamp(timestamp, zone).date().isoformat(), today)
    timestamps = result.get("timestamp") or []
    quote = result["indicators"]["quote"][0]
    adjusted = (result["indicators"].get("adjclose") or [{}])[0].get("adjclose")
    if not timestamps or not isinstance(adjusted, list) or len(adjusted) != len(timestamps):
        raise ValueError("Missing or misaligned adjusted closes")
    for field in ("open","high","low","close","volume"):
        if len(quote[field]) != len(timestamps):
            raise ValueError("Misaligned price arrays")
    rows, missing, seen = [], [], set()
    for i,timestamp in enumerate(timestamps):
        date = day(timestamp)
        if date in seen:
            raise ValueError("Duplicate session date")
        seen.add(date)
        values = [quote[k][i] for k in ("open","high","low","close","volume")] + [adjusted[i]]
        if any(value is None for value in values):
            missing.append(date)
            continue
        if any(isinstance(value,bool) for value in values):
            raise ValueError("Boolean price/volume")
        opening, high, low, close = map(positive,values[:4])
        adj = positive(adjusted[i])
        volume = values[4]
        if not isinstance(volume,int) or volume < 0 or low > min(opening,close) or high < max(opening,close):
            raise ValueError("Invalid OHLCV")
        rows.append({"date":date,"open":opening,"high":high,"low":low,"close":close,
                     "volume":volume,"adjusted_close":adj})
    if not rows:
        raise ValueError("No complete overseas observations")
    events=[]
    for key,kind in (("dividends","DIVIDEND"),("splits","SPLIT"),("capitalGains","CAPITAL_GAIN")):
        for event_id,event in (result.get("events",{}).get(key) or {}).items():
            row={"event_id":str(event_id),"date":day(event["date"]),"kind":kind}
            if kind=="SPLIT":
                row.update(numerator=positive(event["numerator"]),denominator=positive(event["denominator"]))
            else:
                row["amount"]=positive(event["amount"])
            events.append(row)
    return {"observations":sorted(rows,key=lambda r:r["date"]),
            "events":sorted(events,key=lambda e:(e["date"],e["kind"],e["event_id"])),
            "missing_dates":sorted(missing)}


def audit_adjustments(rows, events):
    """Provider-internal diagnostics, never an independent verification stamp."""
    changes=[]
    for before,after in zip(rows,rows[1:]):
        ratio=(before["adjusted_close"]/before["close"])/(after["adjusted_close"]/after["close"])
        related=[e for e in events if e["date"]==after["date"]]
        cash=sum(e["amount"] for e in related if e["kind"] in ("DIVIDEND","CAPITAL_GAIN"))
        if abs(ratio-1)>0.000001 or related:
            expected=1-cash/before["close"] if cash else None
            changes.append({"date":after["date"],"factor_ratio":ratio,"event_kinds":[e["kind"] for e in related],
                            "cash_factor_candidate":expected,
                            "cash_residual":ratio-expected if expected is not None else None,
                            "requires_review":not related or any(e["kind"]=="SPLIT" for e in related) or (expected is not None and abs(ratio-expected)>0.0005)})
    observed_dates={r["date"] for r in rows}
    return {"status":"PROVIDER_INTERNAL_CHECK_ONLY", "rs_eligible":False,
            "split_count":sum(e["kind"]=="SPLIT" for e in events),
            "cash_event_count":sum(e["kind"]!="SPLIT" for e in events),
            "events_without_price_date":[e for e in events if e["date"] not in observed_dates],
            "factor_changes":changes,
            "note":"Close and adjusted close are preserved as received. Never apply a split again to already adjusted prices. Cash-factor comparison is diagnostic, not a total-return certification."}


def capture_overseas(data_dir, config, instrument, fetcher=fetch, now=None):
    now=now or dt.datetime.now(dt.timezone.utc)
    code=instrument["code"]
    capture_id=now.strftime("%Y%m%dT%H%M%S%fZ")+"-YAHOO_CHART_CANDIDATE-"+code
    url=config["url_template"].format(code=code)
    record={"schema_version":2,"capture_id":capture_id,"source_id":config["source_id"],"source_url":url,
            "retrieved_at":now.isoformat(),"kind":"US_PRICE","instrument_code":code,"market":"US_LISTED",
            "currency":"USD","instrument_contract":instrument,"publication_time":None,
            "price_basis":"PROVIDER_CLOSE_AND_ADJUSTED_CLOSE","rs_eligible":False,"observations":[],"events":[]}
    try:
        raw=fetcher(url)
        digest=hashlib.sha256(raw).hexdigest()
        path=data_dir / "raw/series" / f"{digest}.json"
        if not path.exists():
            write_json(path,{"sha256":digest,"encoding":"gzip+base64","content":base64.b64encode(gzip.compress(raw,mtime=0)).decode()})
        record["source_sha256"]=digest
        parsed=parse_yahoo(raw,instrument,now)
        record.update(parsed,status="CAPTURED",quality="QUARANTINED",
                      first_date=parsed["observations"][0]["date"],last_date=parsed["observations"][-1]["date"])
        record["adjustment_audit"]=audit_adjustments(parsed["observations"],parsed["events"])
    except Exception as exc:
        record.update(status="FAILED",quality="UNUSABLE",observations=[],events=[],error=f"{type(exc).__name__}: {exc}")
        if isinstance(exc,urllib.error.HTTPError):
            record["http_status"]=exc.code
    path=data_dir / "series/captures" / f"{capture_id}.json"
    if path.exists():
        raise ValueError("Capture ID collision")
    write_json(path,record)
    return record


def main():
    config=json.loads((ROOT / "data/overseas_sources.json").read_text())
    results=[]
    for item in config["instruments"]:
        record=capture_overseas(ROOT / "data",config,item)
        results.append({k:record.get(k) for k in ("instrument_code","status","first_date","last_date","error")})
        if record.get("http_status") in (401,403,429):
            break  # Respect access/rate limits; do not rotate hosts or retry.
    print(json.dumps(results,ensure_ascii=False))
    return 0 if len(results)==len(config["instruments"]) and all(r["status"]=="CAPTURED" for r in results) else 1


if __name__=="__main__":
    raise SystemExit(main())

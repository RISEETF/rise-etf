#!/usr/bin/env python3
"""Capture dated series with immutable provenance; never promote prices to RS."""
import base64
import datetime as dt
import gzip
import hashlib
import json
import math
import re
import urllib.request
import xml.etree.ElementTree as ET
from update_daily import ROOT, write_json


def positive(value):
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise ValueError("Expected finite positive value")
    return number


def validate_date(value, today):
    date = dt.date.fromisoformat(value)
    if date > today:
        raise ValueError("Future observation date")
    return date.isoformat()


def parse_naver(raw, code, today):
    # The provider declares EUC-KR; ElementTree's byte parser cannot decode it.
    declaration = raw[:160].lower()
    encoding = "cp949" if b"euc-kr" in declaration or b"ks_c_5601" in declaration else "utf-8"
    root = ET.fromstring(raw.decode(encoding))
    chart = root.find(".//chartdata")
    if chart is None or chart.get("symbol") != code:
        raise ValueError("Provider instrument code does not match request")
    rows, dates = [], set()
    for item in chart.findall("item"):
        parts = item.attrib["data"].split("|")
        if len(parts) != 6 or not re.fullmatch(r"\d{8}", parts[0]):
            raise ValueError("Unexpected OHLCV schema")
        day = validate_date(dt.datetime.strptime(parts[0], "%Y%m%d").date().isoformat(), today)
        if day in dates:
            raise ValueError("Duplicate price observation")
        dates.add(day)
        opening, high, low, close = map(positive, parts[1:5])
        if low > min(opening, close) or high < max(opening, close) or low > high:
            raise ValueError("Inconsistent OHLC range")
        volume = int(parts[5])
        if volume < 0:
            raise ValueError("Negative volume")
        rows.append({"date": day, "open": opening, "high": high, "low": low,
                     "close": close, "volume": volume})
    if not rows:
        raise ValueError("Empty price series")
    return sorted(rows, key=lambda row: row["date"])


def parse_ecb(raw, today):
    root = ET.fromstring(raw)
    rows, dates = [], set()
    for cube in root.iter():
        if "time" not in cube.attrib:
            continue
        day = validate_date(cube.attrib["time"], today)
        if day in dates:
            raise ValueError("Duplicate FX date")
        dates.add(day)
        rates = {}
        for child in cube:
            currency = child.get("currency")
            if currency in ("USD", "KRW"):
                if currency in rates:
                    raise ValueError("Duplicate FX currency")
                rates[currency] = positive(child.attrib["rate"])
        if set(rates) != {"USD", "KRW"}:
            raise ValueError("Missing same-date USD/KRW reference leg")
        for quote in ("USD", "KRW"):
            rows.append({"date": day, "base": "EUR", "quote": quote,
                         "rate": rates[quote], "kind": "OFFICIAL_REFERENCE"})
        rows.append({"date": day, "base": "USD", "quote": "KRW",
                     "rate": rates["KRW"] / rates["USD"], "kind": "DERIVED_CROSS_REFERENCE"})
    if not rows:
        raise ValueError("Empty FX series")
    return sorted(rows, key=lambda row: (row["date"], row["base"], row["quote"]))


def fetch(url):
    request = urllib.request.Request(url, headers={"User-Agent": "RISE-research/0.2"})
    with urllib.request.urlopen(request, timeout=25) as response:
        return response.read()


def capture(data_dir, source_id, url, kind, code=None, fetcher=fetch, now=None):
    now = now or dt.datetime.now(dt.timezone.utc)
    capture_id = now.strftime("%Y%m%dT%H%M%S%fZ") + "-" + source_id + ("-" + code if code else "")
    record = {"schema_version": 1, "capture_id": capture_id, "source_id": source_id,
              "source_url": url, "retrieved_at": now.isoformat(), "kind": kind,
              "instrument_code": code, "publication_time": None,
              "price_basis": "ADJUSTMENT_UNCONFIRMED" if kind == "PRICE" else None,
              "currency": "KRW" if kind == "PRICE" else None, "rs_eligible": False,
              "observations": []}
    try:
        raw = fetcher(url)
        digest = hashlib.sha256(raw).hexdigest()
        raw_path = data_dir / "raw/series" / f"{digest}.json"
        if not raw_path.exists():
            write_json(raw_path, {"sha256": digest, "encoding": "gzip+base64",
                                 "content": base64.b64encode(gzip.compress(raw, mtime=0)).decode()})
        record["source_sha256"] = digest
        # KRX date can be one day ahead of UTC. Same-day bars remain quarantined.
        today = (now + dt.timedelta(hours=9)).date() if kind == "PRICE" else now.date()
        rows = parse_naver(raw, code, today) if kind == "PRICE" else parse_ecb(raw, today)
        record.update(status="CAPTURED", quality="QUARANTINED" if kind == "PRICE" else "REFERENCE_ONLY",
                      observations=rows, first_date=rows[0]["date"], last_date=rows[-1]["date"])
    except Exception as exc:
        record.update(status="FAILED", quality="UNUSABLE", error=f"{type(exc).__name__}: {exc}")
    path = data_dir / "series/captures" / f"{capture_id}.json"
    if path.exists():
        raise ValueError("Capture ID collision; refusing to overwrite history")
    write_json(path, record)
    return record


def main():
    config = json.loads((ROOT / "data/series_sources.json").read_text())
    master = json.loads((ROOT / "data/master/latest.json").read_text())
    identities = {p["code"]: p["name"] for p in master["products"]}
    records = []
    for item in config["price_instruments"]:
        if identities.get(item["code"]) != item["name"]:
            raise ValueError("Pilot does not match the official instrument master")
        source = config["price_source"]
        records.append(capture(ROOT / "data", source["id"], source["url_template"].format(code=item["code"]), "PRICE", item["code"]))
    source = config["fx_source"]
    records.append(capture(ROOT / "data", source["id"], source["url"], "FX"))
    summary = [{k: r.get(k) for k in ("capture_id", "kind", "instrument_code", "status", "first_date", "last_date", "error")} for r in records]
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if all(r["status"] == "CAPTURED" for r in records) else 1


if __name__ == "__main__":
    raise SystemExit(main())

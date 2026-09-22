#!/usr/bin/env python3
"""Rebuild a queryable SQLite database from immutable, hash-checked captures."""
import base64
import datetime as dt
import gzip
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
from collect_series import parse_naver, parse_ecb
from collect_overseas import parse_yahoo, audit_adjustments
from update_daily import ROOT, write_json

SCHEMA = """
PRAGMA foreign_keys=ON;
CREATE TABLE instruments (
 instrument_id TEXT PRIMARY KEY, market TEXT NOT NULL, code TEXT NOT NULL,
 name TEXT NOT NULL, currency TEXT NOT NULL, master_date TEXT NOT NULL,
 UNIQUE(market,code));
CREATE TABLE master_memberships (
 snapshot_path TEXT NOT NULL, effective_date TEXT NOT NULL,
 instrument_id TEXT REFERENCES instruments(instrument_id), name TEXT NOT NULL,
 is_current INTEGER NOT NULL CHECK(is_current IN (0,1)),
 PRIMARY KEY(snapshot_path,instrument_id));
CREATE TABLE captures (
 capture_id TEXT PRIMARY KEY, source_id TEXT NOT NULL, source_url TEXT NOT NULL,
 retrieved_at TEXT NOT NULL, source_sha256 TEXT, kind TEXT NOT NULL,
 status TEXT NOT NULL, quality TEXT NOT NULL, error TEXT);
CREATE TABLE prices (
 capture_id TEXT REFERENCES captures(capture_id), instrument_id TEXT REFERENCES instruments(instrument_id),
 observation_date TEXT NOT NULL, open REAL NOT NULL, high REAL NOT NULL,
 low REAL NOT NULL, close REAL NOT NULL CHECK(close>0), volume INTEGER NOT NULL CHECK(volume>=0),
 price_basis TEXT NOT NULL, adjusted_close REAL CHECK(adjusted_close>0),
 PRIMARY KEY(capture_id,instrument_id,observation_date));
CREATE TABLE instrument_contracts (
 capture_id TEXT PRIMARY KEY REFERENCES captures(capture_id),
 instrument_id TEXT NOT NULL REFERENCES instruments(instrument_id),
 contract_json TEXT NOT NULL);
CREATE TABLE corporate_actions (
 capture_id TEXT REFERENCES captures(capture_id), instrument_id TEXT REFERENCES instruments(instrument_id),
 event_id TEXT NOT NULL, observation_date TEXT NOT NULL, kind TEXT NOT NULL,
 amount REAL, numerator REAL, denominator REAL,
 PRIMARY KEY(capture_id,instrument_id,kind,event_id));
CREATE TABLE fx (
 capture_id TEXT REFERENCES captures(capture_id), observation_date TEXT NOT NULL,
 base TEXT NOT NULL, quote TEXT NOT NULL, rate REAL NOT NULL CHECK(rate>0), kind TEXT NOT NULL,
 PRIMARY KEY(capture_id,observation_date,base,quote));
CREATE INDEX price_dates ON prices(instrument_id,observation_date);
CREATE VIEW latest_prices AS
 SELECT * FROM (
 SELECT p.*, c.retrieved_at, c.source_url, c.quality,
 ROW_NUMBER() OVER(PARTITION BY p.instrument_id,p.observation_date ORDER BY c.retrieved_at DESC,c.capture_id DESC) AS vintage_rank
 FROM prices p JOIN captures c USING(capture_id)) WHERE vintage_rank=1;
CREATE VIEW latest_fx AS
 SELECT * FROM (
 SELECT f.*, c.retrieved_at,c.source_url,
 ROW_NUMBER() OVER(PARTITION BY f.observation_date,f.base,f.quote ORDER BY c.retrieved_at DESC,c.capture_id DESC) AS vintage_rank
 FROM fx f JOIN captures c USING(capture_id)) WHERE vintage_rank=1;
"""


def verify_capture(data_dir, record):
    if record["status"] != "CAPTURED":
        if record["observations"]:
            raise ValueError("Failed capture contains observations")
        return
    digest = record["source_sha256"]
    if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
        raise ValueError("Invalid source hash")
    envelope = json.loads((data_dir / "raw/series" / f"{digest}.json").read_text())
    raw = gzip.decompress(base64.b64decode(envelope["content"]))
    if hashlib.sha256(raw).hexdigest() != digest:
        raise ValueError("Source hash mismatch")
    captured = dt.datetime.fromisoformat(record["retrieved_at"])
    if record["kind"] == "PRICE":
        expected = parse_naver(raw, record["instrument_code"], (captured + dt.timedelta(hours=9)).date())
        if record["price_basis"] != "ADJUSTMENT_UNCONFIRMED" or record["quality"] != "QUARANTINED" or record["currency"] != "KRW":
            raise ValueError("Unapproved price metadata promotion")
    elif record["kind"] == "US_PRICE":
        instrument=record["instrument_contract"]
        if (instrument.get("code") != record["instrument_code"] or
            instrument.get("market") != "US_LISTED" or record.get("market") != "US_LISTED" or
            instrument.get("currency") != "USD" or instrument.get("instrument_type") not in ("ETF", "EQUITY") or
            instrument.get("timezone") != "America/New_York" or not instrument.get("name")):
            raise ValueError("Unknown overseas instrument contract")
        parsed=parse_yahoo(raw,instrument,captured)
        expected=parsed["observations"]
        if record["events"]!=parsed["events"] or record["missing_dates"]!=parsed["missing_dates"] or record["adjustment_audit"]!=audit_adjustments(expected,parsed["events"]):
            raise ValueError("Corporate actions or diagnostics differ from raw source")
        if record["price_basis"]!="PROVIDER_CLOSE_AND_ADJUSTED_CLOSE" or record["currency"]!="USD" or record["quality"]!="QUARANTINED":
            raise ValueError("Unapproved overseas metadata promotion")
    elif record["kind"] == "FX":
        expected = parse_ecb(raw, captured.date())
        if record["quality"] != "REFERENCE_ONLY":
            raise ValueError("Unapproved FX metadata promotion")
    else:
        raise ValueError("Unknown series kind")
    if record["observations"] != expected or record["rs_eligible"] is not False:
        raise ValueError("Normalized observations or eligibility differ from source contract")


def build(data_dir, db_path):
    data_dir, db_path = Path(data_dir), Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    master = json.loads((data_dir / "master/latest.json").read_text())
    config = json.loads((data_dir / "series_sources.json").read_text())
    overseas_path=data_dir / "overseas_sources.json"
    overseas=json.loads(overseas_path.read_text())["instruments"] if overseas_path.exists() else []
    with tempfile.NamedTemporaryFile(dir=db_path.parent, suffix=".sqlite", delete=False) as handle:
        temporary = Path(handle.name)
    connection = sqlite3.connect(temporary)
    try:
        connection.executescript(SCHEMA)
        # Retain identities from historical masters; absence today is not delisting evidence.
        historical = [(path, json.loads(path.read_text())) for path in
                      (data_dir / "master").rglob("*.json") if path.name not in {"latest.json", "changes.json"}]
        historical.sort(key=lambda item: (item[1]["effective_date"], item[1].get("retrieved_at", ""), str(item[0])))
        snapshots = historical + [(data_dir / "master/latest.json", master)]
        for path, snapshot in snapshots:
            for p in snapshot["products"]:
                connection.execute("INSERT INTO instruments VALUES (?,?,?,?,?,?) ON CONFLICT(instrument_id) DO UPDATE SET name=excluded.name, master_date=excluded.master_date",
                                   ("XKRX:"+p["code"], "XKRX", p["code"], p["name"], "KRW", snapshot["effective_date"]))
                connection.execute("INSERT INTO master_memberships VALUES (?,?,?,?,?)",
                                   (str(path.relative_to(data_dir)), snapshot["effective_date"], "XKRX:"+p["code"], p["name"], int(path.name == "latest.json")))
        identity_fields = ("market", "currency", "instrument_type", "timezone")
        contracts = {p["code"]: tuple(p[k] for k in identity_fields) for p in overseas}
        for p in overseas:
            connection.execute("INSERT INTO instruments VALUES (?,?,?,?,?,?)",
                               ("US_LISTED:"+p["code"],"US_LISTED",p["code"],p["name"],p["currency"],"PROVISIONAL_PROVIDER_IDENTITY"))
        records = []
        for path in sorted((data_dir / "series/captures").glob("*.json")):
            record = json.loads(path.read_text())
            if path.stem != record["capture_id"]:
                raise ValueError("Capture filename mismatch")
            verify_capture(data_dir, record)
            connection.execute("INSERT INTO captures VALUES (?,?,?,?,?,?,?,?,?)", tuple(record.get(k) for k in
                ("capture_id","source_id","source_url","retrieved_at","source_sha256","kind","status","quality","error")))
            if record["kind"] == "US_PRICE" and record["status"] == "CAPTURED":
                p = record["instrument_contract"]
                identity = tuple(p[k] for k in identity_fields)
                if p["code"] in contracts and contracts[p["code"]] != identity:
                    raise ValueError("Conflicting overseas identity; explicit migration required")
                contracts[p["code"]] = identity
                connection.execute("INSERT OR IGNORE INTO instruments VALUES (?,?,?,?,?,?)",
                                   ("US_LISTED:"+p["code"], "US_LISTED", p["code"], p["name"], p["currency"], "PROVISIONAL_PROVIDER_IDENTITY"))
                connection.execute("INSERT INTO instrument_contracts VALUES (?,?,?)",
                                   (record["capture_id"], "US_LISTED:"+p["code"], json.dumps(p, ensure_ascii=False, sort_keys=True)))
            records.append(record)
            for row in record["observations"]:
                if record["kind"] in ("PRICE","US_PRICE"):
                    market="US_LISTED" if record["kind"]=="US_PRICE" else "XKRX"
                    connection.execute("INSERT INTO prices VALUES (?,?,?,?,?,?,?,?,?,?)", (
                        record["capture_id"], market+":"+record["instrument_code"], row["date"],row["open"],row["high"],row["low"],row["close"],row["volume"],record["price_basis"],row.get("adjusted_close")))
                else:
                    connection.execute("INSERT INTO fx VALUES (?,?,?,?,?,?)", (record["capture_id"],row["date"],row["base"],row["quote"],row["rate"],row["kind"]))
            for event in record.get("events",[]):
                connection.execute("INSERT INTO corporate_actions VALUES (?,?,?,?,?,?,?,?)", (
                    record["capture_id"],"US_LISTED:"+record["instrument_code"],event["event_id"],event["date"],event["kind"],event.get("amount"),event.get("numerator"),event.get("denominator")))
        summary = {"built_at":dt.datetime.now(dt.timezone.utc).isoformat(), "storage":"REBUILDABLE_SQLITE_FROM_GIT_CAPTURES",
                   "rs_status":"BLOCKED", "ranking":None, "series":[], "fx":{}, "capture_count":len(records)}
        for instrument in config["price_instruments"]+overseas:
            code = instrument["code"]
            market=instrument.get("market","XKRX")
            count, first, last = connection.execute("SELECT COUNT(*),MIN(observation_date),MAX(observation_date) FROM latest_prices WHERE instrument_id=?", (market+":"+code,)).fetchone()
            attempts = [r for r in records if r["instrument_code"] == code and r.get("market","XKRX")==market]
            latest = max(attempts, key=lambda r:r["retrieved_at"]) if attempts else {}
            reasons = ["ADJUSTMENT_UNCONFIRMED", "DISTRIBUTIONS_UNVERIFIED", "SESSION_CALENDAR_UNVERIFIED", "CROSS_MARKET_ALIGNMENT_UNRESOLVED"]
            if market=="US_LISTED":
                reasons[0]="PROVIDER_ADJUSTMENT_NOT_INDEPENDENTLY_VERIFIED"
                reasons.append("PROVISIONAL_INSTRUMENT_IDENTITY")
            if count < 253:
                reasons.append("HISTORY_BELOW_253_OBSERVATIONS")
            if not count:
                reasons.append("NO_PRICE_OBSERVATIONS")
            summary["series"].append({**instrument,"observations":count,"first_date":first,"last_date":last,
                "last_attempt_status":latest.get("status","NOT_ATTEMPTED"),"retrieved_at":latest.get("retrieved_at"),
                "error":latest.get("error"),"rs_eligible":False,"blockers":reasons,
                "adjustment_audit":latest.get("adjustment_audit"),"missing_dates":latest.get("missing_dates",[])})
        count, first, last = connection.execute("SELECT COUNT(*),MIN(observation_date),MAX(observation_date) FROM latest_fx WHERE base='USD' AND quote='KRW'").fetchone()
        fx_attempts = [r for r in records if r["kind"] == "FX"]
        latest = max(fx_attempts,key=lambda r:r["retrieved_at"]) if fx_attempts else {}
        summary["fx"] = {"pair":"USD/KRW", "unit":"KRW per USD", "observations":count,"first_date":first,"last_date":last,
                         "last_attempt_status":latest.get("status","NOT_ATTEMPTED"),"retrieved_at":latest.get("retrieved_at"),
                         "kind":"ECB_DERIVED_REFERENCE_ONLY","rs_eligible":False,"error":latest.get("error")}
        connection.commit()
        if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValueError("SQLite integrity check failed")
        connection.close()
        temporary.replace(db_path)
        write_json(data_dir / "series/status.json", summary)
        return summary
    finally:
        connection.close()
        if temporary.exists():
            temporary.unlink()


if __name__ == "__main__":
    print(json.dumps(build(ROOT / "data", ROOT / "var/research.sqlite"), ensure_ascii=False))

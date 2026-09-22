"""Collect and accumulate the official KRX ETF daily snapshot.

The authentication key is read only from KRX_AUTH_KEY. Raw snapshots and the
SQLite database are runtime artifacts; this script never writes the key or
commits market data to the repository.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import sqlite3
import urllib.parse
import urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo


API_URL = "https://data-dbg.krx.co.kr/svc/apis/etp/etf_bydd_trd"
FIELDS = {
    "close": ("TDD_CLSPRC", "KRW"),
    "nav": ("NAV", "KRW"),
    "volume": ("ACC_TRDVOL", "SHARES"),
    "trading_value": ("ACC_TRDVAL", "KRW"),
    "market_cap": ("MKTCAP", "KRW"),
    "net_assets": ("INVSTASST_NETASST_TOTAMT", "KRW"),
    "listed_shares": ("LIST_SHRS", "SHARES"),
}


def number(value: object, field: str) -> float | None:
    text = str(value or "").replace(",", "").strip()
    if not text:
        return None
    try:
        parsed = float(text)
    except ValueError as exc:
        raise ValueError(f"KRX_NUMBER_INVALID:{field}") from exc
    if parsed < 0:
        raise ValueError(f"KRX_NUMBER_NEGATIVE:{field}")
    return parsed


def parse_snapshot(payload: bytes, asof: dt.date) -> dict:
    try:
        document = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("KRX_JSON_INVALID") from exc
    rows = document.get("OutBlock_1")
    if not isinstance(rows, list) or not rows:
        raise ValueError("KRX_ROWS_MISSING")
    dates: set[dt.date] = set()
    tickers: set[str] = set()
    records = []
    for row in rows:
        date_text = str(row.get("BAS_DD") or "")
        if not re.fullmatch(r"\d{8}", date_text):
            raise ValueError("KRX_DATE_INVALID")
        observed = dt.datetime.strptime(date_text, "%Y%m%d").date()
        if observed > asof:
            raise ValueError("FUTURE_KRX_SNAPSHOT")
        ticker = str(row.get("ISU_SRT_CD") or row.get("ISU_CD") or "").strip()
        name = str(row.get("ISU_NM") or "").strip()
        if not re.fullmatch(r"[0-9A-Z]{6,12}", ticker):
            raise ValueError("KRX_TICKER_INVALID")
        if ticker in tickers:
            raise ValueError("KRX_DUPLICATE_TICKER")
        if not name:
            raise ValueError("KRX_NAME_MISSING")
        tickers.add(ticker)
        dates.add(observed)
        record = {"ticker": ticker, "name": name}
        for target, (source, _) in FIELDS.items():
            record[target] = number(row.get(source), source)
        records.append(record)
    if len(dates) != 1:
        raise ValueError("KRX_MIXED_BASE_DATES")
    observed = dates.pop()
    return {"page_date": observed.isoformat(), "records": records}


def fetch_latest(auth_key: str, asof: dt.date) -> tuple[bytes, dict]:
    attempts = []
    for offset in range(8):
        requested = asof - dt.timedelta(days=offset)
        url = API_URL + "?" + urllib.parse.urlencode({"basDd": requested.strftime("%Y%m%d")})
        try:
            request = urllib.request.Request(
                url,
                headers={"AUTH_KEY": auth_key, "User-Agent": "RISE-Research-Collector/1.0"},
            )
            with urllib.request.urlopen(request, timeout=30) as response:
                payload = response.read()
            snapshot = parse_snapshot(payload, asof)
            return payload, {"requested_date": requested.isoformat(), "snapshot": snapshot}
        except Exception as exc:  # keep bounded attempts in the receipt
            attempts.append({"date": requested.isoformat(), "error": str(exc)[:160]})
    raise RuntimeError("KRX_FETCH_FAILED:" + json.dumps(attempts, ensure_ascii=False))


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.executescript(
        """
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS snapshots(
          observation_date TEXT NOT NULL, ticker TEXT NOT NULL, name TEXT NOT NULL,
          field TEXT NOT NULL, value REAL NOT NULL, unit TEXT NOT NULL,
          retrieved_at TEXT NOT NULL, raw_sha256 TEXT NOT NULL,
          PRIMARY KEY(observation_date,ticker,field,raw_sha256));
        CREATE INDEX IF NOT EXISTS ix_snapshots_latest
          ON snapshots(ticker,field,observation_date,retrieved_at);
        """
    )
    return connection


def validate_completeness(db_path: Path, snapshot: dict, asof: dt.date) -> dict:
    """Reject partial or stale market-wide responses before any write."""
    records = snapshot["records"]
    current_count = len(records)
    observed = dt.date.fromisoformat(snapshot["page_date"])
    lag_days = (asof - observed).days
    if lag_days < 0 or lag_days > 7:
        raise ValueError(f"KRX_SNAPSHOT_STALE_OR_FUTURE:{lag_days}")
    if current_count < 500:
        raise ValueError(f"KRX_UNIVERSE_TOO_SMALL:{current_count}")
    coverage = {}
    for field in ("close", "nav", "volume", "listed_shares"):
        present = sum(item.get(field) is not None for item in records)
        ratio = present / current_count
        coverage[field] = ratio
        if ratio < 0.95:
            raise ValueError(f"KRX_FIELD_COVERAGE_LOW:{field}:{ratio:.4f}")
    prior_count = None
    if db_path.is_file():
        with sqlite3.connect(f"file:{db_path.resolve()}?mode=ro", uri=True) as connection:
            latest = connection.execute("SELECT max(observation_date) FROM snapshots").fetchone()[0]
            if latest:
                prior_count = connection.execute(
                    "SELECT count(DISTINCT ticker) FROM snapshots WHERE observation_date=?", (latest,)
                ).fetchone()[0]
    if prior_count and current_count < prior_count * 0.90:
        raise ValueError(f"KRX_UNIVERSE_COLLAPSE:{prior_count}->{current_count}")
    return {
        "lag_calendar_days": lag_days,
        "prior_ticker_count": prior_count,
        "field_coverage": coverage,
    }


def accumulate(db_path: Path, snapshot: dict, raw_hash: str, retrieved_at: str) -> dict:
    new = unchanged = revisions = 0
    with connect(db_path) as connection:
        for item in snapshot["records"]:
            for field, (_, unit) in FIELDS.items():
                value = item.get(field)
                if value is None:
                    continue
                prior = connection.execute(
                    "SELECT value FROM snapshots WHERE observation_date=? AND ticker=? AND field=? "
                    "ORDER BY retrieved_at DESC LIMIT 1",
                    (snapshot["page_date"], item["ticker"], field),
                ).fetchone()
                if prior and prior[0] == value:
                    unchanged += 1
                    continue
                cursor = connection.execute(
                    "INSERT OR IGNORE INTO snapshots VALUES(?,?,?,?,?,?,?,?)",
                    (snapshot["page_date"], item["ticker"], item["name"], field,
                     value, unit, retrieved_at, raw_hash),
                )
                if cursor.rowcount:
                    revisions += int(prior is not None)
                    new += int(prior is None)
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        total = connection.execute("SELECT count(*) FROM snapshots").fetchone()[0]
    if integrity != "ok":
        raise RuntimeError("KRX_DB_INTEGRITY_FAILED")
    return {"new": new, "revisions": revisions, "unchanged": unchanged, "total": total}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="var/krx_etf.sqlite")
    parser.add_argument("--output", default="var/krx-output")
    parser.add_argument("--asof")
    args = parser.parse_args()
    auth_key = os.environ.get("KRX_AUTH_KEY", "").strip()
    if not auth_key:
        raise RuntimeError("KRX_AUTH_KEY_MISSING")
    asof = dt.date.fromisoformat(args.asof) if args.asof else dt.datetime.now(ZoneInfo("Asia/Seoul")).date()
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    retrieved_at = dt.datetime.now(dt.timezone.utc).isoformat()
    payload, result = fetch_latest(auth_key, asof)
    raw_hash = hashlib.sha256(payload).hexdigest()
    raw_path = output / f"krx_etf_{result['snapshot']['page_date'].replace('-', '')}.json"
    raw_path.write_bytes(payload)
    quality = validate_completeness(Path(args.db), result["snapshot"], asof)
    delta = accumulate(Path(args.db), result["snapshot"], raw_hash, retrieved_at)
    receipt = {
        "status": "SUCCESS",
        "source": "KRX_OPEN_API_ETF_DAILY",
        "source_role": "PRIMARY",
        "asof": asof.isoformat(),
        "observation_date": result["snapshot"]["page_date"],
        "record_count": len(result["snapshot"]["records"]),
        "delta": delta,
        "retrieved_at": retrieved_at,
        "raw_sha256": raw_hash,
        "quality": quality,
        "flow_warning": "AUM_OR_LISTED_SHARES_CHANGE_IS_NOT_DIRECT_NET_FLOW",
    }
    (output / "receipt.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2))
    print(json.dumps(receipt, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

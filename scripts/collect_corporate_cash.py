"""Small DART cash screening pilot. No investment-capacity estimate or score."""
import argparse, datetime, io, json, os, urllib.parse, urllib.request, zipfile
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UNIVERSE = ROOT / "data/corporate/universe.json"

def request(endpoint, key, **params):
    url = "https://opendart.fss.or.kr/api/" + endpoint + "?" + urllib.parse.urlencode(dict(crtfc_key=key, **params))
    try:
        with urllib.request.urlopen(url, timeout=35) as response:
            return response.read()
    except Exception as exc:
        raise RuntimeError(type(exc).__name__) from None

def amount(rows, ids=(), names=()):
    hits = [r for r in rows if r.get("sj_div") == "BS" and (r.get("account_id") in ids or r.get("account_nm", "").replace(" ", "") in names)]
    if len(hits) != 1:
        return {"value": None, "status": "unmapped" if not hits else "ambiguous"}
    r = hits[0]
    try:
        value = int(r["thstrm_amount"].replace(",", ""))
    except (ValueError, KeyError):
        value = None
    if r.get("currency") != "KRW":
        value = None
    return {"value": value, "account": r.get("account_nm"), "account_id": r.get("account_id"), "currency": r.get("currency"), "status": "mapped" if value is not None else "unknown"}

def normalize(data):
    rows = data.get("list", [])
    if data.get("status") != "000" or not rows:
        return {"status": "unavailable", "api_status": data.get("status")}
    cash = amount(rows, ["ifrs-full_CashAndCashEquivalents"], ["현금및현금성자산"])
    short = amount(rows, ["dart_ShortTermFinancialInstruments", "ifrs-full_ShorttermDepositsNotClassifiedAsCashEquivalents"], ["단기금융상품"])
    assets = amount(rows, ["ifrs-full_Assets"], ["자산총계"])
    # Deliberately do not map broad short-term financial assets to deposits.
    total = cash["value"] + short["value"] if cash["value"] is not None and short["value"] is not None else None
    clues = sorted(set(r.get("account_nm", "") for r in rows if any(w in r.get("account_nm", "") for w in ["공정가치", "수익증권", "단기매매", "집합투자"])))
    return {"status": "ok", "receipt": rows[0]["rcept_no"], "cash": cash, "short": short, "assets": assets, "cash_plus_short": total, "ratio": total / assets["value"] if total is not None and assets["value"] else None, "clues": clues, "fund_evidence": "미확인 · 주석 미분석"}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--key-file")
    parser.add_argument("--only-new", action="store_true", help="Keep existing same-period companies; collect newly added codes only")
    args = parser.parse_args()
    key = Path(args.key_file).read_text().strip() if args.key_file else os.environ.get("DART_API_KEY", "")
    if not key:
        raise SystemExit("DART_API_KEY or --key-file required")
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dest = ROOT / "data/corporate/captures" / stamp
    dest.mkdir(parents=True, exist_ok=True)
    raw = request("corpCode.xml", key)
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        tree = ET.fromstring(z.read("CORPCODE.xml"))
    master = {x.findtext("stock_code", "").strip(): (x.findtext("corp_code"), x.findtext("corp_name")) for x in tree.findall("list")}
    previous = {}
    latest = ROOT / "data/corporate/latest.json"
    if args.only_new and latest.exists():
        old = json.loads(latest.read_text())
        if (old["period"], old["comparison_period"], old["scope"]) != ("2026-06-30", "2025-12-31", "OFS"):
            raise SystemExit("Existing snapshot period/scope mismatch")
        previous = {c["code"]: dict(c, collected_at=c.get("collected_at", old["collected_at"])) for c in old["companies"]}
    def collect(company):
        code = company["code"]
        if code in previous:
            return previous[code]
        corp, name = master[code]
        item = {"code": code, "name": name, "corp_code": corp, "scope": "별도", "collected_at": stamp, "industry": company["industry"], "periods": {}}
        for period, year, report in [("2025-12-31", "2025", "11011"), ("2026-06-30", "2026", "11012")]:
            try:
                payload = json.loads(request("fnlttSinglAcntAll.json", key, corp_code=corp, bsns_year=year, reprt_code=report, fs_div="OFS"))
                filename = code + "_" + period + ".json"
                (dest / filename).write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
                item["periods"][period] = normalize(payload)
                item["periods"][period]["raw"] = str((dest / filename).relative_to(ROOT))
            except Exception as exc:
                item["periods"][period] = {"status": "failed", "error": type(exc).__name__}
        before, after = [item["periods"][p].get("cash_plus_short") for p in ["2025-12-31", "2026-06-30"]]
        item["change"] = after - before if before is not None and after is not None else None
        print(name, {p: v["status"] for p, v in item["periods"].items()}, flush=True)
        return item
    with ThreadPoolExecutor(max_workers=5) as pool:
        companies = list(pool.map(collect, json.loads(UNIVERSE.read_text())))
    snapshot = {"schema_version": 1, "collected_at": stamp, "period": "2026-06-30", "comparison_period": "2025-12-31", "scope": "OFS", "pilot": True, "companies": companies}
    (dest / "snapshot.json").write_text(json.dumps(snapshot, ensure_ascii=False, indent=2))
    if all(c["periods"]["2026-06-30"]["status"] == "ok" for c in companies):
        (ROOT / "data/corporate/latest.json").write_text(json.dumps(snapshot, ensure_ascii=False, indent=2))
    else:
        print("Incomplete collection: latest left unchanged")

if __name__ == "__main__":
    main()

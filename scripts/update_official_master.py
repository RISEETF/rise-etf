#!/usr/bin/env python3
"""Build the canonical RISE instrument master from the official ETF Finder."""
import base64
import datetime as dt
import gzip
import hashlib
import html
import json
import math
import re
from pathlib import Path
import urllib.parse
import urllib.request

from update_daily import ROOT, write_json

FINDER_URL = "https://riseetf.co.kr/prod/finder"
LIST_URL = "https://riseetf.co.kr/prod/finder/listJquery"
PAGE_SIZE = 12


def clean(fragment):
    fragment = re.sub(r"<span class=\"blind\">.*?</span>", " ", fragment, flags=re.S)
    value = " ".join(html.unescape(re.sub(r"<.*?>", " ", fragment)).split())
    return re.sub(r"\s*/\s*", "/", value)


def extract_overview(page):
    total = re.search(r"전체\s*<span>(\d+)</span>\s*건", page)
    effective = re.search(r"(\d{4}\.\d{2}\.\d{2})\s*기준", page)
    if not total or not effective:
        raise ValueError("Official Finder count or effective date is missing")
    return int(total.group(1)), effective.group(1).replace(".", "-")


def parse_products(page):
    products = []
    for block in re.findall(r'<tr data-class="dataList">(.*?)</tr>', page, re.S):
        link = re.search(r'href="/prod/finderDetail/([^\"]+)">(.*?)</a>', block, re.S)
        if not link:
            raise ValueError("Product row is missing a detail link")
        detail_id = link.group(1)
        name = clean(link.group(2))
        code_match = re.search(r'<span class="code">\(([^)]+)\)</span>', block, re.S)
        if code_match:
            code = code_match.group(1).strip()
        else:
            embedded = re.search(r"\(([0-9A-Z]{6})\)\s*$", name)
            if not embedded:
                raise ValueError("Product row is missing an exchange code")
            code = embedded.group(1)
            name = name[:embedded.start()].strip()

        tag_pairs = re.findall(r'<span class="(tag_type0[123])">(.*?)</span>', block, re.S)
        primary = [clean(value) for kind, value in tag_pairs if kind == "tag_type01"]
        secondary = [clean(value) for kind, value in tag_pairs if kind == "tag_type02"]
        labels = [clean(value) for kind, value in tag_pairs if kind == "tag_type03"]

        without_graph = re.sub(r'<div class="graph".*?</div>', "", block, flags=re.S)
        cells = [clean(value) for value in re.findall(r"<td[^>]*>(.*?)</td>", without_graph, re.S)]
        if len(cells) < 9:
            raise ValueError(f"Product {code} is missing official table fields")
        fee = cells[1]
        listed_on = cells[-2].replace(".", "-")
        dt.date.fromisoformat(listed_on)
        if not re.fullmatch(r"[0-9A-Z]{6}", code) or not name.startswith("RISE "):
            raise ValueError(f"Invalid official product identity: {code} {name}")
        products.append({
            "code": code,
            "name": name,
            "detail_id": detail_id,
            "detail_url": f"https://riseetf.co.kr/prod/finderDetail/{detail_id}",
            "primary_category": primary[0] if primary else None,
            "secondary_categories": secondary,
            "labels": labels,
            "published_total_fee": fee,
            "listed_on": listed_on,
        })
    return products


def validate_master(products, expected_count):
    if len(products) != expected_count:
        raise ValueError(f"Expected {expected_count} official rows, got {len(products)}")
    codes = [item["code"] for item in products]
    details = [item["detail_id"] for item in products]
    if len(codes) != len(set(codes)):
        raise ValueError("Duplicate exchange code in official master")
    if len(details) != len(set(details)):
        raise ValueError("Duplicate detail ID in official master")
    return products


def fetch_text(url, data=None):
    headers = {"User-Agent": "RISE-research/0.1", "Accept": "text/html"}
    if data is not None:
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        headers["Referer"] = FINDER_URL
    request = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(request, timeout=45) as response:
        return response.read().decode("utf-8")


def fetch_official_pages():
    overview = fetch_text(FINDER_URL)
    total, effective_date = extract_overview(overview)
    page_count = math.ceil(total / PAGE_SIZE)
    form = urllib.parse.urlencode({
        "searchText": "", "searchType1": "", "searchType2": "",
        "page": str(page_count), "searchOrder": "", "searchBoardType": "",
        "searchFieldType": "list",
    }).encode()
    listing = fetch_text(LIST_URL, form)
    return overview, listing, total, effective_date


def reconcile_legacy(products, legacy_rows):
    official = {item["code"]: item for item in products}
    records = []
    for row in legacy_rows:
        code, name = str(row[0]), str(row[1])
        match = official.get(code)
        if not match:
            state = "NOT_IN_OFFICIAL_CURRENT_MASTER"
        elif "".join(name.split()) == "".join(match["name"].split()):
            state = "IDENTITY_MATCH"
        else:
            state = "OFFICIAL_NAME_MISMATCH"
        records.append({"code": code, "legacy_name": name,
                        "official_name": match["name"] if match else None, "status": state})
    return records


def reconcile_secondary_capture(products, quotes):
    official = {item["code"]: item["name"] for item in products}
    secondary = {str(item["itemcode"]): str(item["itemname"])
                 for item in quotes if str(item.get("itemname", "")).startswith("RISE ")}
    only_official = sorted(set(official) - set(secondary))
    only_secondary = sorted(set(secondary) - set(official))
    name_mismatches = [{"code": code, "official_name": official[code],
                        "secondary_name": secondary[code]}
                       for code in sorted(set(official) & set(secondary))
                       if "".join(official[code].split()) != "".join(secondary[code].split())]
    return {"official_count": len(official), "secondary_rise_count": len(secondary),
            "only_official": only_official, "only_secondary": only_secondary,
            "name_mismatches": name_mismatches,
            "status": "EXACT_IDENTITY_MATCH" if not only_official and not only_secondary and not name_mismatches
                      else "IDENTITY_DIFFERENCE"}


def main():
    captured_at = dt.datetime.now(dt.timezone.utc).isoformat()
    overview, listing, total, effective_date = fetch_official_pages()
    products = validate_master(parse_products(listing), total)

    raw = listing.encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    raw_record = {
        "source_url": LIST_URL,
        "finder_url": FINDER_URL,
        "retrieved_at": captured_at,
        "effective_date_from_page": effective_date,
        "sha256_uncompressed": digest,
        "content_encoding": "gzip+base64",
        "content": base64.b64encode(gzip.compress(raw, mtime=0)).decode("ascii"),
    }
    write_json(ROOT / "data/raw/rise_finder" / f"{digest}.json", raw_record)

    master = {
        "status": "OFFICIAL_IDENTITY_MASTER",
        "source_url": FINDER_URL,
        "retrieved_at": captured_at,
        "effective_date": effective_date,
        "source_sha256": digest,
        "instrument_count": len(products),
        "field_scope": ["code", "name", "detail_id", "category", "labels", "published_total_fee", "listed_on"],
        "products": products,
    }
    master_dir = ROOT / "data/master"
    write_json(master_dir / f"{effective_date}.json", master)
    write_json(master_dir / "latest.json", master)

    legacy = json.loads((ROOT / "data/latest.json").read_text(encoding="utf-8"))["items"]
    reconciliation = reconcile_legacy(products, legacy)
    counts = {}
    for item in reconciliation:
        counts[item["status"]] = counts.get(item["status"], 0) + 1
    secondary_reconciliation = None
    capture_status_path = ROOT / "data/collection_status.json"
    if capture_status_path.exists():
        capture_status = json.loads(capture_status_path.read_text(encoding="utf-8"))
        secondary_digest = capture_status.get("sha256")
        secondary_path = ROOT / "data/raw/naver" / f"{secondary_digest}.json"
        if secondary_digest and secondary_path.exists():
            raw_record = json.loads(secondary_path.read_text(encoding="utf-8"))
            secondary_raw = base64.b64decode(raw_record["raw_base64"])
            try:
                secondary_text = secondary_raw.decode("utf-8")
            except UnicodeDecodeError:
                secondary_text = secondary_raw.decode("cp949")
            quotes = json.loads(secondary_text)["result"]["etfItemList"]
            secondary_reconciliation = reconcile_secondary_capture(products, quotes)

    quality = {
        "status": "COMPLETE_FOR_IDENTITY_FIELDS",
        "official_effective_date": effective_date,
        "official_source_url": FINDER_URL,
        "official_source_sha256": digest,
        "legacy_count": len(legacy),
        "official_count": len(products),
        "counts": counts,
        "records": reconciliation,
        "secondary_capture_reconciliation": secondary_reconciliation,
        "excluded_from_verification": ["market_price", "NAV", "returns", "AUM", "pension_limit", "marketing_reason"],
    }
    write_json(ROOT / "data/quality/official_master_reconciliation.json", quality)
    lines = [
        "# Official RISE instrument master validation", "",
        f"- Official source: {FINDER_URL}",
        f"- Official effective date: {effective_date}",
        f"- Official products: {len(products)}", "",
        "## Legacy portal reconciliation", "",
        "| Result | Count |", "|---|---:|",
    ]
    lines.extend(f"| {key} | {value} |" for key, value in counts.items())
    if secondary_reconciliation:
        lines.extend(["", "## Secondary market capture check", "",
                      f"Status: **{secondary_reconciliation['status']}**. ",
                      f"The independent capture contained {secondary_reconciliation['secondary_rise_count']} RISE identities."])
    lines.extend(["", "## Scope", "",
                  "Identity, official category labels, published total fee, listing date and official detail URL are captured.",
                  "Price, NAV, returns, AUM, pension limits and marketing claims remain outside this verification.", ""])
    (ROOT / "OFFICIAL_MASTER_VALIDATION.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"official_count": len(products), "effective_date": effective_date,
                      "legacy_reconciliation": counts}, ensure_ascii=False))


if __name__ == "__main__":
    main()

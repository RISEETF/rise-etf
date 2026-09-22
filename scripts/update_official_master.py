#!/usr/bin/env python3
"""Build the canonical RISE instrument master from the official ETF Finder."""
import base64
import datetime as dt
import gzip
import hashlib
import html
import json
import re
from pathlib import Path
import urllib.request
from concurrent.futures import ThreadPoolExecutor

from update_daily import ROOT, write_json
from master_changes import record_changes

FINDER_URL = "https://kbam.co.kr/find"
LIST_URL = "https://kbam.co.kr/api/products/etfs"


def clean(fragment):
    fragment = re.sub(r"<span class=\"blind\">.*?</span>", " ", fragment, flags=re.S)
    value = " ".join(html.unescape(re.sub(r"<.*?>", " ", fragment)).split())
    return re.sub(r"\s*/\s*", "/", value)


def extract_overview(page):
    if 'filtergroup_count_value' in page:
        total = re.search(r'filtergroup_count_value[^\"]*\">(\d+)</span>', page)
        effective = re.search(r'<time dateTime="(\d{4}-\d{2}-\d{2})"', page)
        if not total or not effective:
            raise ValueError('Official count or date missing from redesigned Finder')
        dt.date.fromisoformat(effective.group(1))
        return int(total.group(1)), effective.group(1)
    total = re.search(r"전체\s*<span>(\d+)</span>\s*건", page)
    effective = re.search(r"(\d{4}\.\d{2}\.\d{2})\s*기준", page)
    if not total or not effective:
        raise ValueError("Official Finder count or effective date is missing")
    return int(total.group(1)), effective.group(1).replace(".", "-")


def parse_catalog(page):
    if page.lstrip().startswith('{'):
        envelope=json.loads(page)
        if envelope.get('format')!='KBAM_ETF_API_V1':
            raise ValueError('Unknown official source format')
        pages=envelope['pages']
        if not pages:
            raise ValueError('Missing API pages')
        products=[]; pending=[]
        total=None
        for number, capture in enumerate(pages,1):
            payload=json.loads(capture['body']); info=payload['page_info']
            if (info['current_page']!=number or info['total_page']!=len(pages) or
                (total is not None and info['total_count']!=total)):
                raise ValueError('Incomplete or inconsistent official API pagination')
            total=info['total_count']
            for row in payload['page_items']:
                code=row['krx_cd'];detail=row['fund_cd'];name=row['name'].strip()
                listed=dt.datetime.fromisoformat(row['listing_dt']).date().isoformat()
                if (code is not None and not re.fullmatch(r'[0-9A-Z]{6}',code)) or not re.fullmatch(r'[a-zA-Z0-9]+',detail) or not name.startswith('RISE '):
                    raise ValueError('Invalid official product identity')
                item={'code':code,'name':name,'detail_id':detail,
                                 'detail_url':f'https://kbam.co.kr/products/{detail}',
                                 'primary_category':row.get('category1'),
                                 'secondary_categories':[row['category2']] if row.get('category2') else [],
                                 'labels':[], 'published_total_fee':None,'listed_on':listed}
                if code is None:
                    item['identity_status']='OFFICIAL_CODE_PENDING';pending.append(item)
                else:products.append(item)
        details=[r['detail_id'] for r in products+pending]
        if len(details)!=total or len(set(details))!=len(details):
            raise ValueError('Incomplete or duplicate official catalog')
        validate_master(products,total-len(pending))
        return products,pending
    return parse_products(page),[]


def parse_products(page):
    if page.lstrip().startswith('{'):
        return parse_catalog(page)[0]
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
    if expected_count <= 0:
        raise ValueError("Official master cannot be empty")
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
    headers = {"User-Agent": "RISE-research/0.1", "Accept": "application/json" if '/api/' in url else "text/html"}
    if data is not None:
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        headers["Referer"] = FINDER_URL
    request = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(request, timeout=45) as response:
        return response.read().decode("utf-8")


def fetch_official_pages():
    overview = fetch_text(FINDER_URL)
    total, effective_date = extract_overview(overview)
    first=fetch_text(LIST_URL+'?page=1')
    info=json.loads(first)['page_info']
    if info['total_count']!=total or not 1<=info['total_page']<=100:
        raise ValueError('Finder and API count disagree')
    def capture(number):
        url=LIST_URL+f'?page={number}'
        return {'url':url,'body':first if number==1 else fetch_text(url)}
    with ThreadPoolExecutor(max_workers=4) as pool:
        pages=list(pool.map(capture,range(1,info['total_page']+1)))
    listing=json.dumps({'format':'KBAM_ETF_API_V1','pages':pages},ensure_ascii=False)
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


def persist_master(master_dir, master):
    """Keep the first daily vintage and every distinct captured version."""
    effective = dt.date.fromisoformat(master["effective_date"]).isoformat()
    retrieved = dt.datetime.fromisoformat(master["retrieved_at"])
    capture_id = retrieved.strftime("%Y%m%dT%H%M%S%fZ")
    vintage = master_dir / "captures" / f"{capture_id}-{master['source_sha256']}.json"
    if not vintage.exists():
        write_json(vintage, master)
    daily = master_dir / f"{effective}.json"
    if not daily.exists():
        write_json(daily, master)
    latest = master_dir / "latest.json"
    previous = None
    if latest.exists():
        previous = json.loads(latest.read_text(encoding="utf-8"))
        if previous["effective_date"] > effective:
            raise ValueError("Refusing to replace master with an older effective date")
    write_json(latest, master)
    if 'products' in master:
        record_changes(master_dir, previous, master)


def main():
    captured_at = dt.datetime.now(dt.timezone.utc).isoformat()
    overview, listing, total, effective_date = fetch_official_pages()
    products, pending = parse_catalog(listing)
    validate_master(products, total-len(pending))

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
    raw_path = ROOT / "data/raw/rise_finder" / f"{digest}.json"
    if not raw_path.exists():
        write_json(raw_path, raw_record)
    overview_raw = overview.encode("utf-8")
    overview_digest = hashlib.sha256(overview_raw).hexdigest()
    overview_path = ROOT / "data/raw/rise_finder" / f"{overview_digest}.json"
    if not overview_path.exists():
        write_json(overview_path, {
            "source_url": FINDER_URL, "retrieved_at": captured_at,
            "sha256_uncompressed": overview_digest, "content_encoding": "gzip+base64",
            "content": base64.b64encode(gzip.compress(overview_raw, mtime=0)).decode("ascii"),
        })

    master = {
        "status": "OFFICIAL_IDENTITY_MASTER",
        "source_url": FINDER_URL,
        "retrieved_at": captured_at,
        "effective_date": effective_date,
        "source_sha256": digest,
        "overview_sha256": overview_digest,
        "instrument_count": len(products),
        "source_product_count": total,
        "pending_products": pending,
        "field_scope": ["code", "name", "detail_id", "category", "listed_on"],
        "unavailable_fields": ["pension_labels", "published_total_fee"],
        "products": products,
    }
    master_dir = ROOT / "data/master"

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
            if hashlib.sha256(secondary_raw).hexdigest() != secondary_digest:
                raise ValueError("Secondary source checksum mismatch")
            try:
                secondary_text = secondary_raw.decode("utf-8")
            except UnicodeDecodeError:
                secondary_text = secondary_raw.decode("cp949")
            quotes = json.loads(secondary_text)["result"]["etfItemList"]
            secondary_reconciliation = reconcile_secondary_capture(products, quotes)
            secondary_reconciliation["retrieved_at"] = capture_status.get("retrieved_at")
            secondary_reconciliation["sha256"] = secondary_digest
            secondary_reconciliation["scope"] = "Captured identities only; captures may be from different dates"

    quality = {
        "status": "COMPLETE_FOR_IDENTITY_FIELDS",
        "official_effective_date": effective_date,
        "official_source_url": FINDER_URL,
        "official_source_sha256": digest,
        "legacy_count": len(legacy),
        "official_count": len(products),
        "source_product_count": total,
        "pending_identity_count": len(pending),
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
        f"- Official catalog products: {total}",
        f"- Verified exchange-code identities: {len(products)}",
        f"- Official products awaiting exchange code: {len(pending)}", "",
        "## Legacy portal reconciliation", "",
        "| Result | Count |", "|---|---:|",
    ]
    lines.extend(f"| {key} | {value} |" for key, value in counts.items())
    if secondary_reconciliation:
        lines.extend(["", "## Secondary market capture check", "",
                      f"Status: **{secondary_reconciliation['status']}**.",
                      f"The independent capture contained {secondary_reconciliation['secondary_rise_count']} RISE identities.",
                      f"Secondary retrieval time: {secondary_reconciliation.get('retrieved_at')}. Captures may be from different dates."])
    lines.extend(["", "## Scope", "",
                  "Identity, official categories, listing date and official detail URL are captured. The redesigned list does not supply pension labels or total fees; these are left unavailable, not copied from old snapshots.",
                  "Price, NAV, returns, AUM, pension limits and marketing claims remain outside this verification.", ""])
    (ROOT / "OFFICIAL_MASTER_VALIDATION.md").write_text("\n".join(lines), encoding="utf-8")
    persist_master(master_dir, master)
    print(json.dumps({"official_count": len(products), "source_product_count": total, "pending_identity_count": len(pending), "effective_date": effective_date,
                      "legacy_reconciliation": counts}, ensure_ascii=False))


def run():
    now = dt.datetime.now(dt.timezone.utc)
    status = {"attempted_at": now.isoformat(), "source_url": FINDER_URL}
    try:
        main()
        status["status"] = "SUCCESS"
    except Exception as exc:
        status.update(status="FAILED", reason=f"{type(exc).__name__}: {exc}")
    write_json(ROOT / "data/master_runs" / f"{now.strftime('%Y%m%dT%H%M%S%fZ')}.json", status)
    write_json(ROOT / "data/master_collection_status.json", status)
    print(json.dumps(status, ensure_ascii=False))
    return 0 if status["status"] == "SUCCESS" else 1


if __name__ == "__main__":
    raise SystemExit(run())

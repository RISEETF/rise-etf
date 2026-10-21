#!/usr/bin/env python3
"""Import a legitimately downloaded ETF CSV/XLSX into a quarantined, append-only archive.

Never scrapes websites or overwrites KRX primary data. The operator must provide
a file downloaded through the provider's ordinary export feature.
"""
import argparse
import csv
import datetime as dt
import hashlib
import json
import math
import pathlib
import re
import shutil
import sys
import zipfile

SOURCES = {"etfcheck", "funetf"}
EXTENSIONS = {".csv", ".xlsx"}
MAX_BYTES = 25 * 1024 * 1024

def read_rows(path):
    if path.suffix.lower() == ".csv":
        raw = path.read_bytes()
        for encoding in ("utf-8-sig", "cp949", "utf-8"):
            try:
                text = raw.decode(encoding)
                rows = list(csv.reader(text.splitlines()))
                return rows, encoding
            except UnicodeDecodeError:
                pass
        raise ValueError("CSV_ENCODING_UNSUPPORTED")
    try:
        import openpyxl
    except ImportError as exc:
        raise RuntimeError("XLSX_REQUIRES_OPENPYXL") from exc
    try:
        with zipfile.ZipFile(path) as package:
            if sum(item.file_size for item in package.infolist()) > 100 * 1024 * 1024:
                raise ValueError('XLSX_EXPANDED_SIZE_INVALID')
        book = openpyxl.load_workbook(path, read_only=True, data_only=True)
    except zipfile.BadZipFile as exc:
        raise ValueError('XLSX_INVALID') from exc
    try:
        sheet = book.active
        sheet.reset_dimensions()  # Provider exports can incorrectly declare A1:A1.
        rows = []
        for row in sheet.iter_rows(values_only=True):
            if len(rows) >= 100000 or len(row) > 150:
                raise ValueError('FILE_SHAPE_INVALID')
            rows.append([str(x) if x is not None else "" for x in row])
    finally:
        book.close()
    return rows, "xlsx"

FUNETF_KR_HEADER = [
    'ETF 종목명', 'ETF 단축코드', 'ETF 대유형', '1일(%)', '1주(%)',
    '1개월(%)', '3개월(%)', '6개월(%)', '연초후(%)', '1년(%)', '총보수(%)',
    '합성총보수(TER)(%)', '실부담비율(%)', '순자산(억원)', '3개월 괴리율(%)',
    '운용사명', 'TOP 1', '비율(%)', 'TOP 2', '비율(%)', 'TOP 3', '비율(%)']


def normalize_kr_code(value):
    value = str(value).strip().upper()
    if re.fullmatch(r'[0-9]{1,6}', value):
        value = value.zfill(6)
    if not re.fullmatch(r'[0-9A-Z]{6}', value):
        raise ValueError('PROVIDER_CODE_INVALID')
    return value


def provider_number(value):
    text = str(value).strip().replace(',', '')
    if text in ('', '-', 'N/A', 'None'):
        return None
    try:
        result = float(text)
    except ValueError as exc:
        raise ValueError('PROVIDER_NUMBER_INVALID') from exc
    if not math.isfinite(result):
        raise ValueError('PROVIDER_NUMBER_NONFINITE')
    return result


def normalize_funetf_kr(rows):
    """Exact observed export schema; repeated holding-weight headers are positional."""
    if not rows or [str(v).strip() for v in rows[0]] != FUNETF_KR_HEADER:
        raise ValueError('FUNETF_SCHEMA_UNSUPPORTED')
    records = []; codes = set()
    for row in rows[1:]:
        if not any(str(v).strip() for v in row):
            continue
        if len(row) != len(FUNETF_KR_HEADER):
            raise ValueError('FUNETF_ROW_WIDTH_INVALID')
        code = normalize_kr_code(row[1])
        if code in codes:
            raise ValueError('PROVIDER_DUPLICATE_CODE')
        codes.add(code)
        if not str(row[0]).strip() or not str(row[15]).strip():
            raise ValueError('PROVIDER_IDENTITY_MISSING')
        numbers = {FUNETF_KR_HEADER[i]: provider_number(row[i]) for i in range(3, 15)}
        for label in FUNETF_KR_HEADER[10:14]:
            if numbers[label] is not None and numbers[label] < 0:
                raise ValueError('PROVIDER_NEGATIVE_FEE_OR_ASSETS')
        holdings = [{'name': str(row[i]).strip(), 'weight_pct': provider_number(row[i+1])}
                    for i in (16, 18, 20)]
        records.append({'code': code, 'name': str(row[0]).strip(), 'market': 'KR',
                        'currency': 'KRW', 'category': str(row[2]).strip(),
                        'provider': str(row[15]).strip(), 'metrics': numbers,
                        'holdings_top3': holdings})
    if not records:
        raise ValueError('NO_DATA_ROWS')
    return records


def inspect_funetf_kr(path, inventory, observation_date=None):
    """Read-only QA. Does not archive, build a database or publish provider data."""
    if path.suffix.lower() not in EXTENSIONS or not path.is_file() or not 0 < path.stat().st_size <= MAX_BYTES:
        raise ValueError('FILE_INVALID')
    if observation_date:
        day = dt.date.fromisoformat(observation_date)
        if day > dt.datetime.now(dt.timezone.utc).date() + dt.timedelta(days=1):
            raise ValueError('FUTURE_OBSERVATION_DATE')
    rows, _ = read_rows(path)
    records = normalize_funetf_kr(rows)
    observed = inventory['observed_on']
    dt.date.fromisoformat(observed)
    # Include only presence in this KRX snapshot; historical absence is not a delisting.
    primary = {r['code']: r for r in inventory['products']
               if r['last_observed_on'] == observed and r['status'] == 'OBSERVED'}
    if len(primary) != inventory['observed_count']:
        raise ValueError('KRX_INVENTORY_COUNT_MISMATCH')
    secondary = {r['code']: r for r in records if r['name'].startswith('RISE ')}
    return {
        'status': 'INSPECTED_NOT_PUBLISHED', 'market': 'KR',
        'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
        'inspected_at_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
        'provider_observation_date': observation_date,
        'provider_date_basis': 'OPERATOR_SUPPLIED' if observation_date else 'UNKNOWN',
        'krx_observation_date': observed, 'krx_raw_sha256': inventory['raw_sha256'],
        'date_comparison': ('UNKNOWN' if not observation_date else
                            'SAME_DATE' if observation_date == observed else 'DIFFERENT_DATES'),
        'provider_rows': len(records), 'columns': len(rows[0]),
        'provider_rise_count': len(secondary), 'krx_rise_count': len(primary),
        'matched_rise_count': len(primary.keys() & secondary.keys()),
        'missing_from_provider': [{'code': c, 'name': primary[c]['name']}
                                  for c in sorted(primary.keys() - secondary.keys())],
        'not_observed_in_krx': sorted(secondary.keys() - primary.keys()),
        'name_differences': [{'code': c, 'krx': primary[c]['name'], 'provider': secondary[c]['name']}
                             for c in sorted(primary.keys() & secondary.keys())
                             if ''.join(primary[c]['name'].split()) != ''.join(secondary[c]['name'].split())],
        'metric_nonnull_counts': {label: sum(r['metrics'][label] is not None for r in records)
                                  for label in FUNETF_KR_HEADER[3:15]},
        'publication_eligible': False, 'primary_data_overwritten': False,
        'lifecycle_note': 'Provider absence is not delisting; KRX observation is not a legal lifecycle notice.'}


def ingest(path, source, observation_date, output):
    if source not in SOURCES:
        raise ValueError("SOURCE_NOT_SUPPORTED")
    if path.suffix.lower() not in EXTENSIONS:
        raise ValueError("FILE_TYPE_NOT_SUPPORTED")
    if not path.is_file() or path.stat().st_size == 0 or path.stat().st_size > MAX_BYTES:
        raise ValueError("FILE_SIZE_INVALID")
    day = dt.date.fromisoformat(observation_date)
    if day > dt.datetime.now(dt.timezone.utc).date() + dt.timedelta(days=1):
        raise ValueError("FUTURE_OBSERVATION_DATE")
    rows, encoding = read_rows(path)
    if len(rows) < 2 or not any(any(str(x).strip() for x in row) for row in rows[1:]):
        raise ValueError("NO_DATA_ROWS")
    if len(rows) > 100000 or max(map(len, rows)) > 150:
        raise ValueError("FILE_SHAPE_INVALID")
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    target = output / source / observation_date / digest
    target.mkdir(parents=True, exist_ok=True)
    copy = target / ("original" + path.suffix.lower())
    if copy.exists() and hashlib.sha256(copy.read_bytes()).hexdigest() != digest:
        raise RuntimeError("ARCHIVE_HASH_COLLISION")
    if not copy.exists():
        shutil.copyfile(path, copy)
    manifest = {
        "schema_version": "1.0", "source": source,
        "observation_date": observation_date, "sha256": digest,
        "original_filename": path.name, "encoding": encoding,
        "row_count_including_header": len(rows),
        "header_preview": [str(x)[:100] for x in rows[0][:30]],
        "retrieved_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "status": "QUARANTINED", "publication_eligible": False,
        "primary_data_overwritten": False,
        "note": "Unverified provider export. Requires mapping, licensing and cross-source QA."
    }
    manifest_path = target / "manifest.json"
    if not manifest_path.exists():
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    return {"status": "ARCHIVED_QUARANTINED", "source": source,
            "observation_date": observation_date, "sha256": digest,
            "archive_path": str(target), "rows": len(rows)}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", choices=sorted(SOURCES), required=True)
    parser.add_argument("--file", type=pathlib.Path, required=True)
    parser.add_argument("--observation-date")
    parser.add_argument("--inspect-only", action="store_true")
    parser.add_argument("--krx-inventory", type=pathlib.Path)
    parser.add_argument("--output", type=pathlib.Path, default=pathlib.Path("var/provider_exports"))
    args = parser.parse_args()
    try:
        if args.inspect_only:
            if args.source != 'funetf' or args.krx_inventory is None:
                raise ValueError('INSPECTION_REQUIRES_FUNETF_AND_KRX_INVENTORY')
            result = inspect_funetf_kr(args.file, json.loads(args.krx_inventory.read_text()), args.observation_date)
        else:
            if not args.observation_date:
                raise ValueError('ARCHIVE_REQUIRES_OBSERVATION_DATE')
            result = ingest(args.file, args.source, args.observation_date, args.output)
    except (ValueError, RuntimeError, OSError) as exc:
        print(json.dumps({"status": "FAILED", "reason": str(exc).split(":")[0][:90]}))
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 0

if __name__ == "__main__":
    sys.exit(main())

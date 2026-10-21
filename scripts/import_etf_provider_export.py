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
import pathlib
import re
import shutil
import sys

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
    book = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        sheet = book.active
        rows = [[str(x) if x is not None else "" for x in row]
                for row in sheet.iter_rows(values_only=True)]
    finally:
        book.close()
    return rows, "xlsx"

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
    parser.add_argument("--observation-date", required=True)
    parser.add_argument("--output", type=pathlib.Path, default=pathlib.Path("var/provider_exports"))
    args = parser.parse_args()
    try:
        result = ingest(args.file, args.source, args.observation_date, args.output)
    except (ValueError, RuntimeError, OSError) as exc:
        print(json.dumps({"status": "FAILED", "reason": str(exc).split(":")[0][:90]}))
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 0

if __name__ == "__main__":
    sys.exit(main())

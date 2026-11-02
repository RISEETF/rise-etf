"""Process up to five changed, locally downloaded KRX PDF bundles per run.

Each inbox child directory contains original.csv, receipt.json and queue.json.
No credentials, network requests or deletion; original importer is authoritative.
"""
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path

from collect_krx_etf import write_json_atomic
from import_krx_pdf import ingest

FILES = ('original.csv', 'receipt.json', 'queue.json')


def process(inbox, output, public_receipts=None):
    inbox, output = Path(inbox), Path(output)
    state_path = output / 'inbox_status.json'
    prior = json.loads(state_path.read_text()) if state_path.exists() else {}
    entries = prior.get('entries', {})
    stamp = dt.datetime.now(dt.timezone.utc).isoformat()
    publication = str(Path(public_receipts).resolve()) if public_receipts else None
    processed = failed = deferred = 0
    # Preserve receipts for removed directories; do not delete imported history.
    for directory in sorted(inbox.iterdir(), key=lambda p: (
            entries.get(p.name, {}).get("status") == "FAILED", p.name)):
        if directory.is_symlink() or not directory.is_dir():
            continue
        paths = [directory / name for name in FILES]
        if any(p.is_symlink() or not p.is_file() for p in paths):
            entries[directory.name] = {'status': 'WAITING_FOR_BUNDLE'}
            continue
        if any(p.stat().st_size > 10 * 1024 * 1024 for p in paths):
            entries[directory.name] = {'status': 'FAILED', 'reason': 'BUNDLE_TOO_LARGE'}
            failed += 1
            continue
        digest = hashlib.sha256()
        for path in paths:
            digest.update(hashlib.sha256(path.read_bytes()).digest())
        fingerprint = digest.hexdigest()
        previous = entries.get(directory.name, {})
        if (previous.get('fingerprint') == fingerprint and previous.get('status') == 'SUCCESS'
                and previous.get('publication') == publication
                and (not public_receipts or Path(public_receipts).exists())):
            continue
        if processed >= 5:
            deferred += 1
            continue
        processed += 1
        result = {'fingerprint': fingerprint, 'attempted_at': stamp, 'publication': publication}
        try:
            receipt = json.loads(paths[1].read_text())
            queue = json.loads(paths[2].read_text())
            if not isinstance(queue.get('items'), list) or len(queue['items']) > 5:
                raise ValueError('PDF_QUEUE_INVALID')
            summary = ingest(paths[0], receipt, queue, output, public_receipts)
            result.update(status='SUCCESS', ticker=summary['ticker'],
                          observation_date=summary['observation_date'], sha256=summary['sha256'])
        except Exception as exc:
            failed += 1
            # Keep diagnostics finite: arbitrary exception messages may contain data.
            reason = str(exc)
            result.update(status='FAILED', reason=reason if reason.startswith('PDF_') and
                          reason.replace('_', '').isalnum() else type(exc).__name__)
        entries[directory.name] = result
    report = {'schema': 'KRX_PDF_INBOX_V1', 'attempted_at': stamp,
              'status': 'PARTIAL' if failed or deferred or any(
                  e['status'] != 'SUCCESS' for e in entries.values()) else 'SUCCESS',
              'processed': processed, 'failed': failed, 'deferred': deferred,
              'entries': entries}
    write_json_atomic(state_path, report)
    return report


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--inbox', default='var/etf-pdf-inbox')
    p.add_argument('--output', default='var/etf-pdf')
    p.add_argument('--public-receipts', help='Optional existing metadata receipt path')
    args = p.parse_args()
    print(json.dumps(process(args.inbox, args.output, args.public_receipts), ensure_ascii=False))

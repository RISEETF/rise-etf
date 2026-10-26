"""Download selected DART notes for manual review. No automatic evidence promotion."""
import argparse, html, io, json, re, zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from collect_corporate_cash import ROOT, request


def separate_notes(text):
    # Ignore table-of-contents entries and narrative cross references.
    headings = list(re.finditer(r'5\.\s*재무제표\s*주석\s+(?:1\.|제\s*\d)', text))
    if not headings:
        return None
    start = headings[0].start()
    end = re.search(r'6\.\s*배당에 관한 사항', text[start:])
    return text[start:start + end.start()] if end else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--key-file', required=True)
    ap.add_argument('--codes', required=True, help='Comma separated stock codes')
    args = ap.parse_args()
    key = Path(args.key_file).read_text().strip()
    data = json.loads((ROOT / 'data/corporate/latest.json').read_text())
    wanted = set(args.codes.split(','))
    companies = [c for c in data['companies'] if c['code'] in wanted]
    if len(companies) != len(wanted):
        raise SystemExit('Unknown or duplicate stock code')
    dest = ROOT / 'var/note-review'
    dest.mkdir(parents=True, exist_ok=True)
    def collect(c):
        receipt = c['periods'][data['period']]['receipt']
        path = dest / (c['code'] + '_' + receipt)
        xml_path = path.with_suffix('.xml')
        if not xml_path.exists():
            raw = request('document.xml', key, rcept_no=receipt)
            with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                name = max((n for n in archive.namelist() if n.endswith('.xml')), key=lambda n: archive.getinfo(n).file_size)
                xml_path.write_bytes(archive.read(name))
        text = html.unescape(re.sub('<[^>]+>', ' ', xml_path.read_text()))
        text = re.sub(r'\s+', ' ', text)
        path.with_suffix('.txt').write_text(text)
        section = separate_notes(text)
        if section:
            path.with_suffix('.separate.txt').write_text(section)
        result = {'code': c['code'], 'name': c['name'], 'receipt': receipt, 'period': data['period'], 'status': 'separate_section_found' if section else 'manual_scope_required', 'text_path': str(path.with_suffix('.separate.txt' if section else '.txt').relative_to(ROOT))}
        print(c['name'], result['status'], flush=True)
        return result
    with ThreadPoolExecutor(max_workers=5) as pool:
        results = list(pool.map(collect, companies))
    (dest / 'scan_index.json').write_text(json.dumps(results, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()

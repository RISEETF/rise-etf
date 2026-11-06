import base64
import gzip
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from verify_portable_issuer import verify


class PortableIssuerTests(unittest.TestCase):
    def test_archived_source_and_missing_page(self):
        master = json.loads((ROOT/'data/master/2026-10-04.json').read_text())
        def raw(key):
            record = json.loads((ROOT/'data/raw/rise_finder'/(
                master[key]+'.json')).read_text())
            return gzip.decompress(base64.b64decode(record['content']))
        def b64(value):
            return base64.b64encode(value).decode()
        pages = json.loads(raw('source_sha256'))['pages']
        bundle = dict(format='KBAM_PORTABLE_V1', finder_url='https://kbam.co.kr/find',
                      started_at='2026-10-05T10:11:10Z', captured_at='2026-10-05T10:12:10Z',
                      overview_b64=b64(raw('overview_sha256')),
                      pages=[dict(url=p['url'],body_b64=b64(p['body'].encode())) for p in pages])
        result = verify(bundle)
        self.assertEqual(result['verified_codes'], master['instrument_count'])
        self.assertEqual(result['effective_date'], master['effective_date'])
        self.assertFalse(result['master_updated'])
        bundle['pages'].pop()
        with self.assertRaises(ValueError): verify(bundle)

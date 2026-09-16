import datetime as dt
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
spec = importlib.util.spec_from_file_location('pipeline', Path(__file__).resolve().parents[1] / 'scripts/update_daily.py')
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)

class IntegrityTests(unittest.TestCase):
    def test_failure_never_redates_baseline(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            original = b'{"date":"2020-01-01"}'
            (root/'latest.json').write_bytes(original)
            def failed(): raise OSError('offline')
            result = p.collect(root, failed)
            self.assertEqual(result['status'], 'FAILED')
            self.assertEqual((root/'latest.json').read_bytes(), original)
            self.assertFalse(list(root.glob('????-??-??.json')))

    def test_capture_is_not_a_verified_close(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw = json.dumps({'result': {'etfItemList': [{'itemcode':'069500','nowVal':100}]}}).encode()
            result = p.collect(root, lambda: raw)
            self.assertEqual(result['quote_count'], 1)
            self.assertIsNone(result['observation_date'])
            self.assertFalse(result['published_to_portal'])
            self.assertEqual(len(list((root/'raw/naver').glob('*.json'))), 1)
            self.assertFalse((root/'latest.json').exists())

    def test_archive_preserves_first_vintage(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = {'date':'2020-01-01','items':[['069500'] + ['x']*19]}
            p.write_json(root/'latest.json', data)
            p.archive_snapshot(root)
            saved = (root/'2020-01-01.json').read_bytes()
            data['items'][0][1] = 'changed'
            p.write_json(root/'latest.json', data)
            p.archive_snapshot(root)
            self.assertEqual(saved,(root/'2020-01-01.json').read_bytes())

    def test_invalid_quotes_rejected(self):
        for rows in [[], [{'itemcode':'x','nowVal':0}], [{'itemcode':'x','nowVal':1}]*2]:
            with self.assertRaises(ValueError):
                p.normalize_quotes({'result': {'etfItemList': rows}})

if __name__ == '__main__': unittest.main()

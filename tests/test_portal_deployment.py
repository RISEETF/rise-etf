import importlib.util
import json
import pathlib
import tempfile
import unittest
from unittest.mock import patch
spec=importlib.util.spec_from_file_location('deployment',pathlib.Path(__file__).resolve().parents[1]/'scripts/verify_portal_deployment.py')
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class DeploymentTests(unittest.TestCase):
    def test_price_mismatch_retains_path_and_success_clears_previous_reason(self):
        for recover in (False, True):
            with self.subTest(recover=recover), tempfile.TemporaryDirectory() as tmp:
                root=pathlib.Path(tmp)
                for path in module.FILES:
                    dest=root/path;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(b'expected')
                calls={'price':0}
                def fetch(url, api=False):
                    if url.endswith('/pages'):
                        return json.dumps({'html_url':'https://example.test/','source':{'branch':'main','path':'/'}}).encode(),200
                    if url.endswith('/pages/builds/latest'):return b'{"status":"built"}',200
                    if 'data/etf_market/latest.json' in url:
                        calls['price']+=1
                        if not recover or calls['price']==1:return b'old',200
                    return b'expected',200
                with patch.object(module,'ROOT',root),patch.object(module,'TOKEN','fixture'),patch.object(module,'ATTEMPTS',2),patch.object(module,'WAIT',0),patch.object(module,'fetch',side_effect=fetch):
                    result=module.verify()
                self.assertEqual(result['status'],'PASS' if recover else 'FAIL')
                if recover:self.assertNotIn('reason',result)
                else:
                    self.assertEqual(result['files'][-1]['path'],'data/etf_market/latest.json')
                    self.assertFalse(result['files'][-1]['sha256_match'])

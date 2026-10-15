import datetime as dt
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from record_pipeline_status import record


class PipelineStatusTest(unittest.TestCase):
    def test_failure_before_collection_preserves_source_and_snapshot(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); (root/'master').mkdir()
            (root/'master/latest.json').write_text('{"effective_date":"2026-10-04"}')
            (root/'master_collection_status.json').write_text('{"status":"SUCCESS"}')
            before={p:p.read_bytes() for p in root.rglob('*.json')}
            receipt=record(root,'master',{'setup':'success','preflight':'failure','collect':'skipped'},'123',now=dt.datetime(2026,10,15,tzinfo=dt.timezone.utc))
            self.assertEqual(receipt['failed_stage'],'preflight')
            self.assertEqual(receipt['status'],'FAILED')
            self.assertEqual(json.loads((root/'operations/master.json').read_text()),receipt)
            for p,value in before.items(): self.assertEqual(p.read_bytes(),value)
            record(root,'master',{'setup':'success','preflight':'success','collect':'success'},'124')
            self.assertTrue((root/'operations/runs/master-123-1.json').exists())
            self.assertEqual(json.loads((root/'operations/master.json').read_text())['status'],'SUCCESS')

    def test_partial_failure_and_skipped_never_success(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertEqual(record(folder,'series',{'collect':'failure','rs':'success'},'1')['status'],'FAILED')
            self.assertEqual(record(folder,'series',{'collect':'skipped'},'2')['status'],'INCOMPLETE')

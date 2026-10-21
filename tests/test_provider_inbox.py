import csv
import importlib.util
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import process_etf_provider_inbox as pipeline
from import_etf_provider_export import FUNETF_KR_HEADER

class InboxTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.inbox=self.root/'inbox';self.inbox.mkdir()
        self.out=self.root/'out';self.inventory=self.root/'krx.json'
        self.inventory.write_text(json.dumps({'observed_on':'2026-10-20','observed_count':2,'raw_sha256':'krxhash',
            'products':[{'code':c,'name':n,'status':'OBSERVED','last_observed_on':'2026-10-20'}
                        for c,n in [('0254H0','RISE 신규'),('069500','RISE 테스트')]]}))
    def sample(self,name='sample.csv',code='069500',fee='1',date='2026-10-20'):
        path=self.inbox/name
        row=['RISE 테스트',code,'주식']+['1']*12+['KB운용','A','20','B','10','C','5']
        row[10]=fee
        with path.open('w') as f:csv.writer(f).writerows([FUNETF_KR_HEADER,row])
        path.with_suffix('.csv.json').write_text(json.dumps({'source':'funetf','market':'KR','observation_date':date,'retrieved_at_utc':'2026-10-21T00:00:00+00:00'}))
        return path
    def run_inbox(self):return pipeline.run(self.inbox,self.out,self.inventory)
    def test_real_transaction_idempotence_and_failure_preserves_page(self):
        self.sample();first=self.run_inbox();self.assertEqual(first['status'],'SUCCESS')
        before=(self.out/'index.html').read_bytes()
        self.assertEqual(self.run_inbox()['files'][0]['status'],'DUPLICATE')
        bad=self.inbox/'bad.csv';bad.write_text('bad,header\n1,2\n')
        failed=self.run_inbox();self.assertEqual(failed['status'],'PARTIAL')
        self.assertEqual((self.out/'index.html').read_bytes(),before)
        self.assertIsNotNone(failed['last_success_at_utc'])
        with sqlite3.connect(self.out/'provider.sqlite') as db:
            self.assertEqual(db.execute('SELECT count(*) FROM captures').fetchone()[0],1)
            self.assertEqual(db.execute('SELECT count(*) FROM observations').fetchone()[0],1)
        self.assertEqual(len(list((self.out/'raw').glob('*'))),2)
    def test_changes_and_backfill_do_not_regress_latest(self):
        self.sample();self.run_inbox()
        self.sample('new.csv',code='0254H0',date='2026-10-21');self.run_inbox()
        with sqlite3.connect(self.out/'provider.sqlite') as db:
            before=pipeline.latest_capture(db)[0]
            change=json.loads(db.execute('SELECT payload FROM changes').fetchone()[0])
            self.assertEqual(change['missing_in_provider'],['069500'])
            self.assertEqual(change['new_in_provider'],['0254H0'])
        self.sample('old.csv',fee='2',date='2026-10-19');self.run_inbox()
        with sqlite3.connect(self.out/'provider.sqlite') as db:
            self.assertEqual(pipeline.latest_capture(db)[0],before)
            self.assertEqual(db.execute('SELECT count(*) FROM changes').fetchone()[0],1)
    def test_conflicting_dates_and_us_schema_are_rejected(self):
        p=self.sample();self.run_inbox()
        p.with_suffix('.csv.json').write_text(json.dumps({'observation_date':'2026-10-19'}))
        self.assertEqual(self.run_inbox()['status'],'FAILED')
        p.with_suffix('.csv.json').write_text(json.dumps({'market':'US'}))
        self.assertEqual(self.run_inbox()['status'],'FAILED')
    def test_transaction_rolls_back_if_record_insert_fails(self):
        self.sample();self.out.mkdir();db=pipeline.connect(self.out)
        db.execute("CREATE TRIGGER reject_row BEFORE INSERT ON observations BEGIN SELECT RAISE(ABORT,'fixture failure'); END;");db.close()
        result=self.run_inbox();self.assertEqual(result['status'],'FAILED')
        with sqlite3.connect(self.out/'provider.sqlite') as db:
            self.assertEqual(db.execute('SELECT count(*) FROM captures').fetchone()[0],0)
        self.assertFalse((self.out/'index.html').exists())
    def test_public_output_and_concurrent_runs_rejected(self):
        with self.assertRaisesRegex(ValueError,'PRIVATE'):
            pipeline.run(self.inbox,ROOT/'data/providers',self.inventory)
        self.out.mkdir();(self.out/'.processing.lock').write_text('')
        with self.assertRaisesRegex(RuntimeError,'ALREADY_RUNNING'):
            self.run_inbox()
    def test_page_injection_is_escaped(self):
        p=self.sample();p.write_text(p.read_text().replace('RISE 테스트','RISE </script><script>alert(1)</script>'))
        self.run_inbox();page=(self.out/'index.html').read_text()
        self.assertNotIn('</script><script>alert(1)',page)
        self.assertIn('\\u003c/script',page)

if __name__=='__main__':unittest.main()

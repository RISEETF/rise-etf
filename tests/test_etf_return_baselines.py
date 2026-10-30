import datetime as dt
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from collect_krx_etf import accumulate
from backfill_etf_return_baselines import backfill

class BaselineTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.db=Path(self.tmp.name)/'ledger.sqlite';self.out=Path(self.tmp.name)/'raw'
        self.rows=[{'ticker':f'{i:06d}','name':f'ETF {i}','close':100,'nav':100,'volume':1,'listed_shares':100} for i in range(500)]
        accumulate(self.db,{'page_date':'2026-10-28','records':self.rows},'current','2026-10-29T00:00:00Z')
        self.receipt={'status':'SUCCESS','observation_date':'2026-10-28'}
    def fetch(self,key,target):
        snapshot={'page_date':target.isoformat(),'records':self.rows}
        return json.dumps(snapshot).encode(),{'snapshot':snapshot}
    def test_bounded_idempotent_preserves_current(self):
        with patch('backfill_etf_return_baselines.fetch_latest',side_effect=self.fetch) as f:
            r=backfill(self.db,self.receipt,'test',self.out);self.assertEqual(f.call_count,4);self.assertEqual(r['status'],'SUCCESS')
            r=backfill(self.db,self.receipt,'test',self.out);self.assertEqual(f.call_count,4)
        with sqlite3.connect(self.db) as db:
            self.assertEqual(db.execute('select max(observation_date) from snapshots').fetchone()[0],'2026-10-28')
            self.assertEqual(db.execute("select count(*) from snapshots where raw_sha256='current'").fetchone()[0],2000)
        self.assertEqual(len(list(self.out.glob('*/*.json'))),4)
    def test_failure_never_leaks_key_or_modifies_prices(self):
        with patch('backfill_etf_return_baselines.fetch_latest',side_effect=ValueError('secret-test')):
            r=backfill(self.db,self.receipt,'secret-test',self.out)
        self.assertEqual(r['status'],'PARTIAL');self.assertNotIn('secret-test',json.dumps(r))
        with sqlite3.connect(self.db) as db:self.assertEqual(db.execute('select count(*) from snapshots').fetchone()[0],2000)
    def test_future_baseline_blocked(self):
        with patch('backfill_etf_return_baselines.fetch_latest',return_value=(b'{}',{'snapshot':{'page_date':'2099-01-01','records':self.rows}})):
            r=backfill(self.db,self.receipt,'test',self.out)
        self.assertTrue(all(x['status']=='FAILED' for x in r['items']))

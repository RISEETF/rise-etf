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
    def fetch(self,key,target,**kwargs):
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

    def test_rejected_response_retained_with_safe_diagnostics(self):
        rows=[dict(r,nav=None) for r in self.rows]
        def missing_nav(key,target,**kwargs):
            doc={'page_date':target.isoformat(),'records':rows}
            return json.dumps(doc).encode(),{'snapshot':doc}
        with patch('backfill_etf_return_baselines.fetch_latest',side_effect=missing_nav):
            r=backfill(self.db,self.receipt,'test',self.out)
        self.assertTrue(all(x['reason']=='KRX_FIELD_COVERAGE_LOW' for x in r['items']))
        self.assertEqual(r['items'][0]['quality']['failed_fields'],['nav'])
        self.assertEqual(len(list(self.out.glob('*/*.json'))),4)
        with sqlite3.connect(self.db) as db:self.assertEqual(db.execute('select count(*) from snapshots').fetchone()[0],2000)

    def test_empty_calendar_date_uses_prior_valid_session_within_bound(self):
        from collect_krx_etf import fetch_latest, validate_completeness
        from unittest.mock import MagicMock
        import urllib.parse
        def response(request,timeout):
            day=urllib.parse.parse_qs(urllib.parse.urlparse(request.full_url).query)['basDd'][0]
            blank=day=='20251231'
            rows=[{'BAS_DD':day,'ISU_SRT_CD':f'{i:06d}','ISU_NM':f'ETF {i}',
                   'TDD_CLSPRC':'' if blank else '100','NAV':'' if blank else '100',
                   'ACC_TRDVOL':'' if blank else '1','LIST_SHRS':'100'} for i in range(500)]
            mock=MagicMock();mock.__enter__.return_value.read.return_value=json.dumps({'OutBlock_1':rows}).encode();return mock
        with patch('collect_krx_etf.urllib.request.urlopen',side_effect=response) as request:
            raw,result=fetch_latest('test',dt.date(2025,12,31),snapshot_validator=lambda snapshot,day:validate_completeness(Path(self.tmp.name)/'empty.sqlite',snapshot,day))
        self.assertEqual(request.call_count,2)
        self.assertEqual(result['snapshot']['page_date'],'2025-12-30')
        self.assertEqual(result['snapshot']['records'][0]['close'],100)

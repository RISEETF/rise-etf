import datetime as dt
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from collect_krx_etf import accumulate
from build_etf_investigations import build,publish

class InvestigationTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.db=Path(self.tmp.name)/'db.sqlite';self.day=dt.date(2026,10,28)
  for n in range(21):
   day=(self.day-dt.timedelta(days=20-n)).isoformat()
   rows=[{'ticker':f'{i:06d}','name':f'ETF {i}','close':110 if n==20 else 100,'nav':100,'volume':400 if n==20 else 100} for i in range(8)]
   accumulate(self.db,{'page_date':day,'records':rows},f'h{n}',day+'T10:00:00Z')
  self.receipt={'status':'SUCCESS','observation_date':self.day.isoformat(),'record_count':8,'retrieved_at':'2026-10-28T10:00:00Z','raw_sha256':'h20'}
 def test_cap_dedup_baseline_pending(self):
  d=build(self.db,self.receipt,self.day)
  self.assertEqual(d['candidate_count'],8);self.assertEqual(len(d['items']),5)
  self.assertEqual(d['deferred_count'],3)
  self.assertEqual(d['items'][0]['ticker'],'000000')
  self.assertEqual(d['items'][0]['state'],'PDF_PENDING')
  self.assertEqual(next(s['value'] for s in d['items'][0]['signals'] if s['kind']=='VOLUME_SPIKE'),4)
 def test_revisions_use_latest_not_duplicate(self):
  accumulate(self.db,{'page_date':self.day.isoformat(),'records':[{'ticker':'000000','name':'ETF 0','close':100,'nav':100,'volume':100}]},'revision','2026-10-28T11:00:00Z')
  d=build(self.db,self.receipt,self.day);self.assertEqual(d['candidate_count'],7)
  self.assertNotIn('000000',[r['ticker'] for r in d['items']])
 def test_new_listing_history_missing_not_zero(self):
  import sqlite3
  with sqlite3.connect(self.db) as db:db.execute('delete from snapshots where ticker=? and observation_date<?',('000000',self.day.isoformat()))
  d=build(self.db,self.receipt,self.day)
  row=next(r for r in d['items'] if r['ticker']=='000000') if any(r['ticker']=='000000' for r in d['items']) else None
  self.assertEqual(d['metric_coverage']['volume'],7);self.assertEqual(d['metric_coverage']['price'],7)
 def test_failure_and_regression_preserve_last_good(self):
  out=Path(self.tmp.name)/'queue/latest.json';d=build(self.db,self.receipt,self.day);publish(d,out);before=out.read_bytes()
  for day in [self.day-dt.timedelta(days=1),self.day+dt.timedelta(days=8)]:
   with self.assertRaises(ValueError):build(self.db,self.receipt,day)
  bad=dict(d,observation_date='2026-10-27')
  with self.assertRaises(ValueError):publish(bad,out)
  self.assertEqual(before,out.read_bytes());publish(d,out)
  self.assertEqual(len(list(out.parent.glob('history/*/*.json'))),1)
 def test_receipt_mismatch(self):
  for update in [{'status':'FAILED'},{'record_count':9},{'observation_date':'2026-10-27'}]:
   with self.assertRaises(ValueError):build(self.db,dict(self.receipt,**update),self.day)

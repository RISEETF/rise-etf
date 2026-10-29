import datetime as dt
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from collect_krx_etf import accumulate
from build_etf_market_metrics import build, publish, period_return, target_date

class MarketMetricsTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.db=Path(self.tmp.name)/'db.sqlite'
        self.today=dt.date(2026,10,29)
        for day,close in [('2026-09-28',100),('2026-10-21',110),('2026-10-27',120),('2026-10-28',132)]:
            accumulate(self.db,{'page_date':day,'records':[{'ticker':'0254H0','name':'RISE 테스트','close':close,'nav':130,'volume':0}]},'h',day+'T10:00:00Z')
        self.receipt={'status':'SUCCESS','observation_date':'2026-10-28','raw_sha256':'h','retrieved_at':'2026-10-29T00:00:00Z','record_count':1}
        self.inventory={'source_id':'KRX_OPEN_API_ETF_DAILY','observed_on':'2026-10-28','raw_sha256':'h','observed_count':1,'products':[{'code':'0254H0','name':'RISE 테스트','status':'OBSERVED'}]}
    def result(self):return build(self.db,self.receipt,self.inventory,self.today)
    def test_actual_endpoints_and_missing_long_history(self):
        r=self.result()['products'][0]
        self.assertEqual([r['returns'][k]['pct'] for k in ('1D','1W','1M','3M','YTD')],[10,20,32,None,None])
        self.assertEqual(r['returns']['1M']['base_date'],'2026-09-28')
        self.assertAlmostEqual(r['nav_gap_pct'],1.5385)
        self.assertEqual(r['volume'],0)
        self.assertIsNone(r['investor_flows']['individual_net_krw'])
    def test_latest_revision_and_zero_nav(self):
        accumulate(self.db,{'page_date':'2026-10-28','records':[{'ticker':'0254H0','name':'RISE 테스트','close':120,'nav':0}]},'revision','2026-10-28T11:00:00Z')
        r=self.result()['products'][0];self.assertEqual(r['returns']['1D']['pct'],0);self.assertIsNone(r['nav_gap_pct'])
    def test_missing_base_not_forward_filled(self):
        with sqlite3.connect(self.db) as db:db.execute("delete from snapshots where observation_date='2026-10-27'")
        self.assertIsNone(self.result()['products'][0]['returns']['1D']['pct'])
    def test_absent_inventory_record_is_preserved_not_priced(self):
        self.inventory['products'].append({'code':'000001','name':'RISE 과거','status':'NOT_OBSERVED'})
        self.assertEqual(self.result()['count'],1)
    def test_invalid_receipt_and_nonfinite(self):
        for key,value in [('status','FAILED'),('record_count',2),('raw_sha256','wrong')]:
            old=self.receipt[key];self.receipt[key]=value
            with self.assertRaises(ValueError):self.result()
            self.receipt[key]=old
        with sqlite3.connect(self.db) as db:db.execute("update snapshots set value=? where field='close'",(float('inf'),))
        with self.assertRaises(ValueError):self.result()
    def test_regression_preserves_output_and_deduplicates(self):
        out=Path(self.tmp.name)/'latest.json';doc=self.result();publish(doc,out);before=out.read_bytes();publish(doc,out)
        self.assertEqual(len(list(out.parent.glob('history/*/*.json'))),1)
        with self.assertRaises(ValueError):publish(dict(doc,observation_date='2026-10-27'),out)
        self.assertEqual(before,out.read_bytes())
    def test_calendar_month_and_year(self):
        self.assertEqual(target_date(dt.date(2024,3,31),'1M'),dt.date(2024,2,29))
        self.assertEqual(target_date(dt.date(2026,1,5),'YTD'),dt.date(2025,12,31))
        self.assertEqual(target_date(dt.date(2026,10,26),'1D'),dt.date(2026,10,23))

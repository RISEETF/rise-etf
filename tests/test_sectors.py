import datetime as dt
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from collect_sectors import summarize

class SectorTests(unittest.TestCase):
    def test_missing_candidate_blocks_comparison_and_zero_fill(self):
        records={'SPY':{'status':'CAPTURED','observations':[{'date':'2026-10-01','close':100,'volume':10}]}}
        result=summarize(records,[{'name':'test','primary':'XLK','peer':'VGT'}],dt.datetime(2026,11,18,tzinfo=dt.timezone.utc))
        self.assertIsNone(result['end_date'])
        self.assertTrue(all(r['return_pct'] is None for r in result['rows']))
    def test_shared_period_and_split_hold(self):
        days=['2026-10-16','2026-11-16']
        records={c:{'status':'CAPTURED','observations':[{'date':d,'close':100+i*(20 if c=='XLK' else 10),'volume':10} for i,d in enumerate(days)],'events':[]} for c in ['SPY','XLK','VGT']}
        args=([{'name':'test','primary':'XLK','peer':'VGT'}],dt.datetime(2026,11,18,tzinfo=dt.timezone.utc))
        result=summarize(records,*args)
        self.assertEqual(result['start_date'],'2026-10-16')
        self.assertAlmostEqual(result['rows'][0]['rs_vs_spy_pct'],100*(1.2/1.1-1))
        records['XLK']['events']=[{'date':'2026-11-01','kind':'SPLIT'}]
        self.assertIsNone(summarize(records,*args)['rows'][0]['return_pct'])

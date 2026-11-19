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

class PublicationTests(unittest.TestCase):
    def test_failed_capture_retains_complete_snapshot(self):
        import tempfile
        import json
        from collect_sectors import publish_result
        with tempfile.TemporaryDirectory() as temp:
            directory=Path(temp)
            good={'built_at':'2026-11-18T01:00:00Z','captured_count':23,'requested_count':23,
                  'start_date':'2026-10-16','end_date':'2026-11-16'}
            bad={**good,'captured_count':5,'start_date':None,'end_date':None}
            self.assertTrue(publish_result(good,directory))
            self.assertFalse(publish_result(bad,directory))
            self.assertEqual(json.loads((directory/'latest.json').read_text()),good)
            self.assertEqual(json.loads((directory/'status.json').read_text())['status'],'FAILED')
            self.assertTrue(publish_result(good,directory))
            self.assertEqual(json.loads((directory/'status.json').read_text())['status'],'SUCCESS')

import datetime as dt
import json
import tempfile
import unittest
from pathlib import Path
from scripts.collect_naver_etf import listing, flows, publish, database

class NaverTest(unittest.TestCase):
    def test_dates_and_units(self):
        d={'itemCode':'148020','stockEndType':'etf','stockName':'RISE 200','dealTrendInfos':[{'itemCode':'148020','bizdate':'20261119','foreignerPureBuyQuant':'+9,093','organPureBuyQuant':'-11,984','individualPureBuyQuant':None}]}
        r=flows(d,'148020',dt.date(2026,11,20))[0]
        self.assertEqual(r['foreign_net_shares'],9093)
        self.assertIsNone(r['individual_net_shares'])
        with self.assertRaises(ValueError):flows(d,'148020',dt.date(2026,11,18))
        with self.assertRaises(ValueError):flows(d,'000000',dt.date(2026,11,20))
    def test_unknown_quote_date(self):
        r=listing({'resultCode':'success','result':{'etfItemList':[{'itemcode':'0000Z0','itemname':'RISE test','nowVal':100}]}})[0]
        self.assertIsNone(r['observation_date'])
    def test_partial_preserves_and_history_rebuilds(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)
            d={'status':'SUCCESS','retrieved_at':'2026-11-20T00:00:00Z','capture_date_kst':'2026-11-20','products':[],'flows':[],'failures':[]}
            publish(p,d)
            d={**d,'status':'FAILED','failures':[{'code':'148020'}]}
            publish(p,d)
            self.assertEqual(json.loads((p/'latest.json').read_text())['status'],'SUCCESS')
            self.assertEqual(len(list((p/'history').glob('*/*.json'))),2)
            database(p,p/'db.sqlite')
            database(p,p/'db.sqlite')
            import sqlite3
            with sqlite3.connect(p/'db.sqlite') as db:self.assertEqual(db.execute('select count(*) from snapshots').fetchone()[0],2)

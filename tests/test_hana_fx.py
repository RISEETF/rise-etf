import copy
import datetime as dt
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from collect_hana_fx import parse_notice, parse_bundle, capture, SOURCE
from build_research_db import verify_capture, build
from query_asof import snapshot
from tests.test_research_rs import fixture
from build_research_rs import calculate

FIXTURES=Path(__file__).parent/'fixtures'
FINAL=(FIXTURES/'hana_final_20261014.html').read_text()
CURRENT=(FIXTURES/'hana_current_20261015.html').read_text()
NOW=dt.datetime(2026,10,15,9,tzinfo=dt.timezone.utc)


class HanaFXTests(unittest.TestCase):
    def test_actual_next_morning_notice_keeps_bank_reference_date(self):
        row=parse_notice(FINAL,'2026-10-14',NOW.isoformat(),'2026-10-15')
        self.assertEqual((row['date'],row['rate'],row['notice_sequence']),('2026-10-14',1343,1206))
        self.assertEqual(row['notice_at'],'2026-10-15T07:51:20+09:00')
        weekend=parse_notice(FINAL,'2026-10-17','2026-10-19T09:00:00+00:00','2026-10-19')
        self.assertEqual(weekend['date'],'2026-10-14')  # never label a stale quote with query date

    def test_current_quote_wrong_currency_bad_rate_or_unconfirmed_day_rejected(self):
        for body,bank in ((CURRENT,'2026-10-15'),(FINAL,'2026-10-14'),(FINAL,None),
                          (FINAL.replace('미국 USD','유럽 EUR'),'2026-10-15'),
                          (FINAL.replace('1,343.00','NaN'),'2026-10-15'),
                          (FINAL.replace('매매<br />기준율','다른율'),'2026-10-15')):
            with self.subTest(bank=bank):
                with self.assertRaises(ValueError): parse_notice(body,'2026-10-14',NOW.isoformat(),bank)
        with self.assertRaises(ValueError):parse_notice(FINAL,'2026-10-14','2026-10-14T09:00:00+00:00','2026-10-15')

    def test_capture_cache_failure_and_hash_verified_db(self):
        calls=[]
        def fetcher(day):
            calls.append(day)
            if day is None:return CURRENT
            d=dt.date.fromisoformat(day);next_day=d+dt.timedelta(days=1)
            return FINAL.replace('2026년10월14일',f'{d.year}년{d.month}월{d.day}일').replace('2026년10월15일',f'{next_day.year}년{next_day.month}월{next_day.day}일')
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            first=capture(root,fetcher,NOW,pause=0)
            self.assertEqual(first['status'],'CAPTURED',first.get('error'))
            self.assertEqual(len(calls),91)
            self.assertEqual(len(first['observations']),90)
            verify_capture(root,first)
            calls.clear()
            second=capture(root,fetcher,NOW+dt.timedelta(minutes=1),pause=0)
            self.assertEqual(second['status'],'CAPTURED',second.get('error'))
            self.assertEqual(len(calls),8)  # current anchor plus seven recent revisions
            before=(root/'series/captures'/f"{second['capture_id']}.json").read_bytes()
            failed=capture(root,lambda _:CURRENT,NOW+dt.timedelta(minutes=2),pause=0)
            self.assertEqual(failed['status'],'FAILED')
            self.assertEqual(failed['observations'],[])
            self.assertEqual((root/'series/captures'/f"{second['capture_id']}.json").read_bytes(),before)
            bad=copy.deepcopy(second);bad['observations'][0]['rate']+=1
            with self.assertRaises(ValueError):verify_capture(root,bad)
            (root/'master').mkdir();(root/'master/latest.json').write_text(json.dumps({'effective_date':'2026-10-15','products':[]}))
            (root/'series_sources.json').write_text(json.dumps({'price_instruments':[]}))
            db=root/'test.sqlite';summary=build(root,db)
            self.assertEqual(summary['hana_fx']['last_attempt_status'],'FAILED')
            self.assertEqual(summary['hana_fx']['observations'],90)
            self.assertEqual(summary['fx']['observations'],0)
            snap=snapshot(db,'2026-10-16T00:00:00Z',SOURCE)
            self.assertEqual(len(snap['fx']['notices']),90)
            self.assertEqual(snap['fx']['capture']['capture_id'],second['capture_id'])
            self.assertIsNone(snapshot(db,'2026-10-16T00:00:00Z','ECB_REFERENCE')['fx'])
            with sqlite3.connect(db) as c:
                c.execute('INSERT INTO captures VALUES (?,?,?,?,?,?,?,?,?)',('ecb','ECB_REFERENCE','https://example.test','2026-10-15T09:03:00+00:00','x','FX','CAPTURED','REFERENCE_ONLY',None))
                c.execute('INSERT INTO fx VALUES (?,?,?,?,?,?)',('ecb','2026-10-14','USD','KRW',1300,'REFERENCE'))
            with self.assertRaises(ValueError):snapshot(db,'2026-10-16T00:00:00Z')
            self.assertEqual(snapshot(db,'2026-10-16T00:00:00Z',SOURCE)['fx']['capture']['capture_id'],second['capture_id'])

    def test_explicit_rs_source_and_missing_hana_never_fallback(self):
        data,configs=fixture()
        with self.assertRaises(ValueError):calculate(data,configs,(7,),fx_source_id=SOURCE)
        data['fx']['capture']['source_id']=SOURCE
        result=calculate(data,configs,(7,),fx_source_id=SOURCE)
        self.assertEqual(result['fx_basis'],'HANA_FINAL_NOTICE_MIDPOINT')
        self.assertEqual(result['windows'][0]['status'],'CALCULATED_RESEARCH_ONLY')
        data['fx']=None
        self.assertEqual(calculate(data,configs,(7,),fx_source_id=SOURCE)['windows'][0]['rows'],[])

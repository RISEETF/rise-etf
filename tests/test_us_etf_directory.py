import datetime as dt
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from collect_us_etf_directory import parse, run

NOW=dt.datetime(2026,10,21,12,tzinfo=dt.timezone.utc)
def fixture(kind, ticker='ABC', date='1020202618:00'):
    h='Symbol|Security Name|ETF|Test Issue' if kind=='nasdaqlisted' else 'ACT Symbol|Security Name|ETF|Test Issue|Exchange'
    suffix='' if kind=='nasdaqlisted' else '|P'
    ticker=ticker if kind=='nasdaqlisted' else 'DEF'
    return (h+'\n'+ticker+'|Fund|Y|N'+suffix+'\nZZZ|Test|Y|Y'+suffix+'\nSTK|Stock|N|N'+suffix+'\nFile Creation Time: '+date+'||||\n').encode()

class DirectoryTests(unittest.TestCase):
    def test_filter_dates_and_schema(self):
        self.assertEqual(len(parse(fixture('nasdaqlisted'),'nasdaqlisted',NOW.date())['rows']),1)
        for raw in (b'<html>error</html>',fixture('nasdaqlisted',date='1022202618:00'),fixture('nasdaqlisted',date='1001202618:00'),fixture('nasdaqlisted').replace(b'Y|N',b'X|N')):
            with self.assertRaises(ValueError): parse(raw,'nasdaqlisted',NOW.date())
    def test_history_dedup_failure_preservation(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); first=run(p,fixture,NOW)
            self.assertEqual(first['status'],'SUCCESS')
            good=(p/'latest.json').read_bytes()
            self.assertTrue(run(p,fixture,NOW)['duplicate'])
            def broken(k): return fixture(k) if k=='nasdaqlisted' else b'bad'
            failed=run(p,broken,NOW)
            self.assertEqual(failed['status'],'FAILED')
            self.assertEqual(failed['last_success_at'],first['last_success_at'])
            self.assertEqual((p/'latest.json').read_bytes(),good)
            self.assertEqual(sqlite3.connect(p/'history.sqlite').execute('select count(*) from snapshots').fetchone()[0],1)
            self.assertEqual(run(p,lambda k:fixture(k,'NEW'),NOW)['status'],'SUCCESS')
            changes=json.loads((p/'latest.json').read_text())['changes']
            self.assertEqual(changes['missing_candidates'],['ABC'])
            self.assertEqual(changes['added_candidates'],['NEW'])
    def test_mixed_dates_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            s=run(d,lambda k:fixture(k,date='1020202618:00' if k=='nasdaqlisted' else '1019202618:00'),NOW)
            self.assertEqual(s['status'],'FAILED')
            self.assertFalse((Path(d)/'latest.json').exists())

import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from build_research_db import SCHEMA
from query_asof import snapshot


class AsOfTests(unittest.TestCase):
    def test_cutoff_offsets_revisions_and_coherent_events(self):
        with tempfile.TemporaryDirectory() as directory:
            db = Path(directory)/'test.sqlite'
            with sqlite3.connect(db) as c:
                c.executescript(SCHEMA)
                c.execute('INSERT INTO instruments VALUES (?,?,?,?,?,?)', ('US_LISTED:TEST','US_LISTED','TEST','Current name','USD','NOW'))
                for cid, when, close in [('a','2026-09-17T10:00:00+09:00',100),('b','2026-09-17T02:00:00+00:00',110)]:
                    c.execute('INSERT INTO captures VALUES (?,?,?,?,?,?,?,?,?)',(cid,'TEST','https://example.test',when,'x','US_PRICE','CAPTURED','QUARANTINED',None))
                    c.execute('INSERT INTO prices VALUES (?,?,?,?,?,?,?,?,?,?)',(cid,'US_LISTED:TEST','2026-09-16',close,close,close,close,1,'TEST',close))
                    c.execute('INSERT INTO corporate_actions VALUES (?,?,?,?,?,?,?,?)',(cid,'US_LISTED:TEST','event','2026-09-16','DIVIDEND',close/100,None,None))
                    c.execute('INSERT INTO fx VALUES (?,?,?,?,?,?)',(cid,'2026-09-16','USD','KRW',close*10,'REFERENCE'))
                c.execute('INSERT INTO prices VALUES (?,?,?,?,?,?,?,?,?,?)',('a','US_LISTED:TEST','2026-09-15',99,99,99,99,1,'TEST',99))
            before=db.read_bytes()
            self.assertEqual(snapshot(db,'2026-09-17T00:59:59Z')['prices'],[])
            first=snapshot(db,'2026-09-17T01:00:00Z')
            self.assertEqual(first['prices'][0]['capture']['capture_id'],'a')
            self.assertEqual(first['prices'][0]['corporate_actions'][0]['amount'],1)
            latest=snapshot(db,'2026-09-17T11:00:00+09:00')
            self.assertEqual(latest['prices'][0]['capture']['capture_id'],'b')
            self.assertEqual(len(latest['prices'][0]['prices']),1)
            self.assertEqual(latest['fx']['capture']['capture_id'],'b')
            self.assertNotIn('Current name',json.dumps(latest['prices']))
            self.assertEqual(latest['rs_status'],'BLOCKED')
            self.assertEqual(db.read_bytes(),before)
            with self.assertRaises(ValueError):snapshot(db,'2026-09-17T11:00:00')

    def test_missing_database_does_not_create_an_empty_file(self):
        with tempfile.TemporaryDirectory() as directory:
            db=Path(directory)/'missing.sqlite'
            with self.assertRaises(sqlite3.OperationalError):snapshot(db,'2026-09-17T00:00:00Z')
            self.assertFalse(db.exists())

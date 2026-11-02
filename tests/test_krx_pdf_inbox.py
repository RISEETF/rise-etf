import json
import sqlite3
import unittest
from tests import test_krx_pdf as fixture_module
from import_krx_pdf_inbox import process


class InboxTest(unittest.TestCase):
    def setUp(self):
        self.fixture = fixture_module.PDFImportTest()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.f = self.fixture
        self.inbox = self.f.root / 'inbox'
        self.inbox.mkdir()

    def bundle(self, name, corrupt=False):
        d = self.inbox / name
        d.mkdir()
        (d / 'original.csv').write_bytes(self.f.file.read_bytes())
        r = dict(self.f.receipt)
        if corrupt:
            r['sha256'] = '0' * 64
        (d / 'receipt.json').write_text(json.dumps(r))
        (d / 'queue.json').write_text(json.dumps(self.f.queue))
        return d

    def run_inbox(self):
        return process(self.inbox, self.f.out, self.f.public)

    def test_import_skip_and_private_rows(self):
        d = self.bundle('a')
        self.assertEqual(self.run_inbox()['processed'], 1)
        self.assertEqual(self.run_inbox()['processed'], 0)
        with sqlite3.connect(self.f.out / 'holdings.sqlite') as db:
            self.assertEqual(db.execute('select count(*) from pdf_imports').fetchone()[0], 1)
        self.assertTrue((d / 'original.csv').exists())
        self.assertNotIn('CNE100000F87', self.f.public.read_text())

    def test_failure_isolation_and_last_good(self):
        self.bundle('a')
        self.run_inbox()
        good = self.f.public.read_bytes()
        self.bundle('b', corrupt=True)
        result = self.run_inbox()
        self.assertEqual(result['status'], 'PARTIAL')
        self.assertEqual(result['entries']['b']['reason'], 'PDF_HASH_MISMATCH')
        self.assertEqual(good, self.f.public.read_bytes())
        self.assertEqual(result['entries']['a']['status'], 'SUCCESS')

    def test_limit_and_incomplete_bundle(self):
        for i in range(6):
            self.bundle(str(i))
        (self.inbox / 'unfinished').mkdir()
        a = self.run_inbox()
        self.assertEqual((a['processed'], a['deferred']), (5, 1))
        self.assertEqual(a['entries']['unfinished']['status'], 'WAITING_FOR_BUNDLE')
        self.assertEqual(self.run_inbox()['processed'], 1)

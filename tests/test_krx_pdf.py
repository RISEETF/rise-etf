import copy
import datetime as dt
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import import_krx_pdf as pdf


class PDFImportTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name); self.file=self.root/'export.csv'
        self.file.write_bytes((','.join(pdf.HEADER)+'\n"CNE100000F87","Synthetic","588.00",,,\n"KRD010010001","원화현금",,,"100",\n').encode('cp949'))
        self.receipt={'ticker':'0164G0','name':'Synthetic ETF','observation_date':'2026-10-27',
                      'retrieved_at':'2026-10-28T00:00:00+00:00','source_url':pdf.SOURCE,
                      'date_basis':'BROWSER_OBSERVED_QUERY','quantity_unit':'주(계약)','amount_unit':'원',
                      'row_count':2,'sha256':hashlib.sha256(self.file.read_bytes()).hexdigest()}
        self.queue={'schema':'ETF_INVESTIGATION_QUEUE_V1','observation_date':'2026-10-27','items':[
            {'ticker':'0164G0','name':'Synthetic ETF','observation_date':'2026-10-27',
             'pdf_request':{'requested_date':'2026-10-27'}}]}
        self.out=self.root/'private';self.public=self.root/'receipts.json'

    def run_import(self,r=None):
        return pdf.ingest(self.file,r or self.receipt,self.queue,self.out,self.public)

    def test_actual_schema_nulls_and_cash_not_double_counted(self):
        d=pdf.inspect(self.file,self.receipt,self.queue)
        self.assertEqual(d['encoding'],'cp949')
        self.assertIsNone(d['records'][0]['weight_pct'])
        self.assertEqual(d['summary']['state'],'PDF_ACQUIRED_PARTIAL')
        self.assertEqual(d['summary']['security_count'],1)
        self.assertEqual(d['summary']['cash_related_rows'],1)
        self.assertFalse(d['summary']['attribution_verified'])

    def test_idempotent_retrieval_and_private_rows(self):
        a=self.run_import();r={**self.receipt,'retrieved_at':'2026-10-28T01:00:00+00:00'}
        self.assertEqual(a,self.run_import(r))
        with sqlite3.connect(self.out/'holdings.sqlite') as db:
            self.assertEqual(db.execute('SELECT count(*) FROM pdf_imports').fetchone()[0],1)
        text=self.public.read_text();self.assertNotIn('CNE100000F87',text)
        self.assertNotIn('records',text)
        self.assertEqual((self.out/'raw'/self.receipt['sha256']/'original.csv').read_bytes(),self.file.read_bytes())

    def test_failed_import_keeps_last_good(self):
        self.run_import();good=self.public.read_bytes();stamp=json.loads((self.out/'status.json').read_text())['last_success_at']
        with self.assertRaisesRegex(ValueError,'HASH'):
            self.run_import({**self.receipt,'sha256':'0'*64})
        self.assertEqual(self.public.read_bytes(),good)
        s=json.loads((self.out/'status.json').read_text());self.assertEqual(s['status'],'FAILED')
        self.assertEqual(s['last_success_at'],stamp)

    def test_receipt_binding_dates_units_and_count(self):
        for changes in [{'ticker':'000000'},{'observation_date':'2026-10-26'},{'amount_unit':'천원'},
                        {'row_count':3},{'retrieved_at':'2099-01-01T00:00:00+00:00'}]:
            with self.subTest(changes=changes),self.assertRaises(ValueError):
                self.run_import({**self.receipt,**changes})

    def test_rejects_unknown_schema_duplicate_nonfinite(self):
        original=self.file.read_bytes().decode('cp949')
        for text in [original.replace('구성종목명','종목명'),original+original.splitlines()[1]+'\n',original.replace('588.00','NaN')]:
            self.file.write_bytes(text.encode('cp949'))
            with self.assertRaises(ValueError):
                self.run_import({**self.receipt,'sha256':hashlib.sha256(self.file.read_bytes()).hexdigest()})

    def test_revisions_and_prior_public_dates_preserved(self):
        self.run_import()
        self.file.write_bytes(self.file.read_bytes().replace(b'588.00',b'589.00'))
        revised={**self.receipt,'sha256':hashlib.sha256(self.file.read_bytes()).hexdigest(),'retrieved_at':'2026-10-28T02:00:00+00:00'}
        self.run_import(revised)
        with sqlite3.connect(self.out/'holdings.sqlite') as db:
            self.assertEqual(db.execute('SELECT count(*) FROM pdf_imports').fetchone()[0],2)
        self.assertEqual(json.loads(self.public.read_text())['items'][0]['sha256'],revised['sha256'])


if __name__=='__main__':unittest.main()

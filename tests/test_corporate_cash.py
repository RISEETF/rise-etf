import unittest
from scripts.collect_corporate_cash import normalize

def row(account, amount, name=''):
    return dict(sj_div='BS', account_id=account, account_nm=name, thstrm_amount=str(amount), currency='KRW', rcept_no='20260814003699')

class CashPilotTests(unittest.TestCase):
    def test_parent_financial_asset_is_not_added(self):
        data=normalize({'status':'000','list':[row('ifrs-full_CashAndCashEquivalents',100),row('dart_ShortTermFinancialInstruments',200),row('other',900,'단기금융자산'),row('ifrs-full_Assets',1000)]})
        self.assertEqual(data['cash_plus_short'],300)
        self.assertEqual(data['ratio'],.3)
    def test_missing_is_not_zero(self):
        data=normalize({'status':'000','list':[row('ifrs-full_CashAndCashEquivalents',100)]})
        self.assertIsNone(data['cash_plus_short'])
    def test_duplicate_is_unresolved(self):
        cash=row('ifrs-full_CashAndCashEquivalents',100)
        data=normalize({'status':'000','list':[cash,cash]})
        self.assertEqual(data['cash']['status'],'ambiguous')

    def test_short_term_deposits_use_standard_id(self):
        data=normalize({"status":"000","list":[row("ifrs-full_CashAndCashEquivalents",100),row("ifrs-full_ShorttermDepositsNotClassifiedAsCashEquivalents",200,"유동 금융기관예치금")]})
        self.assertEqual(data["cash_plus_short"],300)

class QuarterlyExecutionTests(unittest.TestCase):
    def test_q3_requests_and_publication(self):
        import tempfile, json, io, zipfile
        from pathlib import Path
        from unittest.mock import patch
        from scripts import collect_corporate_cash as module
        archive=io.BytesIO()
        with zipfile.ZipFile(archive,'w') as z:
            z.writestr('CORPCODE.xml','<result><list><stock_code>000001</stock_code><corp_code>001</corp_code><corp_name>Test</corp_name></list></result>')
        calls=[]
        def request(endpoint,key,**params):
            if endpoint=='corpCode.xml': return archive.getvalue()
            calls.append((params['bsns_year'],params['reprt_code']))
            return json.dumps({'status':'000','list':[row('ifrs-full_CashAndCashEquivalents',100),row('dart_ShortTermFinancialInstruments',200),row('ifrs-full_Assets',1000)]}).encode()
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            (root/'data/corporate').mkdir(parents=True)
            universe=root/'universe.json'
            universe.write_text(json.dumps([{'code':'000001','industry':'test'}]))
            with patch.object(module,'ROOT',root),patch.object(module,'UNIVERSE',universe),patch.object(module,'request',request),patch.dict(module.os.environ,{'DART_API_KEY':'test-only'}),patch('sys.argv',['collect','--period','2026-09-30']):
                module.main()
            self.assertEqual(sorted(calls),[('2025','11011'),('2026','11014')])
            self.assertEqual(json.loads((root/'data/corporate/latest.json').read_text())['period'],'2026-09-30')

class PartialPublicationTests(unittest.TestCase):
    def test_mixed_periods_and_changes(self):
        from scripts.collect_corporate_cash import merge_companies
        ok=lambda v: {'status':'ok','cash_plus_short':v}
        old={'companies':[{'code':'B','periods':{'2025-12-31':ok(10),'2026-06-30':ok(20)}}]}
        fresh=[{'code':'A','periods':{'2025-12-31':ok(30),'2026-09-30':ok(50)}},
               {'code':'B','periods':{'2026-09-30':{'status':'failed'}}},
               {'code':'C','periods':{'2026-09-30':{'status':'failed'}}}]
        result=merge_companies(fresh,old,'2026-09-30','2025-12-31')
        self.assertEqual([r['refresh_status'] for r in result],['UPDATED','RETAINED','UNAVAILABLE'])
        self.assertEqual(result[1]['display_period'],'2026-06-30')
        self.assertEqual(result[1]['change'],10)
        self.assertIsNone(result[2]['change'])

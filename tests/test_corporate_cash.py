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

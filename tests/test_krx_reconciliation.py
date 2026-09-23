import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from reconcile_krx_master import reconcile


class ReconciliationTests(unittest.TestCase):
    def master(self):
        return {'instrument_count':2,'source_product_count':3,'effective_date':'2026-09-23',
                'source_sha256':'issuer', 'products':[
                    {'detail_id':'A','code':'111111','name':'RISE A','listed_on':'2020-01-01'},
                    {'detail_id':'B','code':'222222','name':'RISE B','listed_on':'2026-09-23'}],
                'pending_products':[{'detail_id':'C','code':None,'name':'RISE C','listed_on':'2026-09-22'}]}

    def run_report(self, master=None, records=None):
        records=records if records is not None else [{'ticker':'111111','name':'RISE A'}, {'ticker':'333333','name':'RISE C'}]
        return reconcile(master or self.master(),{'page_date':'2026-09-22','records':records},
                         {'status':'SUCCESS','observation_date':'2026-09-22','record_count':len(records),
                          'retrieved_at':'2026-09-23T00:00:00+00:00','raw_sha256':'krx'})

    def test_code_match_new_listing_lag_and_candidate(self):
        report=self.run_report()
        self.assertEqual([r['status'] for r in report['rows']],
                         ['MATCHED_CODE_NAME','LISTED_AFTER_KRX_DATE','CODE_PENDING_NAME_CANDIDATE'])
        self.assertIsNone(report['rows'][2]['issuer_code'])
        self.assertEqual(report['rows'][2]['krx_code'],'333333')
        self.assertEqual(report['krx_rise_without_confirmed_issuer_code'],[{'code':'333333','name':'RISE C'}])
        self.assertEqual(report['legal_lifecycle_status'],'NOTICE_VERIFICATION_NOT_CONNECTED')

    def test_absence_never_becomes_delisting_and_name_mismatch_keeps_code(self):
        report=self.run_report(records=[{'ticker':'222222','name':'RISE Changed'}])
        self.assertEqual([r['status'] for r in report['rows']],['NOT_OBSERVED','NAME_DIFFERENCE','NO_NAME_CANDIDATE'])
        self.assertFalse(any('delisted_on' in row for row in report['rows']))

    def test_ambiguous_name_and_long_identifier_not_resolved(self):
        for records in [[{'ticker':'333333','name':'RISE C'},{'ticker':'444444','name':'RISE C'}],
                        [{'ticker':'KR1234567890','name':'RISE C'}]]:
            self.assertEqual(self.run_report(records=records)['rows'][2]['status'],'IDENTITY_REVIEW_REQUIRED')

    def test_name_candidate_cannot_steal_known_code(self):
        report=self.run_report(records=[{'ticker':'111111','name':'RISE C'}])
        self.assertEqual(report['rows'][2]['status'],'IDENTITY_REVIEW_REQUIRED')

    def test_duplicate_rejected_and_spacing_only_normalized(self):
        with self.assertRaisesRegex(ValueError,'DUPLICATE'):
            self.run_report(records=[{'ticker':'111111','name':'RISE A'}]*2)
        report=self.run_report(records=[{'ticker':'111111','name':'RISE  A'}])
        self.assertEqual(report['rows'][0]['status'],'MATCHED_CODE_NAME')


if __name__=='__main__':unittest.main()

import datetime as dt
import base64
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import collect_kind_notices as kind

FIXTURES=Path(__file__).parent/'fixtures/kind'
def fixture(name):
    raw=base64.b64decode(json.loads((FIXTURES/'body.json').read_text())['raw_base64']) if name=='body' else (FIXTURES/(name+'.html')).read_bytes()
    return kind.decode(raw)


class KindNoticeTests(unittest.TestCase):
    def test_real_list_and_empty_results_are_distinct_from_broken_pages(self):
        rows,total,pages=kind.parse_page(fixture('list'),1)
        self.assertEqual((len(rows),total,pages),(4,4,1))
        self.assertEqual(kind.parse_page(fixture('empty'),1),([],0,1))
        self.assertEqual({r['receipt_id'] for r in rows if kind.category(r['title'])}, {'20260918000210','20260828000409'})
        with self.assertRaises(ValueError):kind.parse_page('<html>maintenance</html>',1)
        with self.assertRaises(ValueError):kind.parse_page(fixture('list').replace('<em>4</em>','<em>5</em>'),1)

    def test_official_receipt_viewer_and_body_code_date(self):
        code,docs=kind.viewer_fields(fixture('viewer'),'20260918000210')
        self.assertEqual(code,'0240J0');self.assertEqual(len(docs),1)
        self.assertEqual(kind.document_fields(fixture('body'),'LISTING_NOTICE',code),('2026-09-22','NOTICE_CODE_DATE_VERIFIED'))
        with self.assertRaises(ValueError):kind.viewer_fields(fixture('viewer'),'20260918000211')
        self.assertEqual(kind.document_fields(fixture('body'),'LISTING_NOTICE','999999')[1],'BODY_IDENTITY_REVIEW')

    def test_correction_and_delisting_reasons_never_confirm_legal_state(self):
        self.assertEqual(kind.category('[정정]신규상장(TEST)'), 'REVISION_REVIEW')
        self.assertEqual(kind.category('ETF 상장폐지 사유 발생'),'DELISTING_REVIEW')
        self.assertIsNone(kind.category('ETF 신규상장 기준가격 안내'))
        self.assertIsNone(kind.category('ETF 추가 변경상장신청서'))
        body='종목코드: A123456 상장폐지 예정일: 2026.9.30'
        self.assertIsNone(kind.document_fields(body,'DELISTING_NOTICE','123456')[0])
        self.assertIsNone(kind.document_fields(body,'DELISTING_REVIEW','123456')[0])
        self.assertEqual(kind.document_fields('종목코드: A123456 상장폐지일: 2026.9.30','DELISTING_NOTICE','123456')[0],'2026-09-30')

    def test_multiple_dates_and_multiple_codes_require_review(self):
        self.assertIsNone(kind.document_fields('단축코드: A123456 상장일: 2026.9.22 상장일: 2026.9.23','LISTING_NOTICE','123456')[0])
        self.assertIsNone(kind.document_fields('단축코드: A123456 단축코드: A654321 상장일: 2026.9.22','LISTING_NOTICE','123456')[0])

    def test_failed_refresh_keeps_success_evidence(self):
        previous={'events':[{'event_id':'old'}],'window_end':'2026-09-23','last_success_at':'old'}
        with patch.object(kind,'collect',side_effect=ValueError('incomplete page')):
            result=kind.refresh(dt.date(2026,9,24),previous)
        self.assertEqual(result['status'],'FAILED');self.assertEqual(result['events'],previous['events'])
        self.assertEqual(result['last_success_at'],'old')

    def test_empty_success_preserves_older_events_without_claiming_current_presence(self):
        previous={'events':[{'event_id':'old','published_at':'2026-01-01'}]}
        with patch.object(kind,'fetch',return_value=(fixture('empty'),{'sha256':'hash','url':kind.SEARCH})):
            result=kind.collect(dt.date(2026,9,24),previous)
        self.assertEqual(len(result['events']),1)
        self.assertFalse(result['events'][0]['in_latest_search'])
        self.assertEqual(result['current_legal_status'],'NOT_AUTOMATICALLY_ASSIGNED')
        self.assertNotIn('in_latest_search',previous['events'][0])


if __name__=='__main__':unittest.main()

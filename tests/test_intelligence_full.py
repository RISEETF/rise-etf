import json
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import run_intelligence_daily as daily
from build_intelligence_full import coverage, compose, generate
from validate_intelligence_snapshot import validate
from tests import test_intelligence_daily as fixtures
NOW = fixtures.NOW


class AutomaticFullTests(unittest.TestCase):
    setUp = fixtures.DailyTests.setUp
    assert_preserved = fixtures.DailyTests.assert_preserved

    def inputs(self):
        return daily.prepare_input(self.root,NOW)

    def test_current_input_publishes_full_and_repeat_is_unchanged(self):
        result=daily.run(self.root,NOW,lambda _:None,auto_report=True)
        self.assertEqual(result['status'],'PUBLISHED',result)
        snapshot=daily.read_json(self.root/'intelligence/data/latest.json')
        self.assertEqual(snapshot['schema_version'],'1.1')
        self.assertIsNone(snapshot['regime_confidence'])
        self.assertEqual(validate(snapshot),[])
        self.assertEqual(daily.run(self.root,NOW,lambda _:None,auto_report=True)['status'],'UNCHANGED')

    def test_optional_delay_is_excluded_not_fresh(self):
        self.market['series']['DTWEXBGS'].update(observation_date='2026-10-09',data_state='STALE')
        daily.write_json(self.root/daily.INPUTS[0],self.market)
        result=daily.run(self.root,NOW,lambda _:None,auto_report=True)
        self.assertEqual(result['status'],'PUBLISHED',result)
        snapshot=daily.read_json(self.root/'intelligence/data/latest.json')
        self.assertEqual(snapshot['coverage']['state'],'PARTIAL')
        self.assertTrue(all('DTWEXBGS' not in r['series_ids'] for r in snapshot['decision_board']))
        self.assertFalse(next(r for r in snapshot['observations'] if r['series_id']=='DTWEXBGS')['fresh_for_report'])
        self.assertEqual(snapshot['regime_history_update']['transition_gate_crossed'],False)

    def test_critical_stale_remains_blocking(self):
        self.market['series']['DGS10'].update(observation_date='2026-09-01')
        daily.write_json(self.root/daily.INPUTS[0],self.market)
        result=daily.run(self.root,NOW,lambda _:None,auto_report=True)
        self.assertEqual(result['status'],'BLOCKED')
        self.assert_preserved()

    def test_optional_missing_invalid_future_or_too_old_cannot_be_waived(self):
        for update in ({'value':None},{'observation_date':'2026-10-17'},
                       {'observation_date':'2026-09-01'},{'data_state':'ERROR'}):
            with self.subTest(update=update):
                inputs=self.inputs()
                inputs['market']['series']['DTWEXBGS'].update(update)
                inputs['publication_blockers']=['STALE_OR_UNAVAILABLE:DTWEXBGS']
                self.assertTrue(coverage(inputs)[0])
        inputs=self.inputs()
        inputs['publication_blockers']=['REQUIRED_SERIES_MISSING:DTWEXBGS']
        self.assertTrue(coverage(inputs)[0])

    def test_upstream_failure_never_publishes(self):
        from unittest.mock import patch
        with patch.dict('os.environ',{'UPSTREAM_CONCLUSION':'failure'}):
            result=daily.run(self.root,NOW,lambda _:None,auto_report=True)
        self.assertEqual(result['status'],'BLOCKED')
        self.assert_preserved()

    def test_rehashed_fabricated_report_rejected(self):
        inputs=self.inputs(); package=generate(self.root,inputs)
        value=daily.read_json(package/'snapshot.json')
        value['top_change']='fabricated claim'
        daily.write_json(package/'snapshot.json',value)
        evidence=daily.read_json(package/'evidence.json')
        evidence['content_hashes']['snapshot.json']=daily.digest(package/'snapshot.json')
        daily.write_json(package/'evidence.json',evidence)
        self.assertIn('AUTOMATIC_REPORT_EVIDENCE_MISMATCH',daily.check_package(package,inputs,self.root))

    def test_null_without_version_or_explanation_rejected(self):
        s,_,_=compose(self.inputs(),daily.read_json(self.root/'intelligence/data/latest.json'))
        self.assertEqual(validate(s),[])
        for update in ({'schema_version':'1.0'},{'regime_confidence':90},
                       {'regime_confidence_reason':''},{'regime_change_status':'ACTIVE'},
                       {'production_eligible':True},{'macro_absorption_level':'HIGH'},
                       {'snapshot_type':'SUMMARY_ONLY'}):
            with self.subTest(update=update): self.assertTrue(validate(dict(s,**update)))

    def test_same_date_change_preserves_old_report(self):
        first=daily.run(self.root,NOW,lambda _:None,auto_report=True)
        self.assertEqual(first['status'],'PUBLISHED')
        old=(self.root/'intelligence/reports/2026-10-16.html').read_bytes()
        self.market['series']['SOFR']['value']+=0.01
        daily.write_json(self.root/daily.INPUTS[0],self.market)
        result=daily.run(self.root,NOW,lambda _:None,auto_report=True)
        self.assertEqual(result['status'],'PUBLISHED',result)
        vintages=list((self.root/'intelligence/data/vintages/2026-10-16').rglob('report.html'))
        self.assertTrue(any(p.read_bytes()==old for p in vintages))

    def test_manual_inbox_never_overwritten_or_bypassed(self):
        package=self.root/'intelligence/inbox/2026-10-16'
        package.mkdir(parents=True)
        (package/'report.txt').write_text('manual work in progress')
        result=daily.run(self.root,NOW,lambda _:None,auto_report=True)
        self.assertEqual(result['status'],'BLOCKED')
        self.assertEqual((package/'report.txt').read_text(),'manual work in progress')

    def test_run_timestamp_does_not_change_report(self):
        inputs=self.inputs(); prior=daily.read_json(self.root/'intelligence/data/latest.json')
        a=compose(inputs,prior)
        inputs['prepared_at_utc']='new execution'
        inputs['signals']['built_at_utc']='new execution'
        inputs['source_hashes']={'changed':'execution metadata'}
        self.assertEqual(a,compose(inputs,prior))


if __name__=='__main__': unittest.main()

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
        snapshot=daily.read_json(self.root/'intelligence/data/daily/2026-10-16.json')
        self.assertEqual(snapshot['schema_version'],'1.2')
        self.assertIsNone(snapshot['regime_confidence'])
        self.assertEqual(validate(snapshot),[])
        self.assertEqual(daily.run(self.root,NOW,lambda _:None,auto_report=True)['status'],'UNCHANGED')

    def test_optional_delay_is_excluded_not_fresh(self):
        self.market['series']['DTWEXBGS'].update(observation_date='2026-10-09',data_state='STALE')
        daily.write_json(self.root/daily.INPUTS[0],self.market)
        result=daily.run(self.root,NOW,lambda _:None,auto_report=True)
        self.assertEqual(result['status'],'PUBLISHED',result)
        snapshot=daily.read_json(self.root/'intelligence/data/daily/2026-10-16.json')
        self.assertEqual(snapshot['coverage']['state'],'DATED_INPUTS')
        self.assertTrue(all('DTWEXBGS' not in r['series_ids'] for r in snapshot['decision_board']))
        self.assertFalse(next(r for r in snapshot['observations'] if r['series_id']=='DTWEXBGS')['fresh_for_report'])
        self.assertEqual(snapshot['regime_history_update']['transition_gate_crossed'],False)

    def test_stale_value_not_matching_fetched_history_remains_blocking(self):
        self.market['series']['DGS10'].update(observation_date='2026-09-01')
        daily.write_json(self.root/daily.INPUTS[0],self.market)
        result=daily.run(self.root,NOW,lambda _:None,auto_report=True)
        self.assertEqual(result['status'],'BLOCKED')
        self.assert_preserved()

    def test_invalid_or_nonmatching_history_cannot_be_waived(self):
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

    def set_dated_series(self, key, observed):
        from datetime import date, timedelta
        row=self.market['series'][key]
        row.update(observation_date=observed,data_state='STALE')
        daily.write_json(self.root/daily.INPUTS[0],self.market)
        path=self.root/'data/gclri/history.json'
        hist=daily.read_json(path)
        hist['series'][key]=[
            {'date':(date.fromisoformat(observed)-timedelta(days=1)).isoformat(),'value':row['value']-1},
            {'date':observed,'value':row['value']}]
        daily.write_json(path,hist)

    def test_dated_rates_are_published_with_value_date_and_prior_change(self):
        self.set_dated_series('DGS10','2026-09-01')
        result=daily.run(self.root,NOW,lambda _:None,auto_report=True)
        self.assertEqual(result['status'],'PUBLISHED',result)
        d=daily.read_json(self.root/'intelligence/data/daily/2026-10-16.json')
        context=d['coverage']['dated_context'][0]
        self.assertEqual(context['series_id'],'DGS10')
        self.assertEqual(context['asof_label'],'2026-09-01 관측값 기준')
        self.assertAlmostEqual(context['prior_change']['change'],1)
        self.assertTrue(all('DGS10' not in r['series_ids'] for r in d['decision_board']))
        body=(self.root/'intelligence/reports/2026-10-16.html').read_text()
        self.assertIn('2026-09-01 관측값 기준',body)
        self.assertIn('직전 2026-08-31 관측 대비 +100.00bp',body)

    def test_all_delayed_is_a_dated_report_not_a_market_call(self):
        for key in self.market['series']: self.set_dated_series(key,'2026-09-01')
        result=daily.run(self.root,NOW,lambda _:None,auto_report=True)
        self.assertEqual(result['status'],'PUBLISHED',result)
        d=daily.read_json(self.root/'intelligence/data/daily/2026-10-16.json')
        self.assertEqual(d['decision_board'],[])
        self.assertEqual(d['top_rise_matches'],[])
        self.assertIn('오늘의 신호 판단은 보류',d['top_change'])
        self.assertEqual(len(d['coverage']['dated_context']),len(self.market['series']))

    def test_dated_context_cannot_hide_collection_failure(self):
        self.set_dated_series('DGS10','2026-09-01')
        self.market['status']='PARTIAL'
        self.market['errors']=[{'series_id':'DGS10','error':'network failed'}]
        daily.write_json(self.root/daily.INPUTS[0],self.market)
        result=daily.run(self.root,NOW,lambda _:None,auto_report=True)
        self.assertEqual(result['status'],'BLOCKED')
        self.assert_preserved()

    def test_old_collection_is_not_a_successful_latest_fetch(self):
        self.set_dated_series('DGS10','2026-09-01')
        self.market['built_at_utc']='2026-09-01T00:00:00+00:00'
        daily.write_json(self.root/daily.INPUTS[0],self.market)
        result=daily.run(self.root,NOW,lambda _:None,auto_report=True)
        self.assertEqual(result['status'],'BLOCKED')
        self.assertIn('MARKET_BUILD_NOT_CURRENT',result['blockers'])
        self.assert_preserved()

    def test_close_label_is_only_used_for_verified_close_series(self):
        d,_,_=compose(self.inputs(),daily.read_json(self.root/'intelligence/data/latest.json'))
        for r in d['observations']:
            self.assertIn('종가 기준' if r['series_id']=='VIXCLS' else '관측값 기준',r['asof_label'])

    def test_mislabeled_dated_context_and_false_same_day_signal_rejected(self):
        self.set_dated_series('DTWEXBGS','2026-09-01')
        d,_,_=compose(self.inputs(),daily.read_json(self.root/'intelligence/data/latest.json'))
        self.assertEqual(validate(d),[])
        from copy import deepcopy
        for mutation in ('date','value','use','change','decision'):
            copy=deepcopy(d); c=copy['coverage']['dated_context'][0]
            if mutation=='date': c['observation_date']='2026-10-16'
            elif mutation=='value': c['value']+=1
            elif mutation=='use': c['use']='FRESH_RESEARCH'
            elif mutation=='change': c['prior_change']['change']=999
            else: copy['decision_board'][0]['series_ids'].append('DTWEXBGS')
            with self.subTest(mutation=mutation): self.assertTrue(validate(copy))

    def test_historical_version_11_keeps_its_original_contract(self):
        self.set_dated_series('DGS10','2026-09-01')
        self.assertTrue(coverage(self.inputs(),version='1.1')[0])
        self.assertEqual(coverage(self.inputs(),version='1.2')[0],[])


if __name__=='__main__': unittest.main()

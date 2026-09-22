import copy
import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from build_research_rs import calculate


def fixture():
    configs=[{'market':'XKRX','code':'KR','name':'KR','currency':'KRW'},
             {'market':'US_LISTED','code':'SPY','name':'SPY','currency':'USD'}]
    capture={'capture_id':'test','retrieved_at':'2026-09-10T00:00:00Z','source_id':'ECB_REFERENCE'}
    def prices(key,values):
        return {'instrument_id':key,'capture':dict(capture),'corporate_actions':[],
                'prices':[{'observation_date':day,'close':value} for day,value in zip(['2026-09-01','2026-09-08'],values)]}
    data={'status':'CAPTURE_TIME_FILTER_ONLY','decision_time_utc':'2026-09-10T00:00:00Z',
          'prices':[prices('XKRX:KR',[100,110]),prices('US_LISTED:SPY',[200,210])],
          'fx':{'capture':dict(capture),'observations':[
              {'observation_date':'2026-09-01','base':'USD','quote':'KRW','rate':1000},
              {'observation_date':'2026-09-08','base':'USD','quote':'KRW','rate':1100}]}}
    return data,configs


class ResearchRSTests(unittest.TestCase):
    def test_fx_multiplication_relative_strength_and_rank_reversal(self):
        data,configs=fixture();original=copy.deepcopy(data)
        result=calculate(data,configs,(7,));rows={r['instrument_id']:r for r in result['windows'][0]['rows']}
        kr,us=rows['XKRX:KR'],rows['US_LISTED:SPY']
        self.assertAlmostEqual(us['krw_return_pct'],15.5)
        self.assertAlmostEqual(kr['krw_return_pct'],10)
        self.assertAlmostEqual(kr['krw_rs_vs_spy_pct'],100*(1.1/1.155-1))
        self.assertEqual((kr['local_rank'],kr['krw_rank']),(1,2))
        self.assertEqual(us['krw_rs_vs_spy_pct'],0)
        self.assertEqual(result['source_age_calendar_days'],2)
        self.assertEqual(data,original)

    def test_missing_fx_or_instrument_never_filled_or_silently_removed(self):
        data,configs=fixture();data['fx']['observations'].pop(0)
        self.assertEqual(calculate(data,configs,(7,))['windows'][0]['rows'],[])
        data,configs=fixture();data['prices'].pop()
        self.assertIsNone(calculate(data,configs,(7,))['latest_common_date'])

    def test_split_withholds_pool_and_equal_returns_tie(self):
        data,configs=fixture()
        data['prices'][1]['corporate_actions']=[{'kind':'SPLIT','observation_date':'2026-09-08'}]
        self.assertEqual(calculate(data,configs,(7,))['windows'][0]['status'],'KNOWN_SPLIT_IN_WINDOW')
        data,configs=fixture();data['prices'][0]['prices'][1]['close']=115.5
        rows=calculate(data,configs,(7,))['windows'][0]['rows']
        self.assertEqual([r['krw_rank'] for r in rows],[1,1])

    def test_invalid_values_duplicates_source_and_future_capture_rejected(self):
        for mode in ('nan','duplicate','future','wrong_source'):
            data,configs=fixture()
            if mode=='nan':data['prices'][0]['prices'][0]['close']=float('nan')
            if mode=='duplicate':data['prices'][0]['prices'].append(data['prices'][0]['prices'][0])
            if mode=='future':data['prices'][0]['capture']['retrieved_at']='2026-09-11T00:00:00Z'
            if mode=='wrong_source':data['fx']['capture']['source_id']='OTHER'
            with self.assertRaises(ValueError):calculate(data,configs,(7,))

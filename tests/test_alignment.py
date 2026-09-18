import copy
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from check_alignment import diagnose


def fixture():
    def item(key, days):
        return {'instrument_id':key,'capture':{'capture_id':key,'retrieved_at':'2026-09-17T00:00:00Z'},
                'prices':[{'observation_date':'2026-09-'+day} for day in days]}
    return {'status':'CAPTURE_TIME_FILTER_ONLY','rs_status':'BLOCKED','decision_time_utc':'2026-09-17T00:00:00Z',
            'prices':[item('KR',['14','15','16']),item('US',['14','16'])],
            'fx':{'capture':{'capture_id':'fx'},'observations':[
                {'observation_date':'2026-09-14','base':'USD','quote':'KRW'},
                {'observation_date':'2026-09-16','base':'EUR','quote':'KRW'}]}}


class AlignmentTests(unittest.TestCase):
    def test_overlap_missing_dates_and_fx_direction(self):
        data=fixture(); original=copy.deepcopy(data)
        result=diagnose(data,['KR','US'],'2026-09-14','2026-09-16')
        self.assertEqual(result['common_price_dates'],['2026-09-14','2026-09-16'])
        self.assertEqual(result['common_price_and_fx_dates'],['2026-09-14'])
        self.assertEqual(result['common_price_dates_without_fx'],['2026-09-16'])
        self.assertEqual(result['instruments'][1]['absent_dates_relative_to_price_union'],['2026-09-15'])
        self.assertFalse(result['simultaneity_verified'])
        self.assertEqual(data,original)

    def test_missing_instrument_is_not_silently_dropped(self):
        result=diagnose(fixture(),['KR','MISSING'],'2026-09-14','2026-09-16')
        self.assertEqual(result['missing_instruments'],['MISSING'])
        self.assertEqual(result['common_price_dates'],[])

    def test_window_and_invalid_inputs(self):
        result=diagnose(fixture(),['KR','US'],'2026-09-15','2026-09-15')
        self.assertEqual(result['common_price_dates'],[])
        for ids,start,end in [(['KR','KR'],'2026-09-14','2026-09-16'),(['KR','US'],'2026-09-16','2026-09-14')]:
            with self.assertRaises(ValueError):diagnose(fixture(),ids,start,end)
        data=fixture();data['prices'][0]['prices'].append(data['prices'][0]['prices'][0])
        with self.assertRaises(ValueError):diagnose(data,['KR','US'],'2026-09-14','2026-09-16')

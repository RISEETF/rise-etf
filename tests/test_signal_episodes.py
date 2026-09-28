import unittest
from scripts.build_signal_episodes import make_episode, update_episode

class TestSignalEpisodes(unittest.TestCase):
    def sig(self,state="WATCH",z=1.7):
        return {"signal_id":"SIG-X","name":"X","status":"CANDIDATE","signal_state":state,"direction":"UP","strongest_series":"X","strongest_zscore":z,"confidence":"HIGH","production_eligible":False,"details":[{"series_id":"X","observation_date":"2026-09-25","latest_value":10,"horizon_move":1,"zscore":z,"data_state":"CURRENT"}]}

    def test_open_watch(self):
        e=make_episode(self.sig(),"2026-09-28T00:00:00+00:00")
        self.assertEqual(e["episode_status"],"WATCH")
        self.assertTrue(e["confirmation_eligible"])

    def test_one_normal_only_weakens(self):
        e=make_episode(self.sig(),"2026-09-28T00:00:00+00:00")
        e=update_episode(e,self.sig("NORMAL",0.3),"2026-09-29T00:00:00+00:00",{"series":{}},2)
        self.assertEqual(e["episode_status"],"WEAKENING")

    def test_two_normal_close(self):
        e=make_episode(self.sig(),"2026-09-28T00:00:00+00:00")
        e=update_episode(e,self.sig("NORMAL",0.3),"2026-09-29T00:00:00+00:00",{"series":{}},2)
        e=update_episode(e,self.sig("NORMAL",0.2),"2026-09-30T00:00:00+00:00",{"series":{}},2)
        self.assertEqual(e["episode_status"],"CLOSED")
        self.assertEqual(e["falsification_status"],"NOT_FALSIFIED")

if __name__=="__main__": unittest.main()

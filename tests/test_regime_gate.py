import unittest
from scripts.build_regime_gate import channel_state

class TestRegimeGate(unittest.TestCase):
    def test_shared_rates_channel_counts_once(self):
        ch={"channel_id":"RATES","signals":["SIG-RATE-001","SIG-RATE-002"]}
        sigs={"SIG-RATE-001":{"signal_state":"ACTIVE_CANDIDATE"},"SIG-RATE-002":{"signal_state":"ACTIVE_CANDIDATE"}}
        eps={
          "SIG-RATE-001":{"episode_status":"ACTIVE","confirmation_eligible":True,"persistence_runs":2},
          "SIG-RATE-002":{"episode_status":"ACTIVE","confirmation_eligible":True,"persistence_runs":2}
        }
        out=channel_state(ch,sigs,eps)
        self.assertTrue(out["counts_as_independent_confirmation"])
        self.assertEqual(out["channel_id"],"RATES")

    def test_stale_does_not_confirm(self):
        ch={"channel_id":"FX_DOLLAR","signals":["SIG-FX-001"]}
        sigs={"SIG-FX-001":{"signal_state":"ACTIVE_CANDIDATE"}}
        eps={"SIG-FX-001":{"episode_status":"ACTIVE","confirmation_eligible":False,"persistence_runs":2}}
        out=channel_state(ch,sigs,eps)
        self.assertFalse(out["counts_as_independent_confirmation"])

if __name__=="__main__": unittest.main()

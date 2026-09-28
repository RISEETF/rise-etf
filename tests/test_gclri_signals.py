import unittest
from scripts.build_gclri_signals import zscore_current, classify

class TestGCLRISignals(unittest.TestCase):
    def test_zscore_large_last_move(self):
        rows=[{"date":str(i),"value":float(i%3)} for i in range(80)]
        rows[-1]["value"]=20.0
        z=zscore_current(rows,5,60,"diff")
        self.assertIsNotNone(z)
        self.assertGreater(abs(z),2)

    def test_classify(self):
        m={"watch_abs_z":1.5,"active_candidate_abs_z":2.0}
        self.assertEqual(classify(1.6,m),"WATCH")
        self.assertEqual(classify(-2.3,m),"ACTIVE_CANDIDATE")
        self.assertEqual(classify(0.5,m),"NORMAL")

if __name__=="__main__": unittest.main()

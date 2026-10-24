"""Unit tests - run from the python folder with:  python -m unittest"""
import unittest

import risk_monitor as rm


class RiskMonitorTests(unittest.TestCase):
    def test_parse_valid_line(self):
        self.assertEqual(rm.parse_line("FLEX:512,VIB:130\r\n"), (512, 130))

    def test_parse_rejects_bad_lines(self):
        for bad in ["", "garbage", "FLEX:abc,VIB:1", "FLEX:1,VIB:2,X:3", "VIB:1,FLEX:2",
                    "FLEX:2000,VIB:1", "FLEX:-5,VIB:1"]:
            self.assertIsNone(rm.parse_line(bad), bad)

    def test_sliding_window_average(self):
        w = rm.SlidingWindow(size=3)
        self.assertEqual(w.add(10), 10)
        self.assertEqual(w.add(20), 15)
        self.assertEqual(w.add(30), 20)
        self.assertEqual(w.add(40), 30)   # oldest value (10) dropped

    def test_weights_sum_to_one(self):
        self.assertAlmostEqual(rm.WEIGHT_STRAIN + rm.WEIGHT_VIBRATION, 1.0)

    def test_risk_zero_at_baseline(self):
        self.assertEqual(rm.compute_risk(300, 40, 300, 40), 0.0)

    def test_risk_maximum_is_one(self):
        self.assertAlmostEqual(rm.compute_risk(1023, 1023, 300, 40), 1.0)

    def test_risk_is_weighted(self):
        strain_only = rm.compute_risk(300 + rm.FLEX_RANGE, 40, 300, 40)
        vib_only = rm.compute_risk(300, 40 + rm.VIB_RANGE, 300, 40)
        self.assertAlmostEqual(strain_only, rm.WEIGHT_STRAIN)
        self.assertAlmostEqual(vib_only, rm.WEIGHT_VIBRATION)

    def test_classification_boundaries(self):
        self.assertEqual(rm.classify(0.0), "SAFE")
        self.assertEqual(rm.classify(rm.WARNING_THRESHOLD - 0.001), "SAFE")
        self.assertEqual(rm.classify(rm.WARNING_THRESHOLD), "WARNING")
        self.assertEqual(rm.classify(rm.DANGER_THRESHOLD - 0.001), "WARNING")
        self.assertEqual(rm.classify(rm.DANGER_THRESHOLD), "DANGER")
        self.assertEqual(rm.classify(1.0), "DANGER")

    def test_simulation_reaches_all_three_states(self):
        flex_w, vib_w = rm.SlidingWindow(), rm.SlidingWindow()
        readings = list(rm.simulated_readings(120))
        base_f = sum(r[0] for r in readings[:20]) / 20
        base_v = sum(r[1] for r in readings[:20]) / 20
        seen = set()
        for f, v in readings:
            fa, va = flex_w.add(f), vib_w.add(v)
            seen.add(rm.classify(rm.compute_risk(fa, va, base_f, base_v)))
        self.assertEqual(seen, {"SAFE", "WARNING", "DANGER"})


if __name__ == "__main__":
    unittest.main()

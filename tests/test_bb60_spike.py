import os
import sys
import types
import unittest


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_ROOT = os.path.join(REPO_ROOT, "src")
if SRC_ROOT not in sys.path:
    sys.path.insert(0, SRC_ROOT)


if "matplotlib" not in sys.modules:
    matplotlib = types.ModuleType("matplotlib")
    pyplot = types.ModuleType("pyplot")
    matplotlib.pyplot = pyplot
    sys.modules["matplotlib"] = matplotlib
    sys.modules["matplotlib.pyplot"] = pyplot


from equipment.spectrum_analyser.BBD60_Spike import BB60Spike


class BB60SpikeTraceParsingTests(unittest.TestCase):
    def test_parse_trace_amps_preserves_invalid_bins_as_negative_infinity(self):
        amps = BB60Spike._parse_trace_amps("-80.5,-,-75.25,NaN")

        self.assertEqual(len(amps), 4)
        self.assertEqual(amps[0], -80.5)
        self.assertEqual(amps[2], -75.25)
        self.assertEqual(amps[1], float("-inf"))
        self.assertEqual(amps[3], float("-inf"))

    def test_single_sweep_peak_from_trace_data_ignores_placeholder_tokens(self):
        spike = BB60Spike.__new__(BB60Spike)
        spike._configured_center_hz = 2_420_000_000.0
        spike._configured_span_hz = 100_000.0
        spike._send = lambda _cmd: None
        responses = iter(["1", "-95.0,-,-44.5,-"])
        spike._query = lambda _cmd: next(responses)

        peak_hz, peak_dbm = spike._single_sweep_peak_from_trace_data()

        self.assertAlmostEqual(peak_dbm, -44.5)
        self.assertAlmostEqual(peak_hz, 2_420_016_666.6666665)

    def test_parse_trace_amps_rejects_all_invalid_traces(self):
        with self.assertRaisesRegex(RuntimeError, "no numeric amplitude samples"):
            BB60Spike._parse_trace_amps("-,NaN,invalid")


if __name__ == "__main__":
    unittest.main()

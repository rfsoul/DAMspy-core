import importlib.util
import os
import sys
import types
import unittest


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODULE_PATH = os.path.join(
    REPO_ROOT,
    "src",
    "test_methods",
    "Antenna_Pattern_Measurement",
    "1_meas_azimuth.py",
)


if "matplotlib" not in sys.modules:
    matplotlib = types.ModuleType("matplotlib")
    pyplot = types.ModuleType("pyplot")
    matplotlib.pyplot = pyplot
    sys.modules["matplotlib"] = matplotlib
    sys.modules["matplotlib.pyplot"] = pyplot


spec = importlib.util.spec_from_file_location("meas_azimuth", MODULE_PATH)
meas_azimuth = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(meas_azimuth)


class MeasAzimuthHelpersTests(unittest.TestCase):
    def test_normalize_sig_gen_device_type_defaults_to_rxcc(self):
        self.assertEqual(meas_azimuth.normalize_sig_gen_device_type(None), "rxcc")

    def test_normalize_sig_gen_device_type_normalizes_case(self):
        self.assertEqual(
            meas_azimuth.normalize_sig_gen_device_type("HENDRIX_Rx"),
            "hendrix_rx",
        )

    def test_normalize_sig_gen_device_type_rejects_unknown_values(self):
        with self.assertRaisesRegex(ValueError, "device_type"):
            meas_azimuth.normalize_sig_gen_device_type("unknown")

    def test_resolve_sig_gen_sweep_config_keeps_rxcc_antennas(self):
        config = meas_azimuth.resolve_sig_gen_sweep_config(
            {
                "device_type": "rxcc",
                "channels": [0, 20],
                "power_levels": [10],
                "antennas": ["main", "secondary"],
            }
        )

        self.assertEqual(config["device_type"], "rxcc")
        self.assertEqual(config["channels"], [0, 20])
        self.assertEqual(config["power_levels"], [10])
        self.assertEqual(
            config["antennas"],
            [
                {"value": "main", "label": "main", "token": "main"},
                {"value": "secondary", "label": "secondary", "token": "secondary"},
            ],
        )

    def test_resolve_sig_gen_sweep_config_collapses_non_rxcc_antenna_dimension(self):
        config = meas_azimuth.resolve_sig_gen_sweep_config(
            {
                "device_type": "hendrix_tx",
                "tx_mode": "bodyworn",
                "channels": [0, 20],
                "power_levels": [10],
                "antennas": ["main", "secondary"],
            }
        )

        self.assertEqual(config["device_type"], "hendrix_tx")
        self.assertEqual(config["tx_mode"], "bodyworn")
        self.assertEqual(
            config["antennas"],
            [{"value": None, "label": "n/a", "token": "na"}],
        )

    def test_resolve_sig_gen_sweep_config_defaults_hendrix_tx_mode(self):
        config = meas_azimuth.resolve_sig_gen_sweep_config(
            {
                "device_type": "hendrix_tx",
                "channels": [0],
                "power_levels": [10],
            }
        )
        self.assertEqual(config["tx_mode"], "always_in_cradle")

    def test_resolve_sig_gen_sweep_config_rejects_tx_mode_for_non_hendrix_tx(self):
        with self.assertRaisesRegex(ValueError, "tx_mode is only supported"):
            meas_azimuth.resolve_sig_gen_sweep_config(
                {
                    "device_type": "rxcc",
                    "channels": [0],
                    "power_levels": [10],
                    "antennas": ["main"],
                    "tx_mode": "bodyworn",
                }
            )


if __name__ == "__main__":
    unittest.main()

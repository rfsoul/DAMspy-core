import importlib.util
import json
import os
import sys
import tempfile
import types
import unittest
from unittest.mock import patch


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
                "channels": [0, 20],
                "power_levels": [10],
                "antennas": ["main", "secondary"],
            }
        )

        self.assertEqual(config["device_type"], "hendrix_tx")
        self.assertEqual(
            config["antennas"],
            [{"value": None, "label": "n/a", "token": "na"}],
        )

    def test_capture_hendrix_tx_battery_mv_persists_metadata_and_updates_woym(self):
        class FakeSignalGenerator:
            def read_battery_info(self):
                return {"battery_mv": 3810}

        with tempfile.TemporaryDirectory() as tmpdir:
            meta_path = os.path.join(tmpdir, "metadata.json")
            combo_meta = {
                "sig_gen_1": {
                    "device_type": "hendrix_tx",
                    "channel": 11,
                    "power_level": 6,
                    "frequency_hz": 2411000000,
                }
            }
            meas_azimuth.meta_write(meta_path, combo_meta)

            with patch.object(meas_azimuth, "update_woym_generic") as mock_woym:
                battery_mv = meas_azimuth.capture_hendrix_tx_battery_mv(
                    sg=FakeSignalGenerator(),
                    device_type="hendrix_tx",
                    combo_meta=combo_meta,
                    meta_path=meta_path,
                    use_woym=True,
                    run_woym_path=os.path.join(tmpdir, "woym.json"),
                    latest_woym_path=os.path.join(tmpdir, "latest_woym.json"),
                    current_group="Antenna_Pattern_Measurement",
                    current_test_method="1_meas_azimuth",
                    sweep_index=1,
                    total_sweeps=3,
                    total_points=1,
                    axis="azimuth",
                    orientation="upright",
                    polarisation="vertical",
                    antenna="n/a",
                    power_level=6,
                    channel=11,
                    frequency_hz=2411000000,
                    csv_path=os.path.join(tmpdir, "pattern_azimuth.csv"),
                    plot_png_path=os.path.join(tmpdir, "pattern_azimuth_EEmax.png"),
                    combo_dir=tmpdir,
                )

            self.assertEqual(battery_mv, 3810)
            self.assertEqual(combo_meta["sig_gen_1"]["battery_mv"], 3810)

            with open(meta_path, "r", encoding="utf-8") as f:
                stored = json.load(f)

            self.assertEqual(stored["sig_gen_1"]["battery_mv"], 3810)
            self.assertEqual(mock_woym.call_count, 1)
            self.assertEqual(
                mock_woym.call_args.kwargs["current_sweep"]["battery_mv"],
                3810,
            )
            self.assertIn("Captured Hendrix TX battery voltage", mock_woym.call_args.kwargs["event"])

    def test_capture_hendrix_tx_battery_mv_failure_is_non_fatal(self):
        class FakeSignalGenerator:
            def read_battery_info(self):
                raise RuntimeError("device unavailable")

        with tempfile.TemporaryDirectory() as tmpdir:
            meta_path = os.path.join(tmpdir, "metadata.json")
            combo_meta = {"sig_gen_1": {"device_type": "hendrix_tx"}}
            meas_azimuth.meta_write(meta_path, combo_meta)

            with patch.object(meas_azimuth, "update_woym_generic") as mock_woym:
                battery_mv = meas_azimuth.capture_hendrix_tx_battery_mv(
                    sg=FakeSignalGenerator(),
                    device_type="hendrix_tx",
                    combo_meta=combo_meta,
                    meta_path=meta_path,
                    use_woym=True,
                    run_woym_path=os.path.join(tmpdir, "woym.json"),
                    latest_woym_path=os.path.join(tmpdir, "latest_woym.json"),
                    current_group="Antenna_Pattern_Measurement",
                    current_test_method="1_meas_azimuth",
                    sweep_index=1,
                    total_sweeps=1,
                    total_points=1,
                    axis="azimuth",
                    orientation="upright",
                    polarisation="vertical",
                    antenna="n/a",
                    power_level=6,
                    channel=11,
                    frequency_hz=2411000000,
                    csv_path=os.path.join(tmpdir, "pattern_azimuth.csv"),
                    plot_png_path=os.path.join(tmpdir, "pattern_azimuth_EEmax.png"),
                    combo_dir=tmpdir,
                )

            self.assertIsNone(battery_mv)
            self.assertNotIn("battery_mv", combo_meta["sig_gen_1"])
            self.assertEqual(mock_woym.call_count, 1)
            self.assertIn("battery read failed", mock_woym.call_args.kwargs["event"])


if __name__ == "__main__":
    unittest.main()

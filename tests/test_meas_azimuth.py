import importlib.util
import os
import sys
import tempfile
import types
import unittest
from unittest import mock


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


class _FakeSignalGenerator(object):
    def __init__(self):
        self.open_calls = 0
        self.close_calls = 0
        self.device_types = []
        self.antennas = []
        self.power_levels = []
        self.channels = []
        self.rf_on_calls = 0
        self.rf_off_calls = 0

    def open(self):
        self.open_calls += 1

    def close(self):
        self.close_calls += 1

    def set_device_type(self, device_type):
        self.device_types.append(device_type)

    def set_antenna(self, antenna):
        self.antennas.append(antenna)

    def set_power_level(self, power_level):
        self.power_levels.append(power_level)

    def set_channel(self, channel):
        self.channels.append(channel)

    def rf_on(self):
        self.rf_on_calls += 1

    def rf_off(self):
        self.rf_off_calls += 1


class _FakeSpectrumAnalyser(object):
    def __init__(self):
        self.calls = []

    def configure_narrowband(self, center_hz, span_hz, rbw_hz, vbw_hz):
        self.calls.append(
            {
                "center_hz": center_hz,
                "span_hz": span_hz,
                "rbw_hz": rbw_hz,
                "vbw_hz": vbw_hz,
            }
        )
        return {
            "center_hz": center_hz,
            "span_hz": span_hz,
            "rbw_hz": rbw_hz,
            "vbw_hz": vbw_hz,
        }


class _FakePositioner(object):
    pass


class _FakeEquipment(object):
    def __init__(self):
        self.positioner = _FakePositioner()
        self.spectrum_analyser = _FakeSpectrumAnalyser()
        self.signal_generator = _FakeSignalGenerator()


class MeasAzimuthRunTests(unittest.TestCase):
    def _make_params(self, output_dir, sig_gen_1):
        return {
            "output_dir": output_dir,
            "DUT_product": "Hendrix",
            "DUT_serial_number": "SN123",
            "foldername_comment": "",
            "yaml_comment": "",
            "axis": "azimuth",
            "sweep_mode": "boresight_only",
            "boresight_deg": 0,
            "max_angle_deg": 0,
            "step_deg": 1,
            "dwell_s": 0.01,
            "max_hold_seconds": 0.01,
            "live_plot_every_deg": 20,
            "orientations": ["upright"],
            "polarisation": ["V"],
            "sig_gen_1": sig_gen_1,
            "spec_an_1": {
                "span_hz": 10_000,
                "rbw_hz": 1_000,
                "vbw_hz": 1_000,
            },
            "rx_path": {},
        }

    def test_run_skips_rf_toggle_for_hendrix_tx_bodyworn(self):
        equip = _FakeEquipment()
        with tempfile.TemporaryDirectory() as tmpdir:
            params = self._make_params(
                tmpdir,
                {
                    "device_type": "hendrix_tx",
                    "tx_mode": "bodyworn",
                    "channels": [7, 7],
                    "power_levels": [3],
                },
            )
            with mock.patch.object(meas_azimuth, "prompt_manual_change"), \
                 mock.patch.object(meas_azimuth, "prompt_bodyworn_tx_in_cradle") as prompt_in, \
                 mock.patch.object(meas_azimuth, "prompt_bodyworn_tx_remove_from_cradle") as prompt_out, \
                 mock.patch.object(meas_azimuth, "run_single_azimuth_sweep"):
                meas_azimuth.run(params, equip)

        self.assertEqual(equip.signal_generator.open_calls, 1)
        self.assertEqual(equip.signal_generator.close_calls, 1)
        self.assertEqual(equip.signal_generator.device_types, ["hendrix_tx"])
        self.assertEqual(equip.signal_generator.power_levels, [3])
        self.assertEqual(equip.signal_generator.channels, [7])
        self.assertEqual(equip.signal_generator.rf_on_calls, 0)
        self.assertEqual(equip.signal_generator.rf_off_calls, 0)
        self.assertEqual(prompt_in.call_count, 1)
        self.assertEqual(prompt_out.call_count, 1)
        self.assertEqual(len(equip.spectrum_analyser.calls), 2)

    def test_run_preserves_rf_toggle_for_hendrix_tx_non_bodyworn(self):
        equip = _FakeEquipment()
        with tempfile.TemporaryDirectory() as tmpdir:
            params = self._make_params(
                tmpdir,
                {
                    "device_type": "hendrix_tx",
                    "tx_mode": "always_in_cradle",
                    "channels": [7],
                    "power_levels": [3],
                },
            )
            with mock.patch.object(meas_azimuth, "prompt_manual_change"), \
                 mock.patch.object(meas_azimuth, "prompt_bodyworn_tx_in_cradle") as prompt_in, \
                 mock.patch.object(meas_azimuth, "prompt_bodyworn_tx_remove_from_cradle") as prompt_out, \
                 mock.patch.object(meas_azimuth, "run_single_azimuth_sweep"):
                meas_azimuth.run(params, equip)

        self.assertEqual(equip.signal_generator.rf_on_calls, 1)
        self.assertEqual(equip.signal_generator.rf_off_calls, 1)
        self.assertEqual(prompt_in.call_count, 0)
        self.assertEqual(prompt_out.call_count, 0)


if __name__ == "__main__":
    unittest.main()

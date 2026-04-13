import importlib.util
import io
import json
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

            with mock.patch.object(meas_azimuth, "update_woym_generic") as mock_woym:
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
            self.assertIn(
                "Captured Hendrix TX battery voltage",
                mock_woym.call_args.kwargs["event"],
            )

    def test_capture_hendrix_tx_battery_mv_failure_is_non_fatal(self):
        class FakeSignalGenerator:
            def read_battery_info(self):
                raise RuntimeError("device unavailable")

        with tempfile.TemporaryDirectory() as tmpdir:
            meta_path = os.path.join(tmpdir, "metadata.json")
            combo_meta = {"sig_gen_1": {"device_type": "hendrix_tx"}}
            meas_azimuth.meta_write(meta_path, combo_meta)

            with mock.patch.object(meas_azimuth, "update_woym_generic") as mock_woym:
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


class _FakeSignalGenerator:
    def __init__(self, event_log=None, battery_mv=3810):
        self.open_calls = 0
        self.close_calls = 0
        self.device_types = []
        self.antennas = []
        self.power_levels = []
        self.channels = []
        self.rf_on_calls = 0
        self.rf_off_calls = 0
        self.read_battery_info_calls = 0
        self.event_log = event_log if event_log is not None else []
        self.battery_mv = battery_mv

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
        self.event_log.append(f"power:{power_level}")

    def set_channel(self, channel):
        self.channels.append(channel)
        self.event_log.append(f"channel:{channel}")

    def rf_on(self):
        self.rf_on_calls += 1
        self.event_log.append("rf_on")

    def rf_off(self):
        self.rf_off_calls += 1
        self.event_log.append("rf_off")

    def read_battery_info(self):
        self.read_battery_info_calls += 1
        self.event_log.append("battery")
        return {"battery_mv": self.battery_mv}


class _FakeSpectrumAnalyser:
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


class _FakePositioner:
    pass


class _FakeEquipment:
    def __init__(self, event_log=None):
        self.positioner = _FakePositioner()
        self.spectrum_analyser = _FakeSpectrumAnalyser()
        self.signal_generator = _FakeSignalGenerator(event_log=event_log)


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

    def test_run_bodyworn_captures_battery_before_remove_prompt(self):
        events = []
        equip = _FakeEquipment(event_log=events)
        sweep_battery_values = []

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
                 mock.patch.object(
                     meas_azimuth,
                     "prompt_bodyworn_tx_in_cradle",
                     side_effect=lambda **kwargs: events.append(
                         f"in:{kwargs.get('return_from_bodyworn_rf', False)}"
                     ),
                 ) as prompt_in, \
                 mock.patch.object(
                     meas_azimuth,
                     "prompt_bodyworn_tx_remove_from_cradle",
                     side_effect=lambda: events.append("out"),
                 ) as prompt_out, \
                 mock.patch.object(
                     meas_azimuth,
                     "run_single_azimuth_sweep",
                     side_effect=lambda **kwargs: sweep_battery_values.append(kwargs["battery_mv"]),
                 ), \
                 mock.patch("sys.stdout", new=io.StringIO()):
                meas_azimuth.run(params, equip)

        self.assertEqual(equip.signal_generator.open_calls, 1)
        self.assertEqual(equip.signal_generator.close_calls, 1)
        self.assertEqual(equip.signal_generator.device_types, ["hendrix_tx"])
        self.assertEqual(equip.signal_generator.power_levels, [3])
        self.assertEqual(equip.signal_generator.channels, [7])
        self.assertEqual(equip.signal_generator.rf_on_calls, 1)
        self.assertEqual(equip.signal_generator.rf_off_calls, 1)
        self.assertEqual(equip.signal_generator.read_battery_info_calls, 1)
        self.assertEqual(prompt_in.call_count, 2)
        self.assertEqual(prompt_out.call_count, 1)
        self.assertEqual(sweep_battery_values, [3810, 3810])
        self.assertEqual(len(equip.spectrum_analyser.calls), 2)
        self.assertLess(events.index("battery"), events.index("channel:7"))
        self.assertLess(events.index("battery"), events.index("out"))

    def test_run_preserves_rf_toggle_for_hendrix_tx_non_bodyworn(self):
        equip = _FakeEquipment()
        sweep_battery_values = []

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
                 mock.patch.object(
                     meas_azimuth,
                     "run_single_azimuth_sweep",
                     side_effect=lambda **kwargs: sweep_battery_values.append(kwargs["battery_mv"]),
                 ), \
                 mock.patch("sys.stdout", new=io.StringIO()):
                meas_azimuth.run(params, equip)

        self.assertEqual(equip.signal_generator.rf_on_calls, 1)
        self.assertEqual(equip.signal_generator.rf_off_calls, 1)
        self.assertEqual(equip.signal_generator.read_battery_info_calls, 1)
        self.assertEqual(prompt_in.call_count, 0)
        self.assertEqual(prompt_out.call_count, 0)
        self.assertEqual(sweep_battery_values, [3810])


if __name__ == "__main__":
    unittest.main()

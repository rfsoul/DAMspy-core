import importlib.util
import io
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
    "2_fast_meas_azimuth.py",
)


if "matplotlib" not in sys.modules:
    matplotlib = types.ModuleType("matplotlib")
    pyplot = types.ModuleType("pyplot")
    matplotlib.pyplot = pyplot
    matplotlib.use = lambda *_args, **_kwargs: None
    sys.modules["matplotlib"] = matplotlib
    sys.modules["matplotlib.pyplot"] = pyplot


spec = importlib.util.spec_from_file_location("fast_meas_azimuth", MODULE_PATH)
fast_meas_azimuth = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(fast_meas_azimuth)


class _FakeSignalGenerator:
    def __init__(self):
        self.device_types = []
        self.antennas = []
        self.power_levels = []
        self.channels = []
        self.rf_on_calls = 0
        self.rf_off_calls = 0
        self.close_calls = 0

    def open(self):
        return None

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
    def __init__(self):
        self.positioner = _FakePositioner()
        self.spectrum_analyser = _FakeSpectrumAnalyser()
        self.signal_generator = _FakeSignalGenerator()


class FastMeasAzimuthHelpersTests(unittest.TestCase):
    def test_normalize_fastmode_mode_defaults_to_default(self):
        self.assertEqual(
            fast_meas_azimuth.normalize_fastmode_mode(None),
            "default",
        )

    def test_prompt_fastmode_positioner_start_accepts_boresight(self):
        with mock.patch("builtins.input", return_value="2"), \
             mock.patch("sys.stdout", new=io.StringIO()):
            selection = fast_meas_azimuth.prompt_fastmode_positioner_start(
                max_angle_deg=170,
                pattern_direction="cw",
            )

        self.assertEqual(selection, 2)

    def test_fastmode_position_slot_to_angle_maps_slots(self):
        self.assertEqual(
            fast_meas_azimuth.fastmode_position_slot_to_angle(1, 170),
            -170.0,
        )
        self.assertEqual(
            fast_meas_azimuth.fastmode_position_slot_to_angle(2, 170),
            0.0,
        )
        self.assertEqual(
            fast_meas_azimuth.fastmode_position_slot_to_angle(3, 170),
            170.0,
        )

    def test_infer_fastmode_position_slot_classifies_angles(self):
        self.assertEqual(
            fast_meas_azimuth.infer_fastmode_position_slot(-170.0, 170),
            1,
        )
        self.assertEqual(
            fast_meas_azimuth.infer_fastmode_position_slot(0.0, 170),
            2,
        )
        self.assertEqual(
            fast_meas_azimuth.infer_fastmode_position_slot(170.0, 170),
            3,
        )

    def test_resolve_fastmode_pattern_direction_uses_current_position_slot(self):
        self.assertEqual(
            fast_meas_azimuth.resolve_fastmode_pattern_direction(3, "ccw"),
            "cw",
        )
        self.assertEqual(
            fast_meas_azimuth.resolve_fastmode_pattern_direction(1, "cw"),
            "ccw",
        )
        self.assertEqual(
            fast_meas_azimuth.resolve_fastmode_pattern_direction(2, "ccw"),
            "ccw",
        )


class FastMeasAzimuthRunTests(unittest.TestCase):
    def _make_params(self, output_dir, *, channels, fastmode_mode=None):
        params = {
            "output_dir": output_dir,
            "DUT_product": "Hendrix",
            "DUT_serial_number": "SN123",
            "foldername_comment": "",
            "yaml_comment": "",
            "axis": "azimuth",
            "sweep_mode": "full",
            "boresight_deg": 0,
            "max_angle_deg": 170,
            "step_deg": 2,
            "dwell_s": 0.01,
            "max_hold_seconds": 0.01,
            "live_plot_every_deg": 20,
            "orientations": ["ori1"],
            "polarisation": ["H"],
            "sig_gen_1": {
                "device_type": "rxcc",
                "channels": channels,
                "power_levels": [10],
                "antennas": ["main"],
            },
            "spec_an_1": {
                "span_hz": 10_000,
                "rbw_hz": 1_000,
                "vbw_hz": 1_000,
            },
            "rx_path": {},
        }
        if fastmode_mode is not None:
            params["fastmode_mode"] = fastmode_mode
        return params

    def test_run_fastmode_fast_prompts_once_and_alternates_direction(self):
        equip = _FakeEquipment()
        sweep_calls = []

        def fake_run_single_azimuth_sweep(**kwargs):
            sweep_calls.append(kwargs)
            geometry = fast_meas_azimuth.build_fast_sweep_geometry(
                kwargs["maxa"],
                kwargs["pattern_direction"],
            )
            return {"final_angle_deg": geometry["stop_angle_deg"]}

        with tempfile.TemporaryDirectory() as tmpdir:
            params = self._make_params(
                tmpdir,
                channels=[7, 8],
                fastmode_mode="fast",
            )
            with mock.patch.object(fast_meas_azimuth, "prompt_manual_change"), \
                 mock.patch.object(
                     fast_meas_azimuth,
                     "prompt_fastmode_positioner_start",
                     return_value=2,
                 ) as prompt_positioner_start, \
                 mock.patch.object(
                     fast_meas_azimuth,
                     "prompt_rf_stop_override",
                     return_value=False,
                 ), \
                 mock.patch.object(
                     fast_meas_azimuth,
                     "run_single_azimuth_sweep",
                     side_effect=fake_run_single_azimuth_sweep,
                 ), \
                 mock.patch("sys.stdout", new=io.StringIO()):
                fast_meas_azimuth.run(params, equip)

        self.assertEqual(prompt_positioner_start.call_count, 1)
        self.assertEqual(
            [fast_meas_azimuth.infer_fastmode_position_slot(call["initial_position_deg"], call["maxa"]) for call in sweep_calls],
            [2, 1],
        )
        self.assertEqual(
            [call["initial_position_deg"] for call in sweep_calls],
            [0.0, -170.0],
        )
        self.assertEqual(
            [call["pattern_direction"] for call in sweep_calls],
            ["cw", "ccw"],
        )
        self.assertTrue(
            all(call["return_to_boresight_after_sweep"] is False for call in sweep_calls)
        )

    def test_run_fastmode_fast_respects_negative_extreme_selection(self):
        equip = _FakeEquipment()
        sweep_calls = []

        def fake_run_single_azimuth_sweep(**kwargs):
            sweep_calls.append(kwargs)
            geometry = fast_meas_azimuth.build_fast_sweep_geometry(
                kwargs["maxa"],
                kwargs["pattern_direction"],
            )
            return {"final_angle_deg": geometry["stop_angle_deg"]}

        with tempfile.TemporaryDirectory() as tmpdir:
            params = self._make_params(
                tmpdir,
                channels=[7],
                fastmode_mode="fast",
            )
            with mock.patch.object(fast_meas_azimuth, "prompt_manual_change"), \
                 mock.patch.object(
                     fast_meas_azimuth,
                     "prompt_fastmode_positioner_start",
                     return_value=1,
                 ), \
                 mock.patch.object(
                     fast_meas_azimuth,
                     "prompt_rf_stop_override",
                     return_value=False,
                 ), \
                 mock.patch.object(
                     fast_meas_azimuth,
                     "run_single_azimuth_sweep",
                     side_effect=fake_run_single_azimuth_sweep,
                 ), \
                 mock.patch("sys.stdout", new=io.StringIO()):
                fast_meas_azimuth.run(params, equip)

        self.assertEqual(len(sweep_calls), 1)
        self.assertEqual(sweep_calls[0]["initial_position_deg"], -170.0)
        self.assertEqual(sweep_calls[0]["pattern_direction"], "ccw")
        self.assertFalse(sweep_calls[0]["return_to_boresight_after_sweep"])

    def test_run_default_mode_keeps_return_to_boresight_behavior(self):
        equip = _FakeEquipment()
        sweep_calls = []

        def fake_run_single_azimuth_sweep(**kwargs):
            sweep_calls.append(kwargs)
            return {"final_angle_deg": 0.0}

        with tempfile.TemporaryDirectory() as tmpdir:
            params = self._make_params(
                tmpdir,
                channels=[7, 8],
            )
            with mock.patch.object(fast_meas_azimuth, "prompt_manual_change"), \
                 mock.patch.object(
                     fast_meas_azimuth,
                     "prompt_fastmode_positioner_start",
                 ) as prompt_positioner_start, \
                 mock.patch.object(
                     fast_meas_azimuth,
                     "prompt_rf_stop_override",
                     return_value=False,
                 ), \
                 mock.patch.object(
                     fast_meas_azimuth,
                     "run_single_azimuth_sweep",
                     side_effect=fake_run_single_azimuth_sweep,
                 ), \
                 mock.patch("sys.stdout", new=io.StringIO()):
                fast_meas_azimuth.run(params, equip)

        self.assertEqual(prompt_positioner_start.call_count, 0)
        self.assertEqual(
            [call["initial_position_deg"] for call in sweep_calls],
            [0.0, 0.0],
        )
        self.assertEqual(
            [call["pattern_direction"] for call in sweep_calls],
            ["cw", "cw"],
        )
        self.assertTrue(
            all(call["return_to_boresight_after_sweep"] is True for call in sweep_calls)
        )


if __name__ == "__main__":
    unittest.main()

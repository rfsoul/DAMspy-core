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
    def test_build_active_dut_display_prefers_name_and_serial(self):
        self.assertEqual(
            meas_azimuth.build_active_dut_display("DUT1", "TxRF_4"),
            "DUT1 serial TxRF_4",
        )

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
        self.assertEqual(config["ctx_level"], "high")
        self.assertEqual(config["ctx_levels"], ["high"])

    def test_resolve_sig_gen_sweep_config_accepts_ctx_zero_for_hendrix_rx(self):
        config = meas_azimuth.resolve_sig_gen_sweep_config(
            {
                "device_type": "hendrix_rx",
                "ctx": 0,
                "channels": [0],
                "power_levels": [10],
            }
        )

        self.assertEqual(config["ctx_level"], "low")
        self.assertEqual(config["ctx_levels"], ["low"])

    def test_resolve_sig_gen_sweep_config_accepts_uppercase_ctx_list(self):
        config = meas_azimuth.resolve_sig_gen_sweep_config(
            {
                "device_type": "hendrix_tx",
                "tx_mode": "bodyworn",
                "CTX": [1, 0],
                "channels": [0],
                "power_levels": [10],
            }
        )

        self.assertIsNone(config["ctx_level"])
        self.assertEqual(config["ctx_levels"], ["high", "low"])

    def test_resolve_sig_gen_sweep_config_rejects_ctx_for_rxcc(self):
        with self.assertRaisesRegex(ValueError, "ctx is only supported"):
            meas_azimuth.resolve_sig_gen_sweep_config(
                {
                    "device_type": "rxcc",
                    "ctx": 1,
                    "channels": [0],
                    "power_levels": [10],
                    "antennas": ["main"],
                }
            )

    def test_resolve_sig_gen_sweep_config_rejects_tx_mode_for_unsupported_device(self):
        with self.assertRaisesRegex(ValueError, "tx_mode is only supported"):
            meas_azimuth.resolve_sig_gen_sweep_config(
                {
                    "device_type": "hendrix_rx",
                    "channels": [0],
                    "power_levels": [10],
                    "tx_mode": "bodyworn",
                }
            )

    def test_wireless_pro_rx_accepts_tx_mode(self):
        config = meas_azimuth.resolve_sig_gen_sweep_config(
            {
                "device_type": "wireless-pro-rx",
                "wirepro_freq": [78],
                "wirepro_power": [-4],
                "antennas": ["main"],
                "tx_mode": "bodyworn",
            }
        )

        self.assertEqual(config["tx_mode"], "bodyworn")

    def test_wireless_pro_rx_uses_wirepro_sweep_fields(self):
        config = meas_azimuth.resolve_sig_gen_sweep_config(
            {
                "device_type": "wireless-pro-rx",
                "wirepro_freq": [78],
                "wirepro_power": [-4],
                "antennas": ["main"],
            }
        )

        self.assertEqual(config["device_type"], "wireless-pro-rx")
        self.assertEqual(config["channels"], [78])
        self.assertEqual(config["power_levels"], [-4])
        self.assertEqual(config["ctx_levels"], [None])
        self.assertEqual(config["frequency_label"], "wirepro_freq")
        self.assertEqual(config["power_label"], "wirepro_power")
        self.assertEqual(meas_azimuth.wirepro_freq_to_frequency_hz(78), 2_478_000_000)

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

    def test_prompt_bodyworn_tx_update_choice_accepts_numeric_choices(self):
        with mock.patch("builtins.input", side_effect=["1"]), \
             mock.patch("sys.stdout", new=io.StringIO()):
            self.assertEqual(
                meas_azimuth.prompt_bodyworn_tx_update_choice(
                    channel=40,
                    power_level=10,
                    ctx_display="1 (high)",
                    tx_freq=2440000000,
                    reason="Manual fallback is enabled for this run.",
                ),
                "cradle",
            )

        with mock.patch("builtins.input", side_effect=["2"]), \
             mock.patch.object(meas_azimuth, "prompt_manual_change") as prompt_manual_change, \
             mock.patch("sys.stdout", new=io.StringIO()):
            self.assertEqual(
                meas_azimuth.prompt_bodyworn_tx_update_choice(
                    channel=40,
                    power_level=10,
                    ctx_display="1 (high)",
                    tx_freq=2440000000,
                    reason="Manual fallback is enabled for this run.",
                ),
                "manual",
            )

        self.assertEqual(prompt_manual_change.call_count, 1)
        self.assertIn("channel 40", prompt_manual_change.call_args.args[0])

    def test_prompt_bodyworn_tx_in_cradle_mentions_active_dut(self):
        stdout = io.StringIO()

        with mock.patch("builtins.input", return_value=""), \
             mock.patch("sys.stdout", new=stdout):
            meas_azimuth.prompt_bodyworn_tx_in_cradle(
                active_dut_display="DUT1 serial TxRF_4",
            )

        self.assertIn("Place DUT1 serial TxRF_4 in the cradle", stdout.getvalue())

    def test_prompt_bodyworn_tx_in_cradle_allows_skip_on_shutdown(self):
        with mock.patch("builtins.input", return_value="2"), \
             mock.patch("sys.stdout", new=io.StringIO()):
            should_continue = meas_azimuth.prompt_bodyworn_tx_in_cradle(
                active_dut_display="DUT1 serial TxRF_4",
                return_from_bodyworn_rf=True,
                allow_skip=True,
            )

        self.assertFalse(should_continue)

    def test_prompt_rf_stop_override_allows_skip(self):
        with mock.patch("builtins.input", return_value="2"), \
             mock.patch("sys.stdout", new=io.StringIO()):
            should_stop = meas_azimuth.prompt_rf_stop_override(
                device_label="HENDRIX_TX",
                reason="Runner shutdown",
            )

        self.assertFalse(should_stop)


class _FakeSignalGenerator:
    def __init__(
        self,
        event_log=None,
        battery_mv=3810,
        rf_on_error=None,
        rf_off_error=None,
        wirepro_freq_error=None,
    ):
        self.open_calls = 0
        self.close_calls = 0
        self.device_types = []
        self.ctx_levels = []
        self.antennas = []
        self.power_levels = []
        self.wirepro_freqs = []
        self.wirepro_powers = []
        self.channels = []
        self.rf_on_calls = 0
        self.rf_off_calls = 0
        self.read_battery_info_calls = 0
        self.event_log = event_log if event_log is not None else []
        self.battery_mv = battery_mv
        self.rf_on_error = rf_on_error
        self.rf_off_error = rf_off_error
        self.wirepro_freq_error = wirepro_freq_error

    def open(self):
        self.open_calls += 1

    def close(self):
        self.close_calls += 1

    def set_device_type(self, device_type):
        self.device_types.append(device_type)

    def set_ctx(self, ctx_level):
        self.ctx_levels.append(ctx_level)
        self.event_log.append(f"ctx:{ctx_level}")

    def set_antenna(self, antenna):
        self.antennas.append(antenna)

    def set_power_level(self, power_level):
        self.power_levels.append(power_level)
        self.event_log.append(f"power:{power_level}")

    def set_wirepro_power(self, wirepro_power):
        self.wirepro_powers.append(wirepro_power)
        self.event_log.append(f"wirepro_power:{wirepro_power}")

    def set_channel(self, channel):
        self.channels.append(channel)
        self.event_log.append(f"channel:{channel}")

    def set_wirepro_freq(self, wirepro_freq):
        self.wirepro_freqs.append(wirepro_freq)
        self.event_log.append(f"wirepro_freq:{wirepro_freq}")
        if self.wirepro_freq_error is not None:
            raise self.wirepro_freq_error

    def rf_on(self):
        self.rf_on_calls += 1
        self.event_log.append("rf_on")
        if self.rf_on_error is not None:
            raise self.rf_on_error

    def rf_off(self):
        self.rf_off_calls += 1
        self.event_log.append("rf_off")
        if self.rf_off_error is not None:
            raise self.rf_off_error

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
    def __init__(
        self,
        event_log=None,
        rf_on_error=None,
        rf_off_error=None,
        wirepro_freq_error=None,
    ):
        self.positioner = _FakePositioner()
        self.spectrum_analyser = _FakeSpectrumAnalyser()
        self.signal_generator = _FakeSignalGenerator(
            event_log=event_log,
            rf_on_error=rf_on_error,
            rf_off_error=rf_off_error,
            wirepro_freq_error=wirepro_freq_error,
        )


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

    def test_run_single_azimuth_sweep_writes_output_image_once_at_final_point(self):
        class FakePositioner:
            def __init__(self):
                self.moves = []

            def go_azimuth(self, delta_deg):
                self.moves.append(delta_deg)

        class FakeSpectrumAnalyser:
            def __init__(self):
                self.calls = []
                self.results = iter(
                    [
                        (2_400_000_000, -30.0),
                        (2_400_000_100, -29.5),
                        (2_400_000_200, -29.0),
                        (2_400_000_300, -28.5),
                        (2_400_000_400, -28.0),
                    ]
                )

            def read_peak_maxhold(self, hold_s):
                self.calls.append(hold_s)
                return next(self.results)

        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = os.path.join(tmpdir, "pattern_azimuth.csv")
            plot_png_path = os.path.join(tmpdir, "pattern_azimuth_EEmax.png")
            meta_path = os.path.join(tmpdir, "metadata.json")

            pos = FakePositioner()
            sa = FakeSpectrumAnalyser()

            with mock.patch.object(meas_azimuth, "sleep"), \
                 mock.patch.object(
                     meas_azimuth,
                     "write_partial_polar_plot",
                 ) as write_plot, \
                 mock.patch("sys.stdout", new=io.StringIO()):
                meas_azimuth.run_single_azimuth_sweep(
                    pos=pos,
                    sa=sa,
                    csv_path=csv_path,
                    plot_png_path=plot_png_path,
                    run_woym_path="",
                    latest_woym_path="",
                    use_woym=False,
                    current_group="Antenna_Pattern_Measurement",
                    current_test_method="1_meas_azimuth",
                    orientation="upright",
                    polarisation="V",
                    antenna="main",
                    ctx=None,
                    power_level=0,
                    channel=78,
                    tx_freq=2_478_000_000,
                    sweep_index=1,
                    total_sweeps=1,
                    sweep_mode="full",
                    maxa=2.0,
                    step=1.0,
                    dwell_s=0.0,
                    hold_s=0.01,
                    lowest_level_dbm=None,
                    plot_every_deg=0.5,
                    combo_dir=tmpdir,
                    meta_path=meta_path,
                    span_hz=10_000,
                    rbw_hz=1_000,
                    vbw_hz=1_000,
                    battery_mv=None,
                )

        self.assertEqual(len(sa.calls), 5)
        self.assertEqual(write_plot.call_count, 1)
        self.assertEqual(write_plot.call_args.args, (csv_path, plot_png_path))

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
        self.assertEqual(equip.signal_generator.ctx_levels, ["high"])
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
        self.assertEqual(equip.signal_generator.ctx_levels, ["high"])
        self.assertEqual(prompt_in.call_count, 0)
        self.assertEqual(prompt_out.call_count, 0)
        self.assertEqual(sweep_battery_values, [3810])

    def test_run_preserves_primary_bodyworn_failure_when_shutdown_cleanup_also_fails(self):
        equip = _FakeEquipment(rf_off_error=RuntimeError("cleanup failed"))
        primary_error = RuntimeError("sweep failed")

        with tempfile.TemporaryDirectory() as tmpdir:
            params = self._make_params(
                tmpdir,
                {
                    "device_type": "hendrix_tx",
                    "tx_mode": "bodyworn",
                    "channels": [7],
                    "power_levels": [3],
                },
            )
            with mock.patch.object(meas_azimuth, "prompt_manual_change"), \
                 mock.patch.object(meas_azimuth, "prompt_bodyworn_tx_in_cradle"), \
                 mock.patch.object(meas_azimuth, "prompt_bodyworn_tx_remove_from_cradle"), \
                 mock.patch.object(
                     meas_azimuth,
                     "run_single_azimuth_sweep",
                     side_effect=primary_error,
                 ), \
                 mock.patch("sys.stdout", new=io.StringIO()):
                with self.assertRaisesRegex(RuntimeError, "sweep failed"):
                    meas_azimuth.run(params, equip)

        self.assertEqual(equip.signal_generator.rf_on_calls, 1)
        self.assertEqual(equip.signal_generator.rf_off_calls, 1)
        self.assertEqual(equip.signal_generator.close_calls, 1)

    def test_run_bodyworn_manual_fallback_reprompts_after_cradle_update_failure(self):
        equip = _FakeEquipment()
        sweep_calls = []
        update_reasons = []

        with tempfile.TemporaryDirectory() as tmpdir:
            params = self._make_params(
                tmpdir,
                {
                    "device_type": "hendrix_tx",
                    "tx_mode": "bodyworn",
                    "manual_fallback": True,
                    "channels": [7],
                    "power_levels": [3],
                },
            )
            with mock.patch.object(
                meas_azimuth,
                "prompt_bodyworn_tx_update_choice",
                side_effect=lambda **kwargs: (
                    update_reasons.append(kwargs["reason"]),
                    "cradle" if len(update_reasons) == 1 else "manual",
                )[1],
            ), \
                 mock.patch.object(meas_azimuth, "prompt_manual_change"), \
                 mock.patch.object(meas_azimuth, "prompt_bodyworn_tx_in_cradle"), \
                 mock.patch.object(meas_azimuth, "prompt_bodyworn_tx_remove_from_cradle"), \
                 mock.patch.object(
                     equip.signal_generator,
                     "rf_on",
                     side_effect=RuntimeError("hid update failed"),
                 ) as rf_on, \
                 mock.patch.object(
                     meas_azimuth,
                     "run_single_azimuth_sweep",
                     side_effect=lambda **kwargs: sweep_calls.append(kwargs),
                 ), \
                 mock.patch("sys.stdout", new=io.StringIO()):
                meas_azimuth.run(params, equip)

        self.assertEqual(update_reasons, [
            "Manual fallback is enabled for this run.",
            "hid update failed",
        ])
        self.assertEqual(rf_on.call_count, 1)
        self.assertEqual([call["channel"] for call in sweep_calls], [7])
        self.assertEqual(equip.signal_generator.rf_off_calls, 0)

    def test_run_bodyworn_keeps_rf_on_during_midrun_cradle_updates(self):
        equip = _FakeEquipment()
        sweep_calls = []

        with tempfile.TemporaryDirectory() as tmpdir:
            params = self._make_params(
                tmpdir,
                {
                    "device_type": "hendrix_tx",
                    "tx_mode": "bodyworn",
                    "channels": [7, 8],
                    "power_levels": [3],
                },
            )
            with mock.patch.object(meas_azimuth, "prompt_manual_change"), \
                 mock.patch.object(meas_azimuth, "prompt_bodyworn_tx_in_cradle"), \
                 mock.patch.object(meas_azimuth, "prompt_bodyworn_tx_remove_from_cradle"), \
                 mock.patch.object(
                     meas_azimuth,
                     "run_single_azimuth_sweep",
                     side_effect=lambda **kwargs: sweep_calls.append(kwargs),
                 ), \
                 mock.patch("sys.stdout", new=io.StringIO()):
                meas_azimuth.run(params, equip)

        self.assertEqual([call["channel"] for call in sweep_calls], [7, 8])
        self.assertEqual(equip.signal_generator.rf_on_calls, 2)
        self.assertEqual(
            equip.signal_generator.rf_off_calls,
            1,
            "bodyworn cradle updates should not stop RF mid-run",
        )

    def test_run_passes_ctx_low_from_yaml_to_signal_generator(self):
        equip = _FakeEquipment()

        with tempfile.TemporaryDirectory() as tmpdir:
            params = self._make_params(
                tmpdir,
                {
                    "device_type": "hendrix_rx",
                    "ctx": 0,
                    "channels": [7],
                    "power_levels": [3],
                },
            )
            with mock.patch.object(meas_azimuth, "prompt_manual_change"), \
                 mock.patch.object(
                     meas_azimuth,
                     "run_single_azimuth_sweep",
                     side_effect=lambda **kwargs: None,
                 ), \
                 mock.patch("sys.stdout", new=io.StringIO()):
                meas_azimuth.run(params, equip)

        self.assertEqual(equip.signal_generator.device_types, ["hendrix_rx"])
        self.assertEqual(equip.signal_generator.ctx_levels, ["low"])

    def test_run_iterates_all_ctx_values_from_yaml_list(self):
        equip = _FakeEquipment()
        sweep_calls = []

        with tempfile.TemporaryDirectory() as tmpdir:
            params = self._make_params(
                tmpdir,
                {
                    "device_type": "hendrix_rx",
                    "CTX": [1, 0],
                    "channels": [7, 8],
                    "power_levels": [3],
                },
            )
            with mock.patch.object(meas_azimuth, "prompt_manual_change"), \
                 mock.patch.object(
                     meas_azimuth,
                     "run_single_azimuth_sweep",
                     side_effect=lambda **kwargs: sweep_calls.append(kwargs),
                 ), \
                 mock.patch("sys.stdout", new=io.StringIO()):
                meas_azimuth.run(params, equip)

        self.assertEqual(equip.signal_generator.device_types, ["hendrix_rx"])
        self.assertEqual(equip.signal_generator.ctx_levels, ["high", "low", "high", "low"])
        self.assertEqual(equip.signal_generator.channels, [7, 8])
        self.assertEqual(
            [(call["channel"], call["ctx"]) for call in sweep_calls],
            [(7, 1), (7, 0), (8, 1), (8, 0)],
        )

    def test_run_wireless_pro_rx_uses_wirepro_fields_for_rf_and_sa_center(self):
        equip = _FakeEquipment()

        with tempfile.TemporaryDirectory() as tmpdir:
            params = self._make_params(
                tmpdir,
                {
                    "device_type": "wireless-pro-rx",
                    "wirepro_freq": [78],
                    "wirepro_power": [-4],
                    "antennas": ["main"],
                },
            )
            with mock.patch.object(meas_azimuth, "prompt_manual_change"), \
                 mock.patch.object(
                     meas_azimuth,
                     "run_single_azimuth_sweep",
                     side_effect=lambda **kwargs: None,
                 ), \
                 mock.patch("sys.stdout", new=io.StringIO()):
                meas_azimuth.run(params, equip)

        self.assertEqual(equip.signal_generator.device_types, ["wireless-pro-rx"])
        self.assertEqual(equip.signal_generator.antennas, ["main"])
        self.assertEqual(equip.signal_generator.wirepro_freqs, [78])
        self.assertEqual(equip.signal_generator.wirepro_powers, [-4])
        self.assertEqual(equip.signal_generator.ctx_levels, [])
        self.assertEqual(equip.signal_generator.channels, [])
        self.assertEqual(equip.signal_generator.power_levels, [])
        self.assertEqual(equip.spectrum_analyser.calls[0]["center_hz"], 2_478_000_000)

    def test_run_wireless_pro_rx_restarts_rf_across_frequency_changes(self):
        equip = _FakeEquipment()
        sweep_calls = []

        with tempfile.TemporaryDirectory() as tmpdir:
            params = self._make_params(
                tmpdir,
                {
                    "device_type": "wireless-pro-rx",
                    "wirepro_freq": [78, 79],
                    "wirepro_power": [-4],
                    "antennas": ["main"],
                },
            )
            with mock.patch.object(meas_azimuth, "prompt_manual_change"), \
                 mock.patch.object(
                     meas_azimuth,
                     "run_single_azimuth_sweep",
                     side_effect=lambda **kwargs: sweep_calls.append(kwargs),
                 ), \
                 mock.patch("sys.stdout", new=io.StringIO()):
                meas_azimuth.run(params, equip)

        self.assertEqual(equip.signal_generator.device_types, ["wireless-pro-rx"])
        self.assertEqual(equip.signal_generator.wirepro_freqs, [78, 79])
        self.assertEqual(equip.signal_generator.wirepro_powers, [-4])
        self.assertEqual(equip.signal_generator.rf_on_calls, 2)
        self.assertEqual(equip.signal_generator.rf_off_calls, 2)
        self.assertEqual([call["channel"] for call in sweep_calls], [78, 79])

    def test_run_wireless_pro_rx_iterates_all_antennas(self):
        equip = _FakeEquipment()
        sweep_calls = []

        with tempfile.TemporaryDirectory() as tmpdir:
            params = self._make_params(
                tmpdir,
                {
                    "device_type": "wireless-pro-rx",
                    "wirepro_freq": [78],
                    "wirepro_power": [-4],
                    "antennas": ["main", "secondary"],
                },
            )
            with mock.patch.object(meas_azimuth, "prompt_manual_change"), \
                 mock.patch.object(
                     meas_azimuth,
                     "run_single_azimuth_sweep",
                     side_effect=lambda **kwargs: sweep_calls.append(kwargs),
                 ), \
                 mock.patch("sys.stdout", new=io.StringIO()):
                meas_azimuth.run(params, equip)

        self.assertEqual(equip.signal_generator.antennas, ["main", "secondary"])
        self.assertEqual(equip.signal_generator.rf_on_calls, 2)
        self.assertEqual(equip.signal_generator.rf_off_calls, 2)
        self.assertEqual([call["antenna"] for call in sweep_calls], ["main", "secondary"])
        self.assertTrue(all("wfreq-" in call["combo_dir"] for call in sweep_calls))
        self.assertTrue(all("maxa-" in call["combo_dir"] for call in sweep_calls))

    def test_run_supports_multiple_max_angle_sweeps(self):
        equip = _FakeEquipment()
        sweep_calls = []

        with tempfile.TemporaryDirectory() as tmpdir:
            params = self._make_params(
                tmpdir,
                {
                    "device_type": "wireless-pro-rx",
                    "wirepro_freq": [78],
                    "wirepro_power": [-4],
                    "antennas": ["main", "secondary"],
                },
            )
            params["max_angle_deg"] = [10, 30]

            with mock.patch.object(meas_azimuth, "prompt_manual_change"), \
                 mock.patch.object(
                     meas_azimuth,
                     "run_single_azimuth_sweep",
                     side_effect=lambda **kwargs: sweep_calls.append(kwargs),
                 ), \
                 mock.patch("sys.stdout", new=io.StringIO()):
                meas_azimuth.run(params, equip)

        self.assertEqual(
            [(call["antenna"], call["maxa"]) for call in sweep_calls],
            [("main", 10.0), ("main", 30.0), ("secondary", 10.0), ("secondary", 30.0)],
        )
        self.assertEqual(equip.signal_generator.rf_on_calls, 2)
        self.assertEqual(equip.signal_generator.rf_off_calls, 2)
        self.assertTrue(
            all("maxa-" in call["combo_dir"] for call in sweep_calls)
        )
        self.assertTrue(
            all("wfreq-" in call["combo_dir"] for call in sweep_calls)
        )

    def test_run_wireless_pro_rx_keeps_rf_on_across_max_angle_only_changes(self):
        equip = _FakeEquipment()
        sweep_calls = []

        with tempfile.TemporaryDirectory() as tmpdir:
            params = self._make_params(
                tmpdir,
                {
                    "device_type": "wireless-pro-rx",
                    "wirepro_freq": [78],
                    "wirepro_power": [-4],
                    "antennas": ["main"],
                },
            )
            params["max_angle_deg"] = [10, 30, 50]

            with mock.patch.object(meas_azimuth, "prompt_manual_change"), \
                 mock.patch.object(
                     meas_azimuth,
                     "run_single_azimuth_sweep",
                     side_effect=lambda **kwargs: sweep_calls.append(kwargs),
                 ), \
                 mock.patch("sys.stdout", new=io.StringIO()):
                meas_azimuth.run(params, equip)

        self.assertEqual([call["maxa"] for call in sweep_calls], [10.0, 30.0, 50.0])
        self.assertEqual(equip.signal_generator.rf_on_calls, 1)
        self.assertEqual(equip.signal_generator.rf_off_calls, 1)
        self.assertEqual(equip.signal_generator.antennas, ["main"])
        self.assertEqual(equip.signal_generator.wirepro_freqs, [78])
        self.assertEqual(equip.signal_generator.wirepro_powers, [-4])

    def test_run_wireless_pro_rx_manual_fallback_continues_after_freq_config_failure(self):
        equip = _FakeEquipment(
            wirepro_freq_error=TimeoutError("urlopen timed out"),
        )
        sweep_calls = []

        with tempfile.TemporaryDirectory() as tmpdir:
            params = self._make_params(
                tmpdir,
                {
                    "device_type": "wireless-pro-rx",
                    "wirepro_freq": [78],
                    "wirepro_power": [-4],
                    "wirepro_manual_fallback": True,
                    "antennas": ["main"],
                },
            )
            with mock.patch.object(
                meas_azimuth,
                "prompt_manual_change",
            ) as prompt_manual_change, \
                 mock.patch.object(
                     meas_azimuth,
                     "run_single_azimuth_sweep",
                     side_effect=lambda **kwargs: sweep_calls.append(kwargs),
                 ), \
                 mock.patch("sys.stdout", new=io.StringIO()):
                meas_azimuth.run(params, equip)

        self.assertEqual([call["channel"] for call in sweep_calls], [78])
        self.assertEqual(equip.signal_generator.wirepro_freqs, [78])
        self.assertEqual(equip.signal_generator.rf_on_calls, 0)
        self.assertEqual(equip.signal_generator.rf_off_calls, 0)
        self.assertEqual(prompt_manual_change.call_count, 3)
        self.assertEqual(prompt_manual_change.call_args_list[0].args[0], "Set the DUT orientation to 'upright'.")
        self.assertEqual(prompt_manual_change.call_args_list[1].args[0], "Set the manual test setup to polarisation 'V'.")
        fallback_message = prompt_manual_change.call_args_list[2].args[0]
        self.assertIn("Cannot communicate with Wireless Pro RX.", fallback_message)
        self.assertIn("Reason: urlopen timed out", fallback_message)
        self.assertIn("antenna is set to 'main'", fallback_message)
        self.assertIn("wirepro_freq is 78 (2478.000 MHz)", fallback_message)
        self.assertIn("wirepro_power is -4", fallback_message)
        self.assertIn("spectrum analyser", fallback_message)

    def test_run_wireless_pro_rx_manual_fallback_reprompts_when_sweep_settings_change(self):
        equip = _FakeEquipment(
            rf_on_error=TimeoutError("manual fallback"),
        )
        sweep_calls = []

        with tempfile.TemporaryDirectory() as tmpdir:
            params = self._make_params(
                tmpdir,
                {
                    "device_type": "wireless-pro-rx",
                    "wirepro_freq": [78, 79],
                    "wirepro_power": [-4],
                    "wirepro_manual_fallback": True,
                    "antennas": ["main"],
                },
            )
            with mock.patch.object(
                meas_azimuth,
                "prompt_manual_change",
            ) as prompt_manual_change, \
                 mock.patch.object(
                     meas_azimuth,
                     "run_single_azimuth_sweep",
                     side_effect=lambda **kwargs: sweep_calls.append(kwargs),
                 ), \
                 mock.patch("sys.stdout", new=io.StringIO()):
                meas_azimuth.run(params, equip)

        self.assertEqual([call["channel"] for call in sweep_calls], [78, 79])
        self.assertEqual(equip.signal_generator.rf_on_calls, 1)
        self.assertEqual(equip.signal_generator.rf_off_calls, 0)
        self.assertEqual(prompt_manual_change.call_count, 4)
        self.assertEqual(prompt_manual_change.call_args_list[0].args[0], "Set the DUT orientation to 'upright'.")
        self.assertEqual(prompt_manual_change.call_args_list[1].args[0], "Set the manual test setup to polarisation 'V'.")
        first_fallback_message = prompt_manual_change.call_args_list[2].args[0]
        second_fallback_message = prompt_manual_change.call_args_list[3].args[0]
        self.assertIn("Reason: manual fallback", first_fallback_message)
        self.assertIn("wirepro_freq is 78 (2478.000 MHz)", first_fallback_message)
        self.assertIn(
            "Automatic WirePro control is disabled for this run. Confirm the requested settings manually.",
            second_fallback_message,
        )
        self.assertIn("wirepro_freq is 79 (2479.000 MHz)", second_fallback_message)

    def test_run_only_prompts_manual_setup_once_when_orientation_and_polarisation_stay_fixed(self):
        equip = _FakeEquipment()
        sweep_calls = []

        with tempfile.TemporaryDirectory() as tmpdir:
            params = self._make_params(
                tmpdir,
                {
                    "device_type": "wireless-pro-rx",
                    "wirepro_freq": [78],
                    "wirepro_power": [-4],
                    "antennas": ["main", "secondary"],
                },
            )
            params["max_angle_deg"] = [10, 30]
            params["orientations"] = ["ori2"]
            params["polarisation"] = ["V"]

            with mock.patch.object(
                meas_azimuth,
                "prompt_manual_change",
            ) as prompt_manual_change, \
                 mock.patch.object(
                     meas_azimuth,
                     "run_single_azimuth_sweep",
                     side_effect=lambda **kwargs: sweep_calls.append(kwargs),
                 ), \
                 mock.patch("sys.stdout", new=io.StringIO()):
                meas_azimuth.run(params, equip)

        self.assertEqual(
            [call.args[0] for call in prompt_manual_change.call_args_list],
            [
                "Set the DUT orientation to 'ori2'.",
                "Set the manual test setup to polarisation 'V'.",
            ],
        )
        self.assertEqual(len(sweep_calls), 4)

    def test_run_prompts_manual_setup_again_when_orientation_or_polarisation_changes(self):
        equip = _FakeEquipment()

        with tempfile.TemporaryDirectory() as tmpdir:
            params = self._make_params(
                tmpdir,
                {
                    "device_type": "wireless-pro-rx",
                    "wirepro_freq": [78],
                    "wirepro_power": [-4],
                    "antennas": ["main"],
                },
            )
            params["orientations"] = ["ori2", "ori2", "ori3"]
            params["polarisation"] = ["V", "V", "H"]

            with mock.patch.object(
                meas_azimuth,
                "prompt_manual_change",
            ) as prompt_manual_change, \
                 mock.patch.object(
                     meas_azimuth,
                     "run_single_azimuth_sweep",
                     side_effect=lambda **kwargs: None,
                 ), \
                 mock.patch("sys.stdout", new=io.StringIO()):
                meas_azimuth.run(params, equip)

        self.assertEqual(
            [call.args[0] for call in prompt_manual_change.call_args_list],
            [
                "Set the DUT orientation to 'ori2'.",
                "Set the manual test setup to polarisation 'V'.",
                "Set the manual test setup to polarisation 'H'.",
                "Set the manual test setup to polarisation 'V'.",
                "Set the DUT orientation to 'ori3'.",
                "Set the manual test setup to polarisation 'H'.",
            ],
        )


if __name__ == "__main__":
    unittest.main()

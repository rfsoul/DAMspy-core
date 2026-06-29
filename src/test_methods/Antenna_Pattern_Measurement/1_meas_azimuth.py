# ------------------------------------------------------------
# 1_meas_azimuth.py
#
# Antenna Pattern Measurement â€“ Azimuth Sweep
# Multi-condition version:
# - manual setup group (orientation / polarisation) can be outer or inner
# - programmable RF group takes the opposite placement
# - one folder per condition combination
# - live partial polar plot generation during sweep
# - azimuth-specific WOYM content
# ------------------------------------------------------------

import csv
import json
import math
import os
import tempfile
from datetime import datetime
from time import sleep, time

import matplotlib
if hasattr(matplotlib, "use"):
    matplotlib.use("Agg")
import matplotlib.pyplot as plt

VALID_SIG_GEN_DEVICE_TYPES = {"rxcc", "hendrix_tx", "hendrix_rx", "wireless-pro-rx"}
VALID_HENDRIX_TX_MODES = {"always_in_cradle", "bodyworn"}
VALID_MANUAL_SETUP_ORDERS = {"outer", "inner"}
DEFAULT_HENDRIX_TX_MODE = "always_in_cradle"
NON_RXCC_ANTENNA_LABEL = "n/a"
NON_RXCC_ANTENNA_TOKEN = "na"


class SweepStoppedByUser(Exception):
    def __init__(self, stop_mode: str):
        super().__init__(f"Sweep stopped by user: {stop_mode}")
        self.stop_mode = stop_mode


def format_angle(value, decimals: int = 1, signed: bool = True) -> str:
    sign = "+" if signed else ""
    return f"{value:{sign}.{decimals}f} deg"


def format_symmetric_angle(value, decimals: int = 1) -> str:
    return f"+/-{value:.{decimals}f} deg"


def meta_write(path, meta: dict):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)


def rxcc_channel_to_frequency_hz(channel: int) -> int:
    channel = int(channel)
    if not (0 <= channel <= 80):
        raise ValueError(f"RXCC channel must be 0..80, got {channel}")
    return 2_400_000_000 + channel * 1_000_000


def wirepro_freq_to_frequency_hz(wirepro_freq: int) -> int:
    wirepro_freq = int(wirepro_freq)
    if not (0 <= wirepro_freq <= 99):
        raise ValueError(f"Wireless Pro RX wirepro_freq must be 0..99, got {wirepro_freq}")
    return 2_400_000_000 + wirepro_freq * 1_000_000


def ensure_list(value, name: str):
    if isinstance(value, list):
        return value
    if value is None:
        raise ValueError(f"Missing required list-like field: {name}")
    return [value]


def coerce_bool(value, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    value_str = str(value).strip().lower()
    if value_str in {"1", "true", "yes", "y", "on"}:
        return True
    if value_str in {"0", "false", "no", "n", "off"}:
        return False
    raise ValueError(f"Cannot interpret {value!r} as boolean")


def get_first_present(mapping: dict, keys):
    for key in keys:
        if key in mapping:
            return mapping[key]
    return None


def normalize_max_angle_values(value) -> list[float]:
    values = ensure_list(value, "max_angle_deg")
    if not values:
        raise ValueError("max_angle_deg must not be empty")
    return [float(item) for item in values]


def sweep_point_count_for(max_angle_deg: float, step_deg: float, boresight_only: bool) -> int:
    if boresight_only:
        return 1
    return int((2 * max_angle_deg) / step_deg) + 1


def normalize_sig_gen_device_type(value) -> str:
    if value is None:
        return "rxcc"

    device_type = str(value).strip().lower()
    if device_type not in VALID_SIG_GEN_DEVICE_TYPES:
        raise ValueError(
            "sig_gen_1.device_type must be one of "
            f"{sorted(VALID_SIG_GEN_DEVICE_TYPES)}, got {device_type!r}"
        )
    return device_type


def normalize_hendrix_tx_mode(value) -> str:
    if value is None:
        return DEFAULT_HENDRIX_TX_MODE

    tx_mode = str(value).strip().lower()
    if tx_mode not in VALID_HENDRIX_TX_MODES:
        raise ValueError(
            "sig_gen_1.tx_mode must be one of "
            f"{sorted(VALID_HENDRIX_TX_MODES)}, got {tx_mode!r}"
        )
    return tx_mode


def normalize_manual_setup_order(value) -> str:
    manual_setup_order = str(value).strip().lower()
    if manual_setup_order not in VALID_MANUAL_SETUP_ORDERS:
        raise ValueError(
            "manual_setup_order must be one of "
            f"{sorted(VALID_MANUAL_SETUP_ORDERS)}, got {value!r}"
        )
    return manual_setup_order


def normalize_hendrix_ctx_level(value) -> str:
    if value is None:
        return "high"

    if isinstance(value, bool):
        return "high" if value else "low"

    if isinstance(value, int):
        if value in (0, 1):
            return "high" if value == 1 else "low"
        raise ValueError(f"sig_gen_1.ctx must be 0 or 1, got {value!r}")

    ctx_value = str(value).strip().lower()
    if ctx_value in {"1", "high", "true", "on"}:
        return "high"
    if ctx_value in {"0", "low", "false", "off"}:
        return "low"

    raise ValueError(
        "sig_gen_1.ctx must be one of 0, 1, low, or high; "
        f"got {value!r}"
    )


def normalize_hendrix_ctx_levels(value) -> list[str]:
    values = ensure_list(value, "sig_gen_1.CTX")
    if not values:
        raise ValueError("sig_gen_1.CTX must not be empty")
    return [normalize_hendrix_ctx_level(item) for item in values]


def ctx_level_to_numeric(ctx_level):
    if ctx_level is None:
        return None
    return 1 if ctx_level == "high" else 0


def get_ctx_config_value(sg_cfg: dict):
    lower_ctx = sg_cfg.get("ctx")
    upper_ctx = sg_cfg.get("CTX")

    if lower_ctx is not None and upper_ctx is not None and lower_ctx != upper_ctx:
        raise ValueError("sig_gen_1.ctx and sig_gen_1.CTX must match when both are provided")

    if upper_ctx is not None:
        return upper_ctx
    return lower_ctx


def resolve_sig_gen_sweep_config(sg_cfg: dict) -> dict:
    device_type = normalize_sig_gen_device_type(sg_cfg.get("device_type"))
    if device_type == "wireless-pro-rx":
        channels = ensure_list(
            get_first_present(sg_cfg, ("wirepro_freq", "Wpro_freq", "wpro_freq")),
            "sig_gen_1.wirepro_freq",
        )
        power_levels = ensure_list(
            get_first_present(sg_cfg, ("wirepro_power", "wirepro_powe", "Wpro_power", "wpro_power")),
            "sig_gen_1.wirepro_power",
        )
    else:
        channels = ensure_list(sg_cfg.get("channels"), "sig_gen_1.channels")
        power_levels = ensure_list(sg_cfg.get("power_levels"), "sig_gen_1.power_levels")
    tx_mode_raw = sg_cfg.get("tx_mode")
    ctx_raw = get_ctx_config_value(sg_cfg)
    tx_mode = None
    ctx_levels = [None]

    if tx_mode_raw is not None and device_type not in {"hendrix_tx", "wireless-pro-rx"}:
        raise ValueError(
            "sig_gen_1.tx_mode is only supported for device_type "
            "'hendrix_tx' or 'wireless-pro-rx'"
        )
    if ctx_raw is not None and device_type not in {"hendrix_tx", "hendrix_rx"}:
        raise ValueError(
            "sig_gen_1.ctx is only supported for device_type 'hendrix_tx' or 'hendrix_rx'"
        )
    if device_type == "hendrix_tx":
        tx_mode = normalize_hendrix_tx_mode(tx_mode_raw)
    elif device_type == "wireless-pro-rx" and tx_mode_raw is not None:
        tx_mode = normalize_hendrix_tx_mode(tx_mode_raw)

    if device_type in {"rxcc", "wireless-pro-rx"}:
        antenna_values = ensure_list(
            sg_cfg.get("antennas", sg_cfg.get("antenna")),
            "sig_gen_1.antennas",
        )
        antennas = [
            {
                "value": antenna,
                "label": str(antenna),
                "token": sanitize_token(antenna),
            }
            for antenna in antenna_values
        ]
    else:
        antennas = [
            {
                "value": None,
                "label": NON_RXCC_ANTENNA_LABEL,
                "token": NON_RXCC_ANTENNA_TOKEN,
            }
        ]
        ctx_levels = normalize_hendrix_ctx_levels(ctx_raw if ctx_raw is not None else [1])

    return {
        "device_type": device_type,
        "channels": channels,
        "power_levels": power_levels,
        "antennas": antennas,
        "tx_mode": tx_mode,
        "ctx_level": ctx_levels[0] if len(ctx_levels) == 1 else None,
        "ctx_levels": ctx_levels,
        "frequency_label": "wirepro_freq" if device_type == "wireless-pro-rx" else "channel",
        "power_label": "wirepro_power" if device_type == "wireless-pro-rx" else "power_level",
    }


def build_manual_variants(orientations, polarisations) -> list[dict]:
    variants = []
    for index, orientation in enumerate(orientations):
        polarisation_order = polarisations if index % 2 == 0 else list(reversed(polarisations))
        for polarisation in polarisation_order:
            variants.append(
                {
                    "orientation": orientation,
                    "polarisation": polarisation,
                }
            )
    return variants


def manual_variant_change_cost(current_variant: dict, next_variant: dict) -> int:
    cost = 0
    if current_variant["orientation"] != next_variant["orientation"]:
        cost += 1
    if current_variant["polarisation"] != next_variant["polarisation"]:
        cost += 1
    return cost


def order_manual_variants_for_current_state(
    manual_variants: list[dict],
    current_orientation,
    current_polarisation,
) -> list[dict]:
    if not manual_variants:
        return []

    indexed_variants = list(enumerate(manual_variants))
    ordered = []

    start_index = None
    if current_orientation is not None and current_polarisation is not None:
        for index, variant in indexed_variants:
            if (
                variant["orientation"] == current_orientation
                and variant["polarisation"] == current_polarisation
            ):
                start_index = index
                break

    if start_index is None:
        start_index = 0

    current_variant = manual_variants[start_index]
    ordered.append(current_variant)
    remaining = [
        (index, variant)
        for index, variant in indexed_variants
        if index != start_index
    ]

    while remaining:
        next_index, next_variant = min(
            remaining,
            key=lambda item: (
                manual_variant_change_cost(current_variant, item[1]),
                item[0],
            ),
        )
        ordered.append(next_variant)
        current_variant = next_variant
        remaining = [
            (index, variant)
            for index, variant in remaining
            if index != next_index
        ]

    return ordered


def build_rf_variants(antenna_variants, power_levels, channels, ctx_levels) -> list[dict]:
    variants = []
    for antenna_cfg in antenna_variants:
        for power_level in power_levels:
            for channel in channels:
                for ctx_level in ctx_levels:
                    variants.append(
                        {
                            "antenna_cfg": antenna_cfg,
                            "power_level": power_level,
                            "channel": channel,
                            "ctx_level": ctx_level,
                        }
                    )
    return variants


def sanitize_token(value) -> str:
    return str(value).replace(" ", "_").replace("/", "_").replace("\\", "_")


def build_active_dut_display(active_dut_name, dut_serial_number) -> str:
    name = str(active_dut_name).strip() if active_dut_name is not None else ""
    serial = str(dut_serial_number).strip() if dut_serial_number is not None else ""
    if name and serial:
        return f"{name} serial {serial}"
    if serial:
        return f"serial {serial}"
    if name:
        return name
    return ""


def prompt_manual_change(message: str, active_dut_display: str = "") -> None:
    print("\n" + "=" * 90)
    print("[MANUAL ACTION REQUIRED]")
    if active_dut_display:
        print(f"Active DUT: {active_dut_display}")
    print(message)
    print("Press Enter when complete...")
    print("=" * 90)
    input()


def prompt_wirepro_manual_setup(
    *,
    antenna_label,
    wirepro_freq,
    wirepro_power,
    tx_freq,
    reason,
    active_dut_display="",
) -> None:
    prompt_manual_change(
        "Cannot communicate with Wireless Pro RX.\n"
        f"Reason: {reason}\n"
        f"Ensure antenna is set to '{antenna_label}', "
        f"wirepro_freq is {wirepro_freq} ({tx_freq/1e6:.3f} MHz), "
        f"wirepro_power is {wirepro_power}, and the RF signal is visible "
        "on the spectrum analyser before continuing.",
        active_dut_display=active_dut_display,
    )


def prompt_bodyworn_tx_update_choice(
    *,
    channel,
    power_level,
    ctx_display,
    tx_freq,
    reason,
    active_dut_display="",
) -> str:
    print("\n" + "=" * 90)
    print("[HENDRIX TX BODYWORN MODE]")
    if active_dut_display:
        print(f"Active DUT: {active_dut_display}")
    print(f"Reason: {reason}")
    print(
        "Choose update method:\n"
        "  [1] Place the TX in the cradle so DAMspy can update channel/power/ctx\n"
        f"  [2] Confirm the TX is already operating on channel {channel} "
        f"({tx_freq/1e6:.3f} MHz), power {power_level}, ctx {ctx_display}"
    )
    print("=" * 90)

    while True:
        try:
            choice = input("Select 1 or 2: ").strip().lower()
        except EOFError:
            print("[INFO] No operator input detected; defaulting to cradle update.")
            return "cradle"
        if choice in {"1", "cradle", "update"}:
            return "cradle"
        if choice in {"2", "manual"}:
            prompt_manual_change(
                f"Confirm the TX is already operating on channel {channel} "
                f"({tx_freq/1e6:.3f} MHz), power {power_level}, ctx {ctx_display}, "
                "and the RF signal is visible on the spectrum analyser.",
                active_dut_display=active_dut_display,
            )
            return "manual"
        print("Invalid choice. Enter 1 for cradle update or 2 for manual confirmation.")


def prompt_bodyworn_tx_in_cradle(
    *,
    active_dut_display: str = "",
    return_from_bodyworn_rf: bool = False,
    allow_skip: bool = False,
) -> bool:
    print("\n" + "=" * 90)
    print("[HENDRIX TX BODYWORN MODE]")
    device_label = active_dut_display or "the Hendrix TX"
    if return_from_bodyworn_rf:
        print(
            f"Return {device_label} to the cradle so RF can be stopped and "
            "channel/power can be updated."
        )
        print(f"Press Enter when {device_label} is back in the cradle...")
    else:
        print(f"Place {device_label} in the cradle so channel/power can be updated.")
        print(f"Press Enter when {device_label} is in the cradle...")
    if allow_skip:
        print("Type 2 to skip this cradle step and leave RF/state unchanged.")
    print("=" * 90)
    try:
        choice = input().strip().lower()
    except EOFError:
        print("[INFO] No operator input detected; continuing with cradle step.")
        return True
    if allow_skip and choice in {"2", "skip", "s"}:
        return False
    return True


def prompt_bodyworn_tx_remove_from_cradle(*, active_dut_display: str = "") -> None:
    print("\n" + "=" * 90)
    print("[HENDRIX TX BODYWORN MODE]")
    device_label = active_dut_display or "the Hendrix TX"
    print(f"HID update successful. You can now remove {device_label} from the cradle.")
    print(f"Press Enter after {device_label} has been removed...")
    print("=" * 90)
    input()


def prompt_rf_stop_override(*, device_label: str, reason: str) -> bool:
    print("\n" + "=" * 90)
    print("[RF STOP REQUEST]")
    print(f"Target: {device_label}")
    print(f"Reason: {reason}")
    print("1 = stop RF")
    print("2 = skip stop and leave RF/state unchanged")
    print("=" * 90)

    while True:
        try:
            choice = input("Select 1 or 2: ").strip().lower()
        except EOFError:
            print("[INFO] No operator input detected; defaulting to RF stop.")
            return True
        if choice in {"1", "stop"}:
            return True
        if choice in {"2", "skip"}:
            return False
        print("Invalid choice. Enter 1 to stop RF or 2 to skip.")


def prompt_interrupt_menu(current_az: float) -> str:
    print("\n" + "=" * 90)
    print("[INTERRUPT]")
    print(f"Current azimuth reference: {format_angle(current_az)}")
    print("1 = return to test")
    print("2 = return to boresight and stop test")
    print("3 = stop test in current location")
    print("=" * 90)

    while True:
        choice = input("Select 1, 2, or 3: ").strip()
        if choice == "1":
            return "resume"
        if choice == "2":
            return "stop_boresight"
        if choice == "3":
            return "stop_hold"
        print("Invalid choice. Enter 1, 2, or 3.")


def iso_now() -> str:
    return datetime.now().isoformat(timespec="seconds")


# ------------------------------------------------------------
# Generic WOYM file mechanics
# ------------------------------------------------------------

def write_json_atomic(path: str, payload: dict):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    last_error = None

    for attempt in range(8):
        tmp_fd, tmp_path = tempfile.mkstemp(
            prefix=os.path.basename(path) + ".",
            suffix=".tmp",
            dir=os.path.dirname(path),
            text=True,
        )
        try:
            with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, path)
            return
        except PermissionError as e:
            last_error = e
            try:
                os.remove(tmp_path)
            except OSError:
                pass

            if attempt == 7:
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(payload, f, indent=2)
                    f.flush()
                    os.fsync(f.fileno())
                return

            sleep(0.05 * (attempt + 1))
        except Exception:
            try:
                os.remove(tmp_path)
            except OSError:
                pass
            raise

    if last_error is not None:
        raise last_error


def load_woym(path: str) -> dict:
    if not path or not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def append_recent_event(woym: dict, event: str, limit: int = 20):
    events = woym.setdefault("recent_events", [])
    events.append({
        "timestamp": iso_now(),
        "event": event,
    })
    if len(events) > limit:
        del events[:-limit]


def write_woym_snapshot(woym: dict, run_woym_path: str, latest_woym_path: str):
    woym["updated_at"] = iso_now()
    if run_woym_path:
        write_json_atomic(run_woym_path, woym)
    if latest_woym_path:
        write_json_atomic(latest_woym_path, woym)


def update_woym_generic(
    *,
    run_woym_path: str,
    latest_woym_path: str,
    event: str = "",
    status: str = None,
    current_test_group: str = None,
    current_test_method: str = None,
    current_state: dict = None,
    current_sweep: dict = None,
    last_measurement: dict = None,
    artifacts: dict = None,
    error: dict = None,
):
    if not run_woym_path:
        return

    woym = load_woym(run_woym_path)

    if current_test_group is not None:
        woym["current_test_group"] = current_test_group
    if current_test_method is not None:
        woym["current_test_method"] = current_test_method
    if status is not None:
        woym["status"] = status
    if current_state is not None:
        woym["current_state"] = current_state
    if current_sweep is not None:
        woym["current_sweep"] = current_sweep
    if last_measurement is not None:
        woym["last_measurement"] = last_measurement

    if artifacts is not None:
        current_artifacts = woym.setdefault("artifacts", {})
        current_artifacts.update(artifacts)

    if error is not None:
        woym["error"] = error

    if event:
        append_recent_event(woym, event)

    write_woym_snapshot(woym, run_woym_path, latest_woym_path)


def set_woym_error(run_woym_path: str, latest_woym_path: str, message: str, where: str):
    update_woym_generic(
        run_woym_path=run_woym_path,
        latest_woym_path=latest_woym_path,
        status="error",
        current_state={
            "state": "error",
            "message": message,
            "target": {},
        },
        error={
            "status": "active",
            "message": message,
            "where": where,
            "timestamp": iso_now(),
        },
        event=message,
    )


# ------------------------------------------------------------
# Azimuth-specific WOYM payload
# ------------------------------------------------------------

def build_current_sweep_dict(
    *,
    sweep_index: int,
    total_sweeps: int,
    point_index: int,
    total_points: int,
    axis: str,
    orientation,
    polarisation,
    antenna,
    ctx=None,
    power_level,
    channel,
    frequency_hz,
    battery_mv=None,
):
    sweep = {
        "sweep_index": sweep_index,
        "total_sweeps": total_sweeps,
        "point_index": point_index,
        "total_points": total_points,
        "axis": axis,
        "orientation": orientation,
        "polarisation": polarisation,
        "antenna": antenna,
        "power_level": power_level,
        "channel": channel,
        "frequency_hz": frequency_hz,
    }
    if ctx is not None:
        sweep["ctx"] = ctx
    if battery_mv is not None:
        sweep["battery_mv"] = battery_mv
    return sweep


def capture_hendrix_tx_battery_mv(
    *,
    sg,
    device_type: str,
    combo_meta: dict,
    meta_path: str,
    use_woym: bool,
    run_woym_path: str,
    latest_woym_path: str,
    current_group: str,
    current_test_method: str,
    sweep_index: int,
    total_sweeps: int,
    total_points: int,
    axis: str,
    orientation,
    polarisation,
    antenna,
    ctx=None,
    power_level,
    channel,
    frequency_hz,
    csv_path: str,
    plot_png_path: str,
    combo_dir: str,
):
    if device_type != "hendrix_tx":
        return None

    try:
        battery_info = sg.read_battery_info()
        battery_mv = battery_info.get("battery_mv")
        if battery_mv is None:
            raise RuntimeError("battery_mv missing from Hendrix TX battery response")

        combo_meta.setdefault("sig_gen_1", {})["battery_mv"] = battery_mv
        meta_write(meta_path, combo_meta)
        print(f"[META] Updated Hendrix TX battery_mv -> {battery_mv} mV")

        if use_woym:
            update_woym_generic(
                run_woym_path=run_woym_path,
                latest_woym_path=latest_woym_path,
                current_test_group=current_group,
                current_test_method=current_test_method,
                current_sweep=build_current_sweep_dict(
                    sweep_index=sweep_index,
                    total_sweeps=total_sweeps,
                    point_index=0,
                    total_points=total_points,
                    axis=axis,
                    orientation=orientation,
                    polarisation=polarisation,
                    antenna=antenna,
                    ctx=ctx,
                    power_level=power_level,
                    channel=channel,
                    frequency_hz=frequency_hz,
                    battery_mv=battery_mv,
                ),
                artifacts={
                    "latest_csv_path": csv_path,
                    "latest_plot_path": plot_png_path,
                    "latest_metadata_path": meta_path,
                    "combo_dir": combo_dir,
                },
                event=f"Captured Hendrix TX battery voltage: {battery_mv} mV",
            )

        return battery_mv
    except Exception as e:
        print(f"[WARN] Hendrix TX battery read failed: {e}")
        if use_woym:
            update_woym_generic(
                run_woym_path=run_woym_path,
                latest_woym_path=latest_woym_path,
                current_test_group=current_group,
                current_test_method=current_test_method,
                current_sweep=build_current_sweep_dict(
                    sweep_index=sweep_index,
                    total_sweeps=total_sweeps,
                    point_index=0,
                    total_points=total_points,
                    axis=axis,
                    orientation=orientation,
                    polarisation=polarisation,
                    antenna=antenna,
                    ctx=ctx,
                    power_level=power_level,
                    channel=channel,
                    frequency_hz=frequency_hz,
                ),
                artifacts={
                    "latest_csv_path": csv_path,
                    "latest_plot_path": plot_png_path,
                    "latest_metadata_path": meta_path,
                    "combo_dir": combo_dir,
                },
                event=f"Hendrix TX battery read failed: {e}",
            )
        return None


def build_spectrum_analyser_block(
    *,
    requested_center_hz,
    requested_span_hz,
    requested_rbw_hz,
    requested_vbw_hz,
    last_peak_freq_hz,
    last_peak_dbm,
):
    status = "unknown"

    if last_peak_freq_hz is None or last_peak_dbm is None:
        status = "unknown"
    elif last_peak_dbm < -100:
        status = "suspect_noise_floor"
    elif abs(last_peak_freq_hz - requested_center_hz) > max(requested_span_hz / 2.0, 1.0):
        status = "off_tune"
    else:
        status = "ok"

    return {
        "requested_center_hz": requested_center_hz,
        "requested_span_hz": requested_span_hz,
        "requested_rbw_hz": requested_rbw_hz,
        "requested_vbw_hz": requested_vbw_hz,
        "last_peak_freq_hz": last_peak_freq_hz,
        "last_peak_dbm": last_peak_dbm,
        "status": status,
    }


def update_woym_azimuth(
    *,
    run_woym_path: str,
    latest_woym_path: str,
    spectrum_analyser: dict = None,
):
    if not run_woym_path:
        return

    woym = load_woym(run_woym_path)

    if spectrum_analyser is not None:
        woym["spectrum_analyser"] = spectrum_analyser

    write_woym_snapshot(woym, run_woym_path, latest_woym_path)


# ------------------------------------------------------------
# Plot helper
# ------------------------------------------------------------

def write_partial_polar_plot(csv_path: str, out_png: str) -> None:
    """
    Regenerate the azimuth polar plot from the current CSV contents.
    Safe to call repeatedly as the sweep progresses.
    """
    if not os.path.exists(csv_path):
        print(f"[PLOT][WARN] Missing CSV: {csv_path}")
        return

    az_deg = []
    levels_dbm = []

    with open(csv_path, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        required = {"azimuth_deg", "rx_peak_dbm"}
        if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
            print(f"[PLOT][WARN] CSV missing required columns: {reader.fieldnames}")
            return

        for row in reader:
            try:
                az_deg.append(float(row["azimuth_deg"]))
                levels_dbm.append(float(row["rx_peak_dbm"]))
            except (ValueError, TypeError):
                continue

    if not az_deg:
        print("[PLOT][WARN] No valid data points found yet")
        return

    max_dbm = max(levels_dbm)
    e_over_emax = [10 ** ((v - max_dbm) / 20.0) for v in levels_dbm]
    az_rad = [math.radians(a) for a in az_deg]

    plt.figure(figsize=(8, 8))
    ax = plt.subplot(111, projection="polar")

    ax.plot(az_rad, e_over_emax, linewidth=2)

    ax.set_theta_zero_location("N")
    ax.set_theta_direction(-1)
    ax.set_rlim(0, 1.05)

    db_rings = [-3, -6, -10, -20]
    ring_theta = [math.radians(a) for a in range(0, 361)]

    for db in db_rings:
        r = 10 ** (db / 20.0)
        ax.plot(
            ring_theta,
            [r] * len(ring_theta),
            linestyle="--",
            linewidth=0.8,
            color="gray",
        )
        ax.text(
            math.radians(45),
            r,
            f"{db} dB",
            fontsize=9,
            color="gray",
        )

    ax.text(
        math.radians(90),
        1.02,
        f"Emax = {max_dbm:.2f} dBm",
        ha="center",
        va="bottom",
        fontsize=11,
        fontweight="bold",
    )

    point_count = len(az_deg)
    ax.set_title(
        "Antenna Pattern â€“ Azimuth Cut\n"
        f"Linear E / Emax (points so far: {point_count})",
        pad=20,
    )

    ax.grid(True)
    plt.tight_layout()
    plt.savefig(out_png)
    plt.close()

    print(f"[PLOT] Updated partial polar plot -> {out_png}")


def run_single_azimuth_sweep(
    *,
    pos,
    sa,
    csv_path: str,
    plot_png_path: str,
    run_woym_path: str,
    latest_woym_path: str,
    use_woym: bool,
    current_group: str,
    current_test_method: str,
    orientation,
    polarisation,
    antenna,
    ctx=None,
    power_level,
    channel,
    tx_freq,
    sweep_index: int,
    total_sweeps: int,
    sweep_mode: str,
    maxa: float,
    step: float,
    dwell_s: float,
    hold_s: float,
    lowest_level_dbm,
    plot_every_deg: float,
    combo_dir: str,
    meta_path: str,
    span_hz: float,
    rbw_hz: float,
    vbw_hz: float,
    battery_mv=None,
):
    current_az = 0.0
    boresight_only = str(sweep_mode).strip().lower() == "boresight_only"

    if boresight_only:
        steps = 0
        total_points = 1
        maxa = 0.0
    else:
        steps = int((2 * maxa) / step)
        total_points = steps + 1

    def move_rel(delta_deg):
        nonlocal current_az
        if boresight_only:
            return
        if abs(delta_deg) < 1e-9:
            print("[POS] Zero move requested - skipping")
            return

        target = current_az + delta_deg

        if use_woym:
            update_woym_generic(
                run_woym_path=run_woym_path,
                latest_woym_path=latest_woym_path,
                current_test_group=current_group,
                current_test_method=current_test_method,
                status="running",
                current_state={
                    "state": "moving",
                    "message": (
                        f"Moving azimuth from {format_angle(current_az)} "
                        f"to {format_angle(target)}"
                    ),
                    "target": {
                        "azimuth_deg": target,
                    },
                },
                current_sweep=build_current_sweep_dict(
                    sweep_index=sweep_index,
                    total_sweeps=total_sweeps,
                    point_index=0,
                    total_points=total_points,
                    axis="azimuth",
                    orientation=orientation,
                    polarisation=polarisation,
                    antenna=antenna,
                    ctx=ctx,
                    power_level=power_level,
                    channel=channel,
                    frequency_hz=tx_freq,
                    battery_mv=battery_mv,
                ),
                artifacts={
                    "latest_csv_path": csv_path,
                    "latest_plot_path": plot_png_path,
                    "latest_metadata_path": meta_path,
                    "combo_dir": combo_dir,
                },
                event=f"Moving azimuth to {format_angle(target)}",
            )

        print(
            f"[POS] Commanding AZ move: "
            f"{format_angle(current_az)} -> {format_angle(target)} "
            f"(delta {format_angle(delta_deg)})"
        )
        pos.go_azimuth(delta_deg)
        current_az = target
        print(f"[POS] Move complete, settling for {dwell_s:.2f} s")
        sleep(dwell_s)

    def return_to_boresight():
        nonlocal current_az

        if boresight_only or abs(current_az) < 1e-9:
            current_az = 0.0
            print("[POS] Already at boresight reference")
            return

        print("\n[POS] Returning to boresight before stopping")
        move_rel(-current_az)
        current_az = 0.0
        print("[POS] Software azimuth reset to 0 deg")

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["azimuth_deg", "rx_peak_dbm", "peak_freq_hz"])

        print("\n----------------------------------------------------")
        print("[SWEEP] BEGIN AZIMUTH PATTERN SWEEP")
        print("----------------------------------------------------\n")

        print("[POS] Software azimuth reference set to 0 deg")
        current_az = 0.0
        if boresight_only:
            print("[MODE] Boresight-only capture: positioner movement disabled")

        if use_woym:
            update_woym_generic(
                run_woym_path=run_woym_path,
                latest_woym_path=latest_woym_path,
                current_test_group=current_group,
                current_test_method=current_test_method,
                status="running",
                current_state={
                    "state": "configuring",
                    "message": "Starting azimuth sweep",
                    "target": {},
                },
                current_sweep=build_current_sweep_dict(
                    sweep_index=sweep_index,
                    total_sweeps=total_sweeps,
                    point_index=0,
                    total_points=total_points,
                    axis="azimuth",
                    orientation=orientation,
                    polarisation=polarisation,
                    antenna=antenna,
                    ctx=ctx,
                    power_level=power_level,
                    channel=channel,
                    frequency_hz=tx_freq,
                    battery_mv=battery_mv,
                ),
                artifacts={
                    "latest_csv_path": csv_path,
                    "latest_plot_path": plot_png_path,
                    "latest_metadata_path": meta_path,
                    "combo_dir": combo_dir,
                },
                error={
                    "status": "none",
                    "message": "",
                    "where": "",
                    "timestamp": "",
                },
                event=(
                    f"Started sweep {sweep_index}/{total_sweeps}: "
                    f"ORI={orientation} POL={polarisation} ANT={antenna} "
                    f"PWR={power_level} CH={channel}"
                ),
            )

            update_woym_azimuth(
                run_woym_path=run_woym_path,
                latest_woym_path=latest_woym_path,
                spectrum_analyser=build_spectrum_analyser_block(
                    requested_center_hz=tx_freq,
                    requested_span_hz=span_hz,
                    requested_rbw_hz=rbw_hz,
                    requested_vbw_hz=vbw_hz,
                    last_peak_freq_hz=None,
                    last_peak_dbm=None,
                ),
            )

        idx = 0
        pre_positioned = False
        while True:
            try:
                if not pre_positioned:
                    print(f"\n[POS] Pre-positioning to {format_angle(maxa)} (no RF capture)")
                    move_rel(+maxa)
                    pre_positioned = True

                    print("\n[SWEEP] Measurement phase: +max -> 0 -> -max\n")
                    print(f"[SWEEP] Total points: {total_points}")
                    print("[PLOT] Output image will be generated after the final measurement")

                while idx < total_points:
                    az = current_az

                    print("\n----------------------------------------------------")
                    print(f"[POINT {idx+1:03d}] AZIMUTH = {format_angle(az)}")
                    print("----------------------------------------------------")

                    if use_woym:
                        update_woym_generic(
                            run_woym_path=run_woym_path,
                            latest_woym_path=latest_woym_path,
                            current_state={
                                "state": "measuring",
                                "message": f"Measuring azimuth point at {format_angle(az)}",
                                "target": {
                                    "azimuth_deg": az,
                                },
                            },
                            current_sweep=build_current_sweep_dict(
                                sweep_index=sweep_index,
                                total_sweeps=total_sweeps,
                                point_index=idx + 1,
                                total_points=total_points,
                                axis="azimuth",
                                orientation=orientation,
                                polarisation=polarisation,
                                antenna=antenna,
                                ctx=ctx,
                                power_level=power_level,
                                channel=channel,
                                frequency_hz=tx_freq,
                                battery_mv=battery_mv,
                            ),
                            artifacts={
                                "latest_csv_path": csv_path,
                                "latest_plot_path": plot_png_path,
                                "latest_metadata_path": meta_path,
                                "combo_dir": combo_dir,
                            },
                            event=f"Measuring point {idx + 1}/{total_points} at {format_angle(az)}",
                        )

                    print("[SA] Arming per-point MAX HOLD capture")
                    print(f"[SA]   Integrating for {hold_s:.2f} s")

                    t_meas_start = time()
                    pk_f_hz, rx_dbm = sa.read_peak_maxhold(hold_s=hold_s)
                    t_meas_end = time()

                    print(
                        f"[SA] MAX HOLD complete "
                        f"({t_meas_end - t_meas_start:.2f} s elapsed)"
                    )

                    if lowest_level_dbm is not None and rx_dbm < lowest_level_dbm:
                        print(
                            f"[WARN] RX level below expected floor: "
                            f"{rx_dbm:.2f} dBm < {lowest_level_dbm:.2f} dBm"
                        )

                    writer.writerow([f"{az:.1f}", f"{rx_dbm:.6f}", f"{pk_f_hz:.0f}"])
                    f.flush()

                    print(
                        f"[DATA] az {format_angle(az):>10} | "
                        f"RX = {rx_dbm:7.2f} dBm | "
                        f"Fpk = {pk_f_hz/1e6:.6f} MHz"
                    )

                    if use_woym:
                        last_measurement = {
                            "orientation": orientation,
                            "polarisation": polarisation,
                            "antenna": antenna,
                            "power_level": power_level,
                            "channel": channel,
                            "frequency_hz": tx_freq,
                            "azimuth_deg": az,
                            "rx_peak_dbm": rx_dbm,
                            "peak_freq_hz": pk_f_hz,
                            "timestamp": iso_now(),
                        }
                        if ctx is not None:
                            last_measurement["ctx"] = ctx
                        if battery_mv is not None:
                            last_measurement["battery_mv"] = battery_mv

                        update_woym_generic(
                            run_woym_path=run_woym_path,
                            latest_woym_path=latest_woym_path,
                            last_measurement=last_measurement,
                            current_sweep=build_current_sweep_dict(
                                sweep_index=sweep_index,
                                total_sweeps=total_sweeps,
                                point_index=idx + 1,
                                total_points=total_points,
                                axis="azimuth",
                                orientation=orientation,
                                polarisation=polarisation,
                                antenna=antenna,
                                ctx=ctx,
                                power_level=power_level,
                                channel=channel,
                                frequency_hz=tx_freq,
                                battery_mv=battery_mv,
                            ),
                            artifacts={
                                "latest_csv_path": csv_path,
                                "latest_plot_path": plot_png_path,
                                "latest_metadata_path": meta_path,
                                "combo_dir": combo_dir,
                            },
                            event=(
                                f"Measured az {format_angle(az)} "
                                f"RX={rx_dbm:.2f} dBm Fpk={pk_f_hz/1e6:.6f} MHz"
                            ),
                        )

                        update_woym_azimuth(
                            run_woym_path=run_woym_path,
                            latest_woym_path=latest_woym_path,
                            spectrum_analyser=build_spectrum_analyser_block(
                                requested_center_hz=tx_freq,
                                requested_span_hz=span_hz,
                                requested_rbw_hz=rbw_hz,
                                requested_vbw_hz=vbw_hz,
                                last_peak_freq_hz=pk_f_hz,
                                last_peak_dbm=rx_dbm,
                            ),
                        )

                    is_final_point = idx == steps

                    if is_final_point:
                        if use_woym:
                            update_woym_generic(
                                run_woym_path=run_woym_path,
                                latest_woym_path=latest_woym_path,
                                current_state={
                                    "state": "plotting",
                                    "message": f"Writing output image at {format_angle(az)}",
                                    "target": {
                                        "azimuth_deg": az,
                                    },
                                },
                                artifacts={
                                    "latest_csv_path": csv_path,
                                    "latest_plot_path": plot_png_path,
                                    "latest_metadata_path": meta_path,
                                    "combo_dir": combo_dir,
                                },
                                event=f"Writing output image at {format_angle(az)}",
                            )
                        write_partial_polar_plot(csv_path, plot_png_path)

                    if az > -maxa:
                        print(f"[POS] Advancing to next azimuth step ({format_angle(-step)})")
                        move_rel(-step)

                    idx += 1
                break
            except KeyboardInterrupt:
                action = prompt_interrupt_menu(current_az)
                if action == "resume":
                    print("[INTERRUPT] Resuming test")
                    continue

                stop_message = "User stopped sweep in current location"
                if action == "stop_boresight":
                    try:
                        return_to_boresight()
                    except Exception as e:
                        stop_message = f"User requested boresight return, but move failed: {e}"
                        print(f"[WARN] {stop_message}")
                    else:
                        stop_message = "User stopped sweep after return to boresight"

                if use_woym:
                    update_woym_generic(
                        run_woym_path=run_woym_path,
                        latest_woym_path=latest_woym_path,
                        current_state={
                            "state": "idle",
                            "message": stop_message,
                            "target": {
                                "azimuth_deg": current_az,
                            },
                        },
                        current_sweep=build_current_sweep_dict(
                            sweep_index=sweep_index,
                            total_sweeps=total_sweeps,
                            point_index=min(idx + 1, total_points),
                            total_points=total_points,
                            axis="azimuth",
                            orientation=orientation,
                            polarisation=polarisation,
                            antenna=antenna,
                            ctx=ctx,
                            power_level=power_level,
                            channel=channel,
                            frequency_hz=tx_freq,
                            battery_mv=battery_mv,
                        ),
                        artifacts={
                            "latest_csv_path": csv_path,
                            "latest_plot_path": plot_png_path,
                            "latest_metadata_path": meta_path,
                            "combo_dir": combo_dir,
                        },
                        event=stop_message,
                    )

                raise SweepStoppedByUser(action)

        print("\n[POS] Sweep complete - returning to start position")
        move_rel(+maxa)

        current_az = 0.0
        print("[POS] Software azimuth reset to 0 deg")

        if use_woym:
            update_woym_generic(
                run_woym_path=run_woym_path,
                latest_woym_path=latest_woym_path,
                current_state={
                    "state": "idle",
                    "message": (
                        f"Completed sweep {sweep_index}/{total_sweeps} "
                        f"for ORI={orientation} POL={polarisation} ANT={antenna} "
                        f"PWR={power_level} CH={channel}"
                    ),
                    "target": {},
                },
                current_sweep=build_current_sweep_dict(
                    sweep_index=sweep_index,
                    total_sweeps=total_sweeps,
                    point_index=total_points,
                    total_points=total_points,
                    axis="azimuth",
                    orientation=orientation,
                    polarisation=polarisation,
                    antenna=antenna,
                    ctx=ctx,
                    power_level=power_level,
                    channel=channel,
                    frequency_hz=tx_freq,
                    battery_mv=battery_mv,
                ),
                artifacts={
                    "latest_csv_path": csv_path,
                    "latest_plot_path": plot_png_path,
                    "latest_metadata_path": meta_path,
                    "combo_dir": combo_dir,
                },
                event=(
                    f"Completed sweep {sweep_index}/{total_sweeps}: "
                    f"ORI={orientation} POL={polarisation} ANT={antenna} "
                    f"PWR={power_level} CH={channel}"
                ),
            )


def run(params, equip):
    t_start = time()
    print("\n====================================================")
    print("[1_meas_azimuth] STARTING AZIMUTH PATTERN MEASUREMENT")
    print("====================================================\n")

    # ---------------- Equipment ----------------
    pos = equip.positioner
    sa = equip.spectrum_analyser
    sg = equip.signal_generator

    outdir = params["output_dir"]
    os.makedirs(outdir, exist_ok=True)

    use_woym = bool(params.get("use_woym", False))
    run_woym_path = params.get("woym_path", "")
    latest_woym_path = params.get("latest_woym_path", "")
    current_group = params.get("current_group", "")
    current_test_method = params.get("current_test_method", "1_meas_azimuth")

    # ---------------- YAML parameters ----------------
    dut_product = params.get("DUT_product", "Unknown")
    dut_hardware_config = params.get("DUT_hardware_config", "")
    dut_serial_number = params.get("DUT_serial_number", "Unknown")
    active_dut_name = params.get("active_dut_name", "")
    active_dut_index = params.get("active_dut_index")
    active_dut_total = params.get("active_dut_total")
    active_dut_display = build_active_dut_display(active_dut_name, dut_serial_number)
    foldername_comment = params.get("foldername_comment", "")
    yaml_comment = params.get("yaml_comment", "")

    axis = params.get("axis", "azimuth")
    sweep_mode = params.get("sweep_mode", "unknown")

    bore = float(params.get("boresight_deg", 0))
    max_angle_values = normalize_max_angle_values(params["max_angle_deg"])
    step = float(params["step_deg"])

    dwell_s = float(params.get("dwell_s", 0.5))
    hold_s = float(params.get("max_hold_seconds", 1.0))
    height_m = params.get("height_m", None)
    lowest_level_dbm = params.get("lowest_level", None)
    plot_every_deg = float(params.get("live_plot_every_deg", 20.0))
    orientations = ensure_list(params.get("orientations", ["unknown"]), "orientations")
    polarisations = ensure_list(params.get("polarisation", ["Unknown"]), "polarisation")

    sg_cfg = params["sig_gen_1"]
    sg_sweep_cfg = resolve_sig_gen_sweep_config(sg_cfg)
    sa_cfg = params["spec_an_1"]
    rx_cfg = params.get("rx_path", {})

    device_type = sg_sweep_cfg["device_type"]
    tx_mode = sg_sweep_cfg["tx_mode"]
    ctx_levels = sg_sweep_cfg["ctx_levels"]
    is_bodyworn_hendrix_tx = (
        device_type == "hendrix_tx" and tx_mode == "bodyworn"
    )
    raw_manual_setup_order = params.get("manual_setup_order")
    if raw_manual_setup_order is None:
        manual_setup_order = "inner" if is_bodyworn_hendrix_tx else "outer"
    else:
        manual_setup_order = normalize_manual_setup_order(raw_manual_setup_order)
    channels = sg_sweep_cfg["channels"]
    power_levels = sg_sweep_cfg["power_levels"]
    frequency_label = sg_sweep_cfg["frequency_label"]
    power_label = sg_sweep_cfg["power_label"]
    manual_fallback = coerce_bool(
        get_first_present(sg_cfg, ("manual_fallback", "wirepro_manual_fallback")),
        default=False,
    )
    antenna_variants = sg_sweep_cfg["antennas"]
    antenna_labels = [item["label"] for item in antenna_variants]
    manual_variants = build_manual_variants(orientations, polarisations)
    rf_variants = build_rf_variants(
        antenna_variants,
        power_levels,
        channels,
        ctx_levels,
    )

    span_hz = int(sa_cfg.get("span_hz", 10_000))
    rbw_hz = int(sa_cfg.get("rbw_hz", sa_cfg.get("RBW", 10_000)))
    vbw_hz = int(sa_cfg.get("vbw_hz", sa_cfg.get("VBW", 10_000)))
    boresight_only = str(sweep_mode).strip().lower() == "boresight_only"

    total_sweeps = (
        len(manual_variants)
        * len(rf_variants)
        * len(max_angle_values)
    )

    print("[CFG] Parsed YAML parameters:")
    if active_dut_name:
        if active_dut_index is not None and active_dut_total is not None:
            print(
                f"      Active DUT         : {active_dut_name} "
                f"({active_dut_index}/{active_dut_total})"
            )
        else:
            print(f"      Active DUT         : {active_dut_name}")
    print(f"      DUT product        : {dut_product}")
    if dut_hardware_config:
        print(f"      DUT hw config      : {dut_hardware_config}")
    print(f"      DUT serial         : {dut_serial_number}")
    print(f"      Folder comment     : {foldername_comment}")
    print(f"      YAML comment       : {yaml_comment}")
    print(f"      Axis               : {axis}")
    print(f"      Sweep mode         : {sweep_mode}")
    print(f"      Manual setup order : {manual_setup_order}")
    print(f"      Use WOYM          : {use_woym}")
    print(f"      Device type        : {device_type}")
    if tx_mode is not None:
        print(f"      TX mode            : {tx_mode}")
    if manual_fallback:
        print(f"      Manual fallback    : {manual_fallback}")
    if ctx_levels and ctx_levels[0] is not None:
        print(
            "      CTX                : "
            f"{[ctx_level_to_numeric(level) for level in ctx_levels]} "
            f"({ctx_levels})"
        )
    print(f"      Orientations       : {orientations}")
    print(f"      Polarisations      : {polarisations}")
    print(f"      Boresight (logical): {format_angle(bore, signed=False)}")
    if len(max_angle_values) == 1:
        print(f"      Max angle          : {format_symmetric_angle(max_angle_values[0])}")
    else:
        print(
            "      Max angles         : "
            f"{[format_symmetric_angle(value) for value in max_angle_values]}"
        )
    print(f"      Step size          : {format_angle(step, signed=False)}")
    print(f"      Height             : {height_m}")
    print(f"      Dwell time         : {dwell_s:.2f} s")
    print(f"      MAX HOLD time      : {hold_s:.2f} s")
    print(f"      Output plot        : final image only")
    print(f"      Total sweeps       : {total_sweeps}")
    print(f"      {frequency_label:<18} : {channels}")
    print(f"      {power_label:<18} : {power_levels}")
    print(f"      Antennas           : {antenna_labels}")
    print(f"      RX path            : {rx_cfg}")
    print(f"      SA span            : {span_hz/1e3:.1f} kHz")
    print(f"      SA RBW             : {rbw_hz/1e3:.1f} kHz")
    print(f"      SA VBW             : {vbw_hz/1e3:.1f} kHz")

    if use_woym:
        update_woym_generic(
            run_woym_path=run_woym_path,
            latest_woym_path=latest_woym_path,
            current_test_group=current_group,
            current_test_method=current_test_method,
            status="running",
            current_state={
                "state": "configuring",
                "message": f"Preparing {current_test_method}",
                "target": {},
            },
            current_sweep={
                "sweep_index": 0,
                "total_sweeps": total_sweeps,
                "point_index": 0,
                "total_points": 0,
                "axis": axis,
            },
            error={
                "status": "none",
                "message": "",
                "where": "",
                "timestamp": "",
            },
            event=f"Loaded test config for {current_test_method}",
        )

    sg.open()
    if hasattr(sg, "set_device_type"):
        sg.set_device_type(device_type)
    elif device_type != "rxcc":
        raise RuntimeError(
            "sig_gen_1.device_type requires a signal-generator driver that supports set_device_type()"
        )
    if any(level is not None for level in ctx_levels) and not hasattr(sg, "set_ctx"):
        raise RuntimeError(
            "sig_gen_1.ctx requires a signal-generator driver that supports set_ctx()"
        )
    pending_error = None

    try:
        stopped_by_user = None
        combo_index = 0
        current_ctx_level = None
        current_channel = None
        current_power_level = None
        current_antenna = None
        bodyworn_rf_active = False
        bodyworn_manual_mode = False
        wireless_pro_rf_active = False
        wirepro_manual_mode = False
        current_battery_mv = None
        confirmed_orientation = None
        confirmed_polarisation = None

        measurement_dir = os.path.join(outdir, "1_meas_azimuth")
        os.makedirs(measurement_dir, exist_ok=True)

        def activate_wirepro_manual_mode(*, antenna_label, channel, power_level, tx_freq, reason):
            nonlocal wirepro_manual_mode
            nonlocal wireless_pro_rf_active

            if device_type != "wireless-pro-rx" or not manual_fallback:
                return False

            print(f"[WARN] Wireless Pro RX automatic control failed: {reason}")
            prompt_wirepro_manual_setup(
                antenna_label=antenna_label,
                wirepro_freq=channel,
                wirepro_power=power_level,
                tx_freq=tx_freq,
                reason=reason,
                active_dut_display=active_dut_display,
            )
            wirepro_manual_mode = True
            wireless_pro_rf_active = True
            return True

        def ensure_manual_setup(orientation, polarisation):
            nonlocal confirmed_orientation
            nonlocal confirmed_polarisation

            orientation_change_required = confirmed_orientation != orientation
            if use_woym and orientation_change_required:
                update_woym_generic(
                    run_woym_path=run_woym_path,
                    latest_woym_path=latest_woym_path,
                    current_state={
                        "state": "configuring",
                        "message": f"Waiting for manual DUT orientation change to '{orientation}'",
                        "target": {
                            "orientation": orientation,
                        },
                    },
                    event=f"Awaiting DUT orientation change: {orientation}",
                )

            if orientation_change_required:
                prompt_manual_change(
                    f"Set the DUT orientation to '{orientation}'.",
                    active_dut_display=active_dut_display,
                )
                confirmed_orientation = orientation
            else:
                print(f"[MANUAL] DUT orientation already confirmed as '{orientation}', continuing.")

            polarisation_change_required = confirmed_polarisation != polarisation
            if use_woym and polarisation_change_required:
                update_woym_generic(
                    run_woym_path=run_woym_path,
                    latest_woym_path=latest_woym_path,
                    current_state={
                        "state": "configuring",
                        "message": f"Waiting for manual polarisation change to '{polarisation}'",
                        "target": {
                            "polarisation": polarisation,
                        },
                    },
                    event=f"Awaiting polarisation change: {polarisation}",
                )

            if polarisation_change_required:
                prompt_manual_change(
                    f"Set the manual test setup to polarisation '{polarisation}'.",
                    active_dut_display=active_dut_display,
                )
                confirmed_polarisation = polarisation
            else:
                print(f"[MANUAL] Polarisation already confirmed as '{polarisation}', continuing.")

        outer_variants = manual_variants if manual_setup_order == "outer" else rf_variants
        inner_variants = rf_variants if manual_setup_order == "outer" else manual_variants

        for outer_variant in outer_variants:
            if manual_setup_order == "inner":
                inner_variants = order_manual_variants_for_current_state(
                    manual_variants,
                    confirmed_orientation,
                    confirmed_polarisation,
                )

            if manual_setup_order == "outer":
                orientation = outer_variant["orientation"]
                pol = outer_variant["polarisation"]
                ensure_manual_setup(orientation, pol)

            for inner_variant in inner_variants:
                if manual_setup_order == "outer":
                    rf_variant = inner_variant
                    manual_setup_pending = False
                else:
                    rf_variant = outer_variant
                    orientation = inner_variant["orientation"]
                    pol = inner_variant["polarisation"]
                    manual_setup_pending = True

                antenna_cfg = rf_variant["antenna_cfg"]
                antenna = antenna_cfg["value"]
                antenna_label = antenna_cfg["label"]
                antenna_token = antenna_cfg["token"]
                power_level = rf_variant["power_level"]
                channel = rf_variant["channel"]
                tx_freq = (
                    wirepro_freq_to_frequency_hz(channel)
                    if device_type == "wireless-pro-rx"
                    else rxcc_channel_to_frequency_hz(channel)
                )
                ctx_level = rf_variant["ctx_level"]
                ctx_value = ctx_level_to_numeric(ctx_level)
                ctx_display = (
                    f"{ctx_value} ({ctx_level})" if ctx_value is not None else "n/a"
                )
                token_ctx = sanitize_token(ctx_value) if ctx_value is not None else None

                for maxa in max_angle_values:
                    sweep_point_count = sweep_point_count_for(maxa, step, boresight_only)
                    combo_index += 1

                    print("\n" + "#" * 90)
                    print(
                        f"[COMBO {combo_index}] "
                        f"ORI={orientation} | POL={pol} | ANT={antenna_label} | "
                        f"{power_label.upper()}={power_level} | CTX={ctx_display} | "
                        f"{frequency_label.upper()}={channel} "
                        f"({tx_freq/1e6:.3f} MHz) | "
                        f"MAXA={format_symmetric_angle(maxa)}"
                    )
                    print("#" * 90)

                    token_ori = sanitize_token(orientation)
                    token_pol = sanitize_token(pol)
                    token_pwr = sanitize_token(power_level)
                    token_ch = sanitize_token(channel)
                    token_freq_prefix = "wfreq" if device_type == "wireless-pro-rx" else "ch"
                    token_power_prefix = "wpwr" if device_type == "wireless-pro-rx" else "pwr"
                    token_maxa_value = int(maxa) if float(maxa).is_integer() else maxa
                    token_maxa = sanitize_token(token_maxa_value)

                    combo_parts = [
                        f"ori-{token_ori}",
                        f"pol-{token_pol}",
                        f"ant-{antenna_token}",
                        f"{token_power_prefix}-{token_pwr}",
                    ]
                    if token_ctx is not None:
                        combo_parts.append(f"ctx-{token_ctx}")
                    combo_parts.append(f"{token_freq_prefix}-{token_ch}")
                    combo_parts.append(f"maxa-{token_maxa}")
                    combo_dir_name = "_".join(combo_parts)
                    combo_dir = os.path.join(measurement_dir, combo_dir_name)
                    os.makedirs(combo_dir, exist_ok=True)

                    csv_path = os.path.join(combo_dir, "pattern_azimuth.csv")
                    meta_path = os.path.join(combo_dir, "metadata.json")
                    plot_png_path = os.path.join(combo_dir, "pattern_azimuth_EEmax.png")

                    combo_meta = {
                        "test_method": "1_meas_azimuth",
                        "measurement": "Azimuth Pattern Measurement",
                        "axis": axis,
                        "sweep_mode": sweep_mode,
                        "manual_setup_order": manual_setup_order,
                        "active_dut_name": active_dut_name,
                        "active_dut_index": active_dut_index,
                        "active_dut_total": active_dut_total,
                        "DUT_product": dut_product,
                        "DUT_hardware_config": dut_hardware_config,
                        "DUT_serial_number": dut_serial_number,
                        "foldername_comment": foldername_comment,
                        "yaml_comment": yaml_comment,
                        "orientation": orientation,
                        "polarisation": pol,
                        "boresight_deg": bore,
                        "max_angle_deg": maxa,
                        "step_deg": step,
                        "height_m": height_m,
                        "sig_gen_1": {
                            "device_type": device_type,
                            "tx_mode": tx_mode,
                            "ctx": ctx_value,
                            "channel": channel,
                            "power_level": power_level,
                            "wirepro_freq": channel if device_type == "wireless-pro-rx" else None,
                            "wirepro_power": power_level if device_type == "wireless-pro-rx" else None,
                            "antenna": antenna,
                            "frequency_hz": tx_freq,
                        },
                        "rx_path": rx_cfg,
                        "spec_an_1": {
                            "center_frequency_hz": tx_freq,
                            "span_hz": span_hz,
                            "rbw_hz": rbw_hz,
                            "vbw_hz": vbw_hz,
                        },
                        "capture_method": {
                            "type": "per_point_max_hold",
                            "max_hold_seconds": hold_s,
                            "dwell_seconds": dwell_s,
                            "live_plot_every_deg": plot_every_deg,
                        },
                        "limits": {
                            "lowest_level_dbm": lowest_level_dbm
                        },
                    }

                    meta_write(meta_path, combo_meta)
                    print(f"[META] Written -> {meta_path}")
                    print(f"[OUT]  CSV output  -> {csv_path}")
                    print(f"[OUT]  Plot output -> {plot_png_path}")

                    if use_woym:
                        update_woym_generic(
                            run_woym_path=run_woym_path,
                            latest_woym_path=latest_woym_path,
                            current_state={
                                "state": "configuring",
                                "message": (
                                    f"Configuring sweep {combo_index}/{total_sweeps} "
                                    f"ORI={orientation} POL={pol} ANT={antenna_label} "
                                    f"{power_label.upper()}={power_level} CTX={ctx_display} "
                                    f"{frequency_label.upper()}={channel} "
                                    f"MAXA={format_symmetric_angle(maxa)}"
                                ),
                                "target": {},
                            },
                            current_sweep=build_current_sweep_dict(
                                sweep_index=combo_index,
                                total_sweeps=total_sweeps,
                                point_index=0,
                                total_points=sweep_point_count,
                                axis=axis,
                                orientation=orientation,
                                polarisation=pol,
                                antenna=antenna_label,
                                ctx=ctx_value,
                                power_level=power_level,
                                channel=channel,
                                frequency_hz=tx_freq,
                            ),
                            artifacts={
                                "latest_csv_path": csv_path,
                                "latest_plot_path": plot_png_path,
                                "latest_metadata_path": meta_path,
                                "combo_dir": combo_dir,
                            },
                            error={
                                "status": "none",
                                "message": "",
                                "where": "",
                                "timestamp": "",
                            },
                            event=(
                                f"Prepared sweep {combo_index}/{total_sweeps}: "
                                f"ORI={orientation} POL={pol} ANT={antenna_label} "
                                f"{power_label.upper()}={power_level} CTX={ctx_display} "
                                f"{frequency_label.upper()}={channel} "
                                f"MAXA={format_symmetric_angle(maxa)}"
                            ),
                        )

                        update_woym_azimuth(
                            run_woym_path=run_woym_path,
                            latest_woym_path=latest_woym_path,
                            spectrum_analyser=build_spectrum_analyser_block(
                                requested_center_hz=tx_freq,
                                requested_span_hz=span_hz,
                                requested_rbw_hz=rbw_hz,
                                requested_vbw_hz=vbw_hz,
                                last_peak_freq_hz=None,
                                last_peak_dbm=None,
                            ),
                        )

                    antenna_change_required = current_antenna != antenna
                    ctx_change_required = current_ctx_level != ctx_level
                    channel_change_required = current_channel != channel
                    power_change_required = current_power_level != power_level
                    config_change_required = (
                        antenna_change_required
                        or ctx_change_required
                        or channel_change_required
                        or power_change_required
                    )

                    if device_type == "wireless-pro-rx" and wirepro_manual_mode:
                        if config_change_required:
                            print(
                                "[TX] WIRELESS-PRO-RX manual mode active; "
                                "manual confirmation required for changed sweep settings"
                            )
                            activate_wirepro_manual_mode(
                                antenna_label=antenna_label,
                                channel=channel,
                                power_level=power_level,
                                tx_freq=tx_freq,
                                reason=(
                                    "Automatic WirePro control is disabled for this run. "
                                    "Confirm the requested settings manually."
                                ),
                            )
                    else:
                        if (
                            device_type == "wireless-pro-rx"
                            and wireless_pro_rf_active
                            and config_change_required
                        ):
                            if prompt_rf_stop_override(
                                device_label="WIRELESS-PRO-RX",
                                reason="Reconfiguring sweep variant",
                            ):
                                print(
                                    "[TX] Stopping WIRELESS-PRO-RX RF before "
                                    "reconfiguring sweep variant"
                                )
                                try:
                                    sg.rf_off()
                                    wireless_pro_rf_active = False
                                except Exception as e:
                                    if not activate_wirepro_manual_mode(
                                        antenna_label=antenna_label,
                                        channel=channel,
                                        power_level=power_level,
                                        tx_freq=tx_freq,
                                        reason=str(e),
                                    ):
                                        raise
                            else:
                                activate_wirepro_manual_mode(
                                    antenna_label=antenna_label,
                                    channel=channel,
                                    power_level=power_level,
                                    tx_freq=tx_freq,
                                    reason=(
                                        "RF stop skipped by operator. "
                                        "Confirm the requested settings manually."
                                    ),
                                )

                        if (
                            device_type == "wireless-pro-rx"
                            and not wirepro_manual_mode
                        ):
                            try:
                                if antenna is not None and antenna_change_required:
                                    sg.set_antenna(antenna)
                                if power_change_required:
                                    if hasattr(sg, "set_wirepro_power"):
                                        sg.set_wirepro_power(power_level)
                                    else:
                                        raise RuntimeError(
                                            "wireless-pro-rx requires a signal-generator driver "
                                            "that supports set_wirepro_power()"
                                        )
                                if channel_change_required:
                                    if hasattr(sg, "set_wirepro_freq"):
                                        sg.set_wirepro_freq(channel)
                                    else:
                                        raise RuntimeError(
                                            "wireless-pro-rx requires a signal-generator driver "
                                            "that supports set_wirepro_freq()"
                                        )
                            except Exception as e:
                                if not activate_wirepro_manual_mode(
                                    antenna_label=antenna_label,
                                    channel=channel,
                                    power_level=power_level,
                                    tx_freq=tx_freq,
                                    reason=str(e),
                                ):
                                    raise
                        elif antenna is not None and antenna_change_required:
                            sg.set_antenna(antenna)

                    bodyworn_config_applied = False

                    if is_bodyworn_hendrix_tx and config_change_required:
                        def perform_bodyworn_cradle_update():
                            nonlocal bodyworn_rf_active
                            nonlocal current_battery_mv

                            prompt_bodyworn_tx_in_cradle(
                                active_dut_display=active_dut_display,
                                return_from_bodyworn_rf=bodyworn_rf_active
                            )

                            current_battery_mv = capture_hendrix_tx_battery_mv(
                                sg=sg,
                                device_type=device_type,
                                combo_meta=combo_meta,
                                meta_path=meta_path,
                                use_woym=use_woym,
                                run_woym_path=run_woym_path,
                                latest_woym_path=latest_woym_path,
                                current_group=current_group,
                                current_test_method=current_test_method,
                                sweep_index=combo_index,
                                total_sweeps=total_sweeps,
                                total_points=sweep_point_count,
                                axis=axis,
                                orientation=orientation,
                                polarisation=pol,
                                antenna=antenna_label,
                                ctx=ctx_value,
                                power_level=power_level,
                                channel=channel,
                                frequency_hz=tx_freq,
                                csv_path=csv_path,
                                plot_png_path=plot_png_path,
                                combo_dir=combo_dir,
                            )

                            if ctx_change_required and ctx_level is not None:
                                print(f"[TX] Setting Hendrix CTX to {ctx_display}")
                                sg.set_ctx(ctx_level)
                            if power_change_required:
                                sg.set_power_level(power_level)
                            if channel_change_required:
                                sg.set_channel(channel)

                            print(f"[TX] Starting {device_type.upper()} RF")
                            sg.rf_on()
                            bodyworn_rf_active = True
                            prompt_bodyworn_tx_remove_from_cradle()

                        update_reason = (
                            "Manual fallback is enabled for this run."
                            if manual_fallback
                            else "Choose cradle update or manual confirmation."
                        )
                        while True:
                            update_method = prompt_bodyworn_tx_update_choice(
                                channel=channel,
                                power_level=power_level,
                                ctx_display=ctx_display,
                                tx_freq=tx_freq,
                                reason=update_reason,
                                active_dut_display=active_dut_display,
                            )
                            bodyworn_manual_mode = update_method == "manual"
                            if bodyworn_manual_mode:
                                bodyworn_rf_active = True
                                break

                            try:
                                perform_bodyworn_cradle_update()
                                bodyworn_config_applied = True
                                break
                            except Exception as e:
                                update_reason = str(e)
                                print(
                                    "[WARN] Hendrix TX cradle update failed; "
                                    "choose 1 to try again or 2 for manual confirmation."
                                )
                                print(f"[WARN] Reason: {update_reason}")
                                if use_woym:
                                    update_woym_generic(
                                        run_woym_path=run_woym_path,
                                        latest_woym_path=latest_woym_path,
                                        current_test_group=current_group,
                                        current_test_method=current_test_method,
                                        event=(
                                            "Hendrix TX cradle update failed; "
                                            f"manual fallback prompt reopened: {update_reason}"
                                        ),
                                    )

                    if (
                        ctx_change_required
                        and ctx_level is not None
                        and not bodyworn_manual_mode
                        and not bodyworn_config_applied
                    ):
                        print(f"[TX] Setting Hendrix CTX to {ctx_display}")
                        sg.set_ctx(ctx_level)
                    if (
                        device_type != "wireless-pro-rx"
                        and not bodyworn_manual_mode
                        and not bodyworn_config_applied
                    ):
                        if power_change_required:
                            sg.set_power_level(power_level)
                        if channel_change_required:
                            sg.set_channel(channel)

                    if (
                        is_bodyworn_hendrix_tx
                        and config_change_required
                        and not bodyworn_manual_mode
                        and not bodyworn_config_applied
                    ):
                        print(f"[TX] Starting {device_type.upper()} RF")
                        sg.rf_on()
                        bodyworn_rf_active = True
                        prompt_bodyworn_tx_remove_from_cradle()

                    current_ctx_level = ctx_level
                    current_channel = channel
                    current_power_level = power_level
                    current_antenna = antenna

                    if manual_setup_pending:
                        ensure_manual_setup(orientation, pol)
                        manual_setup_pending = False

                    print("\n[SA] Configuring spectrum analyser (narrowband mode)")
                    print(
                        f"[SA] Requested retune: {frequency_label.upper()}={channel} "
                        f"FREQ={tx_freq/1e6:.6f} MHz "
                        f"SPAN={span_hz/1e3:.1f} kHz "
                        f"RBW={rbw_hz/1e3:.1f} kHz "
                        f"VBW={vbw_hz/1e3:.1f} kHz"
                    )
                    verified_sa = sa.configure_narrowband(
                        center_hz=tx_freq,
                        span_hz=span_hz,
                        rbw_hz=rbw_hz,
                        vbw_hz=vbw_hz,
                    )
                    print(
                        "[SA] Verified retune: "
                        f"CENT={verified_sa['center_hz']/1e6:.6f} MHz "
                        f"SPAN={verified_sa['span_hz']/1e3:.1f} kHz "
                        f"RBW={verified_sa['rbw_hz']/1e3:.1f} kHz "
                        f"VBW={verified_sa['vbw_hz']/1e3:.1f} kHz"
                    )

                    if is_bodyworn_hendrix_tx:
                        battery_mv = current_battery_mv
                        if battery_mv is not None:
                            combo_meta.setdefault("sig_gen_1", {})["battery_mv"] = battery_mv
                            meta_write(meta_path, combo_meta)
                        if bodyworn_manual_mode:
                            print(
                                "[TX] Hendrix TX bodyworn manual fallback active: "
                                "assuming RF is already correct for this sweep"
                            )
                        elif bodyworn_rf_active:
                            print(
                                "[TX] Hendrix TX bodyworn mode: "
                                "RF already on for this sweep"
                            )
                        else:
                            print(
                                "[TX] Hendrix TX bodyworn mode: "
                                "awaiting cradle update before RF start"
                            )
                    else:
                        if device_type == "wireless-pro-rx" and wirepro_manual_mode:
                            print(
                                "[TX] WIRELESS-PRO-RX manual mode active; "
                                "assuming RF is already on for this sweep"
                            )
                        elif device_type == "wireless-pro-rx" and wireless_pro_rf_active:
                            print(
                                "[TX] WIRELESS-PRO-RX RF already on; "
                                "reusing current RF state for this sweep"
                            )
                        else:
                            print(f"[TX] Starting {device_type.upper()} RF")
                            try:
                                sg.rf_on()
                                if device_type == "wireless-pro-rx":
                                    wireless_pro_rf_active = True
                            except Exception as e:
                                if not activate_wirepro_manual_mode(
                                    antenna_label=antenna_label,
                                    channel=channel,
                                    power_level=power_level,
                                    tx_freq=tx_freq,
                                    reason=str(e),
                                ):
                                    raise
                        battery_mv = capture_hendrix_tx_battery_mv(
                            sg=sg,
                            device_type=device_type,
                            combo_meta=combo_meta,
                            meta_path=meta_path,
                            use_woym=use_woym,
                            run_woym_path=run_woym_path,
                            latest_woym_path=latest_woym_path,
                            current_group=current_group,
                            current_test_method=current_test_method,
                            sweep_index=combo_index,
                            total_sweeps=total_sweeps,
                            total_points=sweep_point_count,
                            axis=axis,
                            orientation=orientation,
                            polarisation=pol,
                            antenna=antenna_label,
                            ctx=ctx_value,
                            power_level=power_level,
                            channel=channel,
                            frequency_hz=tx_freq,
                            csv_path=csv_path,
                            plot_png_path=plot_png_path,
                            combo_dir=combo_dir,
                        )
                    try:
                        run_single_azimuth_sweep(
                            pos=pos,
                            sa=sa,
                            csv_path=csv_path,
                            plot_png_path=plot_png_path,
                            run_woym_path=run_woym_path,
                            latest_woym_path=latest_woym_path,
                            use_woym=use_woym,
                            current_group=current_group,
                            current_test_method=current_test_method,
                            orientation=orientation,
                            polarisation=pol,
                            antenna=antenna_label,
                            ctx=ctx_value,
                            power_level=power_level,
                            channel=channel,
                            tx_freq=tx_freq,
                            sweep_index=combo_index,
                            total_sweeps=total_sweeps,
                            sweep_mode=sweep_mode,
                            maxa=maxa,
                            step=step,
                            dwell_s=dwell_s,
                            hold_s=hold_s,
                            lowest_level_dbm=lowest_level_dbm,
                            plot_every_deg=plot_every_deg,
                            combo_dir=combo_dir,
                            meta_path=meta_path,
                            span_hz=span_hz,
                            rbw_hz=rbw_hz,
                            vbw_hz=vbw_hz,
                            battery_mv=battery_mv,
                        )
                    except SweepStoppedByUser:
                        raise
                    except Exception as e:
                        if use_woym:
                            set_woym_error(
                                run_woym_path,
                                latest_woym_path,
                                f"Azimuth sweep failed: {e}",
                                "1_meas_azimuth.run_single_azimuth_sweep",
                            )
                        raise
                    finally:
                        if not is_bodyworn_hendrix_tx and device_type != "wireless-pro-rx":
                            if prompt_rf_stop_override(
                                device_label=device_type.upper(),
                                reason="End of sweep combination",
                            ):
                                print(f"[TX] Stopping {device_type.upper()} RF")
                                sg.rf_off()
                            else:
                                print(
                                    f"[TX] Leaving {device_type.upper()} RF/state "
                                    "unchanged by operator request"
                                )
    except SweepStoppedByUser as e:
        stopped_by_user = e
    except Exception as e:
        pending_error = e
        raise
    finally:
        cleanup_error = None
        cleanup_where = "1_meas_azimuth.run/finally"

        try:
            if is_bodyworn_hendrix_tx and bodyworn_rf_active:
                if bodyworn_manual_mode:
                    print(
                        "[TX] Hendrix TX bodyworn manual fallback active; "
                        "leaving RF state unchanged at shutdown"
                    )
                else:
                    should_stop_rf = prompt_bodyworn_tx_in_cradle(
                        active_dut_display=active_dut_display,
                        return_from_bodyworn_rf=True,
                        allow_skip=True,
                    )
                    if should_stop_rf is not False:
                        print("[TX] Stopping HENDRIX_TX RF before shutdown")
                        sg.rf_off()
                    else:
                        print(
                            "[TX] Leaving HENDRIX_TX RF/state unchanged at shutdown "
                            "by operator request"
                        )
                bodyworn_rf_active = False
            if device_type == "wireless-pro-rx" and wireless_pro_rf_active:
                if wirepro_manual_mode:
                    print(
                        "[TX] WIRELESS-PRO-RX manual mode active; "
                        "leaving RF state unchanged at shutdown"
                    )
                else:
                    if prompt_rf_stop_override(
                        device_label="WIRELESS-PRO-RX",
                        reason="Runner shutdown",
                    ):
                        print("[TX] Stopping WIRELESS-PRO-RX RF before shutdown")
                        sg.rf_off()
                    else:
                        print(
                            "[TX] Leaving WIRELESS-PRO-RX RF/state unchanged at shutdown "
                            "by operator request"
                        )
                wireless_pro_rf_active = False
        except Exception as e:
            cleanup_error = e

        try:
            sg.close()
        except Exception as e:
            if cleanup_error is None:
                cleanup_error = e

        if cleanup_error is not None:
            cleanup_message = f"Signal generator cleanup failed: {cleanup_error}"
            if pending_error is not None:
                print(
                    "[WARN] "
                    f"{cleanup_message} (preserving original failure: {pending_error})"
                )
                if use_woym:
                    update_woym_generic(
                        run_woym_path=run_woym_path,
                        latest_woym_path=latest_woym_path,
                        current_test_group=current_group,
                        current_test_method=current_test_method,
                        event=(
                            f"{cleanup_message} while preserving original failure: "
                            f"{pending_error}"
                        ),
                    )
            else:
                if use_woym:
                    set_woym_error(
                        run_woym_path,
                        latest_woym_path,
                        cleanup_message,
                        cleanup_where,
                    )
                raise cleanup_error

    if stopped_by_user is not None:
        if use_woym:
            stop_mode_labels = {
                "resume": "resumed",
                "stop_boresight": "stopped at boresight",
                "stop_hold": "stopped in current location",
            }
            stop_label = stop_mode_labels.get(stopped_by_user.stop_mode, "stopped by user")
            update_woym_generic(
                run_woym_path=run_woym_path,
                latest_woym_path=latest_woym_path,
                current_state={
                    "state": "idle",
                    "message": f"{current_test_method} {stop_label}",
                    "target": {},
                },
                event=f"{current_test_method} {stop_label}",
            )

        print("\n====================================================")
        print("[1_meas_azimuth] STOPPED BY USER")
        print(f"[1_meas_azimuth] Total elapsed time: {time() - t_start:.1f} s")
        print("====================================================\n")
        return

    if use_woym:
        update_woym_generic(
            run_woym_path=run_woym_path,
            latest_woym_path=latest_woym_path,
            current_state={
                "state": "idle",
                "message": f"{current_test_method} complete",
                "target": {},
            },
            event=f"{current_test_method} complete",
        )

    print("\n====================================================")
    print("[1_meas_azimuth] COMPLETE")
    print(f"[1_meas_azimuth] Total elapsed time: {time() - t_start:.1f} s")
    print("====================================================\n")

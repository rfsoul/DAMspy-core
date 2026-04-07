# ------------------------------------------------------------
# 1_meas_azimuth.py
#
# Antenna Pattern Measurement – Azimuth Sweep
# Multi-condition version:
# - manual outer loop for DUT orientation
# - manual next loop for polarisation
# - automated inner loops for RXCC antenna / power / channel
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

import matplotlib.pyplot as plt


def meta_write(path, meta: dict):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)


def rxcc_channel_to_frequency_hz(channel: int) -> int:
    channel = int(channel)
    if not (0 <= channel <= 80):
        raise ValueError(f"RXCC channel must be 0..80, got {channel}")
    return 2_400_000_000 + channel * 500_000


def ensure_list(value, name: str):
    if isinstance(value, list):
        return value
    if value is None:
        raise ValueError(f"Missing required list-like field: {name}")
    return [value]


def sanitize_token(value) -> str:
    return str(value).replace(" ", "_").replace("/", "_").replace("\\", "_")


def prompt_manual_change(message: str) -> None:
    print("\n" + "=" * 90)
    print("[MANUAL ACTION REQUIRED]")
    print(message)
    print("Press Enter when complete...")
    print("=" * 90)
    input()


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
    power_level,
    channel,
    frequency_hz,
):
    return {
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
        "Antenna Pattern – Azimuth Cut\n"
        f"Linear E / Emax (points so far: {point_count})",
        pad=20,
    )

    ax.grid(True)
    plt.tight_layout()
    plt.savefig(out_png)
    plt.close()

    print(f"[PLOT] Updated partial polar plot → {out_png}")


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
    power_level,
    channel,
    tx_freq,
    sweep_index: int,
    total_sweeps: int,
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
):
    current_az = 0.0
    last_plot_az = None

    steps = int((2 * maxa) / step)
    total_points = steps + 1

    def move_rel(delta_deg):
        nonlocal current_az
        if abs(delta_deg) < 1e-9:
            print("[POS] Zero move requested – skipping")
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
                    "message": f"Moving azimuth from {current_az:+.1f}° to {target:+.1f}°",
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
                event=f"Moving azimuth to {target:+.1f}°",
            )

        print(
            f"[POS] Commanding AZ move: "
            f"{current_az:+.1f}° → {target:+.1f}° "
            f"(Δ {delta_deg:+.1f}°)"
        )
        pos.go_azimuth(delta_deg)
        current_az = target
        print(f"[POS] Move complete, settling for {dwell_s:.2f} s")
        sleep(dwell_s)

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["azimuth_deg", "rx_peak_dbm", "peak_freq_hz"])

        print("\n----------------------------------------------------")
        print("[SWEEP] BEGIN AZIMUTH PATTERN SWEEP")
        print("----------------------------------------------------\n")

        print("[POS] Software azimuth reference set to 0°")
        current_az = 0.0

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

        print(f"\n[POS] Pre-positioning to +{maxa:.1f}° (no RF capture)")
        move_rel(+maxa)

        print("\n[SWEEP] Measurement phase: +max → 0 → -max\n")
        print(f"[SWEEP] Total points: {total_points}")
        print(f"[PLOT] Live plot update threshold: {plot_every_deg:.1f}°")

        for idx in range(total_points):
            az = current_az

            print("\n----------------------------------------------------")
            print(f"[POINT {idx+1:03d}] AZIMUTH = {az:+.1f}°")
            print("----------------------------------------------------")

            if use_woym:
                update_woym_generic(
                    run_woym_path=run_woym_path,
                    latest_woym_path=latest_woym_path,
                    current_state={
                        "state": "measuring",
                        "message": f"Measuring azimuth point at {az:+.1f}°",
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
                    event=f"Measuring point {idx + 1}/{total_points} at {az:+.1f}°",
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
                f"[DATA] az {az:+6.1f}° | "
                f"RX = {rx_dbm:7.2f} dBm | "
                f"Fpk = {pk_f_hz/1e6:.6f} MHz"
            )

            if use_woym:
                update_woym_generic(
                    run_woym_path=run_woym_path,
                    latest_woym_path=latest_woym_path,
                    last_measurement={
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
                    event=(
                        f"Measured az {az:+.1f}° "
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

            is_first_point = last_plot_az is None
            moved_enough = (
                last_plot_az is not None
                and abs(az - last_plot_az) >= plot_every_deg
            )
            is_final_point = idx == steps

            if is_first_point or moved_enough or is_final_point:
                if use_woym:
                    update_woym_generic(
                        run_woym_path=run_woym_path,
                        latest_woym_path=latest_woym_path,
                        current_state={
                            "state": "plotting",
                            "message": f"Updating live plot at {az:+.1f}°",
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
                        event=f"Updating live plot at {az:+.1f}°",
                    )
                write_partial_polar_plot(csv_path, plot_png_path)
                last_plot_az = az

            if az > -maxa:
                print(f"[POS] Advancing to next azimuth step (-{step:.1f}°)")
                move_rel(-step)

        print("\n[POS] Sweep complete – returning to start position")
        move_rel(+maxa)

        current_az = 0.0
        print("[POS] Software azimuth reset to 0°")

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
    dut_serial_number = params.get("DUT_serial_number", "Unknown")
    foldername_comment = params.get("foldername_comment", "")
    yaml_comment = params.get("yaml_comment", "")

    axis = params.get("axis", "azimuth")
    sweep_mode = params.get("sweep_mode", "unknown")

    bore = float(params.get("boresight_deg", 0))
    maxa = float(params["max_angle_deg"])
    step = float(params["step_deg"])

    dwell_s = float(params.get("dwell_s", 0.5))
    hold_s = float(params.get("max_hold_seconds", 1.0))
    height_m = params.get("height_m", None)
    lowest_level_dbm = params.get("lowest_level", None)
    plot_every_deg = float(params.get("live_plot_every_deg", 20.0))

    orientations = ensure_list(params.get("orientations", ["unknown"]), "orientations")
    polarisations = ensure_list(params.get("polarisation", ["Unknown"]), "polarisation")

    sg_cfg = params["sig_gen_1"]
    sa_cfg = params["spec_an_1"]
    rx_cfg = params.get("rx_path", {})

    channels = ensure_list(sg_cfg.get("channels"), "sig_gen_1.channels")
    power_levels = ensure_list(sg_cfg.get("power_levels"), "sig_gen_1.power_levels")
    antennas = ensure_list(
        sg_cfg.get("antennas", sg_cfg.get("antenna")),
        "sig_gen_1.antennas",
    )

    span_hz = int(sa_cfg.get("span_hz", 10_000))
    rbw_hz = int(sa_cfg.get("rbw_hz", sa_cfg.get("RBW", 10_000)))
    vbw_hz = int(sa_cfg.get("vbw_hz", sa_cfg.get("VBW", 10_000)))

    total_sweeps = (
        len(orientations)
        * len(polarisations)
        * len(antennas)
        * len(power_levels)
        * len(channels)
    )

    print("[CFG] Parsed YAML parameters:")
    print(f"      DUT product        : {dut_product}")
    print(f"      DUT serial         : {dut_serial_number}")
    print(f"      Folder comment     : {foldername_comment}")
    print(f"      YAML comment       : {yaml_comment}")
    print(f"      Axis               : {axis}")
    print(f"      Sweep mode         : {sweep_mode}")
    print(f"      Use WOYM          : {use_woym}")
    print(f"      Orientations       : {orientations}")
    print(f"      Polarisations      : {polarisations}")
    print(f"      Boresight (logical): {bore:.1f}°")
    print(f"      Max angle          : ±{maxa:.1f}°")
    print(f"      Step size          : {step:.1f}°")
    print(f"      Height             : {height_m}")
    print(f"      Dwell time         : {dwell_s:.2f} s")
    print(f"      MAX HOLD time      : {hold_s:.2f} s")
    print(f"      Live plot every    : {plot_every_deg:.1f}°")
    print(f"      Total sweeps       : {total_sweeps}")
    print(f"      Channels           : {channels}")
    print(f"      Power levels       : {power_levels}")
    print(f"      Antennas           : {antennas}")
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
    try:
        combo_index = 0

        measurement_dir = os.path.join(outdir, "1_meas_azimuth")
        os.makedirs(measurement_dir, exist_ok=True)

        for orientation in orientations:
            if use_woym:
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

            prompt_manual_change(
                f"Set the DUT orientation to '{orientation}'."
            )

            for pol in polarisations:
                if use_woym:
                    update_woym_generic(
                        run_woym_path=run_woym_path,
                        latest_woym_path=latest_woym_path,
                        current_state={
                            "state": "configuring",
                            "message": f"Waiting for manual polarisation change to '{pol}'",
                            "target": {
                                "polarisation": pol,
                            },
                        },
                        event=f"Awaiting polarisation change: {pol}",
                    )

                prompt_manual_change(
                    f"Set the manual test setup to polarisation '{pol}'."
                )

                for antenna in antennas:
                    for power_level in power_levels:
                        for channel in channels:
                            combo_index += 1
                            tx_freq = rxcc_channel_to_frequency_hz(channel)

                            print("\n" + "#" * 90)
                            print(
                                f"[COMBO {combo_index}] "
                                f"ORI={orientation} | POL={pol} | ANT={antenna} | "
                                f"PWR={power_level} | CH={channel} "
                                f"({tx_freq/1e6:.3f} MHz)"
                            )
                            print("#" * 90)

                            token_ori = sanitize_token(orientation)
                            token_pol = sanitize_token(pol)
                            token_ant = sanitize_token(antenna)
                            token_pwr = sanitize_token(power_level)
                            token_ch = sanitize_token(channel)

                            combo_dir_name = (
                                f"ori-{token_ori}_"
                                f"pol-{token_pol}_"
                                f"ant-{token_ant}_"
                                f"pwr-{token_pwr}_"
                                f"ch-{token_ch}"
                            )
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
                                "DUT_product": dut_product,
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
                                    "channel": channel,
                                    "power_level": power_level,
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
                            print(f"[META] Written → {meta_path}")
                            print(f"[OUT]  CSV output  → {csv_path}")
                            print(f"[OUT]  Plot output → {plot_png_path}")

                            if use_woym:
                                update_woym_generic(
                                    run_woym_path=run_woym_path,
                                    latest_woym_path=latest_woym_path,
                                    current_state={
                                        "state": "configuring",
                                        "message": (
                                            f"Configuring sweep {combo_index}/{total_sweeps} "
                                            f"ORI={orientation} POL={pol} ANT={antenna} "
                                            f"PWR={power_level} CH={channel}"
                                        ),
                                        "target": {},
                                    },
                                    current_sweep=build_current_sweep_dict(
                                        sweep_index=combo_index,
                                        total_sweeps=total_sweeps,
                                        point_index=0,
                                        total_points=int((2 * maxa) / step) + 1,
                                        axis=axis,
                                        orientation=orientation,
                                        polarisation=pol,
                                        antenna=antenna,
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
                                        f"ORI={orientation} POL={pol} ANT={antenna} "
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

                            # Configure source
                            sg.set_antenna(antenna)
                            sg.set_power_level(power_level)
                            sg.set_channel(channel)

                            # Configure analyser
                            print("\n[SA] Configuring spectrum analyser (narrowband mode)")
                            print(
                                f"[SA] Requested retune: CH={channel} "
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

                            print("[TX] Starting RXCC RF")
                            sg.rf_on()
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
                                    antenna=antenna,
                                    power_level=power_level,
                                    channel=channel,
                                    tx_freq=tx_freq,
                                    sweep_index=combo_index,
                                    total_sweeps=total_sweeps,
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
                                )
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
                                print("[TX] Stopping RXCC RF")
                                sg.rf_off()

    except Exception:
        raise
    finally:
        try:
            sg.close()
        except Exception as e:
            if use_woym:
                set_woym_error(
                    run_woym_path,
                    latest_woym_path,
                    f"Signal generator close failed: {e}",
                    "1_meas_azimuth.run/finally",
                )
            raise

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

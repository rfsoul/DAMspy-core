# ------------------------------------------------------------
# 1_meas_azimuth.py
#
# Antenna Pattern Measurement – Azimuth Sweep
# Multi-condition version:
# - manual outer loop for polarisation
# - automated inner loops for RXCC antenna / power / channel
# - one folder per condition combination
# ------------------------------------------------------------

import os
import json
import csv
from time import sleep, time


def meta_write(path, meta: dict):
    with open(path, "w") as f:
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


def run_single_azimuth_sweep(
    *,
    pos,
    sa,
    csv_path: str,
    maxa: float,
    step: float,
    dwell_s: float,
    hold_s: float,
    lowest_level_dbm,
):
    current_az = 0.0

    def move_rel(delta_deg):
        nonlocal current_az
        if abs(delta_deg) < 1e-9:
            print("[POS] Zero move requested – skipping")
            return

        target = current_az + delta_deg
        print(
            f"[POS] Commanding AZ move: "
            f"{current_az:+.1f}° → {target:+.1f}° "
            f"(Δ {delta_deg:+.1f}°)"
        )
        pos.go_azimuth(delta_deg)
        current_az = target
        print(f"[POS] Move complete, settling for {dwell_s:.2f} s")
        sleep(dwell_s)

    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["azimuth_deg", "rx_peak_dbm", "peak_freq_hz"])

        print("\n----------------------------------------------------")
        print("[SWEEP] BEGIN AZIMUTH PATTERN SWEEP")
        print("----------------------------------------------------\n")

        print("[POS] Software azimuth reference set to 0°")
        current_az = 0.0

        print(f"\n[POS] Pre-positioning to +{maxa:.1f}° (no RF capture)")
        move_rel(+maxa)

        print("\n[SWEEP] Measurement phase: +max → 0 → -max\n")

        steps = int((2 * maxa) / step)
        print(f"[SWEEP] Total points: {steps + 1}")

        for idx in range(steps + 1):
            az = current_az

            print("\n----------------------------------------------------")
            print(f"[POINT {idx+1:03d}] AZIMUTH = {az:+.1f}°")
            print("----------------------------------------------------")

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

            print(
                f"[DATA] az {az:+6.1f}° | "
                f"RX = {rx_dbm:7.2f} dBm | "
                f"Fpk = {pk_f_hz/1e6:.6f} MHz"
            )

            if az > -maxa:
                print(f"[POS] Advancing to next azimuth step (-{step:.1f}°)")
                move_rel(-step)

        print("\n[POS] Sweep complete – returning to start position")
        move_rel(+maxa)

        current_az = 0.0
        print("[POS] Software azimuth reset to 0°")


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

    # ---------------- YAML parameters ----------------
    bore = params.get("boresight_deg", 0)
    maxa = float(params["max_angle_deg"])
    step = float(params["step_deg"])

    dwell_s = float(params.get("dwell_s", 0.5))
    hold_s = float(params.get("max_hold_seconds", 1.0))

    dut = params.get("DUT", "Unknown")
    lowest_level_dbm = params.get("lowest_level", None)

    polarisations = ensure_list(params.get("polarisation", ["Unknown"]), "polarisation")

    sg_cfg = params["sig_gen_1"]
    sa_cfg = params["spec_an_1"]

    channels = ensure_list(sg_cfg.get("channels"), "sig_gen_1.channels")
    power_levels = ensure_list(sg_cfg.get("power_levels"), "sig_gen_1.power_levels")
    antennas = ensure_list(
        sg_cfg.get("antennas", sg_cfg.get("antenna")),
        "sig_gen_1.antennas",
    )

    span_hz = int(sa_cfg.get("span_hz", 10_000))
    rbw_hz = int(sa_cfg.get("rbw_hz", sa_cfg.get("RBW", 10_000)))
    vbw_hz = int(sa_cfg.get("vbw_hz", sa_cfg.get("VBW", 10_000)))

    print("[CFG] Parsed YAML parameters:")
    print(f"      DUT                : {dut}")
    print(f"      Polarisations      : {polarisations}")
    print(f"      Boresight (logical): {bore:.1f}°")
    print(f"      Max angle          : ±{maxa:.1f}°")
    print(f"      Step size          : {step:.1f}°")
    print(f"      Dwell time         : {dwell_s:.2f} s")
    print(f"      MAX HOLD time      : {hold_s:.2f} s")
    print(f"      Channels           : {channels}")
    print(f"      Power levels       : {power_levels}")
    print(f"      Antennas           : {antennas}")
    print(f"      SA span            : {span_hz/1e3:.1f} kHz")
    print(f"      SA RBW             : {rbw_hz/1e3:.1f} kHz")
    print(f"      SA VBW             : {vbw_hz/1e3:.1f} kHz")

    sg.open()
    try:
        combo_index = 0

        # Manual-change dimensions outermost
        for pol in polarisations:
            prompt_manual_change(
                f"Set the manual test setup to polarisation '{pol}'."
            )

            # Automated dimensions innermost
            for antenna in antennas:
                for power_level in power_levels:
                    for channel in channels:
                        combo_index += 1
                        tx_freq = rxcc_channel_to_frequency_hz(channel)

                        print("\n" + "#" * 90)
                        print(
                            f"[COMBO {combo_index}] "
                            f"POL={pol} | ANT={antenna} | PWR={power_level} | CH={channel} "
                            f"({tx_freq/1e6:.3f} MHz)"
                        )
                        print("#" * 90)

                        # Configure source
                        sg.set_antenna(antenna)
                        sg.set_power_level(power_level)
                        sg.set_channel(channel)

                        # Configure analyser
                        print("\n[SA] Configuring spectrum analyser (narrowband mode)")
                        print(
                            f"[SA]   Center = {tx_freq/1e6:.6f} MHz | "
                            f"Span = {span_hz/1e3:.1f} kHz"
                        )
                        sa.configure_narrowband(center_hz=tx_freq, span_hz=span_hz)

                        # Output structure:
                        # run root (from run.py)
                        #   -> azimuth/
                        #       -> one folder per combination
                        token_pol = sanitize_token(pol)
                        token_ant = sanitize_token(antenna)
                        token_pwr = sanitize_token(power_level)
                        token_ch = sanitize_token(channel)

                        measurement_dir = os.path.join(outdir, "1_meas_azimuth")
                        os.makedirs(measurement_dir, exist_ok=True)

                        combo_dir_name = (
                            f"pol-{token_pol}_"
                            f"ant-{token_ant}_"
                            f"pwr-{token_pwr}_"
                            f"ch-{token_ch}"
                        )
                        combo_dir = os.path.join(measurement_dir, combo_dir_name)
                        os.makedirs(combo_dir, exist_ok=True)

                        csv_path = os.path.join(combo_dir, "pattern_azimuth.csv")
                        meta_path = os.path.join(combo_dir, "metadata.json")

                        combo_meta = {
                            "DUT": dut,
                            "measurement": "Azimuth Pattern Measurement",
                            "sweep_axis": "azimuth",
                            "coordinate_frame": "DUT_PCB_XYZ (Altium)",
                            "polarisation": pol,
                            "boresight_deg": bore,
                            "max_angle_deg": maxa,
                            "step_deg": step,
                            "sweep_mode": "single_pass_relative",
                            "sig_gen_1": {
                                "channel": channel,
                                "power_level": power_level,
                                "antenna": antenna,
                                "frequency_hz": tx_freq,
                            },
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
                            },
                            "limits": {
                                "lowest_level_dbm": lowest_level_dbm
                            },
                        }

                        meta_write(meta_path, combo_meta)
                        print(f"[META] Written → {meta_path}")
                        print(f"[OUT]  CSV output → {csv_path}")

                        # Start RF
                        print("[TX] Starting RXCC RF")
                        sg.rf_on()
                        try:
                            run_single_azimuth_sweep(
                                pos=pos,
                                sa=sa,
                                csv_path=csv_path,
                                maxa=maxa,
                                step=step,
                                dwell_s=dwell_s,
                                hold_s=hold_s,
                                lowest_level_dbm=lowest_level_dbm,
                            )
                        finally:
                            print("[TX] Stopping RXCC RF")
                            sg.rf_off()

    finally:
        sg.close()

    print("\n====================================================")
    print("[1_meas_azimuth] COMPLETE")
    print(f"[1_meas_azimuth] Total elapsed time: {time() - t_start:.1f} s")
    print("====================================================\n")
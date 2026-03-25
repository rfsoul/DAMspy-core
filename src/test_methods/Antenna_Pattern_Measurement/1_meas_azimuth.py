# ------------------------------------------------------------
# 1_meas_azimuth.py
#
# Antenna Pattern Measurement – Azimuth Sweep
# VERBOSE per-point MAX HOLD capture
# ------------------------------------------------------------

import os
import json
import csv
from time import sleep, time


def meta_write(path, meta: dict):
    with open(path, "w") as f:
        json.dump(meta, f, indent=2)


def run(params, equip):
    t_start = time()
    print("\n====================================================")
    print("[1_meas_azimuth] STARTING AZIMUTH PATTERN MEASUREMENT")
    print("====================================================\n")

    # ---------------- Equipment ----------------
    pos = equip.positioner
    sa  = equip.spectrum_analyser

    outdir = params["output_dir"]
    os.makedirs(outdir, exist_ok=True)

    # ---------------- YAML parameters ----------------
    bore = params.get("boresight_deg", 0)     # logical only
    maxa = float(params["max_angle_deg"])
    step = float(params["step_deg"])

    dwell_s = float(params.get("dwell_s", 0.5))
    hold_s  = float(params.get("max_hold_seconds", 1.0))

    pol = params.get("polarisation", "Unknown")
    dut = params.get("DUT", "Unknown")

    tx_cfg  = params["tx"]
    tx_freq = tx_cfg["frequency_hz"]
    span_hz = tx_cfg.get("span_hz", 10_000)

    lowest_level_dbm = params.get("lowest_level_dbm", None)

    print("[CFG] Parsed YAML parameters:")
    print(f"      DUT                : {dut}")
    print(f"      Polarisation       : {pol}")
    print(f"      Boresight (logical): {bore:.1f}°")
    print(f"      Max angle          : ±{maxa:.1f}°")
    print(f"      Step size          : {step:.1f}°")
    print(f"      Dwell time         : {dwell_s:.2f} s")
    print(f"      MAX HOLD time      : {hold_s:.2f} s")
    print(f"      TX frequency       : {tx_freq/1e6:.6f} MHz")
    print(f"      SA span            : {span_hz/1e3:.1f} kHz")

    # ---------------- Metadata ----------------
    meta = {
        "DUT": dut,
        "measurement": "Azimuth Pattern Measurement",
        "sweep_axis": "azimuth",
        "coordinate_frame": "DUT_PCB_XYZ (Altium)",
        "polarisation": pol,
        "boresight_deg": bore,
        "max_angle_deg": maxa,
        "step_deg": step,
        "sweep_mode": "single_pass_relative",
        "tx": tx_cfg,
        "capture_method": {
            "type": "per_point_max_hold",
            "max_hold_seconds": hold_s,
            "dwell_seconds": dwell_s,
        },
        "limits": {
            "lowest_level_dbm": lowest_level_dbm
        },
    }

    meta_path = os.path.join(outdir, "metadata.json")
    meta_write(meta_path, meta)
    print(f"[META] Written → {meta_path}")

    # ---------------- Configure Spectrum Analyser ----------------
    print("\n[SA] Configuring spectrum analyser (narrowband mode)")
    print(
        f"[SA]   Center = {tx_freq/1e6:.6f} MHz | "
        f"Span = {span_hz/1e3:.1f} kHz"
    )
    sa.configure_narrowband(center_hz=tx_freq, span_hz=span_hz)
    print("[SA] Narrowband configuration complete")

    # ---------------- Output CSV ----------------
    csv_path = os.path.join(outdir, "pattern_azimuth.csv")
    print(f"[OUT] CSV output → {csv_path}")

    # ---------------- Motion state (logical only) ----------------
    current_az = 0.0

    def move_rel(delta_deg):
        nonlocal current_az
        if abs(delta_deg) < 1e-6:
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

    # ---------------- Begin sweep ----------------
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["azimuth_deg", "rx_peak_dbm"])

        print("\n----------------------------------------------------")
        print("[SWEEP] BEGIN AZIMUTH PATTERN SWEEP")
        print("----------------------------------------------------\n")

        # ------------------------------------------------
        # Define software azimuth zero
        # ------------------------------------------------
        print("[POS] Software azimuth reference set to 0°")
        current_az = 0.0

        # ------------------------------------------------
        # Pre-position to +max (NO measurement)
        # ------------------------------------------------
        print(f"\n[POS] Pre-positioning to +{maxa:.1f}° (no RF capture)")
        move_rel(+maxa)

        # ------------------------------------------------
        # Measurement sweep: +max → 0 → -max
        # ------------------------------------------------
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

            writer.writerow([f"{az:.1f}", f"{rx_dbm:.6f}"])

            print(
                f"[DATA] az {az:+6.1f}° | "
                f"RX = {rx_dbm:7.2f} dBm | "
                f"Fpk = {pk_f_hz/1e6:.6f} MHz"
            )

            if az > -maxa:
                print(f"[POS] Advancing to next azimuth step (-{step:.1f}°)")
                move_rel(-step)

        # ------------------------------------------------
        # Return to start (relative)
        # ------------------------------------------------
        print("\n[POS] Sweep complete – returning to start position")
        move_rel(+maxa)

        current_az = 0.0
        print("[POS] Software azimuth reset to 0°")

    print("\n====================================================")
    print("[1_meas_azimuth] COMPLETE")
    print(f"[1_meas_azimuth] CSV saved → {csv_path}")
    print(f"[1_meas_azimuth] Total elapsed time: {time() - t_start:.1f} s")
    print("====================================================\n")

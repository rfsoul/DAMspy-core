# ------------------------------------------------------------
# 1_xy_cut_polar_plot_ee.py
#
# Post-processing for Antenna Pattern Measurement – XY Cut
#
# Plot:
#   - Linear E / Emax (radius)
#   - dB reference rings
#   - Annotated absolute Emax (dBm)
#
# Reads:
#   pattern_xy.csv
#
# Writes:
#   pattern_xy_polar_EEmax.png
#
# Contract:
#   run(run_dir: str)
#
# No hardware interaction.
# Safe to re-run on archived data.
# ------------------------------------------------------------

import os
import csv
import math
import matplotlib.pyplot as plt

result_dir = r"C:\DAMspySandbox\DAMspy\DAMspy_logs\Antenna_Pattern_Measurement_2026-01-23_13-11-53_Hendrix_EV3-07_YZ_from_-Z_HPol_rx_10deg_dwell_0s"

def main():
    print("running polar polot directly")
    run(result_dir)
    print("polar plot complete")

def run(run_dir: str):
    print("[POST] Azimuth Polar Plot (Linear E/Emax)")

    csv_path = os.path.join(run_dir, "pattern_azimuth.csv")
    out_png  = os.path.join(run_dir, "pattern_azimuth_EEmax.png")

    if not os.path.exists(csv_path):
        print(f"[POST][WARN] Missing CSV: {csv_path}")
        return

    az_deg = []
    levels_dbm = []

    # ---------------- Read CSV ----------------
    with open(csv_path, "r", newline="") as f:
        reader = csv.DictReader(f)
        if "azimuth_deg" not in reader.fieldnames or "rx_peak_dbm" not in reader.fieldnames:
            print("[POST][ERROR] CSV missing required columns")
            print(f"[POST] Found columns: {reader.fieldnames}")
            return

        for row in reader:
            try:
                az_deg.append(float(row["azimuth_deg"]))
                levels_dbm.append(float(row["rx_peak_dbm"]))
            except ValueError:
                continue

    if not az_deg:
        print("[POST][WARN] No valid data points found")
        return

    # ---------------- Normalise to E/Emax ----------------
    max_dbm = max(levels_dbm)
    e_over_emax = [
        10 ** ((v - max_dbm) / 20.0)
        for v in levels_dbm
    ]

    # Convert to radians
    az_rad = [math.radians(a) for a in az_deg]

    # ---------------- Plot ----------------
    plt.figure(figsize=(8, 8))
    ax = plt.subplot(111, projection="polar")

    # Main pattern
    ax.plot(az_rad, e_over_emax, linewidth=2)

    # Polar conventions (match existing style)
    ax.set_theta_zero_location("N")   # 0° at top (boresight)
    ax.set_theta_direction(-1)        # Clockwise
    ax.set_rlim(0, 1.05)

    # ---------------- dB reference rings ----------------
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

    # ---------------- Annotate Emax ----------------
    ax.text(
        math.radians(90),
        1.02,
        f"Emax = {max_dbm:.2f} dBm",
        ha="center",
        va="bottom",
        fontsize=11,
        fontweight="bold",
    )

    ax.set_title(
        "Antenna Pattern – XY Cut\n"
        "Linear E / Emax (dB reference rings)",
        pad=20
    )

    ax.grid(True)

    plt.tight_layout()
    plt.savefig(out_png)
    plt.close()

    print(f"[POST] Linear E/Emax polar plot saved → {out_png}")

# ----------------------------------------------------------
# Entry point
# ----------------------------------------------------------
if __name__ == "__main__":
    main()
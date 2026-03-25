# 1_Emissions_meas_OptionA_MaxHoldOnly.py
# Emits only:
#   - maxhold.csv
#   - maxhold.png
# No screenshots, no dBuV/m, no raw sweep.

import os
import json
from time import sleep


def ensure(path):
    os.makedirs(path, exist_ok=True)
    return path


def meta_write(path, meta: dict):
    with open(path, "w") as f:
        json.dump(meta, f, indent=2)


def prompt_user(msg: str):
    print(msg)
    ans = input().strip().lower()
    if ans in ["", "y"]:
        return True
    print("Are you sure you want to cancel? (y/n)")
    return input().strip().lower() != "y"


def run(params, equip):
    print("[1_Emissions_meas] Starting emissions measurement...")

    pos = equip.positioner
    sa = equip.spectrum_analyser

    outdir = params["output_dir"]

    # YAML params
    az_list = params.get("az_degrees", [])
    rx_distances = params.get("rx_distance", [])
    rx_heights = params.get("rx_heights", [])
    pols = params.get("rx_pol", [])
    rx_ant = params.get("rx_ant", "Unknown")
    dut_name = params.get("DUT", "Unknown")

    # Root metadata
    root_meta = {
        "DUT": dut_name,
        "rx_ant": rx_ant,
        "pols": pols,
        "rx_distances": rx_distances,
        "rx_heights": rx_heights,
        "az_degrees": az_list,
        "mode": "MaxHoldOnly"
    }
    meta_write(os.path.join(outdir, "metadata.json"), root_meta)
    print("[INFO] Root-level metadata.json created.")

    # ----------------------------------------------------------
    # Copy AF + Cable Loss CSVs to output directory
    # ----------------------------------------------------------
    af_src = params.get("antenna_factor_file")
    loss_src = params.get("path_loss_file")

    def safe_copy(src_path, outdir):
        import shutil
        if src_path and os.path.isfile(src_path):
            try:
                base = os.path.basename(src_path)
                dest = os.path.join(outdir, base)
                shutil.copy2(src_path, dest)
                print(f"[INFO] Copied → {dest}")
            except Exception as e:
                print(f"[WARN] Could not copy {src_path}: {e}")
        else:
            print(f"[WARN] Source file missing: {src_path}")

    print("[INFO] Copying antenna/pathloss files...")
    safe_copy(af_src, outdir)
    safe_copy(loss_src, outdir)

    # Start azimuth software angle
    current_az = 0.0
    print(f"[SOFTABS] Initial software azimuth = {current_az}°")

    print("\n===================================================")
    print("        BEGIN EMISSIONS MEASUREMENT LOOP")
    print("===================================================\n")

    # Confirm RX antenna
    if not prompt_user(f"[PROMPT] Confirm RX antenna = {rx_ant}\nPress ENTER or Y to continue:"):
        print("[ABORT] User cancelled.")
        return

    prev_pol = None
    prev_dist = None
    prev_height = None

    # MAIN LOOP
    for pol in pols:
        print(f"\n========== POL: {pol} ==========\n")

        for dist_m in rx_distances:
            for height_m in rx_heights:

                # Smart prompting
                if pol != prev_pol:
                    if not prompt_user(f"[PROMPT] Set POL to: {pol}\nPress ENTER or Y to continue:"):
                        return

                if dist_m != prev_dist:
                    if not prompt_user(f"[PROMPT] Set RX distance to: {dist_m} m\nPress ENTER or Y to continue:"):
                        return

                if height_m != prev_height:
                    if not prompt_user(f"[PROMPT] Set RX height to: {height_m} m\nPress ENTER or Y to continue:"):
                        return

                prev_pol = pol
                prev_dist = dist_m
                prev_height = height_m

                for az_deg in az_list:

                    print("\n----------------------------------------------")
                    print(f"[MEAS] Target AZ = {az_deg}°")
                    print("----------------------------------------------")

                    delta = az_deg - current_az
                    if abs(delta) < 0.001:
                        print(f"[POS] Already at {az_deg}°, skipping move.")
                    else:
                        print(f"[POS] Moving from {current_az}° → {az_deg}° (delta {delta:+.2f}°)")
                        pos.go_azimuth(delta)
                        current_az = az_deg
                        print("[POS] Move complete. Settling…")
                        sleep(1.0)

                    # Folder name
                    tag = f"Pol_{pol} rxdist_{dist_m:.1f}m rxheight_{height_m:.1f}m az {az_deg:+03d}deg"
                    folder = ensure(os.path.join(outdir, tag))

                    print(f"[MEAS] Max-Hold measurement ({pol}, {dist_m}m, {height_m}m, az={az_deg})")

                    # Perform Max-Hold sweep
                    freqs, maxamps = sa.get_trace_max_hold(seconds=1.0)

                    # Save CSV + Plot
                    csv_path = os.path.join(folder, f"maxhold_{tag}.csv")
                    png_path = os.path.join(folder, f"maxhold_{tag}.png")

                    sa.save_maxhold_csv(csv_path, freqs, maxamps)
                    sa.save_maxhold_plot(png_path, freqs, maxamps)

                    print(f"[MEAS] Saved max-hold output for {tag}\n")
                    sleep(0.5)

                # Return to zero
                print(f"[POS] Finished POL {pol}, DIST {dist_m}m, HEIGHT {height_m}m. Returning to 0°…")
                if abs(current_az) < 0.001:
                    print("[POS] Already at 0°, skipping.")
                else:
                    delta = -current_az
                    print(f"[POS] Moving delta {delta:+.2f}° → 0°")
                    pos.go_azimuth(delta)
                    current_az = 0.0
                    print("[POS] Returned to 0°")

    print("\n===================================================")
    print("        FINAL RETURN TO ZERO")
    print("===================================================\n")

    if abs(current_az) > 0.001:
        pos.go_azimuth(-current_az)

    print("[1_Emissions_meas] COMPLETE.\n")

"""
Process_emissions.py

Pipeline:
    RAW sweep (*.csv ending in 'deg.csv')
        ↓  normalize filename
    *_raw_dBm.csv
        ↓  convert to compressed dBuV/m file
    *_dBuvm.csv
        ↓  generate compact summary (limit - 5dB)
    *_dBuvm_compact_summary.csv

Notes:
    - Frequencies < 30 MHz removed (not meaningful for radiated EMC)
    - dBuV/m rounded to 0.1 dB
    - dBuV/m file compressed into:
            <freq_step>
            <bin>, <dBuV/m>
    - Compact summary filters bins above limit - margin
"""

import os
import glob
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")       # safe backend for any import environment


# ============================================================
# File names and path setups
# ============================================================

product_1 = "RCV-s"
product_2 = "RCV"

AF_filename = "Bicolog30100 in path loss menu.csv"
Cableloss_filename = "RX_Cable_Loss.csv"
metadata_filename = "metadata.json"

Ambient_results_foldername  = "Emissions_Measurement_2025-12-08_16-43-47_RCV_Sn2_Ambient"
Product_1_results_foldername = "Emissions_Measurement_2025-12-08_10-58-13_RCV-S_Sn10"
Product_2_results_foldername = "Emissions_Measurement_2025-12-08_15-26-17_RCV_1.5_Sn2"

script_abs_folderpath = os.path.dirname(os.path.abspath(__file__))
test_results_parent_abs_folderpath = r"C:\al\Rode\Emissions testing\results 8th Dec\results 8th Dec"

AF_abs_filename      = os.path.join(script_abs_folderpath, AF_filename)
Cableloss_abs_filename = os.path.join(script_abs_folderpath, Cableloss_filename)

RCV_Sn2_Ambient_results_abs_folderpath = os.path.join(test_results_parent_abs_folderpath, Ambient_results_foldername)
RCV_S_Sn10_results_abs_folderpath      = os.path.join(test_results_parent_abs_folderpath, Product_1_results_foldername)
RCV_Sn2_results_abs_folderpath         = os.path.join(test_results_parent_abs_folderpath, Product_2_results_foldername)


# ============================================================
# Limit Line (CISPR-like)
# ============================================================

def limit_line(freq_hz):
    """
    Returns CISPR limit line amplitude (dBuV/m).
    40 dBuV/m up to 215 MHz, then 47 dBuV/m above.
    """
    if freq_hz < 215_000_000:
        return 40
    return 47


# ============================================================
# NORMALIZE RAW SWEEP FILENAME
# ============================================================

def normalize_raw_sweep_filename(abs_folderpath):
    """
    Ensure exactly one *_raw_dBm.csv exists.
    If only '*deg.csv' exists, rename it.
    """

    # Check for existing normalized file
    raw_pattern = os.path.join(abs_folderpath, "*_raw_dBm.csv")
    raw_files = glob.glob(raw_pattern)

    if len(raw_files) == 1:
        print(f"[OK] Raw sweep already normalized: {os.path.basename(raw_files[0])}")
        return raw_files[0]

    if len(raw_files) > 1:
        raise RuntimeError("Multiple *_raw_dBm.csv files in folder:\n" + "\n".join(raw_files))

    # Find raw deg.csv file
    deg_pattern = os.path.join(abs_folderpath, "*deg.csv")
    deg_files = glob.glob(deg_pattern)

    if len(deg_files) == 0:
        raise FileNotFoundError(f"No raw sweep '*deg.csv' found in folder:\n{abs_folderpath}")

    if len(deg_files) > 1:
        raise RuntimeError("Multiple *deg.csv files found:\n" + "\n".join(deg_files))

    # Rename raw file
    old_path = deg_files[0]
    folder = os.path.dirname(old_path)
    base, ext = os.path.splitext(os.path.basename(old_path))

    new_name = base + "_raw_dBm" + ext
    new_path = os.path.join(folder, new_name)
    os.rename(old_path, new_path)

    print(f"[OK] Renamed raw sweep → {new_name}")
    return new_path


# ============================================================
# CONVERT RAW → COMPRESSED dBuV/m FILE
# ============================================================

def convert_raw_to_dBuvm(abs_raw_csv):
    """
    Convert raw (Freq_Hz, dBm) to compressed dBuV/m CSV:
        Row 0: <freq_step_Hz>
        Rows 1+: <bin>, <dBuV_m (0.1dB)>
    """
    df = pd.read_csv(abs_raw_csv)
    if not {"Freq_Hz", "dBm"}.issubset(df.columns):
        raise ValueError(f"Raw file missing columns: {abs_raw_csv}")

    # Remove <30 MHz
    df = df[df["Freq_Hz"] >= 30_000_000].reset_index(drop=True)

    freqs = df["Freq_Hz"].values
    dBm = df["dBm"].values

    if len(freqs) < 2:
        raise RuntimeError("Not enough data above 30 MHz.")

    freq_step = freqs[1] - freqs[0]

    # Load AF table
    af = pd.read_csv(AF_abs_filename, header=None)
    af.columns = ["freq_MHz", "AF_dB_per_m"]
    af["freq_Hz"] = af["freq_MHz"] * 1e6

    # Load cable loss table
    cable = pd.read_csv(Cableloss_abs_filename)
    cable["freq_Hz"] = cable["Freq_MHz"] * 1e6

    # Interpolate AF + cable
    AF_interp = np.interp(freqs, af["freq_Hz"], af["AF_dB_per_m"])
    Cable_interp = np.interp(freqs, cable["freq_Hz"], cable["Loss_dB"])

    # Convert to dBuV/m
    dBuV = dBm + 107
    dBuVm = dBuV + AF_interp + Cable_interp

    # Build compressed output
    rows = []
    rows.append([freq_step])   # First row: frequency step

    for bin_i, val in enumerate(dBuVm):
        rows.append([bin_i, round(float(val), 1)])

    out_csv = abs_raw_csv.replace("_raw_dBm.csv", "_dBuvm.csv")

    pd.DataFrame(rows).to_csv(out_csv, index=False, header=False)
    print(f"[OK] Compressed dBuV/m file saved → {out_csv}")

    return out_csv


# ============================================================
# CREATE COMPACT SUMMARY FROM COMPRESSED dBuV/m
# ============================================================

def create_compact_summary_from_dBuvm(abs_dBuvm_csv, margin_db=5):
    """
    Compact summary:
        Row 0:   freq_step
        Rows 1+: bin, dBuV_m
        Only include bins >= limit - margin_db
    """

    df = pd.read_csv(abs_dBuvm_csv, header=None)

    freq_step = float(df.iloc[0, 0])
    data = df.iloc[1:].dropna()
    data.columns = ["bin", "dBuVm"]
    data["bin"] = data["bin"].astype(int)
    data["dBuVm"] = data["dBuVm"].astype(float)

    # Reconstruct frequencies
    freqs = 30_000_000 + data["bin"].values * freq_step

    limits = np.array([limit_line(f) for f in freqs])

    mask = data["dBuVm"].values >= (limits - margin_db)
    filtered = data[mask]

    # Build compact result
    rows = []
    rows.append([freq_step])
    for _, row in filtered.iterrows():
        rows.append([int(row["bin"]), round(float(row["dBuVm"]), 1)])

    out_csv = abs_dBuvm_csv.replace("_dBuvm.csv", "_dBuvm_compact_summary.csv")
    pd.DataFrame(rows).to_csv(out_csv, index=False, header=False)

    print(f"[OK] Compact summary saved → {out_csv}")
    return out_csv


# ============================================================
# Utility folder functions
# ============================================================

def get_first_subfolder_sorted_by_name(abs_folderpath):
    pattern = os.path.join(abs_folderpath, "*/")
    subs = glob.glob(pattern)
    if not subs:
        return None
    return sorted(subs, key=lambda p: os.path.basename(os.path.normpath(p)))[0]

def get_oldest_subfolder(abs_folderpath):
    pattern = os.path.join(abs_folderpath, "*/")
    subs = glob.glob(pattern)
    if not subs:
        return None
    return min(subs, key=os.path.getctime)

def get_youngest_subfolder(abs_folderpath):
    pattern = os.path.join(abs_folderpath, "*/")
    subs = glob.glob(pattern)
    if not subs:
        return None
    return max(subs, key=os.path.getctime)



# ============================================================
# MAIN
# ============================================================

def main():

    first_sweep_folder = get_first_subfolder_sorted_by_name(RCV_S_Sn10_results_abs_folderpath)
    print("Processing sweep folder:", first_sweep_folder)

    raw_csv = normalize_raw_sweep_filename(first_sweep_folder)

    dbuvm_csv = convert_raw_to_dBuvm(raw_csv)

    compact_csv = create_compact_summary_from_dBuvm(dbuvm_csv)

    print("\nDONE.")
    print("Raw CSV:", raw_csv)
    print("dBuV/m CSV:", dbuvm_csv)
    print("Compact Summary:", compact_csv)



# ============================================================
if __name__ == "__main__":
    main()

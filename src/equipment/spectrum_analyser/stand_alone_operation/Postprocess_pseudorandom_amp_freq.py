import os
import glob
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


BASE_LOG_DIR = r"C:\DAMspySandbox\DAMspy\DAMspy_logs\spec_an_freq_amp_histogram"

# ----------------------------------------------------------
# FOLDER SELECTION MODE
# ----------------------------------------------------------
# Set to None to automatically use youngest folder
# Or set to a folder name inside BASE_LOG_DIR
# Or set to a full absolute path

#TARGET_FOLDER = None
TARGET_FOLDER = "2026-02-16_15-58-13_Hendrix_EV3-7_on_mobile_normal_adaptor_to_back_ch0_Rx_Horn_WR340"


# ----------------------------------------------------------
# Find youngest run folder
# ----------------------------------------------------------

def find_youngest_folder(base_dir):
    subdirs = [
        os.path.join(base_dir, d)
        for d in os.listdir(base_dir)
        if os.path.isdir(os.path.join(base_dir, d))
    ]

    if not subdirs:
        raise RuntimeError("No run folders found")

    youngest = max(subdirs, key=os.path.getmtime)
    return youngest


# ----------------------------------------------------------
# Collate shift files
# ----------------------------------------------------------

def collate_shift_files(folder):
    csv_files = sorted(glob.glob(os.path.join(folder, "*_shift_*.csv")))

    if not csv_files:
        raise RuntimeError("No shift CSV files found")

    frames = []

    for f in csv_files:
        print(f"Reading {f}")
        df = pd.read_csv(f)
        frames.append(df)

    collated = pd.concat(frames, ignore_index=True)
    return collated


# ----------------------------------------------------------
# Amplitude histogram + capped + summary CSV
# ----------------------------------------------------------

def amplitude_histogram(folder, df):

    print("\n========== AMPLITUDE DEBUG ==========")

    amps = df["amplitude_dbm"].astype(float)

    max_amp = amps.max()
    min_amp = amps.min()
    diff = max_amp - min_amp
    total_samples = len(amps)

    print(f"Total samples     : {total_samples}")
    print(f"Max amplitude raw : {max_amp}")
    print(f"Min amplitude raw : {min_amp}")
    print(f"Range (max-min)   : {diff}")

    # Normalise so max becomes 0
    amps_norm = amps - max_amp

    # 0.1 dB bins
    bin_width = 0.1
    min_edge = np.floor(amps_norm.min() / bin_width) * bin_width
    max_edge = 0.0

    bins = np.arange(min_edge, max_edge + bin_width, bin_width)

    # Compute histogram counts
    counts, edges = np.histogram(amps_norm, bins=bins)
    total_bins = len(counts)

    print(f"Total bins        : {total_bins}")

    # ---- Stats box ----
    textstr = (
        f"Max: {max_amp:.3f} dBm\n"
        f"Min: {min_amp:.3f} dBm\n"
        f"Range: {diff:.3f} dB"
    )

    # ======================================================
    # ORIGINAL HISTOGRAM
    # ======================================================
    plt.figure()
    plt.hist(amps_norm, bins=bins)

    plt.xlabel("Amplitude relative to max (dB)")
    plt.ylabel("Count")
    plt.title("Normalised Amplitude Histogram (0.1 dB bins)")

    max_count = max(counts)
    y_max = int(np.ceil(max_count / 2000.0) * 2000)

    plt.ylim(0, y_max)
    plt.yticks(np.arange(0, y_max + 1, 2000))

    plt.gca().text(
        0.02, 0.95,
        textstr,
        transform=plt.gca().transAxes,
        fontsize=10,
        verticalalignment='top',
        horizontalalignment='left',
        bbox=dict(boxstyle="round", facecolor="white", alpha=0.8)
    )

    out_path = os.path.join(folder, "amplitude_histogram_normalised.png")
    plt.savefig(out_path)
    plt.close()

    print(f"Saved amplitude histogram to {out_path}")

    # ======================================================
    # CAPPED HISTOGRAM (Y max 1000)
    # ======================================================
    plt.figure()
    plt.hist(amps_norm, bins=bins)

    plt.xlabel("Amplitude relative to max (dB)")
    plt.ylabel("Count")
    plt.title("Normalised Amplitude Histogram (Y capped at 1000)")

    plt.ylim(0, 1000)
    plt.yticks(np.arange(0, 1001, 200))

    plt.gca().text(
        0.02, 0.95,
        textstr,
        transform=plt.gca().transAxes,
        fontsize=10,
        verticalalignment='top',
        horizontalalignment='left',
        bbox=dict(boxstyle="round", facecolor="white", alpha=0.8)
    )

    capped_path = os.path.join(folder, "amplitude_histogram_normalised_capped_1000.png")
    plt.savefig(capped_path)
    plt.close()

    print(f"Saved capped amplitude histogram to {capped_path}")

    # ======================================================
    # SUMMARY CSV (machine-friendly)
    # ======================================================
    folder_name = os.path.basename(folder)
    summary_name = f"{folder_name}_amplitude_summary.csv"
    summary_path = os.path.join(folder, summary_name)

    bin_centers = edges[:-1]

    with open(summary_path, "w", newline="") as f:

        f.write("metric,value\n")
        f.write(f"max_dbm,{max_amp}\n")
        f.write(f"min_dbm,{min_amp}\n")
        f.write(f"range_db,{diff}\n")
        f.write(f"total_samples,{total_samples}\n")
        f.write(f"total_bins,{total_bins}\n")
        f.write("\n")
        f.write("bin_db_relative_to_max,count\n")

        for b, c in zip(bin_centers, counts):
            f.write(f"{b:.3f},{c}\n")

    print(f"Saved amplitude summary CSV to {summary_path}")
    print("=====================================\n")


# ----------------------------------------------------------
# Frequency histogram
# ----------------------------------------------------------

def frequency_histogram(folder, df):

    freqs = df["frequency_hz"].astype(float)

    min_f = freqs.min()
    max_f = freqs.max()

    print(f"Frequency min: {min_f}")
    print(f"Frequency max: {max_f}")

    bins = np.linspace(min_f, max_f, 51)

    plt.figure()
    plt.hist(freqs, bins=bins)

    plt.xlabel("Frequency (Hz)")
    plt.ylabel("Count")
    plt.title("Frequency Histogram (50 bins)")

    out_path = os.path.join(folder, "frequency_histogram.png")
    plt.savefig(out_path)
    plt.close()

    print(f"Saved frequency histogram to {out_path}")


# ----------------------------------------------------------
# MAIN
# ----------------------------------------------------------

def main():

    print("Post-processing amplitude data...")

    # Folder selection logic
    if TARGET_FOLDER is None:
        print("Finding youngest run folder...")
        folder = find_youngest_folder(BASE_LOG_DIR)
        print(f"Youngest folder: {folder}")
    else:
        if os.path.isdir(TARGET_FOLDER):
            folder = TARGET_FOLDER
        else:
            folder = os.path.join(BASE_LOG_DIR, TARGET_FOLDER)

        if not os.path.isdir(folder):
            raise RuntimeError(f"Specified folder not found: {folder}")

        print(f"Using specified folder: {folder}")

    print("\nCollating shift files...")
    df = collate_shift_files(folder)

    # Save collated CSV
    folder_name = os.path.basename(folder)
    collated_path = os.path.join(folder, f"{folder_name}_collated.csv")
    df.to_csv(collated_path, index=False)
    print(f"Saved collated CSV: {collated_path}")

    amplitude_histogram(folder, df)
    frequency_histogram(folder, df)

    print("\nDone.")


if __name__ == "__main__":
    main()

import csv
import os
import sys
import time
import statistics
from datetime import datetime
from contextlib import redirect_stdout
import io


# ============================================================
# IMPORT DRIVER FROM ONE FOLDER ABOVE THIS SCRIPT
# ============================================================

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DRIVER_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))

if DRIVER_DIR not in sys.path:
    sys.path.insert(0, DRIVER_DIR)

from BBD60_Spike import BB60Spike


# ============================================================
# USER SETTINGS
# ============================================================

SPIKE_CFG = {
    "host": "127.0.0.1",
    "port": 5025,
}

TEST_DURATION_S = 60.0

# 0.0 = run as fast as possible.
WAIT_AFTER_SAMPLE_S = 0.0

THROW_AWAY_FIRST_SWEEP = True

# Suppress the BB60Spike driver's startup print messages
SUPPRESS_DRIVER_PRINTS = True

# Log under the standalone script folder
LOG_DIR = os.path.join(SCRIPT_DIR, "logs", "spike_timing_test")


# ============================================================
# SMALL HELPERS
# ============================================================

def ensure_dir(path):
    os.makedirs(path, exist_ok=True)


def percentile(values, p):
    if not values:
        return float("nan")

    vals = sorted(values)

    if len(vals) == 1:
        return vals[0]

    k = (len(vals) - 1) * (p / 100.0)
    f = int(k)
    c = min(f + 1, len(vals) - 1)

    if f == c:
        return vals[f]

    return vals[f] + (vals[c] - vals[f]) * (k - f)


def safe_stats(values):
    if not values:
        return {
            "mean": float("nan"),
            "median": float("nan"),
            "p95": float("nan"),
            "min": float("nan"),
            "max": float("nan"),
        }

    return {
        "mean": statistics.mean(values),
        "median": statistics.median(values),
        "p95": percentile(values, 95),
        "min": min(values),
        "max": max(values),
    }


def make_log_path():
    ensure_dir(LOG_DIR)
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    return os.path.join(LOG_DIR, f"{ts}_spike_instant_peak_timing_quiet.csv")


def make_summary_path(csv_path):
    root, _ = os.path.splitext(csv_path)
    return root + "_summary.txt"


# ============================================================
# INSTANTANEOUS SINGLE-SWEEP PEAK READ
# ============================================================

def single_sweep_peak_instant(sa, center_hz, span_hz):
    """
    Perform one instantaneous sweep and return timing + peak.

    This is NOT max hold.

    It assumes Spike is already centred/span/RBW/VBW configured.

    It does:
        :INIT:IMM
        *OPC?
        :TRAC:DATA?

    Then finds the max bin from that one returned trace.
    """

    request_start_s = time.monotonic()

    sa._send(":INIT:IMM")
    sa._query("*OPC?")

    opc_return_s = time.monotonic()

    raw = sa._query(":TRAC:DATA?")
    data_return_s = time.monotonic()

    amps = [float(x) for x in raw.split(",") if x]

    if not amps:
        raise RuntimeError("Empty trace from Spike")

    peak_idx = max(range(len(amps)), key=lambda i: amps[i])
    peak_dbm = amps[peak_idx]

    n = len(amps)

    if n > 1:
        bin_hz = span_hz / (n - 1)
    else:
        bin_hz = 0.0

    start_hz = center_hz - span_hz / 2.0
    peak_hz = start_hz + peak_idx * bin_hz

    return {
        "request_start_s": request_start_s,
        "opc_return_s": opc_return_s,
        "measurement_return_s": data_return_s,
        "read_time_s": data_return_s - request_start_s,
        "sweep_wait_s": opc_return_s - request_start_s,
        "trace_read_parse_s": data_return_s - opc_return_s,
        "peak_frequency_hz": peak_hz,
        "power_dBm": peak_dbm,
        "trace_points": n,
    }


# ============================================================
# SUMMARY
# ============================================================

def build_summary(rows, csv_path, center_hz, span_hz):
    if not rows:
        return "[TEST] No samples logged."

    total_elapsed_s = rows[-1]["elapsed_s"]
    sample_count = len(rows)
    avg_rate_hz = sample_count / total_elapsed_s if total_elapsed_s > 0 else float("nan")

    dts = [
        r["return_to_return_dt_s"]
        for r in rows
        if r["return_to_return_dt_s"] is not None
    ]

    read_times = [r["read_time_s"] for r in rows]
    sweep_waits = [r["sweep_wait_s"] for r in rows]
    trace_times = [r["trace_read_parse_s"] for r in rows]
    powers = [r["power_dBm"] for r in rows]

    dt_stats = safe_stats(dts)
    read_stats = safe_stats(read_times)
    sweep_stats = safe_stats(sweep_waits)
    trace_stats = safe_stats(trace_times)
    power_stats = safe_stats(powers)

    gaps_025 = sum(1 for x in dts if x > 0.25)
    gaps_050 = sum(1 for x in dts if x > 0.50)
    gaps_100 = sum(1 for x in dts if x > 1.00)
    gaps_200 = sum(1 for x in dts if x > 2.00)

    bucket_counts = {}
    for r in rows:
        bucket = int(r["elapsed_s"] // 10) * 10
        bucket_counts[bucket] = bucket_counts.get(bucket, 0) + 1

    lines = []

    lines.append("============================================================")
    lines.append(" Spike instantaneous peak timing test - QUIET")
    lines.append("============================================================")
    lines.append("")
    lines.append(f"CSV log:                    {csv_path}")
    lines.append(f"Centre frequency:           {center_hz / 1e6:.6f} MHz")
    lines.append(f"Span:                       {span_hz:.0f} Hz")
    lines.append(f"Measurement type:           instantaneous single-sweep peak")
    lines.append(f"Max hold:                   NO")
    lines.append(f"Retune/configure freq:      NO")
    lines.append("")
    lines.append("SUMMARY")
    lines.append("------------------------------------------------------------")
    lines.append(f"Samples logged:             {sample_count}")
    lines.append(f"Elapsed time:               {total_elapsed_s:.3f} s")
    lines.append(f"Average sample rate:        {avg_rate_hz:.3f} Hz")
    lines.append("")
    lines.append("Return-to-return spacing:")
    lines.append(f"    mean:                   {dt_stats['mean']:.6f} s")
    lines.append(f"    median:                 {dt_stats['median']:.6f} s")
    lines.append(f"    p95:                    {dt_stats['p95']:.6f} s")
    lines.append(f"    min:                    {dt_stats['min']:.6f} s")
    lines.append(f"    max:                    {dt_stats['max']:.6f} s")
    lines.append("")
    lines.append("Single read time:")
    lines.append(f"    mean:                   {read_stats['mean']:.6f} s")
    lines.append(f"    median:                 {read_stats['median']:.6f} s")
    lines.append(f"    p95:                    {read_stats['p95']:.6f} s")
    lines.append(f"    min:                    {read_stats['min']:.6f} s")
    lines.append(f"    max:                    {read_stats['max']:.6f} s")
    lines.append("")
    lines.append("Breakdown:")
    lines.append(f"    sweep wait median:      {sweep_stats['median']:.6f} s")
    lines.append(f"    trace read median:      {trace_stats['median']:.6f} s")
    lines.append("")
    lines.append("Large gaps:")
    lines.append(f"    gaps > 0.25 s:          {gaps_025}")
    lines.append(f"    gaps > 0.50 s:          {gaps_050}")
    lines.append(f"    gaps > 1.00 s:          {gaps_100}")
    lines.append(f"    gaps > 2.00 s:          {gaps_200}")
    lines.append("")
    lines.append("Power:")
    lines.append(f"    min:                    {power_stats['min']:.2f} dBm")
    lines.append(f"    median:                 {power_stats['median']:.2f} dBm")
    lines.append(f"    max:                    {power_stats['max']:.2f} dBm")
    lines.append("")
    lines.append("Samples per 10-second bucket:")

    for bucket in sorted(bucket_counts):
        lines.append(f"    {bucket:3d} to {bucket + 10:3d} s:       {bucket_counts[bucket]} samples")

    lines.append("")
    lines.append("Interpretation:")
    lines.append("    2 Hz or better is already roughly equivalent to 2-degree steps.")
    lines.append("    5 Hz is excellent.")
    lines.append("    10 Hz is luxury mode.")
    lines.append("    Repeated multi-second gaps are the main thing to worry about.")
    lines.append("")

    return "\n".join(lines)


# ============================================================
# MAIN
# ============================================================

def main():
    print("")
    print("============================================================")
    print(" Spike instantaneous peak timing test - QUIET")
    print("============================================================")
    print("")

    csv_path = make_log_path()
    summary_path = make_summary_path(csv_path)

    print(f"Script folder:              {SCRIPT_DIR}")
    print(f"Driver folder:              {DRIVER_DIR}")
    print(f"Duration:                   {TEST_DURATION_S:.1f} s")
    print(f"Wait after sample:          {WAIT_AFTER_SAMPLE_S:.3f} s")
    print("Measurement type:           instantaneous single-sweep peak")
    print("Max hold:                   NO")
    print("Retune/configure freq:      NO")
    print(f"CSV log:                    {csv_path}")
    print(f"Summary log:                {summary_path}")
    print("")

    if SUPPRESS_DRIVER_PRINTS:
        with redirect_stdout(io.StringIO()):
            sa = BB60Spike(SPIKE_CFG)
    else:
        sa = BB60Spike(SPIKE_CFG)

    center_hz = float(sa._query(":FREQ:CENT?"))
    span_hz = float(sa._query(":FREQ:SPAN?"))

    print(f"[Spike] Current centre:     {center_hz / 1e6:.6f} MHz")
    print(f"[Spike] Current span:       {span_hz:.0f} Hz")
    print("")

    # Do not retune frequency/span/RBW/VBW.
    # Only force instantaneous WRITE trace mode so this is not max hold.
    sa._send(":INIT:CONT OFF")
    sa._send(":AVER:STAT OFF")
    sa._send(":DISP:TRAC:AVER OFF")
    sa._send(":TRAC:TYPE WRIT")
    sa._send(":TRAC:CLE")
    sa._query("*OPC?")

    if THROW_AWAY_FIRST_SWEEP:
        single_sweep_peak_instant(sa, center_hz, span_hz)

    print(f"[TEST] Running quietly for {TEST_DURATION_S:.1f} seconds...")
    print("")

    rows = []
    previous_return_s = None
    t0 = time.monotonic()
    sample_number = 0

    try:
        while True:
            if time.monotonic() - t0 >= TEST_DURATION_S:
                break

            result = single_sweep_peak_instant(sa, center_hz, span_hz)

            measurement_return_s = result["measurement_return_s"]
            elapsed_s = measurement_return_s - t0

            if previous_return_s is None:
                return_to_return_dt_s = None
            else:
                return_to_return_dt_s = measurement_return_s - previous_return_s

            previous_return_s = measurement_return_s

            rows.append({
                "sample_number": sample_number,
                "timestamp_iso": datetime.now().isoformat(timespec="milliseconds"),
                "request_start_s": result["request_start_s"],
                "opc_return_s": result["opc_return_s"],
                "measurement_return_s": result["measurement_return_s"],
                "elapsed_s": elapsed_s,
                "read_time_s": result["read_time_s"],
                "sweep_wait_s": result["sweep_wait_s"],
                "trace_read_parse_s": result["trace_read_parse_s"],
                "return_to_return_dt_s": return_to_return_dt_s,
                "peak_frequency_hz": result["peak_frequency_hz"],
                "power_dBm": result["power_dBm"],
                "trace_points": result["trace_points"],
            })

            sample_number += 1

            if WAIT_AFTER_SAMPLE_S > 0:
                time.sleep(WAIT_AFTER_SAMPLE_S)

    except KeyboardInterrupt:
        print("[TEST] Stopped early by user.")

    finally:
        fieldnames = [
            "sample_number",
            "timestamp_iso",
            "request_start_s",
            "opc_return_s",
            "measurement_return_s",
            "elapsed_s",
            "read_time_s",
            "sweep_wait_s",
            "trace_read_parse_s",
            "return_to_return_dt_s",
            "peak_frequency_hz",
            "power_dBm",
            "trace_points",
        ]

        with open(csv_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    summary_text = build_summary(rows, csv_path, center_hz, span_hz)

    with open(summary_path, "w") as f:
        f.write(summary_text)

    print(summary_text)
    print(f"Summary saved:              {summary_path}")
    print("Done.")


if __name__ == "__main__":
    main()
import socket
import os
import time
import zipfile
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime


# ---------------------------------------------------------
# SCPI HELPERS
# ---------------------------------------------------------
def scpi_send(sock, cmd: str):
    print(f"[SCPI SEND] {cmd}")
    sock.send((cmd + "\n").encode())


def scpi_recv(sock) -> str:
    resp = sock.recv(1024 * 1024).decode().strip()
    print(f"[SCPI RECV] {resp[:200]}{'...' if len(resp) > 200 else ''}")
    return resp


def scpi_query(sock, cmd: str) -> str:
    scpi_send(sock, cmd)
    return scpi_recv(sock)


# ---------------------------------------------------------
# LOCAL MAXIMA DETECTION
# ---------------------------------------------------------
def find_local_maxima(freqs, amps, min_spacing_hz=50_000):
    """
    Returns (freq, amp) pairs for local maxima.
    """
    amps = np.array(amps)
    freqs = np.array(freqs)

    # Basic local max detection
    maxima_idx = np.where((amps[1:-1] > amps[:-2]) & (amps[1:-1] > amps[2:]))[0] + 1

    maxima = list(zip(freqs[maxima_idx], amps[maxima_idx]))
    print(f"[SPURS] Raw maxima found: {len(maxima)}")

    # Apply minimum frequency spacing
    filtered = []
    last_freq = -1e12

    for f, a in maxima:
        if (f - last_freq) >= min_spacing_hz:
            filtered.append((f, a))
            last_freq = f

    print(f"[SPURS] Filtered maxima after spacing: {len(filtered)}")
    return filtered


# ---------------------------------------------------------
# COMPRESS TRACE (Δf + rounded amplitude)
# ---------------------------------------------------------
def write_delta_trace_zip(out_zip_path, freqs, amps):
    print(f"[ZIP] Creating simplified delta trace CSV...")

    start_freq = freqs[0]
    delta_fs = np.diff(freqs)
    amps_r = np.round(amps, 1)

    # Build CSV text
    lines = [f"Start_freq_Hz,{start_freq}"]
    lines.append("Delta_Hz,Amplitude_dBm")

    # First delta = 0
    lines.append(f"0,{amps_r[0]}")

    for df, a in zip(delta_fs, amps_r[1:]):
        lines.append(f"{df:.2f},{a}")

    csv_text = "\n".join(lines)

    # Now zip it
    with zipfile.ZipFile(out_zip_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr("trace_simplified.csv", csv_text)

    print(f"[ZIP] Wrote compressed trace → {out_zip_path}")


# ---------------------------------------------------------
# MAIN SCRIPT
# ---------------------------------------------------------
def main():
    print("[START] Beginning script…")

    # -----------------------------------------------------
    # Make timestamped folder
    # -----------------------------------------------------
    tstamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    outdir = os.path.join("Signalhound_BBD60_data", tstamp)
    folder_tag = tstamp  # appended to all filenames

    print(f"[DIR] Creating folder: {outdir}")
    os.makedirs(outdir, exist_ok=True)

    # File paths
    zip_path = os.path.join(outdir, f"trace__{folder_tag}.zip")
    spur_path = os.path.join(outdir, f"spurs__{folder_tag}.csv")
    screenshot_path = os.path.join(outdir, f"screenshot__{folder_tag}.png")
    plot_path = os.path.join(outdir, f"trace_plot__{folder_tag}.png")

    # -----------------------------------------------------
    # Connect to Spike
    # -----------------------------------------------------
    print("[NETWORK] Opening socket to Spike…")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(("127.0.0.1", 5025))
    print("[NETWORK] Connected to Spike.")

    # -----------------------------------------------------
    # Stop continuous + trigger sweep
    # -----------------------------------------------------
    scpi_send(sock, ":INIT:CONT OFF")
    resp = scpi_query(sock, ":INIT; *OPC?")

    # -----------------------------------------------------
    # Get center + span
    # -----------------------------------------------------
    cf = float(scpi_query(sock, ":FREQ:CENT?"))
    sp = float(scpi_query(sock, ":FREQ:SPAN?"))
    print(f"[TRACE] Center = {cf}, Span = {sp}")

    # Compute frequency array
    start_f = cf - sp / 2
    stop_f  = cf + sp / 2

    # -----------------------------------------------------
    # Get trace data
    # -----------------------------------------------------
    print("[TRACE] Getting trace data…")
    trace_raw = scpi_query(sock, ":TRAC:DATA?")
    amps = np.array([float(v) for v in trace_raw.split(",")])
    print(f"[TRACE] Received {len(amps)} points.")

    freqs = np.linspace(start_f, stop_f, len(amps))

    # -----------------------------------------------------
    # COMPRESSED ZIP FILE
    # -----------------------------------------------------
    write_delta_trace_zip(zip_path, freqs, amps)

    # -----------------------------------------------------
    # SPUR FINDING
    # -----------------------------------------------------
    print("[SPURS] Detecting local maxima…")
    maxima = find_local_maxima(freqs, amps)

    print(f"[FILE] Saving spur table → {spur_path}")
    with open(spur_path, "w") as f:
        f.write("Freq_Hz,Amplitude_dBm\n")
        for f_hz, a_db in maxima:
            f.write(f"{f_hz},{a_db:.1f}\n")

    # -----------------------------------------------------
    # SCREENSHOT
    # -----------------------------------------------------
    print("[SCREENSHOT] Saving screenshot…")
    abs_png = os.path.abspath(screenshot_path)
    scpi_send(sock, f'SYST:IMAG:SAV "{abs_png}"')
    print(f"[SCREENSHOT] Saved → {abs_png}")

    # -----------------------------------------------------
    # PLOT
    # -----------------------------------------------------
    print("[PLOT] Plotting trace…")
    plt.figure(figsize=(10,4))
    plt.plot(freqs, amps)
    plt.title("Trace")
    plt.xlabel("Frequency (Hz)")
    plt.ylabel("Amplitude (dBm)")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(plot_path)
    plt.close()
    print(f"[PLOT] Saved → {plot_path}")

    print("[DONE] All tasks complete.")


# ---------------------------------------------------------
if __name__ == "__main__":
    main()

import socket
import os
import csv
import time
import random
from datetime import datetime, timedelta


# ===================== USER SETTINGS =====================

SPIKE_HOST = "127.0.0.1"
SPIKE_PORT = 5025

CENTER_FREQ_HZ = 2.399978967e9
SPAN_HZ        = 100_000
RBW_HZ         = 10_000
VBW_HZ         = 10_000

SHIFT_DURATION  = timedelta(hours=4)

BASE_LOG_DIR = r"C:\DAMspySandbox\DAMspy\DAMspy_logs\spec_an_freq_amp_histogram"
DUTinfo = r"Hendrix_EV3-7_on_mobile_90deg adaptor_to_back_ch0_Rx_Horn_WR340"

# ===================== SPIKE SCPI =====================

class BB60Spike:
    def __init__(self, host, port):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((host, port))
        print(f"[Spike] Connected to {host}:{port}")

        self._send(":DISP:ENAB OFF")
        print("[Spike] GUI disabled (SCPI ownership asserted)")

    def _send(self, cmd):
        self.sock.send((cmd + "\n").encode())

    def _query(self, cmd):
        self._send(cmd)
        return self.sock.recv(1024 * 1024).decode().strip()

    def assert_measurement_state(self):
        self._send(":INIT:CONT OFF")
        self._send(":DET POS")
        self._send(":AVER:STAT OFF")
        self._send(":DISP:TRAC:AVER OFF")
        self._send(f":BAND:RES {RBW_HZ}")
        self._send(f":BAND:VID {VBW_HZ}")
        self._send(f":FREQ:CENT {CENTER_FREQ_HZ}")
        self._send(f":FREQ:SPAN {SPAN_HZ}")

    def single_sweep_peak(self):
        self._send(":INIT:IMM")
        self._query("*OPC?")

        raw = self._query(":TRAC:DATA?")
        amps = [float(x) for x in raw.split(",") if x]

        if not amps:
            raise RuntimeError("Empty trace from Spike")

        peak_idx = max(range(len(amps)), key=lambda i: amps[i])
        peak_dbm = amps[peak_idx]

        cf = float(self._query(":FREQ:CENT?"))
        sp = float(self._query(":FREQ:SPAN?"))
        n  = len(amps)

        bin_hz   = sp / (n - 1)
        start_hz = cf - sp / 2.0
        peak_hz  = start_hz + peak_idx * bin_hz

        return peak_hz, peak_dbm


# ===================== LOGGING =====================

def ensure_dir(path):
    os.makedirs(path, exist_ok=True)

def new_run_folder():
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    # Sanitize DUTinfo for Windows-safe folder names
    safe_dut = "".join(c if c.isalnum() or c in "-_." else "_" for c in DUTinfo)

    folder_name = f"{ts}_{safe_dut}"
    path = os.path.join(BASE_LOG_DIR, folder_name)

    ensure_dir(path)
    return path


def open_shift_csv(folder, shift_idx):
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    fname = f"{ts}_shift_{shift_idx}.csv"
    path = os.path.join(folder, fname)

    f = open(path, "w", newline="")
    w = csv.writer(f)
    w.writerow([
        "time_elapsed_s",
        "frequency_hz",
        "amplitude_dbm",
        "random_sleep_s"
    ])
    f.flush()

    return f, w, path


# ===================== MAIN =====================

def main():
    print("[CW LOGGER] Starting pseudorandom CW logger")

    ensure_dir(BASE_LOG_DIR)
    run_dir = new_run_folder()
    print(f"[CW LOGGER] Run directory: {run_dir}")

    sa = BB60Spike(SPIKE_HOST, SPIKE_PORT)

    shift_idx   = 1
    shift_start = datetime.now()
    csv_file, writer, csv_path = open_shift_csv(run_dir, shift_idx)

    print(f"[CW LOGGER] Shift {shift_idx} → {csv_path}")

    # High precision monotonic timer
    start_time = time.perf_counter()

    try:
        while True:
            now = datetime.now()
            elapsed = time.perf_counter() - start_time

            # Rotate file every 4 hours
            if now - shift_start >= SHIFT_DURATION:
                csv_file.close()
                shift_idx += 1
                shift_start = now
                csv_file, writer, csv_path = open_shift_csv(run_dir, shift_idx)
                print(f"[CW LOGGER] Shift {shift_idx} → {csv_path}")

            # Reassert state (GUI-safe)
            sa.assert_measurement_state()

            # Throwaway sweep
            sa.single_sweep_peak()

            # Measurement sweep
            pk_freq, pk_dbm = sa.single_sweep_peak()

            # Random wait between 0–1 seconds
            rand_sleep = random.uniform(0, 1)
            time.sleep(rand_sleep)

            # Log
            writer.writerow([
                f"{elapsed:.6f}",
                f"{pk_freq:.3f}",
                f"{pk_dbm:.3f}",
                f"{rand_sleep:.6f}"
            ])
            csv_file.flush()

            print(
                f"[CW] {elapsed:10.3f}s | "
                f"{pk_freq/1e6:.6f} MHz | "
                f"{pk_dbm:7.2f} dBm | "
                f"sleep {rand_sleep:5.3f}s"
            )

    except KeyboardInterrupt:
        print("\n[CW LOGGER] Stopped by user")

    finally:
        try:
            csv_file.close()
        except Exception:
            pass
        print("[CW LOGGER] Exit")


if __name__ == "__main__":
    main()

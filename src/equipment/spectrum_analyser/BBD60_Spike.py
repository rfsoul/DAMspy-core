# BBD60_Spike_OptionA_MaxHoldOnly.py
# Option A: Raw dBm Max-Hold only. No field strength, no screenshots.
# Produces stable envelope to compare with Spike GUI MAX HOLD.

import socket
import os
import numpy as np
import time
import matplotlib.pyplot as plt
import csv
import statistics
import math



class BB60Spike:
    def __init__(self, cfg):
        host = cfg.get("host", "127.0.0.1")
        port = cfg.get("port", 5025)

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((host, port))
        print(f"[BB60Spike] Connected to Spike at {host}:{port}")

        # Disable GUI immediately for safe SCPI-only control
        self._send(":DISP:ENAB OFF")
        print("[Spike] GUI disabled (SCPI safe mode).")

    # ---------------------------------------------------------
    # SCPI helpers
    # ---------------------------------------------------------
    def _send(self, cmd: str):
        self.sock.send((cmd + "\n").encode())

    def _query(self, cmd: str) -> str:
        self._send(cmd)
        return self.sock.recv(1024 * 1024).decode().strip()

    # ---------------------------------------------------------
    # SCPI single sweep (PEAK, 120k RBW/VBW)
    # ---------------------------------------------------------
    def _scpi_config(self):
        """ Configure Spike for EMC-style PEAK trace """
        self._send(":INIT:CONT OFF")     # SCPI sweep engine takes over
        self._send(":DET POS")           # Peak detector
        self._send(":AVER:STAT OFF")     # No averaging
        self._send(":DISP:TRAC:AVER OFF")
        self._send(":BAND:RES 120000")   # CISPR RBW
        self._send(":BAND:VID 120000")   # Match VBW
        self._send(":TRAC:TYPE WRIT")    # Clear/write mode

    def get_trace(self):
        """ Return one single-peak sweep (dBm trace) """
        self._scpi_config()

        self._send(":INIT:IMM")
        self._query("*OPC?")

        # Frequency axis
        cf = float(self._query(":FREQ:CENT?"))
        sp = float(self._query(":FREQ:SPAN?"))

        # Amplitudes
        raw = self._query(":TRAC:DATA?")
        amps = np.array([float(x) for x in raw.split(",") if x])

        freqs = np.linspace(cf - sp/2, cf + sp/2, len(amps))
        return freqs, amps

    # ---------------------------------------------------------
    # Max-Hold Engine
    # ---------------------------------------------------------
    def get_trace_max_hold(self, seconds=2.0):
        """
        Perform max-hold accumulation over several seconds.
        Returns (freqs[], maxamps_dBm[]).
        """
        start = time.time()
        max_trace = None
        freqs = None

        while time.time() - start < seconds:
            f, a = self.get_trace()
            if max_trace is None:
                max_trace = a.copy()
                freqs = f.copy()
            else:
                max_trace = np.maximum(max_trace, a)

        return freqs, max_trace

    # ---------------------------------------------------------
    # Save CSV + Plot
    # ---------------------------------------------------------
    def save_maxhold_csv(self, path, freqs, amps):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write("Freq_Hz,dBm\n")
            for fr, am in zip(freqs, amps):
                f.write(f"{fr},{am}\n")
        print(f"[Spike] MaxHold CSV saved → {path}")

    def save_maxhold_plot(self, path, freqs, amps):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        plt.figure(figsize=(12, 6))
        plt.plot(freqs, amps)
        plt.xlabel("Frequency (Hz)")
        plt.ylabel("Amplitude (dBm)")
        plt.title("Max-Hold Trace (Python SCPI)")
        plt.grid(True)
        plt.tight_layout()
        plt.savefig(path)
        plt.close()
        print(f"[Spike] MaxHold plot saved → {path}")

    def configure_narrowband(self, center_hz: float, span_hz: float):
        """
        Configure Spike as a narrowband tuned receiver.
        """
        self._send(":INIT:CONT OFF")
        self._send(":DET POS")              # Peak detector
        self._send(":AVER:STAT OFF")
        self._send(":DISP:TRAC:AVER OFF")
        self._send(f":FREQ:CENT {center_hz}")
        self._send(f":FREQ:SPAN {span_hz}")


    def read_peak_maxhold(self, hold_s: float):
        """
        Perform a MAX HOLD measurement by accumulating discrete sweeps
        over a wall-clock time window.

        This implementation is derived directly from the known-good
        standalone reference script.

        Assumptions:
        - Centre frequency, span, RBW, and VBW are already configured.
        - MAX HOLD accumulation is visible on the GUI.
        - The value returned matches exactly what the user sees on screen.

        Parameters
        ----------
        hold_s : float
            Hold window duration in seconds.

        Returns
        -------
        (peak_freq_hz, peak_dbm)
        """

        # Ensure no continuous acquisition
        self._send(":INIT:CONT OFF")

        # Reset trace cleanly in WRITE mode
        self._send(":TRAC:TYPE WRIT")
        self._send(":TRAC:CLE")

        # Arm MAX HOLD
        self._send(":TRAC:TYPE MAX")

        # Optional sanity check (matches reference)
        trace_type = self._query(":TRAC:TYPE?")
        # Could log this if desired

        t_start = time.monotonic()
        sweep_count = 0

        # Time-gated discrete sweeps
        for _ in range(600):  # safety cap only
            elapsed = time.monotonic() - t_start
            print(f"[MAXH] t = {elapsed:0.3f} s")
            if elapsed >= hold_s:
                break

            # Trigger one sweep (reference behaviour)
            self._send(":INIT:IMM")
            self._query("*OPC?")

            sweep_count += 1

        # Read peak from the accumulated MAX HOLD trace
        self._send(":CALC:MARK:MAX")
        peak_dbm = float(self._query(":CALC:MARK:Y?"))
        peak_hz = float(self._query(":CALC:MARK:X?"))

        return peak_hz, peak_dbm

    def read_peak_gui_maxhold(self, hold_s):
        """
        GUI-accumulated MAX HOLD.
        Allows Spike to free-run and accumulate MAX HOLD for hold_s seconds,
        then reads back the peak exactly as displayed.
        """

        # Select Trace 1 explicitly
        self._send(":TRAC1:SEL")

        # Ensure continuous acquisition
        self._send(":INIT:CONT OFF")

        # Reset trace in WRITE mode
        self._send(":TRAC:TYPE WRIT")
        self._send(":TRAC:CLE")

        # One or two sweeps to settle
        for _ in range(2):
            self._send(":INIT:IMM")
            self._query("*OPC?")

        # Switch to MAX HOLD
        self._send(":TRAC:TYPE MAX")

        # Enable continuous sweep so GUI accumulates
        self._send(":INIT:CONT ON")

        t_start = time.monotonic()
        while True:
            elapsed = time.monotonic() - t_start
            print(f"[GUI MAXH] accumulating t = {elapsed:0.2f} s")
            if elapsed >= hold_s:
                break
            time.sleep(0.25)  # human-visible cadence

        # Freeze acquisition
        self._send(":INIT:CONT OFF")

        # Read peak marker
        self._send(":CALC:MARK:MAX")
        peak_dbm = float(self._query(":CALC:MARK:Y?"))
        peak_hz = float(self._query(":CALC:MARK:X?"))

        return peak_hz, peak_dbm

    def _single_sweep_peak(self):
        """
        Perform one sweep and return (peak_freq_hz, peak_dbm).
        """
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

        bin_hz = sp / (n - 1) if n > 1 else 0.0
        start_hz = cf - sp / 2.0
        peak_hz = start_hz + peak_idx * bin_hz

        return peak_hz, peak_dbm

    def read_peak_median(
        self,
        sweeps: int = 3,
        prev_dbm: float | None = None,
        max_jump_db: float | None = None,
        retries_on_jump: int = 0
    ):
        """
        Median-of-N narrowband peak measurement with optional jump guard.
        Returns (peak_freq_hz, median_peak_dbm).
        """

        def measure_block():
            vals = []
            for _ in range(max(1, int(sweeps))):
                _, dbm = self._single_sweep_peak()
                if isinstance(dbm, (int, float)) and not math.isnan(dbm):
                    vals.append(dbm)
            return statistics.median(vals) if vals else float("nan")

        median_dbm = measure_block()
        tries = 0

        if prev_dbm is not None and max_jump_db is not None:
            while (
                tries < retries_on_jump
                and not math.isnan(median_dbm)
                and abs(median_dbm - prev_dbm) > max_jump_db
            ):
                tries += 1
                print(
                    f"[Spike] Large jump {median_dbm:.1f} dB vs {prev_dbm:.1f} dB — retry {tries}"
                )
                extra = [median_dbm] + [
                    self._single_sweep_peak()[1]
                    for _ in range(max(1, sweeps))
                ]
                extra = [v for v in extra if isinstance(v, (int, float))]
                median_dbm = statistics.median(extra) if extra else median_dbm

        pk_freq, _ = self._single_sweep_peak()
        return pk_freq, median_dbm

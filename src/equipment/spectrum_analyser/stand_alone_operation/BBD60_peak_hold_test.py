import socket
import time

SPIKE_HOST = "127.0.0.1"
SPIKE_PORT = 5025


class BB60Spike:
    def __init__(self, host, port):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((host, port))
        print(f"[Spike] Connected to {host}:{port}")

        # Force SCPI ownership
        self._send(":DISP:ENAB OFF")
        print("[Spike] GUI disabled (SCPI ownership asserted)")

    def _send(self, cmd):
        self.sock.send((cmd + "\n").encode())

    def _query(self, cmd):
        self._send(cmd)
        return self.sock.recv(1024 * 1024).decode().strip()

    def single_sweep(self):
        self._send(":INIT:IMM")
        self._query("*OPC?")


def main():
    sa = BB60Spike(SPIKE_HOST, SPIKE_PORT)

    print("\n==============================")
    print(" Spike Deterministic MAX HOLD ")
    print("==============================")

    sa._send(":TRAC1:SEL")
    sa._send(":INIT:CONT OFF")

    # -----------------------------
    # STAGE 1: WRITE MODE
    # -----------------------------
    print("\n--- STAGE 1: WRITE MODE ---")
    sa._send(":TRAC:TYPE WRIT")
    sa._send(":TRAC:CLE")

    print("[STATE] Trace = WRITE")

    for i in range(1, 3):
        print(f"[WRITE] Sweep {i} / 2")
        sa.single_sweep()

    # -----------------------------
    # STAGE 2: MAX HOLD MODE
    # -----------------------------
    print("\n--- STAGE 2: MAX HOLD MODE ---")
    sa._send(":TRAC:TYPE MAX")

    trace_type = sa._query(":TRAC:TYPE?")
    print(f"[STATE] Trace type = {trace_type}")



    hold_seconds = 1.0

    t_start = time.monotonic()

    sweep_count = 0

    for i in range(600):
        elapsed = time.monotonic() - t_start
        print(f"[MAXH] t = {elapsed:0.3f} s")

        if elapsed >= hold_seconds:
            break

        sa.single_sweep()  # no OPC in MAX HOLD
        sweep_count += 1

    print(f"[MAXH] Done. Total sweeps = {sweep_count}")

    # -----------------------------
    # STAGE 3: READ PEAK
    # -----------------------------
    print("\n--- STAGE 3: READ PEAK ---")
    sa._send(":CALC:MARK:MAX")

    peak_dbm = float(sa._query(":CALC:MARK:Y?"))
    peak_hz  = float(sa._query(":CALC:MARK:X?"))

    print(f"[RESULT] Peak level     = {peak_dbm:.2f} dBm")
    print(f"[RESULT] Peak frequency = {peak_hz:.3f} Hz")

    print("\n=== TEST COMPLETE ===")


if __name__ == "__main__":
    main()

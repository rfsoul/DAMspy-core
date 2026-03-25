# RotateElevation_ignore_limits.py
# Minimal "move elevation" script that ignores limit flags and just tries to move.

import time
import serial
import re

PORT = "COM3"        # <- your port
BAUD = 57600
AXIS = "X"           # elevation axis
STEPS_PER_DEG = 320  # 320 steps/° on X


def send(ser, s):
    ser.write((s + '\r').encode('ascii'))
    time.sleep(0.02)
    resp = ser.read_all().decode('ascii', errors='ignore')
    print(f"{s} -> {resp.strip()}")
    return resp


def read_counts(ser, axis=AXIS) -> int:
    """Read back internal step counter using the 'm' command."""
    resp = send(ser, f"{axis}0m")
    nums = re.findall(r'[-+]?\d+', resp)
    if nums:
        try:
            return int(nums[-1])
        except ValueError:
            pass
    return 0


def move_elevation_rel(deg: float):
    """
    Relative move by 'deg' degrees on the elevation axis.
    ALWAYS uses RN (ignore switches) and does not interpret flags.
    """
    steps = int(round(deg * STEPS_PER_DEG))
    print(f"\nRequest: {deg:+.2f}° -> {steps:+d} steps")

    if steps == 0:
        print("No move requested (0 steps).")
        return True

    with serial.Serial(PORT, BAUD, timeout=0.2) as ser:
        # Basic init for X (same as your working sequence)
        if AXIS == "X":
            for cmd in ["X0P3,163,81,10", "X0H4", "X0B500", "X0E3000", "X0S8"]:
                send(ser, cmd)

        start_counts = read_counts(ser, AXIS)
        print(f"Start counts: {start_counts}")

        # Force RN (ignore switches) regardless of anything
        move_prefix = f"{AXIS}0RN"
        cmd = f"{move_prefix}{steps:+d}"
        send(ser, cmd)

        # Just wait based on step count – no interpretation of status flags
        est_time = max(3.0, 0.0006 * abs(steps))  # rough heuristic
        t0 = time.time()
        while time.time() - t0 < est_time:
            # Optional: poll & print status, but don't act on it
            resp = send(ser, f"{AXIS}0")
            # Comment out the next line if it's too spammy
            print("STATUS:", resp.strip())
            time.sleep(0.1)

        end_counts = read_counts(ser, AXIS)
        print(f"End   counts: {end_counts}")
        print(f"Delta counts: {end_counts - start_counts}")

        return True


if __name__ == "__main__":
    time.sleep(2)
    # Try a small move first
    move_elevation_rel(10.0)
    # move_elevation_rel(-10.0)

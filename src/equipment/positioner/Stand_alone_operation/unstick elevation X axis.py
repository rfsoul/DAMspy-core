
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
unstick_elevation_abs.py
Clears a latched limit on the Elevation axis (X) and makes a visible move so you can confirm.
Run directly in PyCharm (edit SETTINGS below).

Behavior
- Initializes X axis with safe speeds/currents
- Reads limit inputs (X0I1 = home/CW, X0I3 = max/CCW)
- Reads current step count (X0m)
- Issues an ABSOLUTE move X0M<steps> away from the active switch (~±8° by default)
- After the limit clears, performs a visible obey‑limits move (e.g., −20°)
"""

# ================== SETTINGS (EDIT THESE) ==================
PORT            = "COM3"     # your motion controller COM port
BAUD            = 57600
AXIS            = "X"        # Elevation
STEPS_PER_DEG   = 320        # from your RotateElevation script
BACKOFF_DEG     = 8.0        # how far to move off the tripped switch (ABSOLUTE)
VISIBLE_MOVE_DEG= -20.0      # obey‑limits move after clearing (0 to disable)
# ===========================================================

import time, re
import serial

def tx(ser, s, wait=0.05, echo=True):
    ser.write((s + "\r").encode("ascii"))
    time.sleep(wait)
    data = ser.read_all().decode("ascii", errors="ignore")
    if echo:
        print(f"{s} -> {data.strip()}")
    return data

def init_axis(ser, axis):
    # Conservative init for safe motion
    for c in [
        "GGN-0cz00",        # global clear/enable style (safe)
        f"{axis}0H4",       # 1/16 microstep
        f"{axis}0P3,200,100,10",  # drive/hold current example
        f"{axis}0B100",     # begin speed (slow)
        f"{axis}0E1200",    # end speed (slowish)
        f"{axis}0S7",       # slope (gentle)
    ]:
        tx(ser, c)

def poll_finished(ser, axis, timeout=20.0):
    t0 = time.time()
    while time.time() - t0 < timeout:
        st = tx(ser, f"{axis}0", echo=False)
        if "f" in st.lower():
            return True
        time.sleep(0.05)
    print("[WARN] Move did not report finished within timeout")
    return False

def parse_steps(resp: str) -> int:
    # Expect forms like: x0>0000003500  or  x0>-0000002000
    m = re.search(r">([+-]?\d+)", resp.strip())
    if not m:
        raise RuntimeError(f"Couldn't parse steps from: {resp!r}")
    return int(m.group(1))

def main():
    steps_off = int(round(BACKOFF_DEG * STEPS_PER_DEG))
    vis_steps = int(round(VISIBLE_MOVE_DEG * STEPS_PER_DEG))

    print(f"Opening {PORT} @ {BAUD}, axis={AXIS}")
    with serial.Serial(PORT, BAUD, timeout=0.3) as ser:
        init_axis(ser, AXIS)

        # Snapshot status / inputs / position
        st  = tx(ser, f"{AXIS}0");      print("Status:", st.strip())
        i1  = tx(ser, f"{AXIS}0I1");    print("Home sw (I1):", i1.strip(), "(1=not tripped, 0=tripped)")
        i3  = tx(ser, f"{AXIS}0I3");    print("Max  sw (I3):", i3.strip(), "(1=not tripped, 0=tripped)")
        pos = tx(ser, f"{AXIS}0m");     print("Pos:", pos.strip())
        curr = parse_steps(pos)

        # Decide direction
        home_tripped = i1.strip().endswith("0")
        max_tripped  = i3.strip().endswith("0")

        cleared = False
        tried = []

        def do_abs(target):
            print(f"ABS move to {target:+d} steps (~{(target/float(STEPS_PER_DEG)):+.2f}°)")
            tx(ser, f"{AXIS}0M{target:+d}", wait=0.1)
            ok = poll_finished(ser, AXIS)
            st2 = tx(ser, f"{AXIS}0").strip()
            print("Status after abs:", st2)
            return ok and ("L" not in st2)

        # Prefer directed move based on which switch is tripped
        if max_tripped:   # CCW limit hit -> move more negative (toward CW)
            target = curr - steps_off
            tried.append(target)
            if do_abs(target): cleared = True
        if (not cleared) and home_tripped:  # CW/home limit hit -> move more positive (toward CCW)
            target = curr + steps_off
            tried.append(target)
            if do_abs(target): cleared = True

        # Ambiguous: try both ways
        if not cleared:
            for delta in (-steps_off, +steps_off):
                target = curr + delta
                if target in tried: continue
                if do_abs(target):
                    cleared = True
                    break

        if not cleared:
            print("\n[FAIL] Limit still latched. Try increasing BACKOFF_DEG (e.g., 15–30°),")
            print("      or manually wind off the switch slightly, then re-run.\n")
            return

        # Visible obey-limits move (to confirm motion)
        if vis_steps != 0:
            print(f"\nVisible obey-limits move {VISIBLE_MOVE_DEG:+.2f}°")
            tx(ser, f"{AXIS}0RYY{vis_steps:+d}", wait=0.1)
            poll_finished(ser, AXIS)
            print("Final status:", tx(ser, f"{AXIS}0").strip())
            print("Final position:", tx(ser, f"{AXIS}0m").strip())

        print("\nSuccess. Elevation axis should now respond to normal moves.\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted by user.")

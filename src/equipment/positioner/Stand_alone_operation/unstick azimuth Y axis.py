
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
unstick_from_pycharm.py
Run this directly in PyCharm (no command‑line args needed).

What it does
- Opens the motion controller (serial) for the selected AXIS (Y=azimuth, X=elevation)
- Re-initializes the axis (same commands as your working scripts)
- If a LIMIT ("...L") is latched, performs tiny override jogs away from the limit
- Optionally toggles DTR/RTS and sends a short BREAK to clear faults
- After the limit clears, performs a visible obey‑limits move (e.g., -30°) so you can notice it
- Prints status and position after each step

Requires: pyserial  (pip install pyserial)
"""

# ================== SETTINGS (EDIT THESE) ==================
PORT            = "COM3"   # e.g. "COM3"
BAUD            = 57600
AXIS            = "Y"      # "Y" = azimuth, "X" = elevation
# Back-off direction when stuck at MAX limit is usually negative.
# Set to +1 if you know you're at the MIN limit and need to go positive.
BACK_OFF_SIGN   = -1       # +1 or -1
TINY_JOG_DEG    = 0.2      # magnitude of tiny override jogs (deg)
TINY_TRIES      = 6        # how many tiny tries before line toggle/BRK
FALLBACK_JOG_DEG= 1.0      # final larger override jog if still stuck (deg)
POST_MOVE_DEG   = 30.0    # obey‑limits move AFTER clearing the limit (0 to disable)
SHOW_STATUS     = True     # print status/position chatter
# Steps per degree (from your scripts)
STEPS_PER_DEG   = {"Y": 800, "X": 320}
# ===========================================================

import time, sys
import serial

def tx(ser, s, wait=0.05, echo=SHOW_STATUS):
    """Send a command with CR and return any response."""
    ser.write((s + "\r").encode("ascii"))
    time.sleep(wait)
    resp = ser.read_all().decode("ascii", errors="ignore")
    if echo:
        print(f"{s} -> {resp.strip()}")
    return resp

def has_limit(resp: str) -> bool:
    """True if controller status shows a latched limit (e.g., 'y0L')."""
    return "L" in (resp or "")

def init_axis(ser, axis: str):
    """Initialize the axis using the same sequence as your working scripts."""
    for c in [f"{axis}0N-0cz00",
              f"{axis}0B200",
              f"{axis}0P3,200,75,0",
              f"{axis}0H4",
              f"{axis}0E5000",
              f"{axis}0S5"]:
        tx(ser, c)

def poll_done(ser, axis: str, timeout=20.0):
    t0 = time.time()
    while time.time() - t0 < timeout:
        st = tx(ser, f"{axis}0", echo=False)
        if "f" in st.lower():  # finished
            return True
        time.sleep(0.1)
    print("WARN: move did not report 'finished' within timeout")
    return False

def obey_limits_move(ser, axis: str, deg: float):
    steps = int(round(deg * STEPS_PER_DEG[axis]))
    if steps == 0:
        return
    print(f"Obey-limits move {deg:+.2f}°  ->  {axis}0RYY{steps:+d}")
    tx(ser, f"{axis}0RYY{steps:+d}", wait=0.05)
    poll_done(ser, axis)
    if SHOW_STATUS:
        tx(ser, f"{axis}0")
        tx(ser, f"{axis}0m")

def override_move(ser, axis: str, deg: float):
    steps = int(round(deg * STEPS_PER_DEG[axis]))
    if steps == 0:
        steps = BACK_OFF_SIGN * -1  # ensure at least one step in chosen direction
    print(f"Override move {deg:+.3f}°  ->  {axis}0RY{steps:+d}")
    tx(ser, f"{axis}0RY{steps:+d}", wait=0.1)
    if SHOW_STATUS:
        tx(ser, f"{axis}0")
        tx(ser, f"{axis}0m")

def toggle_lines_and_break(ser):
    print("Toggling DTR/RTS and sending short BREAK…")
    try:
        ser.dtr = False; ser.rts = False; time.sleep(0.2)
        ser.dtr = True;  ser.rts = True;  time.sleep(0.2)
        ser.send_break(duration=0.2)
        time.sleep(0.2)
        ser.reset_input_buffer(); ser.reset_output_buffer()
    except Exception as e:
        print("Line toggle/BRK not supported:", e)

def main():
    print(f"Opening {PORT} @ {BAUD}, AXIS={AXIS}")
    with serial.Serial(PORT, BAUD, timeout=0.3) as ser:
        # Initialize
        init_axis(ser, AXIS)
        st = tx(ser, f"{AXIS}0")
        tx(ser, f"{AXIS}0m")

        # If limit, start recovery
        if has_limit(st):
            print("Limit indicated; starting tiny override jogs…")
            tiny = BACK_OFF_SIGN * abs(TINY_JOG_DEG)
            ok = False
            for i in range(1, TINY_TRIES+1):
                print(f"[{i}/{TINY_TRIES}] tiny override {tiny:+.3f}°")
                override_move(ser, AXIS, tiny)
                st = tx(ser, f"{AXIS}0")
                if not has_limit(st):
                    ok = True; print("Limit cleared via tiny jogs."); break
                time.sleep(0.2)

            if not ok:
                # Try line toggle + BREAK, re-init, then tiny jogs again
                toggle_lines_and_break(ser)
                init_axis(ser, AXIS)
                st = tx(ser, f"{AXIS}0")
                if has_limit(st):
                    for i in range(1, TINY_TRIES+1):
                        print(f"[retry {i}/{TINY_TRIES}] tiny override {tiny:+.3f}°")
                        override_move(ser, AXIS, tiny)
                        st = tx(ser, f"{AXIS}0")
                        if not has_limit(st):
                            ok = True; print("Limit cleared after line toggle/BRK."); break
                        time.sleep(0.2)

            # Final fallback: slightly larger override
            if not ok and FALLBACK_JOG_DEG > 0:
                big = BACK_OFF_SIGN * abs(FALLBACK_JOG_DEG)
                print(f"Final fallback: override {big:+.3f}°")
                override_move(ser, AXIS, big)
                st = tx(ser, f"{AXIS}0")
                ok = not has_limit(st)

            if not ok:
                print("Still latched. If safe, manually back off a degree or power-cycle, then re-run.")
                return

        else:
            print("No limit latched; proceeding to visible move.")

        # Visible obey-limits move (only after we are out of limit)
        if abs(POST_MOVE_DEG) > 0:
            obey_limits_move(ser, AXIS, POST_MOVE_DEG)
        print("Done.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted by user.")

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Apply the azimuth-axis unstick command sequence without moving the axis.

Behavior
- Opens the controller on the azimuth axis (Y)
- Sends the usual init / clear commands
- Optionally toggles DTR/RTS and sends a short BREAK
- Reads status and current position
- Does not issue any move command
"""

PORT = "COM3"
BAUD = 57600
AXIS = "Y"
SHOW_STATUS = True

import time
import serial


def tx(ser, cmd, wait=0.05, echo=SHOW_STATUS):
    ser.write((cmd + "\r").encode("ascii"))
    time.sleep(wait)
    resp = ser.read_all().decode("ascii", errors="ignore")
    if echo:
        print(f"{cmd} -> {resp.strip()}")
    return resp


def has_limit(resp: str) -> bool:
    return "L" in (resp or "")


def init_axis(ser, axis: str):
    for cmd in [
        f"{axis}0N-0cz00",
        f"{axis}0B200",
        f"{axis}0P3,200,75,0",
        f"{axis}0H4",
        f"{axis}0E5000",
        f"{axis}0S5",
    ]:
        tx(ser, cmd)


def toggle_lines_and_break(ser):
    print("Toggling DTR/RTS and sending short BREAK...")
    try:
        ser.dtr = False
        ser.rts = False
        time.sleep(0.2)
        ser.dtr = True
        ser.rts = True
        time.sleep(0.2)
        ser.send_break(duration=0.2)
        time.sleep(0.2)
        ser.reset_input_buffer()
        ser.reset_output_buffer()
    except Exception as exc:
        print("Line toggle/BRK not supported:", exc)


def main():
    print(f"Opening {PORT} @ {BAUD}, AXIS={AXIS}")
    with serial.Serial(PORT, BAUD, timeout=0.3) as ser:
        init_axis(ser, AXIS)
        status = tx(ser, f"{AXIS}0")
        position = tx(ser, f"{AXIS}0m")

        if has_limit(status):
            print("Limit indicated; applying non-moving recovery line toggle only.")
            toggle_lines_and_break(ser)
            init_axis(ser, AXIS)
            status = tx(ser, f"{AXIS}0")
            position = tx(ser, f"{AXIS}0m")
        else:
            print("No limit latched; applying init-only unstick sequence.")

        print("\nNo motion command will be sent by this script.")
        print("Final status:", status.strip())
        print("Final position:", position.strip())
        print("\nFinished. Azimuth unstick commands applied without moving the axis.\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted by user.")

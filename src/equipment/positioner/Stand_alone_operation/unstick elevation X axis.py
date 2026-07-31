#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Apply the elevation-axis unstick command sequence without moving the axis.

Behavior
- Opens the controller on the elevation axis (X)
- Sends the usual safe init / clear commands
- Reads status, switch inputs, and current position
- Does not issue any move command
"""

PORT = "COM3"
BAUD = 57600
AXIS = "X"

import time
import re
import serial


def tx(ser, cmd, wait=0.05, echo=True):
    ser.write((cmd + "\r").encode("ascii"))
    time.sleep(wait)
    data = ser.read_all().decode("ascii", errors="ignore")
    if echo:
        print(f"{cmd} -> {data.strip()}")
    return data


def init_axis(ser, axis):
    for cmd in [
        "GGN-0cz00",
        f"{axis}0H4",
        f"{axis}0P3,200,100,10",
        f"{axis}0B100",
        f"{axis}0E1200",
        f"{axis}0S7",
    ]:
        tx(ser, cmd)


def parse_steps(resp: str):
    match = re.search(r">([+-]?\d+)", resp.strip())
    if not match:
        return None
    return int(match.group(1))


def main():
    print(f"Opening {PORT} @ {BAUD}, axis={AXIS}")
    with serial.Serial(PORT, BAUD, timeout=0.3) as ser:
        init_axis(ser, AXIS)

        status = tx(ser, f"{AXIS}0")
        print("Status:", status.strip())
        i1 = tx(ser, f"{AXIS}0I1")
        print("Home sw (I1):", i1.strip(), "(1=not tripped, 0=tripped)")
        i3 = tx(ser, f"{AXIS}0I3")
        print("Max  sw (I3):", i3.strip(), "(1=not tripped, 0=tripped)")
        pos = tx(ser, f"{AXIS}0m")
        print("Pos:", pos.strip())

        steps = parse_steps(pos)
        print(f"Parsed steps: {steps if steps is not None else 'unparsed'}")
        print("\nNo motion command will be sent by this script.")
        print("Final status:", tx(ser, f"{AXIS}0").strip())
        print("Final position:", tx(ser, f"{AXIS}0m").strip())
        print("\nFinished. Elevation unstick commands applied without moving the axis.\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted by user.")

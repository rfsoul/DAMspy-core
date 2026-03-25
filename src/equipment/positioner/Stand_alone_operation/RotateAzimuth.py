# move_azimuth.py  (Python 3.6+)
# Y0m -> y0>0000xxxxx    0 degrees (example format)
import time, serial

PORT = "COM3"        # <- your port
BAUD = 57600
AXIS = "Y"           # azimuth axis on your rig
STEPS_PER_DEG = 800  # 800 steps/° at 1/16 microstep on Y

def send(ser, s):
    ser.write((s + '\r').encode('ascii'))
    time.sleep(0.02)
    return ser.read_all().decode('ascii', errors='ignore')

def poll_done(ser, axis=AXIS, timeout=15.0):
    t0 = time.time()
    done_tok = f"{axis.lower()}0f"
    home_tok = f"{axis.lower()}0H"
    max_tok  = f"{axis.lower()}0L"
    while True:
        resp = send(ser, f"{axis}0")       # status poll
        if done_tok in resp:
            return True
        if (home_tok in resp) or (max_tok in resp):
            print("Limit switch event:", resp.strip())
            return False
        if time.time() - t0 > timeout:
            print("Timed out waiting for move; last:", resp.strip())
            return False
        time.sleep(0.05)

def axis_has_switch(ser, axis, code: int) -> bool:
    """code=1 (home), 3 (max). Returns True if controller answers in the expected format."""
    resp = send(ser, f"{axis}0I{code}")
    return ">" in resp   # quick existence check

def move_azimuth_rel(deg, obey_limits=True):
    """Relative move by 'deg' degrees on the azimuth axis (Y)."""
    steps = int(round(deg * STEPS_PER_DEG))
    print(f"Request: {deg:+.2f}° -> {steps:+d} steps")
    if steps == 0:
        print("No move requested (0 steps).")
        return True

    with serial.Serial(PORT, BAUD, timeout=0.2) as ser:
        # Optional init for Y; mirror what you do for X if needed
        # Comment this block out if you already initialized in a wider session.
        if AXIS == "Y":
            for cmd in ["Y0P3,163,81,10", "Y0H4", "Y0B500", "Y0E3000", "Y0S8"]:
                print(cmd, send(ser, cmd))

        # Choose safest move mode available
        move_prefix = f"{AXIS}0RN"  # default: ignore switches (if none present)
        if obey_limits:
            has_home = axis_has_switch(ser, AXIS, 1)
            has_max  = axis_has_switch(ser, AXIS, 3)
            if has_home and has_max:
                move_prefix = f"{AXIS}0RYY"
            elif has_home:
                move_prefix = f"{AXIS}0RY"

        cmd = f"{move_prefix}{steps:+d}"
        print(cmd, send(ser, cmd))
        ok = poll_done(ser, AXIS)

        # Read back internal step counter (optional verification)
        print(f"{AXIS}0m ->", send(ser, f"{AXIS}0m").strip())
        return ok

if __name__ == "__main__":
    # Examples:
    # positive deg = one direction, negative = the other

    time.sleep(2)
    # move_azimuth_rel(+10.0, obey_limits=False)   # e.g. 10° one way
    move_azimuth_rel(-161, obey_limits=False)      # e.g. 10° back  positive is CCW

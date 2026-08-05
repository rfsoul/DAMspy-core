import time
import serial
import re


PORT = "COM3"
BAUD = 57600
AXES = (
    ("Y", "azimuth"),
    ("X", "elevation"),
)
STEPS_PER_DEG = {
    "Y": 800.0,
    "X": 320.0,
}


def send(ser, cmd, wait_s=0.05):
    ser.write((cmd + "\r").encode("ascii"))
    time.sleep(wait_s)
    return ser.read_all().decode("ascii", errors="ignore").strip()


def parse_steps(response):
    nums = re.findall(r"[-+]?\d+", response or "")
    if not nums:
        return None
    try:
        return int(nums[-1])
    except ValueError:
        return None


def main():
    print(f"Opening {PORT} @ {BAUD}")
    with serial.Serial(PORT, BAUD, timeout=0.3) as ser:
        for axis, label in AXES:
            raw_status = send(ser, f"{axis}0")
            raw_counts = send(ser, f"{axis}0m")
            steps = parse_steps(raw_counts)
            steps_per_deg = STEPS_PER_DEG[axis]
            deg = None if steps is None else steps / steps_per_deg

            print()
            print(f"[{label.upper()}]")
            print(f"{axis}0  -> {raw_status}")
            print(f"{axis}0m -> {raw_counts}")
            print(f"Parsed steps  : {steps if steps is not None else 'unparsed'}")
            print(f"Parsed degrees: {deg if deg is not None else 'unparsed'}")


if __name__ == "__main__":
    main()

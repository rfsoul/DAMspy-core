import time
import re
import serial


class DiamondD6050:
    """
    Diamond Engineering D6050 driver

    Logging behaviour:
    - High-level move start / completion is always printed.
    - Low-level encoder polling chatter is only printed when
      cfg["verbose_logging"] is true.
    """

    def __init__(self, cfg):
        self.port = cfg.get("port")
        self.baud = cfg.get("baud", 57600)

        self.az_axis = cfg.get("az_axis", "Y")
        self.el_axis = cfg.get("el_axis", "X")

        self.az_steps_per_deg = cfg.get("az_steps_per_deg", 800)
        self.el_steps_per_deg = cfg.get("el_steps_per_deg", 800)

        self.verbose_logging = bool(cfg.get("verbose_logging", False))

        self.ser = serial.Serial(self.port, self.baud, timeout=0.2)
        print(f"[DiamondD6050] Connected on {self.port} @ {self.baud}")

        # Initialise both axes
        for cmd in [
            "Y0P3,163,81,10", "Y0H4", "Y0B500", "Y0E3000", "Y0S8",
            "X0P3,163,81,10", "X0H4", "X0B500", "X0E3000", "X0S8"
        ]:
            self._send(cmd)

    # -----------------------------------------------------------
    # Logging helper
    # -----------------------------------------------------------
    def _vprint(self, message: str):
        if self.verbose_logging:
            print(message)

    # -----------------------------------------------------------
    # Low-level
    # -----------------------------------------------------------
    def _send(self, cmd):
        self.ser.write((cmd + "\r").encode("ascii"))
        time.sleep(0.02)
        return self.ser.read_all().decode("ascii", errors="ignore")

    # -----------------------------------------------------------
    # Encoder reading (correct command: Y0m / X0m)
    # -----------------------------------------------------------
    def _read_steps(self, axis):
        resp = self._send(f"{axis}0m")
        try:
            nums = re.findall(r'[-+]?\d+', resp)
            return int(nums[-1])
        except Exception:
            return None

    # -----------------------------------------------------------
    # Angle read with correct RF sign convention
    # -----------------------------------------------------------
    def get_current_az_deg(self):
        steps = self._read_steps(self.az_axis)
        if steps is None:
            return None
        # NEGATE the angle so CW = negative
        return -(steps / float(self.az_steps_per_deg))

    # -----------------------------------------------------------
    # Wait for motion start
    # -----------------------------------------------------------
    def _wait_for_motion_start(self):
        initial = self.get_current_az_deg()
        if initial is None:
            initial = 0.0

        self._vprint("[POS] Waiting for motion to begin…")

        for _ in range(25):  # ~5 seconds
            time.sleep(0.2)
            ang = self.get_current_az_deg()
            if ang is None:
                continue
            if abs(ang - initial) > 0.2:
                self._vprint("[POS] Motion started.")
                return True

        self._vprint("[POS] Motion start not detected (continuing anyway).")
        return True

    # -----------------------------------------------------------
    # Wait for motion stop
    # -----------------------------------------------------------
    def wait_until_stopped(self):
        self._vprint("[POS] Monitoring movement via encoder…")

        last = None
        stable = 0

        while True:
            ang = self.get_current_az_deg()
            if ang is None:
                self._vprint("[POS] Encoder read failed, retrying…")
                time.sleep(0.2)
                continue

            if self.verbose_logging:
                steps = int(-ang * self.az_steps_per_deg)  # invert back for raw display
                print(f"[POS] Encoder: {steps:+7d} steps  ({ang:+6.2f}°)")

            if last is not None:
                if abs(ang - last) < 0.2:
                    stable += 1
                    if stable >= 6:
                        self._vprint(f"[POS] Movement stopped at {ang:+.2f}°")
                        return ang
                else:
                    stable = 0

            last = ang
            time.sleep(0.2)

    # -----------------------------------------------------------
    # Azimuth move (relative)
    # -----------------------------------------------------------
    def go_azimuth(self, deg):
        # steps unchanged – sign convention handled in angle read
        steps = int(round(deg * self.az_steps_per_deg))
        cmd = f"{self.az_axis}0RN{steps:+d}"
        print(f"[DiamondD6050] AZ MOVE {deg:+.2f}° -> {cmd}")

        self._send(cmd)
        self._wait_for_motion_start()
        final = self.wait_until_stopped()

        print(f"[DiamondD6050] AZ MOVE complete at {final:+.2f}°")
        return True
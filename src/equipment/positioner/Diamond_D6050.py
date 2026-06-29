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
    def _read_response(self, timeout_s=0.3, idle_after_data_s=0.05):
        deadline = time.monotonic() + max(0.0, float(timeout_s))
        last_data_at = None
        chunks = []

        while time.monotonic() < deadline:
            waiting = getattr(self.ser, "in_waiting", 0)
            if waiting:
                chunks.append(self.ser.read(waiting).decode("ascii", errors="ignore"))
                last_data_at = time.monotonic()
                continue

            if last_data_at is not None and (time.monotonic() - last_data_at) >= idle_after_data_s:
                break

            time.sleep(0.01)

        return "".join(chunks)

    def _send(self, cmd, response_timeout_s=0.3, idle_after_data_s=0.05, clear_input=False):
        if clear_input:
            self.ser.reset_input_buffer()
        self.ser.write((cmd + "\r").encode("ascii"))
        return self._read_response(
            timeout_s=response_timeout_s,
            idle_after_data_s=idle_after_data_s,
        )

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

        self._vprint("[POS] Waiting for motion to begin...")

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

    def _wait_for_axis_motion_start_response(self, axis, timeout_s):
        axis_token = f"{axis.lower()}0b"
        deadline = time.monotonic() + max(0.0, float(timeout_s))
        chunks = []

        while time.monotonic() < deadline:
            waiting = getattr(self.ser, "in_waiting", 0)
            if waiting:
                chunk = self.ser.read(waiting).decode("ascii", errors="ignore")
                chunks.append(chunk)
                response = "".join(chunks)
                if axis_token in response.lower():
                    timestamp = time.time()
                    self._vprint(
                        f"[POS] Motion start response received for axis {axis}: {response.strip()}"
                    )
                    return {
                        "timestamp": timestamp,
                        "response": response.strip(),
                        "method": "controller_response",
                    }
            time.sleep(0.01)

        return {
            "timestamp": None,
            "response": "".join(chunks).strip(),
            "method": "controller_response_timeout",
        }

    def _wait_for_axis_motion_start_fallback(self, axis, initial_angle):
        self._vprint("[POS] Falling back to encoder-based motion start detection...")

        if axis != self.az_axis:
            return {
                "timestamp": time.time(),
                "response": "",
                "method": "command_timestamp_fallback",
            }

        for _ in range(25):
            time.sleep(0.2)
            ang = self.get_current_az_deg()
            if ang is None:
                continue
            if abs(ang - initial_angle) > 0.2:
                self._vprint("[POS] Motion start inferred from encoder change.")
                return {
                    "timestamp": time.time(),
                    "response": "",
                    "method": "encoder_change",
                }

        self._vprint("[POS] Motion start fallback timed out; using current timestamp.")
        return {
            "timestamp": time.time(),
            "response": "",
            "method": "command_timestamp_fallback",
        }

    # -----------------------------------------------------------
    # Wait for motion stop
    # -----------------------------------------------------------
    def wait_until_stopped(self):
        self._vprint("[POS] Monitoring movement via encoder...")

        last = None
        stable = 0

        while True:
            ang = self.get_current_az_deg()
            if ang is None:
                self._vprint("[POS] Encoder read failed, retrying...")
                time.sleep(0.2)
                continue

            if self.verbose_logging:
                steps = int(-ang * self.az_steps_per_deg)  # invert back for raw display
                print(f"[POS] Encoder: {steps:+7d} steps  ({ang:+6.2f} deg)")

            if last is not None:
                if abs(ang - last) < 0.2:
                    stable += 1
                    if stable >= 6:
                        self._vprint(f"[POS] Movement stopped at {ang:+.2f} deg")
                        return ang
                else:
                    stable = 0

            last = ang
            time.sleep(0.2)

    # -----------------------------------------------------------
    # Azimuth move (relative)
    # -----------------------------------------------------------
    def start_azimuth_move(self, deg, motion_start_timeout_s=15.0):
        steps = int(round(deg * self.az_steps_per_deg))
        cmd = f"{self.az_axis}0RN{steps:+d}"
        print(f"[DiamondD6050] AZ MOVE {deg:+.2f} deg -> {cmd}")

        initial_angle = self.get_current_az_deg()
        if initial_angle is None:
            initial_angle = 0.0

        command_timestamp = time.time()
        self._send(
            cmd,
            response_timeout_s=0.0,
            clear_input=True,
        )

        start_info = self._wait_for_axis_motion_start_response(
            self.az_axis,
            motion_start_timeout_s,
        )
        if start_info["timestamp"] is None:
            start_info = self._wait_for_axis_motion_start_fallback(
                self.az_axis,
                initial_angle,
            )

        start_info.update(
            {
                "command": cmd,
                "command_timestamp": command_timestamp,
                "requested_deg": deg,
                "requested_steps": steps,
            }
        )
        return start_info

    def go_azimuth(self, deg):
        self.start_azimuth_move(deg)
        final = self.wait_until_stopped()

        print(f"[DiamondD6050] AZ MOVE complete at {final:+.2f} deg")
        return True

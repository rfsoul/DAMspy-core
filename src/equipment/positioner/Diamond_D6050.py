import time
import re
import serial


class PositionerMotionError(RuntimeError):
    """Raised when the controller accepts a move command but motion cannot be verified."""


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

        self.ser = None
        self.open()

    def open(self):
        if self.ser is not None:
            return
        self.ser = serial.Serial(self.port, self.baud, timeout=0.2)
        print(f"[DiamondD6050] Connected on {self.port} @ {self.baud}")

        # Initialise both axes
        for cmd in [
            "Y0P3,163,81,10", "Y0H4", "Y0B500", "Y0E3000", "Y0S8",
            "X0P3,163,81,10", "X0H4", "X0B500", "X0E3000", "X0S8"
        ]:
            self._send(cmd)

    def close(self):
        if self.ser is None:
            return
        try:
            self.ser.close()
        finally:
            self.ser = None
            print(f"[DiamondD6050] Closed {self.port}")

    # -----------------------------------------------------------
    # Logging helper
    # -----------------------------------------------------------
    def _vprint(self, message: str):
        if self.verbose_logging:
            print(message)

    # -----------------------------------------------------------
    # Low-level
    # -----------------------------------------------------------
    def _require_open(self):
        if self.ser is None:
            raise RuntimeError(
                f"Positioner serial port {self.port} is not open. Call open() before use."
            )

    def _read_response(self, timeout_s=0.3, idle_after_data_s=0.05):
        self._require_open()
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
        self._require_open()
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

    def get_current_az_steps(self):
        return self.get_current_axis_steps("azimuth")

    def get_current_el_steps(self):
        return self.get_current_axis_steps("elevation")

    def get_current_axis_steps(self, logical_axis="azimuth"):
        cfg = self._axis_config(logical_axis)
        return self._read_steps(cfg["controller_axis"])

    def _axis_config(self, logical_axis="azimuth"):
        axis_name = str(logical_axis).strip().lower()
        if axis_name in {"azimuth", "az", self.az_axis.lower()}:
            return {
                "logical_name": "azimuth",
                "controller_axis": self.az_axis,
                "steps_per_deg": self.az_steps_per_deg,
                "log_prefix": "AZ",
            }
        if axis_name in {"elevation", "vertical", "el", self.el_axis.lower()}:
            return {
                "logical_name": "elevation",
                "controller_axis": self.el_axis,
                "steps_per_deg": self.el_steps_per_deg,
                "log_prefix": "EL",
            }
        raise ValueError(f"Unsupported positioner axis: {logical_axis!r}")

    def _steps_to_angle_deg(self, cfg, steps):
        if steps is None:
            return None
        if cfg["logical_name"] == "azimuth":
            return -(steps / float(cfg["steps_per_deg"]))
        return steps / float(cfg["steps_per_deg"])

    def _angle_to_raw_steps(self, cfg, angle_deg):
        if cfg["logical_name"] == "azimuth":
            return int(round(-angle_deg * cfg["steps_per_deg"]))
        return int(round(angle_deg * cfg["steps_per_deg"]))

    def _motion_threshold_deg(self, cfg, requested_deg=0.0):
        requested_magnitude = abs(float(requested_deg))
        one_step_deg = 1.0 / float(cfg["steps_per_deg"])
        if requested_magnitude <= 1e-9:
            return 0.2
        return max(one_step_deg / 2.0, min(0.2, requested_magnitude / 2.0))

    def _toggle_lines_and_break(self):
        self._require_open()
        try:
            self.ser.dtr = False
            self.ser.rts = False
            time.sleep(0.2)
            self.ser.dtr = True
            self.ser.rts = True
            time.sleep(0.2)
            self.ser.send_break(duration=0.2)
            time.sleep(0.2)
            self.ser.reset_input_buffer()
            self.ser.reset_output_buffer()
        except Exception as exc:
            self._vprint(f"[DiamondD6050] Line toggle/BRK not supported: {exc}")

    def unstick_axis_without_motion(self, logical_axis="azimuth"):
        cfg = self._axis_config(logical_axis)
        axis = cfg["controller_axis"]
        axis_name = cfg["logical_name"]

        if axis_name == "azimuth":
            print("[DiamondD6050] Applying azimuth unstick commands without motion")
            for cmd in [
                f"{axis}0N-0cz00",
                f"{axis}0B200",
                f"{axis}0P3,200,75,0",
                f"{axis}0H4",
                f"{axis}0E5000",
                f"{axis}0S5",
            ]:
                self._send(cmd)
            status = self._send(f"{axis}0").strip()
            position = self._send(f"{axis}0m").strip()
            if "L" in status.upper():
                print("[DiamondD6050] Azimuth limit latched; applying line toggle only")
                self._toggle_lines_and_break()
                for cmd in [
                    f"{axis}0N-0cz00",
                    f"{axis}0B200",
                    f"{axis}0P3,200,75,0",
                    f"{axis}0H4",
                    f"{axis}0E5000",
                    f"{axis}0S5",
                ]:
                    self._send(cmd)
                status = self._send(f"{axis}0").strip()
                position = self._send(f"{axis}0m").strip()
            return {"status": status, "position": position}

        print("[DiamondD6050] Applying elevation unstick commands without motion")
        for cmd in [
            "GGN-0cz00",
            f"{axis}0H4",
            f"{axis}0P3,200,100,10",
            f"{axis}0B100",
            f"{axis}0E1200",
            f"{axis}0S7",
        ]:
            self._send(cmd)
        status = self._send(f"{axis}0").strip()
        home_sw = self._send(f"{axis}0I1").strip()
        max_sw = self._send(f"{axis}0I3").strip()
        position = self._send(f"{axis}0m").strip()
        return {
            "status": status,
            "home_switch": home_sw,
            "max_switch": max_sw,
            "position": position,
        }

    # -----------------------------------------------------------
    # Angle read with correct RF sign convention
    # -----------------------------------------------------------
    def get_current_az_deg(self):
        return self.get_current_axis_deg("azimuth")

    def get_current_el_deg(self):
        return self.get_current_axis_deg("elevation")

    def get_current_axis_deg(self, logical_axis="azimuth"):
        cfg = self._axis_config(logical_axis)
        steps = self.get_current_axis_steps(cfg["logical_name"])
        return self._steps_to_angle_deg(cfg, steps)

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
        cfg = self._axis_config(axis)
        motion_threshold_deg = self._motion_threshold_deg(cfg, 0.0)

        for _ in range(25):
            time.sleep(0.2)
            ang = self.get_current_axis_deg(cfg["logical_name"])
            if ang is None:
                continue
            if abs(ang - initial_angle) > motion_threshold_deg:
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
    def wait_until_stopped(
        self,
        axis="azimuth",
        *,
        initial_angle_deg=None,
        requested_deg=0.0,
        encoder_read_timeout_s=5.0,
        no_motion_timeout_s=5.0,
    ):
        cfg = self._axis_config(axis)
        self._vprint("[POS] Monitoring movement via encoder...")

        last = None
        stable = 0
        last_encoder_read_at = time.monotonic()
        motion_required = abs(float(requested_deg)) > 1e-9
        motion_detected = not motion_required
        initial_angle = initial_angle_deg
        motion_threshold_deg = self._motion_threshold_deg(cfg, requested_deg)
        no_motion_deadline = (
            time.monotonic() + max(0.0, float(no_motion_timeout_s))
            if motion_required
            else None
        )

        while True:
            now = time.monotonic()
            ang = self.get_current_axis_deg(cfg["logical_name"])
            if ang is None:
                if (now - last_encoder_read_at) >= max(0.0, float(encoder_read_timeout_s)):
                    raise PositionerMotionError(
                        f"{cfg['log_prefix']} encoder read timed out while waiting for motion"
                    )
                self._vprint("[POS] Encoder read failed, retrying...")
                time.sleep(0.2)
                continue

            last_encoder_read_at = now

            if self.verbose_logging:
                steps = self._angle_to_raw_steps(cfg, ang)
                print(f"[POS] Encoder: {steps:+7d} steps  ({ang:+6.2f} deg)")

            if motion_required and not motion_detected:
                if initial_angle is None:
                    initial_angle = ang
                if abs(ang - initial_angle) > motion_threshold_deg:
                    motion_detected = True
                    self._vprint(f"[POS] Motion verified at {ang:+.2f} deg")
                elif no_motion_deadline is not None and now >= no_motion_deadline:
                    raise PositionerMotionError(
                        f"{cfg['log_prefix']} move command was accepted but no encoder motion was detected"
                    )

            if last is not None:
                if abs(ang - last) < 0.2:
                    stable += 1
                    if stable >= 6 and (motion_detected or not motion_required):
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
        return self.start_axis_move("azimuth", deg, motion_start_timeout_s=motion_start_timeout_s)

    def start_elevation_move(self, deg, motion_start_timeout_s=15.0):
        return self.start_axis_move("elevation", deg, motion_start_timeout_s=motion_start_timeout_s)

    def start_axis_move(self, axis, deg, motion_start_timeout_s=15.0):
        cfg = self._axis_config(axis)
        steps = int(round(deg * cfg["steps_per_deg"]))
        cmd = f"{cfg['controller_axis']}0RN{steps:+d}"
        print(f"[DiamondD6050] {cfg['log_prefix']} MOVE {deg:+.2f} deg -> {cmd}")

        initial_angle = self.get_current_axis_deg(cfg["logical_name"])
        if initial_angle is None:
            initial_angle = 0.0

        command_timestamp = time.time()
        self._send(
            cmd,
            response_timeout_s=0.0,
            clear_input=True,
        )

        start_info = self._wait_for_axis_motion_start_response(
            cfg["controller_axis"],
            motion_start_timeout_s,
        )
        if start_info["timestamp"] is None:
            start_info = self._wait_for_axis_motion_start_fallback(
                cfg["logical_name"],
                initial_angle,
            )

        start_info.update(
            {
                "command": cmd,
                "command_timestamp": command_timestamp,
                "requested_deg": deg,
                "requested_steps": steps,
                "initial_angle_deg": initial_angle,
            }
        )
        return start_info

    def go_azimuth(self, deg):
        return self.go_axis("azimuth", deg)

    def go_elevation(self, deg):
        return self.go_axis("elevation", deg)

    def go_axis(self, axis, deg):
        cfg = self._axis_config(axis)
        start_info = self.start_axis_move(cfg["logical_name"], deg)
        final = self.wait_until_stopped(
            cfg["logical_name"],
            initial_angle_deg=start_info.get("initial_angle_deg"),
            requested_deg=deg,
        )

        print(f"[DiamondD6050] {cfg['log_prefix']} MOVE complete at {final:+.2f} deg")
        return True

# src/equipment/signal_generator/rxcc.py

from __future__ import annotations

import json
import socket
from typing import Any, Dict, Optional
from urllib import error, request

from equipment.utils.driver_base import SignalGeneratorBase


class RXCC(SignalGeneratorBase):
    """
    Rpicontrol-backed signal-generator adapter.

    Per-device unified command examples:
        curl -X POST http://<pi-ip>:8000/api/devices/rxcc/commands/start-rf \
          -H "Content-Type: application/json" \
          -d '{"antenna": "main", "channel": 0, "power": 10}'

        curl -X POST http://<pi-ip>:8000/api/devices/tx/commands/stop-rf \
          -H "Content-Type: application/json" \
          -d '{}'

    The measurement YAML selects the runtime device_type:
    - rxcc
    - hendrix_tx
    - hendrix_rx
    - wireless-pro-rx

    Shared RF controls:
    - channel: integer 0..80
    - power_level: integer 0..10

    Wireless Pro RX RF controls:
    - wirepro_freq: integer 0..99, interpreted as 2400 MHz + value MHz
    - wirepro_power: dBm level, may be negative

    RXCC-only RF control:
    - antenna: "main" or "secondary"

    It does NOT pretend to support arbitrary frequency or dBm-level control.

    Expected cfg keys from location/equipment config:
        - rpicontrol_ipaddress: base URL, e.g. "http://10.0.1.195:8000"
        - timeout: optional request timeout in seconds (default 5.0)
        - max_retries: optional retry count for retryable failures (default 2)

    Optional defaults may also be provided in cfg:
        - channel
        - power_level
        - wirepro_freq
        - wirepro_power
        - antenna
    """

    DEFAULT_DEVICE_TYPE = "rxcc"
    VALID_DEVICE_TYPES = {"rxcc", "hendrix_tx", "hendrix_rx", "wireless-pro-rx"}
    VALID_ANTENNAS = {"main", "secondary"}
    VALID_CTX_LEVELS = {"high", "low"}
    COMMAND_PATHS = {
        "rxcc": {
            "start": "/api/devices/rxcc/commands/start-rf",
            "stop": "/api/devices/rxcc/commands/stop-rf",
        },
        "hendrix_tx": {
            "start": "/api/devices/tx/commands/start-rf",
            "stop": "/api/devices/tx/commands/stop-rf",
        },
        "hendrix_rx": {
            "start": "/api/devices/rx/commands/start-rf",
            "stop": "/api/devices/rx/commands/stop-rf",
        },
        "wireless-pro-rx": {
            "start": "/api/devices/wireless-pro-rx/commands/start-rf",
            "stop": "/api/devices/wireless-pro-rx/commands/stop-rf",
        },
    }
    CTX_PATHS = {
        "hendrix_tx": {
            "high": "/api/ctx/tx/high",
            "low": "/api/ctx/tx/low",
        },
        "hendrix_rx": {
            "high": "/api/ctx/rx/high",
            "low": "/api/ctx/rx/low",
        },
    }

    def __init__(self, cfg: dict):
        super().__init__()

        if "rpicontrol_ipaddress" not in cfg:
            raise KeyError("RXCC driver requires 'rpicontrol_ipaddress' in cfg")

        self.cfg = cfg
        self.base_url = str(cfg["rpicontrol_ipaddress"]).rstrip("/")
        self.timeout = float(cfg.get("timeout", 5.0))
        self.max_retries = int(cfg.get("max_retries", 2))

        self._channel: Optional[int] = None
        self._power_level: Optional[int] = None
        self._wirepro_freq: Optional[int] = None
        self._wirepro_power: Optional[float] = None
        self._antenna: Optional[str] = None
        self._device_type = self.DEFAULT_DEVICE_TYPE
        self._ctx_level = "high"
        self._last_health: Optional[Dict[str, Any]] = None

        # Optional constructor defaults
        if "device_type" in cfg:
            self.set_device_type(cfg["device_type"])
        if "channel" in cfg:
            self.set_channel(cfg["channel"])
        if "power_level" in cfg:
            self.set_power_level(cfg["power_level"])
        if "wirepro_freq" in cfg:
            self.set_wirepro_freq(cfg["wirepro_freq"])
        if "wirepro_power" in cfg:
            self.set_wirepro_power(cfg["wirepro_power"])
        if "antenna" in cfg:
            self.set_antenna(cfg["antenna"])
        if "ctx" in cfg:
            self.set_ctx(cfg["ctx"])

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def open(self) -> None:
        """
        Validate service reachability and mark the device as open.
        """
        self._last_health = self.get_health()
        super().open()

    def close(self) -> None:
        """
        Best-effort RF stop, then mark the device as closed.

        Hendrix TX stop commands should be explicit at the test-flow layer so
        bodyworn/manual cradle workflows can prompt the operator first.
        """
        if self.is_open and self._rf_on and self._device_type != "hendrix_tx":
            try:
                self.rf_off()
            except Exception:
                pass
        super().close()

    # ------------------------------------------------------------------
    # Public RXCC configuration API
    # ------------------------------------------------------------------
    def set_channel(self, channel: int) -> None:
        channel = int(channel)
        if not (0 <= channel <= 80):
            raise ValueError(f"RXCC channel must be 0..80, got {channel}")
        self._channel = channel

    def set_power_level(self, power_level: int) -> None:
        power_level = int(power_level)
        if not (0 <= power_level <= 10):
            raise ValueError(f"RXCC power_level must be 0..10, got {power_level}")
        self._power_level = power_level

    def set_wirepro_freq(self, wirepro_freq: int) -> None:
        wirepro_freq = int(wirepro_freq)
        if not (0 <= wirepro_freq <= 99):
            raise ValueError(f"Wireless Pro RX wirepro_freq must be 0..99, got {wirepro_freq}")
        self._wirepro_freq = wirepro_freq

    def set_wirepro_power(self, wirepro_power: float) -> None:
        self._wirepro_power = float(wirepro_power)

    def set_antenna(self, antenna: str) -> None:
        antenna = str(antenna).strip().lower()
        if antenna not in self.VALID_ANTENNAS:
            raise ValueError(
                f"RXCC antenna must be one of {sorted(self.VALID_ANTENNAS)}, got {antenna!r}"
            )
        self._antenna = antenna

    def set_device_type(self, device_type: str) -> None:
        device_type = str(device_type).strip().lower()
        if device_type not in self.VALID_DEVICE_TYPES:
            raise ValueError(
                "RXCC device_type must be one of "
                f"{sorted(self.VALID_DEVICE_TYPES)}, got {device_type!r}"
            )
        self._device_type = device_type

    def set_ctx(self, ctx) -> None:
        if isinstance(ctx, bool):
            ctx_level = "high" if ctx else "low"
        elif isinstance(ctx, int):
            if ctx not in (0, 1):
                raise ValueError(f"Hendrix CTX must be 0 or 1, got {ctx}")
            ctx_level = "high" if ctx == 1 else "low"
        else:
            value = str(ctx).strip().lower()
            if value in {"1", "high", "true", "on"}:
                ctx_level = "high"
            elif value in {"0", "low", "false", "off"}:
                ctx_level = "low"
            else:
                raise ValueError(
                    "Hendrix CTX must be one of 0, 1, low, or high; "
                    f"got {ctx!r}"
                )

        self._ctx_level = ctx_level

    def configure(
        self,
        *,
        channel: int,
        power_level: int,
        antenna: Optional[str] = None,
    ) -> None:
        """
        Convenience method for setting RF-start parameters together.
        """
        self.set_channel(channel)
        self.set_power_level(power_level)
        if antenna is not None:
            self.set_antenna(antenna)

    def configure_wirepro(
        self,
        *,
        wirepro_freq: int,
        wirepro_power: float,
        antenna: Optional[str] = None,
    ) -> None:
        """
        Convenience method for setting Wireless Pro RX RF-start parameters together.
        """
        self.set_wirepro_freq(wirepro_freq)
        self.set_wirepro_power(wirepro_power)
        if antenna is not None:
            self.set_antenna(antenna)

    # ------------------------------------------------------------------
    # SignalGeneratorBase compatibility
    # ------------------------------------------------------------------
    def set_frequency(self, freq_hz: float) -> None:
        raise NotImplementedError(
            "RXCC does not support arbitrary frequency selection; use set_channel()."
        )

    def set_level(self, level_dbm: float) -> None:
        raise NotImplementedError(
            "RXCC does not use dBm level control; use set_power_level() with integer 0..10."
        )

    def rf_on(self) -> None:
        """
        Start RF using the configured rpicontrol device_type.
        """
        self.ensure_open()
        self._require_rf_start_parameters()
        self._apply_hendrix_ctx()
        self._request_json(
            "POST",
            self.COMMAND_PATHS[self._device_type]["start"],
            payload=self._build_start_payload(),
        )
        self._rf_on = True

    def rf_off(self) -> None:
        """
        Stop RF output using the configured rpicontrol device_type.
        """
        self.ensure_open()
        self._request_json(
            "POST",
            self.COMMAND_PATHS[self._device_type]["stop"],
            payload={},
        )
        self._rf_on = False

    # ------------------------------------------------------------------
    # Health / state helpers
    # ------------------------------------------------------------------
    def get_health(self) -> Dict[str, Any]:
        """
        Return parsed JSON from /health.
        """
        data = self._request_json("GET", "/health")
        self._last_health = data
        return data

    def read_battery_info(self) -> Dict[str, int]:
        """
        Read Hendrix TX battery telemetry from damspy-rpicontrol.
        """
        self.ensure_open()
        if self._device_type != "hendrix_tx":
            raise RuntimeError("Battery info is only supported for hendrix_tx")

        data = self._request_json("POST", "/api/battery/tx", payload={})

        if data.get("status") != "ok":
            raise RuntimeError(f"Unexpected Hendrix TX battery status: {data!r}")

        battery_mv = data.get("battery_mv")
        if battery_mv is None:
            raise RuntimeError(f"Hendrix TX battery response missing battery_mv: {data!r}")

        try:
            battery_mv = int(battery_mv)
        except (TypeError, ValueError) as e:
            raise RuntimeError(
                f"Invalid Hendrix TX battery_mv value in response: {data!r}"
            ) from e

        return {
            "battery_mv": battery_mv,
        }

    @property
    def channel(self) -> Optional[int]:
        return self._channel

    @property
    def power_level(self) -> Optional[int]:
        return self._power_level

    @property
    def wirepro_freq(self) -> Optional[int]:
        return self._wirepro_freq

    @property
    def wirepro_power(self) -> Optional[float]:
        return self._wirepro_power

    @property
    def antenna(self) -> Optional[str]:
        return self._antenna

    @property
    def device_type(self) -> str:
        return self._device_type

    @property
    def last_health(self) -> Optional[Dict[str, Any]]:
        return self._last_health

    @property
    def ctx_level(self) -> str:
        return self._ctx_level

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _build_start_payload(self) -> Dict[str, Any]:
        if self._device_type == "wireless-pro-rx":
            return {
                "device": "wireless-pro-rx",
                "antenna": self._antenna,
                "wirepro_freq": self._wirepro_freq,
                "wirepro_power": self._wirepro_power,
            }

        payload = {
            "channel": self._channel,
            "power": self._power_level,
        }
        if self._device_type == "rxcc":
            payload["antenna"] = self._antenna
        return payload

    def _require_rf_start_parameters(self) -> None:
        if self._device_type == "wireless-pro-rx":
            missing = []
            if self._wirepro_freq is None:
                missing.append("wirepro_freq")
            if self._wirepro_power is None:
                missing.append("wirepro_power")
            if self._antenna is None:
                missing.append("antenna")
            if missing:
                raise RuntimeError(
                    "Wireless Pro RX rf_on() requires "
                    f"{', '.join(missing)} to be set before starting RF"
                )
            return

        missing = []
        if self._channel is None:
            missing.append("channel")
        if self._power_level is None:
            missing.append("power_level")

        if missing:
            raise RuntimeError(
                f"RXCC rf_on() requires {', '.join(missing)} to be set before starting RF"
            )
        if self._device_type == "rxcc" and self._antenna is None:
            raise RuntimeError("RXCC rf_on() requires antenna to be set before starting RF")

    def _apply_hendrix_ctx(self) -> None:
        if self._device_type not in self.CTX_PATHS:
            return

        self._request_json(
            "POST",
            self.CTX_PATHS[self._device_type][self._ctx_level],
        )

    def _request_json(
        self,
        method: str,
        path: str,
        payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Make an HTTP request to damspy-rpicontrol and return parsed JSON.

        Retry policy:
        - retry network/timeouts and HTTP 502
        - do not retry HTTP 422 or HTTP 503
        """
        device_label = self._request_target_label()
        url = f"{self.base_url}{path}"
        body: Optional[bytes] = None
        headers = {"Accept": "application/json"}

        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"

        last_exc: Optional[Exception] = None

        for attempt in range(self.max_retries + 1):
            req = request.Request(url=url, data=body, headers=headers, method=method)

            try:
                with request.urlopen(req, timeout=self.timeout) as resp:
                    raw = resp.read().decode("utf-8").strip()
                    if not raw:
                        return {}
                    return json.loads(raw)

            except error.HTTPError as e:
                detail = e.read().decode("utf-8", errors="replace").strip()

                if e.code == 422:
                    raise ValueError(f"{device_label} request rejected (422): {detail}") from e

                if e.code == 503:
                    raise RuntimeError(
                        f"{device_label} service/device unavailable (503): {detail}"
                    ) from e

                if e.code == 502:
                    last_exc = RuntimeError(f"{device_label} communication failure (502): {detail}")
                    if attempt < self.max_retries:
                        continue
                    raise last_exc from e

                raise RuntimeError(f"{device_label} unexpected HTTP error {e.code}: {detail}") from e

            except (error.URLError, socket.timeout, TimeoutError) as e:
                last_exc = RuntimeError(f"{device_label} network/timeout failure: {e}")
                if attempt < self.max_retries:
                    continue
                raise last_exc from e

        if last_exc is not None:
            raise last_exc

        raise RuntimeError(f"{device_label} request failed for an unknown reason")

    def _request_target_label(self) -> str:
        if self._device_type == "hendrix_tx":
            return "Hendrix HID"
        if self._device_type == "hendrix_rx":
            return "Hendrix RX"
        if self._device_type == "wireless-pro-rx":
            return "Wireless Pro RX"
        return "RXCC"


__all__ = ["RXCC"]

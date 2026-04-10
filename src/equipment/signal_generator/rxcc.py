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

    Shared RF controls:
    - channel: integer 0..80
    - power_level: integer 0..10

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
        - antenna
    """

    DEFAULT_DEVICE_TYPE = "rxcc"
    VALID_DEVICE_TYPES = {"rxcc", "hendrix_tx", "hendrix_rx"}
    VALID_ANTENNAS = {"main", "secondary"}
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
        self._antenna: Optional[str] = None
        self._device_type = self.DEFAULT_DEVICE_TYPE
        self._last_health: Optional[Dict[str, Any]] = None

        # Optional constructor defaults
        if "device_type" in cfg:
            self.set_device_type(cfg["device_type"])
        if "channel" in cfg:
            self.set_channel(cfg["channel"])
        if "power_level" in cfg:
            self.set_power_level(cfg["power_level"])
        if "antenna" in cfg:
            self.set_antenna(cfg["antenna"])

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

    @property
    def channel(self) -> Optional[int]:
        return self._channel

    @property
    def power_level(self) -> Optional[int]:
        return self._power_level

    @property
    def antenna(self) -> Optional[str]:
        return self._antenna

    @property
    def device_type(self) -> str:
        return self._device_type

    @property
    def last_health(self) -> Optional[Dict[str, Any]]:
        return self._last_health

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _build_start_payload(self) -> Dict[str, Any]:
        payload = {
            "channel": self._channel,
            "power": self._power_level,
        }
        if self._device_type == "rxcc":
            payload["antenna"] = self._antenna
        return payload

    def _require_rf_start_parameters(self) -> None:
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
        return "RXCC"


__all__ = ["RXCC"]

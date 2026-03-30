# src/equipment/signal_generator/rxcc.py

from __future__ import annotations

import json
import socket
from typing import Any, Dict, Optional
from urllib import error, request

from equipment.utils.driver_base import SignalGeneratorBase


class RXCC(SignalGeneratorBase):
    """
    RXCC signal-generator-like driver backed by damspy-rpicontrol.

    This driver is intentionally truthful to the RXCC control model:
    - channel: integer 0..80
    - power_level: integer 0..10
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

    VALID_ANTENNAS = {"main", "secondary"}

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
        self._last_health: Optional[Dict[str, Any]] = None

        # Optional constructor defaults
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
        """
        if self.is_open:
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

    def configure(self, *, channel: int, power_level: int, antenna: str) -> None:
        """
        Convenience method for setting all RF-start parameters together.
        """
        self.set_channel(channel)
        self.set_power_level(power_level)
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
        Start RF using the currently cached antenna/channel/power_level.
        """
        self.ensure_open()
        self._require_rf_start_parameters()

        payload = {
            "antenna": self._antenna,
            "channel": self._channel,
            "power": self._power_level,
        }
        self._request_json("POST", "/api/rf/start", payload=payload)
        self._rf_on = True

    def rf_off(self) -> None:
        """
        Stop RF output.
        """
        self.ensure_open()
        self._request_json("POST", "/api/rf/stop")
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
    def last_health(self) -> Optional[Dict[str, Any]]:
        return self._last_health

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _require_rf_start_parameters(self) -> None:
        missing = []
        if self._channel is None:
            missing.append("channel")
        if self._power_level is None:
            missing.append("power_level")
        if self._antenna is None:
            missing.append("antenna")

        if missing:
            raise RuntimeError(
                f"RXCC rf_on() requires {', '.join(missing)} to be set before starting RF"
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
                    raise ValueError(f"RXCC request rejected (422): {detail}") from e

                if e.code == 503:
                    raise RuntimeError(f"RXCC service/device unavailable (503): {detail}") from e

                if e.code == 502:
                    last_exc = RuntimeError(f"RXCC communication failure (502): {detail}")
                    if attempt < self.max_retries:
                        continue
                    raise last_exc from e

                raise RuntimeError(f"RXCC unexpected HTTP error {e.code}: {detail}") from e

            except (error.URLError, socket.timeout, TimeoutError) as e:
                last_exc = RuntimeError(f"RXCC network/timeout failure: {e}")
                if attempt < self.max_retries:
                    continue
                raise last_exc from e

        if last_exc is not None:
            raise last_exc

        raise RuntimeError("RXCC request failed for an unknown reason")


__all__ = ["RXCC"]
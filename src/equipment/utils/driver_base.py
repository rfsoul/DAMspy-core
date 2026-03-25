# equipment/utils/driver_base.py
"""
Permissive driver base classes for DAMSpy (SETI-style).

- Concrete defaults for set_frequency()/set_level() so drivers that only
  implement set_cw() are still instantiable.
- Keep open()/close() and rf_on()/rf_off() abstract so drivers define essentials.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Optional


# ──────────────────────────────────────────────────────────────────────────────
# Core base with simple lifecycle and context-manager support
# ──────────────────────────────────────────────────────────────────────────────
class DeviceBase(ABC):
    """Minimal lifecycle that most devices share."""

    def __init__(self) -> None:
        self._is_open: bool = False

    # --- lifecycle ------------------------------------------------------------
    @abstractmethod
    def open(self) -> None:
        """
        Open connections/resources (USB/LAN/VISA/etc).
        Call super().open() LAST on success to set state.
        """
        self._is_open = True

    @abstractmethod
    def close(self) -> None:
        """
        Close/free resources (idempotent).
        Call super().close() LAST.
        """
        self._is_open = False

    # --- helpers --------------------------------------------------------------
    @property
    def is_open(self) -> bool:
        return self._is_open

    def ensure_open(self) -> None:
        if not self._is_open:
            raise RuntimeError(f"{self.__class__.__name__} is not open")

    # --- context manager ------------------------------------------------------
    def __enter__(self) -> "DeviceBase":
        self.open()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        try:
            self.close()
        except Exception:
            # avoid masking original exceptions
            pass


# ──────────────────────────────────────────────────────────────────────────────
# Signal Generator (permissive SETI-style)
# ──────────────────────────────────────────────────────────────────────────────
class SignalGeneratorBase(DeviceBase):
    """
    Base for RF signal generators.

    Concrete drivers MUST implement:
      - open(), close()
      - rf_on(), rf_off()

    They MAY implement either:
      - set_cw(freq_hz, level_dbm)              (preferred single-call)
      - set_frequency(freq_hz) + set_level(dbm) (split calls)

    This base provides concrete cache-only set_frequency/set_level so a driver
    that only implements set_cw() remains instantiable.
    """

    def __init__(self) -> None:
        super().__init__()
        self._frequency_hz: Optional[float] = None
        self._level_dbm: Optional[float] = None
        self._rf_on: bool = False

    # Preferred single-call interface; concrete drivers usually override this.
    def set_cw(self, freq_hz: float, level_dbm: float) -> None:
        """Optional convenience to set CW frequency and level together."""
        self.set_frequency(freq_hz)
        self.set_level(level_dbm)

    # ── Permissive concrete defaults (cache only; override to hit hardware) ──
    def set_frequency(self, freq_hz: float) -> None:
        """Default: cache only; override in driver to call vendor API."""
        self._frequency_hz = float(freq_hz)

    def set_level(self, level_dbm: float) -> None:
        """Default: cache only; override in driver to call vendor API."""
        self._level_dbm = float(level_dbm)

    # ── RF state (still required) ──
    @abstractmethod
    def rf_on(self) -> None:
        """Enable RF output (override to call vendor API)."""
        self._rf_on = True

    @abstractmethod
    def rf_off(self) -> None:
        """Disable RF output (override to call vendor API)."""
        self._rf_on = False

    # Introspection (optional convenience for tests)
    @property
    def frequency_hz(self) -> Optional[float]:
        return self._frequency_hz

    @property
    def level_dbm(self) -> Optional[float]:
        return self._level_dbm

    @property
    def rf_enabled(self) -> bool:
        return self._rf_on


# ──────────────────────────────────────────────────────────────────────────────
# Placeholders for future devices
# ──────────────────────────────────────────────────────────────────────────────
class SpectrumAnalyserBase(DeviceBase):
    """Extend with center/span/RBW/VBW/trace APIs as needed."""
    pass


class PositionerBase(DeviceBase):
    """Extend with move/zero/read-angle APIs as needed."""
    pass


__all__ = [
    "DeviceBase",
    "SignalGeneratorBase",
    "SpectrumAnalyserBase",
    "PositionerBase",
]

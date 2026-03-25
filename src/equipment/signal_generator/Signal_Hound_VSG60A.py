# equipment/signal_generator/Signal_Hound_VSG60A.py
"""
Signal Hound VSG60A driver (DAMSpy, monolith-aligned).

Matches the monolith's behavior:
- vsg_open_device() returns a dict; we use result["handle"].
- set_cw() mirrors monolith: set_frequency, set_level, (optional) set_sample_rate + repeat_waveform.
- rf_off() uses vsg_abort.
- Robust DLL discovery and tolerant imports.
"""

from __future__ import annotations
from pathlib import Path
from contextlib import contextmanager
import os
import sys
from typing import Any, Optional

from equipment.utils.driver_base import SignalGeneratorBase


# ───────────────────────────── Helpers: env & CWD ─────────────────────────────
@contextmanager
def _pushd(new_dir: Path):
    prev = Path.cwd()
    os.chdir(str(new_dir))
    try:
        yield
    finally:
        os.chdir(str(prev))


def _prepare_api_env() -> tuple[Path, Path]:
    """
    Returns (api_dir, dll_dir) and ensures:
      - api_dir and dll_dir are on sys.path
      - dll_dir is on the Windows loader search path (add_dll_directory or PATH)
    """
    here = Path(__file__).resolve().parent
    api_dir = here / "API"
    dll_dir = api_dir / "vsgdevice"

    # Python module search
    for p in (api_dir, dll_dir):
        sp = str(p)
        if sp not in sys.path:
            sys.path.insert(0, sp)

    # Windows DLL search
    if hasattr(os, "add_dll_directory"):
        os.add_dll_directory(str(dll_dir))
    else:
        os.environ["PATH"] = str(dll_dir) + os.pathsep + os.environ.get("PATH", "")

    return api_dir, dll_dir


# ───────────────────────────── Driver implementation ──────────────────────────
class Vsg60A(SignalGeneratorBase):
    def __init__(self) -> None:
        super().__init__()
        self.handle: Optional[Any] = None
        self._api_loaded: bool = False

        # Bound vendor functions
        self._vsg_open_device = None
        self._vsg_close_device = None
        self._vsg_abort = None
        self._vsg_set_cw = None
        self._vsg_set_frequency = None
        self._vsg_set_level = None
        self._vsg_set_sample_rate = None
        self._vsg_repeat_waveform = None
        self._vsg_rf_on = None
        self._vsg_rf_off = None

    # ---------- internals ----------
    def _load_api(self) -> None:
        if self._api_loaded:
            return

        api_dir, _ = _prepare_api_env()

        # Some wrappers resolve DLLs relative to CWD; make CWD the API dir for import
        with _pushd(api_dir):
            vsg_api = None
            # Preferred absolute path (project layout)
            try:
                from equipment.signal_generator.API.vsgdevice import vsg_api as _v
                vsg_api = _v
            except ModuleNotFoundError:
                pass
            # Fallback to monolith import path
            if vsg_api is None:
                try:
                    from vsgdevice import vsg_api as _v
                    vsg_api = _v
                except ModuleNotFoundError as e:
                    raise ImportError(
                        "Could not import VSG API. Tried "
                        "'equipment.signal_generator.API.vsgdevice.vsg_api' and 'vsgdevice.vsg_api'."
                    ) from e

        # Bind callables (no strict ctypes signatures; use as-is like monolith)
        self._vsg_open_device     = getattr(vsg_api, "vsg_open_device", None)
        self._vsg_close_device    = getattr(vsg_api, "vsg_close_device", None)
        self._vsg_abort           = getattr(vsg_api, "vsg_abort", None)
        self._vsg_set_cw          = getattr(vsg_api, "vsg_set_cw", None)  # may not exist
        self._vsg_set_frequency   = getattr(vsg_api, "vsg_set_frequency", None)
        self._vsg_set_level       = getattr(vsg_api, "vsg_set_level", None)
        self._vsg_set_sample_rate = getattr(vsg_api, "vsg_set_sample_rate", None)
        self._vsg_repeat_waveform = getattr(vsg_api, "vsg_repeat_waveform", None)
        self._vsg_rf_on           = getattr(vsg_api, "vsg_rf_on", None)   # may not exist
        self._vsg_rf_off          = getattr(vsg_api, "vsg_rf_off", None)  # may not exist

        if self._vsg_open_device is None:
            raise RuntimeError("VSG API missing vsg_open_device()")

        self._api_loaded = True

    # ---------- required lifecycle ----------
    def open(self) -> None:
        print("[VSG] Opening VSG60A")
        self._load_api()

        # Monolith behavior: open returns dict-like with "handle"
        result = self._vsg_open_device()
        if isinstance(result, dict) and "handle" in result:
            self.handle = result["handle"]
        else:
            # be tolerant: some wrappers might return the handle directly
            self.handle = result

        # Reset to known state if available (monolith aborts on open)
        if self._vsg_abort is not None and self.handle is not None:
            try:
                self._vsg_abort(self.handle)
            except Exception:
                pass

        super().open()

    def close(self) -> None:
        try:
            if self.handle is not None:
                # Monolith closes by abort then close_device
                if self._vsg_abort is not None:
                    try:
                        self._vsg_abort(self.handle)
                    except Exception:
                        pass
                if self._vsg_close_device is not None:
                    try:
                        self._vsg_close_device(self.handle)
                    except Exception:
                        pass
        finally:
            self.handle = None
            super().close()

    # ---------- RF control ----------
    def rf_on(self) -> None:
        # Some APIs don't have explicit RF ON; monolith starts output by repeating waveform
        # We don't implicitly start here; set_cw() will push a minimal waveform if available.
        self._rf_on = True

    def rf_off(self) -> None:
        print("[VSG] RF OFF")
        if self._vsg_rf_off is not None and self.handle is not None:
            try:
                self._vsg_rf_off(self.handle)
            except Exception:
                pass
        elif self._vsg_abort is not None and self.handle is not None:
            try:
                self._vsg_abort(self.handle)
            except Exception:
                pass
        self._rf_on = False

    # ---------- Frequency/level ----------
    def set_cw(self, freq_hz: float, level_dbm: float) -> None:
        """
        Monolith-aligned:
          - set frequency and level
          - optionally set sample rate and repeat a tiny waveform
        """
        super().set_cw(freq_hz, level_dbm)

        if self.handle is None:
            self.ensure_open()

        # Prefer single-call if the API provides it
        if self._vsg_set_cw is not None:
            try:
                self._vsg_set_cw(self.handle, float(freq_hz), float(level_dbm))
                return
            except Exception:
                pass  # fall back to split path

        # Split path (exactly like the monolith's VSGCW.configure)
        if self._vsg_set_frequency is not None:
            try:
                self._vsg_set_frequency(self.handle, float(freq_hz))
            except Exception:
                pass

        if self._vsg_set_level is not None:
            try:
                self._vsg_set_level(self.handle, float(level_dbm))
            except Exception:
                pass

        # Optional: sample rate + minimal waveform (monolith sends 2-sample IQ and repeats)
        # Only do this if both functions are present.
        if self._vsg_set_sample_rate is not None and self._vsg_repeat_waveform is not None:
            try:
                # Default sample rate (match your monolith default 50e6 unless overridden elsewhere)
                sr = 50e6
                self._vsg_set_sample_rate(self.handle, float(sr))

                # Build a 2-sample waveform: I=1.0, Q=0.0
                import numpy as np
                iq = np.zeros(2, dtype=np.float32)
                iq[0] = 1.0
                self._vsg_repeat_waveform(self.handle, iq, 1)
            except Exception:
                # Non-fatal if the API differs
                pass

# test_methods/Hardware_Smoketests/1_siggenTest.py
import time

SIGGEN_KEY = "sig_gen_1"

def _log(logger, msg, colour="w"):
    try:
        logger.add_line(msg, colour=colour)
    except Exception:
        print(msg)

def _fail(logger, msg):
    try:
        logger.fail_line(msg)
    except Exception:
        print(msg)

def _pick_siggen(equip_mgr):
    """
    Prefer dict layout (equip_mgr.signal_generator['sig_gen_1']),
    but gracefully handle single-object layouts.
    """
    sg_group = getattr(equip_mgr, "signal_generator", None)
    if sg_group is None:
        return None
    if isinstance(sg_group, dict):
        return sg_group.get(SIGGEN_KEY)
    return sg_group  # single object fallback

def run(equip_mgr, _unused, logger, test_config):
    """
    Smoketest: turn on CW at freq/level, dwell, optionally leave on.
    Returns True on success, False on any error.
    """
    _log(logger, f"[1_siggenTest] Selecting signal generator: {SIGGEN_KEY}")

    siggen = _pick_siggen(equip_mgr)
    if not siggen:
        _fail(logger, "No 'signal_generator' loaded — check location_config drivers and EquipmentLoader.")
        return False

    # --- read config knobs ---
    freq_hz   = float(test_config.get("frequency_hz", 2.555e9))
    level_dbm = float(test_config.get("level_dbm", 0.0))
    dwell_s   = float(test_config.get("Sig_gen_settling_time_s", 1.0))
    leave_on  = bool(test_config.get("leave_rf_on", False))

    try:
        # open/init
        if hasattr(siggen, "open"):
            siggen.open()

        # set frequency/level (support set_cw or separate calls)
        if hasattr(siggen, "set_cw"):
            siggen.set_cw(freq_hz=freq_hz, level_dbm=level_dbm)
        else:
            if hasattr(siggen, "set_frequency"):
                siggen.set_frequency(freq_hz)
            if hasattr(siggen, "set_level"):
                siggen.set_level(level_dbm)

        # RF on → dwell → optional RF off
        if hasattr(siggen, "rf_on"):
            siggen.rf_on()
        _log(logger, f"[{SIGGEN_KEY}] CW ON @ {freq_hz/1e6:.3f} MHz / {level_dbm:.1f} dBm", colour="g")

        time.sleep(dwell_s)

        if not leave_on and hasattr(siggen, "rf_off"):
            siggen.rf_off()

        _log(logger, "PASS", colour="g")
        return True

    except Exception as e:
        _fail(logger, f"[{SIGGEN_KEY}] Signal generator smoketest failed: {e}")
        # best-effort cleanup on failure
        try:
            if hasattr(siggen, "rf_off"):
                siggen.rf_off()
        except Exception:
            pass
        return False

    finally:
        # If we are leaving RF on, don't close the device (many drivers disable RF on close)
        if not leave_on and hasattr(siggen, "close"):
            try:
                siggen.close()
            except Exception:
                pass

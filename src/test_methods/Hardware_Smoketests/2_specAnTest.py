# test_methods/Hardware_Smoketests/2_specAnTest.py
import time

SPECAN_KEY = "spec_an_1"

def run(equip_mgr, _unused, logger, test_config):
    sa_group = getattr(equip_mgr, "spectrum_analyser", None)
    sa = sa_group.get(SPECAN_KEY) if isinstance(sa_group, dict) else sa_group
    if not sa:
        logger.fail_line("BB60D (spec_an_1) not loaded.")
        return False

    cf_hz      = float(test_config.get("center_frequency_hz", 2.555e9))
    span_hz    = float(test_config.get("span_hz", 100e3))
    ref_dbm    = float(test_config.get("reference_level_dbm", 10.0))
    dwell_s    = float(test_config.get("dwell_time_s", 2.0))
    expect_dbm = float(test_config.get("expected_peak_dbm", -30.0))

    try:
        sa.open()
        sa.set_center_frequency(cf_hz)
        sa.set_span(span_hz)
        sa.set_reference_level(ref_dbm)
        time.sleep(dwell_s)

        # Either method works; driver provides at least one.
        if hasattr(sa, "get_peak_level"):
            peak_dbm = float(sa.get_peak_level())
        else:
            peak_dbm, _ = sa.peak_measure_dbm()

        logger.add_line(f"[BB60D] Peak {peak_dbm:.2f} dBm @ {cf_hz/1e6:.3f} MHz",
                        colour="g" if peak_dbm >= expect_dbm else "y")
        return peak_dbm >= expect_dbm

    except Exception as e:
        logger.fail_line(f"[BB60D] SpecAn smoketest failed: {e}")
        return False
    finally:
        try: sa.close()
        except Exception: pass

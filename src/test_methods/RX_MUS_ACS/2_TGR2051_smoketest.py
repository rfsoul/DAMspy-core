# test_methods/RX_MUS_ACS/2_TGR2051_smoketest.py

from SETI_logging.text_formatter import print_green, print_red

def run(params, radio_ctrl, equip_mgr, test_results):
    """
    Smoke test for the TGR2051 Signal Generator using the 'tgr2051' key.
    Expects params: { frequency_hz, amplitude_dbm }
    """

    # 1) Grab the already‐opened TGR2051 driver from equip_mgr
    try:
        tgr = equip_mgr.TGR2051
    except AttributeError:
        raise RuntimeError("No TGR2051 configured under key 'tgr2051'")

    # 2) Read desired frequency and amplitude from YAML params
    freq = params.get("frequency_hz")
    amp  = params.get("amplitude_dbm")

    if freq is None or amp is None:
        raise KeyError("2_TGR2051_smoketest.yaml must include 'frequency_hz' and 'amplitude_dbm'")

    try:
        # 3) Issue SCPI commands to set frequency/amplitude, enable output
        tgr.set_frequency(freq)
        current_freq_str = tgr.get_frequency()
        tgr.enable_output()
        tgr.set_amplitude(amp)
        current_amp = tgr.get_amplitude()

        # 4) Report success with both requested and actual instrument readings
        print_green(
            f"[OK] Requested: {freq/1e6:.6f} MHz @ {amp:.1f} dBm; "
            f"Instrument reports: {float(current_freq_str)/1e6:.6f} MHz @ {current_amp:.1f} dBm"
        )

    except Exception as e:
        print_red(f"[ERROR] TGR2051 smoketest failed: {e}")
        return False

    finally:
        # 5) Clean up: disable output and close the driver
        try:
            tgr.disable_output()
        except Exception:
            pass
        tgr.close()

    return True

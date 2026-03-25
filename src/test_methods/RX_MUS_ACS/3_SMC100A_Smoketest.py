# test_methods/RX_MUS_ACS/3_SMC100A_Smoketest.py

from SETI_logging.text_formatter import print_green, print_red

def run(params, radio_ctrl, equip_mgr, test_results):
    """
    Smoke test for the SMC100A Signal Generator using the 'SMC100A' key.
    Expects params: { frequency_hz, power_dbm }
    """

    # 1) Grab the already-opened SMC100A driver from equip_mgr
    try:
        smc = equip_mgr.SMC100A
    except AttributeError:
        raise RuntimeError("No SMC100A configured under key 'SMC100A'")

    # 2) Read desired frequency and power from YAML params
    freq = params.get("frequency_hz")
    power = params.get("power_dbm")

    if freq is None or power is None:
        raise KeyError("3_SMC100A_Smoketest.yaml must include 'frequency_hz' and 'power_dbm'")

    try:
        # 3) Issue SCPI commands to set frequency/power, enable output
        smc.set_frequency(freq)
        actual_freq = smc.get_frequency()
        smc.set_power(power)
        actual_power = smc.get_power()
        smc.enable_output()

        # 4) Report success with requested vs. actual readings
        print_green(
            f"[OK] Requested: {freq/1e6:.6f} MHz @ {power:.1f} dBm; "
            f"Instrument reports: {actual_freq/1e6:.6f} MHz @ {actual_power:.1f} dBm"
        )

    except Exception as e:
        print_red(f"[ERROR] SMC100A smoketest failed: {e}")
        return False

    finally:
        # 5) Clean up: disable output and close the driver
        try:
            smc.disable_output()
        except Exception:
            pass
        smc.close()

    return True

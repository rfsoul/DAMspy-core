# test_methods/RX_MUS_ACS/1_Behringer_SINAD_smoketest.py

from SETI_logging.text_formatter import print_green, print_red

def run(params, radio_ctrl, equip_mgr, test_results):
    """
    Smoke test for the Behringer SINAD meter.
    Expects params: { num_samps, ccitt }
    """

    # Pull the already‐opened SINAD driver from equip_mgr
    try:
        drv = equip_mgr.sinad_meter
    except AttributeError:
        raise RuntimeError("No SINAD meter configured under key 'sinad_meter'")

    try:
        # Measure SINAD (driver was opened by the top‐level loader)
        sinad_value = drv.measure_sinad(ccitt=params.get('ccitt', False))
        print_green(f"[OK] SINAD: {sinad_value:.2f} dB")
    except Exception as e:
        print_red(f"[ERROR] Behringer smoke test failed: {e}")
        return False
    finally:
        # Close just the SINAD driver so COM4 is freed for the next test
        drv.close()

    return True

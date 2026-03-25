# test_methods/CP50_comms_smoke_test_3.py
print("This is test 3")


import time
from SETI_logging.text_formatter import print_green, print_red

def run(params, radio_ctrl, equip_mgr, test_results):
    """
    Smoke test #1 for CP50 communications:

      1) check connection & firmware
      2) read serial number
      3) read any ADC channels (e.g. battery, RSSI) via read_adc(ch)
      4) set channel → default 1
      5) TX on/off (pa_selection=2, mic-modulation)
      6) direct-frequency tune → default 483.25 MHz
      7) read those ADC channels again at the tuned freq

    Expects in your YAML (CP50_comms_smoke_test_1.yaml) something like:

      adc_channels:
        - 0     # battery channel
        - 1     # RSSI channel
      channel:       1
      channel_delay: 0.1
      pa_selection:  2
      modulation:
        sel:  0
        tone: 0
      tx_on_time: 5
      frequency: 483.25e6
      freq_delay: 0.1
      rssi_reads: 3
      rssi_delay: 0.5
    """

    # Create per-test folder and dump the parameters
    test_results.create_test_results_path('CP50_Smoketest', 'CP50_comms_smoke_test_1')
    test_results.test_param_log(params, 'CP50_comms_smoke_test_1')

    try:
        # 1) Connection & firmware
        radio_ctrl.check_connection()
        print_green(f"[OK] Firmware version: {radio_ctrl.firmware_version_string}")

        # 2) Serial number
        sn = radio_ctrl.get_serial_no()
        print_green(f"[OK] Serial number: {sn!r}")

        # 3) First pass of ADC reads
        for ch in params.get('adc_channels', []):
            try:
                val = radio_ctrl.read_adc(ch)
                print_green(f"[OK] ADC@{ch}: {val}")
            except Exception as e:
                print_red(f"[WARN] read_adc({ch}) failed: {e}")

        # 4) Channel-based tuning
        ch = params.get('channel', 1)
        print(f"[→] Setting channel {ch}")
        radio_ctrl.set_channel(ch)
        time.sleep(params.get('channel_delay', 0.1))

        # # 5) Transmit on/off
        # print("[→] TX on (PTT)")
        # mod = params.get('modulation', {})
        # radio_ctrl.tx_on(
        #     pa_selection         = params.get('pa_selection', 2),
        #     modulation_selection = mod.get('sel', 0),
        #     modulation_tone      = mod.get('tone', 0)
        # )
        # time.sleep(params.get('tx_on_time', 5))
        # print("[→] TX off (PTT)")
        # radio_ctrl.tx_off()

        # 6) Direct-frequency tune
        f_hz = params.get('frequency', 483.25e6)
        print(f"[→] Tuning to {f_hz/1e6:.3f} MHz")
        radio_ctrl.set_frequency(f_hz)
        time.sleep(params.get('freq_delay', 0.1))
        time.sleep(0.2)
        radio_ctrl.set_frequency(f_hz)
        time.sleep(0.1)
        actual = radio_ctrl.get_frequency()
        print(f"[CP50 DEBUG] Radio now reports: {actual} Hz")


        # 7) Read ADCs again at tuned frequency
        for i in range(params.get('rssi_reads', 3)):
            for ch in params.get('adc_channels', []):
                try:
                    val = radio_ctrl.read_adc(ch)
                    print_green(f"[OK] ADC@{ch}@{f_hz/1e6:.3f} MHz: {val}")
                except Exception as e:
                    print_red(f"[WARN] read_adc({ch}) at tuned freq failed: {e}")
            time.sleep(params.get('rssi_delay', 0.5))

    except Exception as e:
        print_red(f"[ERROR] Smoke Test 1 failed: {e}")
        return False

    # ensure PTT is off
    radio_ctrl.tx_off()
    return True

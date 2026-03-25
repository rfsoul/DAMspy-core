from test_methods.radio_tests_common import RadioTest
import time
import numpy as np
import os
import sys
import yaml
from ETS_logging import text_formatter as gui

class Custom_GME_Standard(RadioTest):
    def __init__(self, equip_config, test_equipment, radio_eeprom, radio_param, radio_ctrl, test_results):
        super().__init__(equip_config, test_equipment, radio_eeprom, radio_param, radio_ctrl, test_results=test_results)
        self.standard_id = 'CUSTOM_GME_STANDARD'


    def test_1(self):
        self.test_results.test_id = 'Non Standard Test 1'
        return True

    def test_2(self):
        self.test_results.test_id = 'Non Standard Test 2'
        return True

    def ets_calibration(self, test_config):
        test_id = 'tx_cal_radio_to_spec_an'
        self.test_equip.rf_switch.tx_radio_to_spec_an(filter='TX_NO_FILTER')
        self.test_results.create_test_results_path(standards_id=self.standard_id, test_id=test_id)

        self.test_equip.signal_gen_1.transmit_from_sig_gen(rf_freq=rf_freq, rf_on=rf_on, rf_power=rf_power,
        rf_power_units=rf_power_units, lfo_freq=lfo_freq, lfo_voltage_mv=lfo_voltage_mv, lfo_on=lfo_on, fm_dev=fm_dev, fm_dev_on=fm_dev_on)

                    #fut1 = executor.submit(self.radio_receive, freq=rf_freq, sql_toggle=sql_toggle, audio_vol=audio_vol)
        # def transmit_from_sig_gen(self, rf_freq=None, rf_on=None, rf_power=None, rf_power_units=None, lfo_freq=None,
        #                           lfo_voltage_mv=None, lfo_on=None, fm_dev=None, fm_dev_on=None):





    def calculate_sinad_oscilloscope(self):
        self.test_results.test_id = 'calculate_sinad_oscilloscope'


    def rx_setup(self, test_config_opt):
        self.test_results.test_id = 'rx setup'
        input('Connect Signal Generator to radio and press enter')
        return True

    def measure_power_sig_gen(self, test_config):
        # This test will measure the power from the signal generator
        self.test_results.test_id = 'Signal Generator Power Measurement'
        self.test_equip.rf_switch.rx_sig_gen_to_radio()
        self.check_radio_serial_comms()
        self.radio_tx_off()

        # self.transmit_sig_gen_to_radio(rf_power_units='dbm',
        #                                lfo_freq=1000,
        #                                fm_dev=1500,
        #                                lfo_on=True, rf_on=True, fm_dev_on=True, sig_gen_no=1, audio_vol=10)

        # freq = 158.2e6
        # rf_power = 30 #dbm
        # volume = 20
        # self.transmit_sig_gen_to_radio(rf_freq=freq, rf_power=rf_power, rf_on=True, fm_dev_on=True,
        #                                sig_gen_no=1,
        #                                audio_vol=volume, sql_toggle=1)


        self.transmit_sig_gen_to_radio(rf_power_units='dbm',
                                       lfo_freq=1000,
                                       fm_dev=1500,
                                       lfo_on=True, rf_on=False, fm_dev_on=False, sig_gen_no=1, audio_vol=10)



        input('Press ENTER to continue')

        self.test_equip.psu.on = False
        self.test_equip.signal_gen_1.power_dbm = -68
        self.test_equip.spec_an.freq_centre = 477.2
        self.test_equip.spec_an.freq_span = 1e4

        #self.test_equip.spec_an.freq_centre(freq_mhz=477.5)

    def _freq_error_test_run(self, freq, voltage, temp, radio_power, screenshot):

        freq = float(freq)
        self.test_equip.psu.voltage = voltage

        if temp != 'NOT_USED':
            gui.print_yellow('[Notionally] Setting Temp to ' + str(temp))

        self.test_equip.psu.current_limit = self.radio_param.tx_on_current_max[radio_power]
        self.test_equip.spec_an.freq_centre = freq


        self.radio_transmit(freq=freq, power_level=radio_power)
        self.test_equip.spec_an.marker_1 = 'MAX'
        print(self.test_equip.spec_an.all_commands_set())

        freq, power = self.test_equip.spec_an.marker_1
        freq_error = freq - self.test_equip.spec_an.freq_centre

        print(f'Frequency: {self.test_equip.spec_an.freq_centre}, Freq Error: {freq_error}, Power: {power}')

        if screenshot:
            self.test_equip.spec_an.screenshot(filename='test_1')
        self.radio_tx_off()

        return True


    def frequency_error_test(self):

        with open('config\\Non_Standard_Tests\\frequency_error_test.yaml', "r") as file_descriptor:
            config_data = yaml.load(file_descriptor, Loader=yaml.FullLoader)



        config_profile = config_data['selected_config']
        config = config_data[config_profile]

        print('display on: ', config['spec_an']['display_on'])

        frequency_array = self.array_maker(config['frequency'])
        voltage_array = self.array_maker(config['radio_voltage'])
        temperature_array = self.array_maker(config['temperature'])
        radio_power_array = self.array_maker(config['radio_power'])

        self.radio_power_on()

        self.test_equip.spec_an.reset()
        self.test_equip.spec_an.disp_on = config['spec_an']['display_on']
        self.test_equip.spec_an.freq_span = config['spec_an']['frequency_span']
        self.test_equip.spec_an.attenuation = config['spec_an']['internal_attenuation']
        self.test_equip.spec_an.rbw = config['spec_an']['resolution_bw']
        self.test_equip.spec_an.vbw = config['spec_an']['video_bw']
        self.test_equip.spec_an.ref_level_offset = config['spec_an']['rf_level_offset']
        self.test_equip.spec_an.rf_level = config['spec_an']['rf_level']
        self.test_equip.spec_an.trace_peak = config['spec_an']['trace_peak']
        self.test_equip.spec_an.sweep_points = config['spec_an']['sweep_points']
        self.test_equip.spec_an.all_commands_set()

        self.check_radio_serial_comms()
        self.radio_tx_off()

        for temp in temperature_array:
            for volt in voltage_array:
                for radio_power in radio_power_array:
                    for freq in frequency_array:
                        self._freq_error_test_run(freq=freq, voltage=volt, temp=temp, radio_power=radio_power, screenshot=config['spec_an']['screenshot'])

        return True

    def CP50_comms_smoke_test(self, test_config):
        """
        Smoke test for CP50 communications using the existing radio_ctrl.
        """
        import os, time, yaml
        from ETS_logging import text_formatter as gui

        # 1) Load parameters
        test_name = 'CP50_comms_smoke_test'
        yaml_path = os.path.join(
            'config', 'test_settings_config',
            test_config, f"{test_name}.yaml"
        )
        with open(yaml_path, 'r') as fd:
            params = yaml.safe_load(fd)

        # 2) Use the existing radio control (already opened COM6)
        radio = self.radio_ctrl

        # 3) Connection check
        if params.get('check_connection', False):
            radio.check_connection()
            gui.print_green(f"[OK] Firmware version: {radio.firmware_version_string}")

        # 4) Serial number
        if params.get('read_serial_no', False):
            sn = radio.get_serial_no()
            gui.print_green(f"[OK] Serial number: {sn}")

        # 5) Pre-tune ADC measures (optional, safe‐guarded)
        if params.get('adc_batt_volts', {}).get('calibrated', False):
            try:
                batt_ch = params.get('adc_channel', 0)
                batt = radio.read_adc(batt_ch)
                gui.print_green(f"[OK] ADC@{batt_ch}: {batt}")
            except Exception as e:
                gui.print_red(f"[WARN] Failed battery ADC read: {e}")

        if params.get('read_rssi_initial', False):
            try:
                rssi_ch = params.get('rssi_channel', 1)
                r0 = radio.read_adc(rssi_ch)
                gui.print_green(f"[OK] RSSI@{rssi_ch}: {r0}")
            except Exception as e:
                gui.print_red(f"[WARN] Failed RSSI ADC read: {e}")

        # 6) Channel set
        if 'channel' in params:
            radio.set_channel(params['channel'])
            time.sleep(0.1)
            gui.print_green(f"[→] Channel set to {params['channel']}")

        # 7) PTT on/off
        if (tx := params.get('tx')):
            radio.tx_on(
                pa_selection=tx['pa_selection'],
                modulation_selection=tx['modulation_selection'],
                modulation_tone=tx['modulation_tone']
            )
            gui.print_green("[→] PTT on")
            time.sleep(tx['on_duration_s'])
            radio.ptt_off()
            gui.print_green("[→] PTT off")

        # 8) Frequency tune
        if 'frequency_hz' in params:
            f_hz = params['frequency_hz']
            radio.set_frequency(f_hz)
            time.sleep(0.1)
            gui.print_green(f"[→] Tuned to {f_hz / 1e6:.3f} MHz")

        # 9) Post-tune RSSI readings
        rssi_cfg = params.get('rssi', {})
        for _ in range(rssi_cfg.get('count', 0)):
            try:
                val = radio.read_adc(rssi_cfg.get('rssi_channel', 1))
                gui.print_green(f"[OK] RSSI @ tune: {val}")
            except Exception as e:
                gui.print_red(f"[WARN] Failed post-tune RSSI: {e}")
            time.sleep(rssi_cfg.get('delay_s', 0))

        gui.print_green("Smoke test complete")
        self.radio_ctrl.ptt_off()  # ensure final PTT‐off
        self.radio_ctrl.port.close()  # the raw serial.Serial.close()
        return True

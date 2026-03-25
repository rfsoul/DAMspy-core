import yaml
import sys
import time
from datetime import datetime
from ETS_logging import text_formatter as gui
from test_methods.radio_tests_common import RadioTest
import json
import math
import numpy as np
from decimal import * # should aviod wildcard import mentioned in PEP08
getcontext().prec = 10 # set 10 decimal values precision

class ETSI_EN301025(RadioTest):
    def __init__(self, equip_config, test_equipment, radio_eeprom, radio_param, radio_ctrl, test_results):
        super().__init__(equip_config, test_equipment, radio_eeprom, radio_param, radio_ctrl, test_results=test_results)
        self.standard_id = 'ETSI_EN301025'
        self.first_test_loop = None

    def test_1(self, config):
        self.test_results.test_id = 'ETSI_EN301025 Test 1'
        print('Testing ETSI_EN301025 Test 1...')
        return True

    def test_2(self, config):
        self.test_results.test_id = 'ETSI_EN301025 Test 2'
        print('Testing ETSI_EN301025 Test 2...')
        return False

    def list_of_tests(self): # Not a function - just to help keep track of things...

        TX_my_list = [
            self.tx_frequency_error,  # Done
            self.tx_frequency_deviation,  # Done
            self.tx_audio_frequency_response,  # Done
            self.tx_audio_frequency_harmonic_distortion_emission,  # WIP - Needs Debugging
            self.tx_adjacent_channel_power,
            self.tx_conducted_spurious_emissions_conveyed_antenna,
            self.tx_transient_frequency_behaviour_transmitter,
            self.tx_residual_modulation_transmitter,
        ]

        RX_my_list = [
            self.rx_harmonic_distortion_rated_audio_frequency_output_power,
            self.rx_audio_frequency_response,
            self.rx_maximum_usable_sensitivity,  # Done
            self.rx_co_channel_rejection, # Done
            self.rx_adjacent_channel_selectivity,  # Done
            self.rx_spurious_response_rejection,  # Done
            self.rx_intermodulation_response,  # Done
            self.rx_blocking_desensitization, # Done
            self.rx_spurious_emissions, # Done
            self.rx_receiver_radiated_spurious_emissions,
            self.rx_receiver_residual_noise_level,
            self.rx_squelch_operation,
            self.rx_squelch_hysteresis,
            self.rx_receiver_dynamic_range,
        ]

    def get_test_config(self, test_config_opt, test_id):

        if test_config_opt == 'default_config':
            with open('config\\test_settings_config\\ETSI_EN301025_DEFAULT\\' + test_id + '.yaml', "r") as file_descriptor:
                test_config = yaml.load(file_descriptor, Loader=yaml.FullLoader)[test_config_opt]
        else:
            with open('config\\test_settings_config\\ETSI_EN301025_CUSTOM\\' + test_id + '.yaml', "r") as file_descriptor:
                test_config = yaml.load(file_descriptor, Loader=yaml.FullLoader)[test_config_opt]

        return test_config

    def tx_frequency_error(self, test_config_opt):
        test_id = 'tx_frequency_error'
        self.test_equip.rf_switch.tx_radio_to_spec_an()

        self.test_results.create_test_results_path(standards_id=self.standard_id, test_id=test_id)

        self.radio_power_on()
        self.check_radio_serial_comms()
        self.radio_tx_off()

        test_config = self.get_test_config(test_config_opt=test_config_opt, test_id=test_id)
        self.test_results.test_param_log(test_config, test_config_opt)

        self.setup_spec_an(config=test_config['spec_an'])

        screenshot = test_config['spec_an']['screenshot']
        looping_arrays = self.get_looping_arrays(test_config=test_config)

        self.test_results.log_dict = {"Frequency[Hz]" : [],
                                      "Frequency_Error[Hz]" : [],
                                      "Power[dBm]" : [],
                                      "Voltage[V]" : [],
                                      "Radio_Power_Mode": [],
                                      "Timestamp": [],
                                      "Temperature[C]": [],
                                      }
        self.first_test_loop = True
        test_result = self.tx_test_executor(looping_arrays=looping_arrays, test_function=self._tx_frequency_error, screenshot=screenshot)
        self.test_results.save_log()

        return test_result

    def _tx_frequency_error(self, freq, voltage, temp, radio_power, screenshot, test_config=None):

        self.test_equip.psu.voltage = voltage


        if temp != 'NOT_USED':
            gui.print_yellow('[Notionally] Setting Temp to ' + str(temp))

        self.test_equip.psu.current_limit = self.radio_param.tx_on_current_max[radio_power]
        self.test_equip.spec_an.freq_centre = freq
        self.radio_transmit(freq=freq, power_level=radio_power)

        start = time.perf_counter()
        self.test_equip.spec_an.trace_peak = 'MAXH'
        # time.sleep(1)
        self.test_equip.spec_an.trace_peak = 'VIEW'
        self.test_equip.spec_an.marker_1 = 'MAX'
        # print(self.test_equip.spec_an.all_commands_set())
        finish_a = time.perf_counter()
        freq, power = self.test_equip.spec_an.marker_1
        finish_b = time.perf_counter()
        #print(f'Time Elapsed: {finish_a-start/1e3:.2f}ms') #, B: {finish_b-start/1e3:.2f}ms')

        freq_error = freq - self.test_equip.spec_an.freq_centre

        # self.test_equip.
        print(f'Frequency: {self.test_equip.spec_an.freq_centre/1e6:.3f} MHz, Freq Error: {freq_error:.2f} Hz, Power: {power:.2f} dBm, '
              f'Power Mode: {radio_power}, Temp: {temp}, Voltage: {voltage}')

        date_time = datetime.now().strftime("%d/%m/%Y, %H:%M:%S")
        self.test_results.log_dict["Frequency[Hz]"].append(freq)
        self.test_results.log_dict["Frequency_Error[Hz]"].append(freq_error)
        self.test_results.log_dict["Power[dBm]"].append(power)
        self.test_results.log_dict["Voltage[V]"].append(voltage)
        self.test_results.log_dict["Radio_Power_Mode"].append(radio_power)
        self.test_results.log_dict["Timestamp"].append(date_time)
        self.test_results.log_dict["Temperature[C]"].append(temp)

        if screenshot:
            date_time = datetime.now().strftime("%Y_%m_%d_%H%M_%S")
            self.test_equip.spec_an.screenshot(filename=date_time)
        self.radio_tx_off()

        return True

    def tx_frequency_deviation(self, test_config_opt):
        test_id = 'tx_frequency_deviation'
        self.test_equip.rf_switch.tx_radio_to_spec_an(filter='TX_NO_FILTER')

        self.test_results.create_test_results_path(standards_id=self.standard_id, test_id=test_id)

        self.radio_power_on()
        self.check_radio_serial_comms()
        self.radio_tx_off()

        test_config = self.get_test_config(test_config_opt=test_config_opt, test_id=test_id)
        self.test_results.test_param_log(test_config, test_config_opt)

        self.setup_spec_an(config=test_config['spec_an'])

        screenshot = test_config['spec_an']['screenshot']
        looping_arrays = self.get_looping_arrays(test_config=test_config)

        self.test_results.log_dict = {"Frequency[Hz]" : [],
                                      "Mod_Freq[Hz]" : [],
                                      # "LF_Power_nom[mV]":[],
                                      # "FM_Dev_nom[Hz]" : [],
                                      "LF_Power[mV]": [],
                                      "FM_Dev_pk_plus[Hz]": [],
                                      "FM_Dev_pk_minus[Hz]": [],
                                      "FM_Dev_pk_avg[Hz]": [],
                                      "FM_Dev_max_permissible[Hz]": [],
                                      #"TX_Power[dBm]" : [],
                                      "Radio_Voltage[V]" : [],
                                      "Radio_Power_Mode": [],
                                      "Temperature[C]": [],
                                      "Timestamp": [],
                                      "Test_Passed": [],
                                      }
        self.first_test_loop = True
        test_result = self.tx_test_executor(looping_arrays=looping_arrays, test_function=self._tx_frequency_deviation,
                                            screenshot=screenshot, test_config=test_config)
        self.test_results.save_log()

        return test_result

    def _tx_frequency_deviation(self, freq, voltage, temp, radio_power, screenshot, test_config):
        test_passed = []
        self.test_equip.psu.voltage = voltage
        self.test_equip.psu.current_limit = self.radio_param.tx_on_current_max[radio_power]


        if temp != 'NOT_USED':
            gui.print_yellow('[Notionally] Setting Temp to ' + str(temp))

        if self.first_test_loop:
            self.lf_set_power_mv = test_config['sig_gen_1']['power']['start_mv']
            self.transmit_radio_to_spec_an(freq=freq, power=radio_power, mod_source=0)
            self.first_test_loop = False

        else:
            self.transmit_radio_to_spec_an(freq=freq, power=radio_power, mod_source=0)

        # Find 3k deviation at nominal frequency
        self.test_equip.signal_gen_1.lfo_frequency = test_config['normal_test_mod']
        self.test_equip.signal_gen_1.lfo_voltage_mv = self.lf_set_power_mv
        self.test_equip.signal_gen_1.lfo_output_on = True

        fm_dev_pk_avg = float(self.test_equip.spec_an.meas_analog_demod_fm_dev()[0])
        target_fm_dev = float(test_config['normal_fm_dev'])

        found_target_fm_dev = False
        #lf_power_nominal = None
        fm_dev_nominal = None
        max_permissible_fm_dev = None

        while not found_target_fm_dev:
            print(f'Searching for Target FM Dev. LF_set_mv: {self.lf_set_power_mv}')

            if (fm_dev_pk_avg >= target_fm_dev + float(test_config['tolerance_fm_dev'])) and self.lf_set_power_mv > test_config['sig_gen_1']['power']['min_mv']:
                self.lf_set_power_mv -= float(test_config['sig_gen_1']['power']['step'])
                self.test_equip.signal_gen_1.lfo_voltage_mv = self.lf_set_power_mv


            elif fm_dev_pk_avg < target_fm_dev and self.lf_set_power_mv < test_config['sig_gen_1']['power']['max_mv']:
                self.lf_set_power_mv += test_config['sig_gen_1']['power']['step']
                self.test_equip.signal_gen_1.lfo_voltage_mv = self.lf_set_power_mv

            fm_dev_pk_avg = self.test_equip.spec_an.meas_analog_demod_fm_dev()[0]

            if target_fm_dev <=  fm_dev_pk_avg <= target_fm_dev + float(test_config['tolerance_fm_dev']):
                gui.print_green(f"Found {fm_dev_pk_avg} fm_dev @ {test_config['normal_test_mod']}kHz")
                found_target_fm_dev = True
                if screenshot:
                    date_time = datetime.now().strftime("%Y_%m_%d_%H%M_%S")
                    # self.test_equip.spec_an.screenshot(filename=str(test_config['normal_test_mod']) + '_hz_' + date_time)
                    self.test_equip.spec_an.screenshot(filename='_' + str(freq) + 'Hz_ ' + str(test_config['normal_test_mod']) + '_hz_' + date_time)

                fm_dev_nominal = fm_dev_pk_avg
                #self.lf_set_power_mv = self.lf_set_power_mv * 10 # Increase output by 20 dB

        lf_power_set = self.lf_set_power_mv * 10
                #print('Debug new lf_set_power_mv ', lf_power_set)


        mod_frequencies = test_config['lfo_frequency']

        self._tx_frequency_deviation_executor(freq, radio_power, temp, voltage,
                                              screenshot, test_config, test_passed,
                                              emu_start=0, mod_frequencies=test_config['lfo_frequency'],
                                              lf_power_set=lf_power_set,)

        self._tx_frequency_deviation_executor(freq, radio_power, temp, voltage,
                                              screenshot, test_config, test_passed,
                                              emu_start=16, mod_frequencies=test_config['lfo_frequency_high'],
                                              lf_power_set=lf_power_set/10)

        self.radio_tx_off()
        if False in test_passed:
            return False
        else:
            return True

    def _tx_frequency_deviation_executor(self, freq, radio_power, temp, voltage,
                                         screenshot, test_config, test_passed,
                                         emu_start, mod_frequencies, lf_power_set):

        for idx, mod_freq in enumerate(mod_frequencies, start=emu_start):
            mod_freq = float(mod_freq)
            self.test_equip.signal_gen_1.lfo_frequency = mod_freq
            self.test_equip.signal_gen_1.lfo_voltage_mv = lf_power_set

            fm_dev_pk_avg, fm_dev_pk_plus, fm_dev_pk_minus = self.test_equip.spec_an.meas_analog_demod_fm_dev()

            if screenshot:
                date_time = datetime.now().strftime("%Y_%m_%d_%H%M_%S")
                self.test_equip.spec_an.screenshot(filename='_' + str(freq) + 'Hz_ ' + str(mod_freq) + '_hz_' + date_time)

            if float(test_config['lf_freq_normal_range'][0]) <= mod_freq <= (float(test_config['lf_freq_normal_range'][1])):
                max_permissible_fm_dev = test_config['max_fm_dev_normal_range']

            elif float(test_config['lf_freq_high_range'][0]) <= mod_freq <= float(test_config['lf_freq_high_range'][1]):
                # attn_per_octave = 14 # Attenuation per octave

                log_base_volt = 10
                log_const_volt = 20 # Gain for Voltage is 20 * log_10_(f2/f1)

                gain_per_octave = test_config['gain_per_octave_dB'] # # Gain per octave


                no_octaves = math.log(mod_freq/float(test_config['lf_freq_high_range'][0]), 2)

                max_permissible_fm_dev = log_base_volt**(gain_per_octave*no_octaves/log_const_volt)*test_config['max_fm_dev_high_range']

                print(f'Max Permissible FM_Dev: {max_permissible_fm_dev:.2f} No_Octaves: {no_octaves:.2f} ')

            if fm_dev_pk_avg <= max_permissible_fm_dev:
                test_passed.append(True)
            else:
                test_passed.append(False)

            print(
                f'Frequency: {freq / 1e6:.3f} MHz, Mod_Freq {mod_freq:.2f} Hz, LF_Power_nom: {self.lf_set_power_mv:.2f} mV, '
                f'LF_Set_Power[mV] {lf_power_set:.2f}, fm_dev_pk_avg {fm_dev_pk_avg:.2f}, '
                f'Power Mode: {radio_power}, Temp: {temp}, Voltage: {voltage} Test_Passed: {test_passed[idx]}')

            date_time = datetime.now().strftime("%d/%m/%Y, %H:%M:%S")
            self.test_results.log_dict["Frequency[Hz]"].append(freq)
            self.test_results.log_dict["Mod_Freq[Hz]"].append(mod_freq)
            # self.test_results.log_dict["LF_Power_nom[mV]"].append(self.lf_set_power_mv)
            # self.test_results.log_dict["FM_Dev_nom[Hz]"].append(fm_dev_nominal)
            self.test_results.log_dict["LF_Power[mV]"].append(lf_power_set)
            self.test_results.log_dict["FM_Dev_pk_plus[Hz]"].append(fm_dev_pk_plus)
            self.test_results.log_dict["FM_Dev_pk_minus[Hz]"].append(fm_dev_pk_minus)
            self.test_results.log_dict["FM_Dev_pk_avg[Hz]"].append(fm_dev_pk_avg)
            self.test_results.log_dict["FM_Dev_max_permissible[Hz]"].append(max_permissible_fm_dev)
            # self.test_results.log_dict["TX_Power[dBm]"].append()
            self.test_results.log_dict["Radio_Voltage[V]"].append(voltage)
            self.test_results.log_dict["Radio_Power_Mode"].append(radio_power)
            self.test_results.log_dict["Temperature[C]"].append(temp)
            self.test_results.log_dict["Timestamp"].append(date_time)
            self.test_results.log_dict["Test_Passed"].append(test_passed[idx])

    def tx_audio_frequency_response(self, test_config_opt):

        test_id = 'tx_audio_frequency_response'
        self.test_equip.rf_switch.tx_radio_to_spec_an(filter='TX_NO_FILTER')

        self.test_results.create_test_results_path(standards_id=self.standard_id, test_id=test_id)

        self.radio_power_on()
        self.check_radio_serial_comms()
        self.radio_tx_off()

        test_config = self.get_test_config(test_config_opt=test_config_opt, test_id=test_id)
        self.test_results.test_param_log(test_config, test_config_opt)

        self.setup_spec_an(config=test_config['spec_an'])

        screenshot = test_config['spec_an']['screenshot']
        looping_arrays = self.get_looping_arrays(test_config=test_config)

        self.test_results.log_dict = {"Frequency[Hz]" : [],
                                      "Mod_Freq[Hz]" : [],
                                      # "FM_Dev_nom[Hz]" : [],
                                      # "LF_Power[mV]": [],
                                      "FM_Dev_min_permissible[dB]": [],
                                      "FM_Dev_max_permissible[dB]": [],
                                      "FM_Dev_pk_avg[dB]": [],
                                      "FM_Dev_pk_avg[Hz]": [],
                                      # "FM_Dev_pk_plus[Hz]": [],
                                      # "FM_Dev_pk_minus[Hz]": [],
                                      "Radio_Voltage[V]" : [],
                                      "Radio_Power_Mode": [],
                                      "Temperature[C]": [],
                                      "Timestamp": [],
                                      "Test_Passed": [],
                                      }
        self.first_test_loop = True
        test_result = self.tx_test_executor(looping_arrays=looping_arrays, test_function=self._tx_audio_frequency_response,
                                            screenshot=screenshot, test_config=test_config)
        self.test_results.save_log()

        return test_result

    def _tx_audio_frequency_response(self, freq, voltage, temp, radio_power, screenshot, test_config):
        test_passed = []
        self.test_equip.psu.voltage = voltage
        self.test_equip.psu.current_limit = self.radio_param.tx_on_current_max[radio_power]

        if temp != 'NOT_USED':
            gui.print_yellow('[Notionally] Setting Temp to ' + str(temp))

        if self.first_test_loop:
            self.lf_set_power_mv = test_config['sig_gen_1']['power']['start_mv']
            self.transmit_radio_to_spec_an(freq=freq, power=radio_power, mod_source=0)
            self.first_test_loop = False

        else:
            self.transmit_radio_to_spec_an(freq=freq, power=radio_power, mod_source=0)

        # Find 1k deviation at nominal frequency
        self.test_equip.signal_gen_1.lfo_frequency = test_config['normal_test_mod']
        self.test_equip.signal_gen_1.lfo_voltage_mv = self.lf_set_power_mv
        self.test_equip.signal_gen_1.lfo_output_on = True

        fm_dev_pk_avg = float(self.test_equip.spec_an.meas_analog_demod_fm_dev()[0])
        target_fm_dev = float(test_config['normal_fm_dev'])
        found_target_fm_dev = False
        # lf_power_nominal = None
        fm_dev_nominal = None
        max_permissible_fm_dev = None

        while not found_target_fm_dev:
            print(f'Searching for Target FM Dev. LF_set_mv: {self.lf_set_power_mv}')

            if (fm_dev_pk_avg >= target_fm_dev + float(test_config['tolerance_fm_dev'])) and self.lf_set_power_mv > \
                    test_config['sig_gen_1']['power']['min_mv']:
                self.lf_set_power_mv -= float(test_config['sig_gen_1']['power']['step'])
                self.test_equip.signal_gen_1.lfo_voltage_mv = self.lf_set_power_mv


            elif fm_dev_pk_avg < target_fm_dev and self.lf_set_power_mv < test_config['sig_gen_1']['power'][
                'max_mv']:
                self.lf_set_power_mv += test_config['sig_gen_1']['power']['step']
                self.test_equip.signal_gen_1.lfo_voltage_mv = self.lf_set_power_mv

            fm_dev_pk_avg = self.test_equip.spec_an.meas_analog_demod_fm_dev()[0]

            if target_fm_dev <= fm_dev_pk_avg <= target_fm_dev + float(test_config['tolerance_fm_dev']):
                gui.print_green(f"Found {fm_dev_pk_avg} fm_dev @ {test_config['normal_test_mod']}kHz")
                found_target_fm_dev = True
                if screenshot:
                    date_time = datetime.now().strftime("%Y_%m_%d_%H%M_%S")
                    self.test_equip.spec_an.screenshot(filename='_' + str(freq) + 'Hz_ ' + str(
                        test_config['normal_test_mod']) + '_hz_' + date_time)

                fm_dev_nominal = fm_dev_pk_avg

        mod_frequencies = test_config['lfo_frequency']

        for idx, mod_freq in enumerate(mod_frequencies):
            mod_freq = float(mod_freq)
            self.test_equip.signal_gen_1.lfo_frequency = mod_freq
            time.sleep(0.1) # this delay is essential as it gives spec-an some time to read new values
            fm_dev_pk_avg, fm_dev_pk_plus, fm_dev_pk_minus = self.test_equip.spec_an.meas_analog_demod_fm_dev()

            if screenshot:
                date_time = datetime.now().strftime("%Y_%m_%d_%H%M_%S")
                self.test_equip.spec_an.screenshot(filename='_' + str(freq) + 'Hz_ ' + str(mod_freq) + '_hz_' + date_time)

            log_const_freq = 20  # Gain for frequency is 20 * log_10_(f2/f1)
            log_base_freq = 10

            no_octaves = math.log(mod_freq / test_config['normal_test_mod'], 2)
            gain_per_octave = test_config['gain_per_octave_dB'] # # Gain per octave

            fm_dev_pk_avg_db = log_const_freq * math.log(fm_dev_pk_avg/fm_dev_nominal, log_base_freq)
            max_permissible_fm_dev_db = gain_per_octave * no_octaves + test_config['af_response_upper_lim']
            min_permissible_fm_dev_db = gain_per_octave * no_octaves + test_config['af_response_lower_lim']

            if min_permissible_fm_dev_db <= fm_dev_pk_avg_db <= max_permissible_fm_dev_db:
                test_passed.append(True)
            else:
                test_passed.append(False)

            print(
                f'Frequency: {freq / 1e6:.3f} MHz, Mod_Freq {mod_freq:.2f} Hz, '
                f'LF_Power[mV] {self.lf_set_power_mv}, fm_dev_pk_avg {fm_dev_pk_avg:.2f}, '
                f'fm_dev_pk_avg_db {fm_dev_pk_avg_db}, FM_Dev_min_permissible[dB]: {min_permissible_fm_dev_db:.2f}, \n FM_Dev_max_permissible[dB]: {max_permissible_fm_dev_db:.2f} '
                f'Power Mode: {radio_power}, Temp: {temp}, Voltage: {voltage} Test_Passed: {test_passed[idx]}')

            date_time = datetime.now().strftime("%d/%m/%Y, %H:%M:%S")
            self.test_results.log_dict["Frequency[Hz]"].append(freq)
            self.test_results.log_dict["Mod_Freq[Hz]"].append(mod_freq)
            # self.test_results.log_dict["FM_Dev_nom[Hz]"].append(fm_dev_nominal)
            # self.test_results.log_dict["LF_Power[mV]"].append(self.lf_set_power_mv)
            self.test_results.log_dict["FM_Dev_min_permissible[dB]"].append(min_permissible_fm_dev_db)
            self.test_results.log_dict["FM_Dev_max_permissible[dB]"].append(max_permissible_fm_dev_db)
            self.test_results.log_dict["FM_Dev_pk_avg[dB]"].append(fm_dev_pk_avg_db)
            self.test_results.log_dict["FM_Dev_pk_avg[Hz]"].append(fm_dev_pk_avg)
            # self.test_results.log_dict["FM_Dev_pk_plus[Hz]"].append(fm_dev_pk_plus)
            # self.test_results.log_dict["FM_Dev_pk_minus[Hz]"].append(fm_dev_pk_minus)
            # self.test_results.log_dict["TX_Power[dBm]"].append()
            self.test_results.log_dict["Radio_Voltage[V]"].append(voltage)
            self.test_results.log_dict["Radio_Power_Mode"].append(radio_power)
            self.test_results.log_dict["Temperature[C]"].append(temp)
            self.test_results.log_dict["Timestamp"].append(date_time)
            self.test_results.log_dict["Test_Passed"].append(test_passed[idx])

        self.radio_tx_off()
        if False in test_passed:
            return False
        else:
            return True

    def tx_audio_frequency_harmonic_distortion_emission(self, test_config_opt):

        test_id = 'tx_audio_frequency_harmonic_distortion_emission'
        self.test_equip.rf_switch.tx_radio_to_spec_an(filter='TX_NO_FILTER')

        self.test_results.create_test_results_path(standards_id=self.standard_id, test_id=test_id)

        self.radio_power_on()
        self.check_radio_serial_comms()
        self.radio_tx_off()

        test_config = self.get_test_config(test_config_opt=test_config_opt, test_id=test_id)
        self.test_results.test_param_log(test_config, test_config_opt)

        self.setup_spec_an(config=test_config['spec_an'])

        screenshot = test_config['spec_an']['screenshot']
        looping_arrays = self.get_looping_arrays(test_config=test_config)

        self.test_results.log_dict = {"Frequency[Hz]" : [],
                                      "Mod_Freq[Hz]" : [],
                                      "AF_Measured[Hz]": [],
                                      # "FM_Dev_nom[Hz]" : [],
                                      "LF_Power[mV]": [],
                                      "FM_Dev_pk_avg[Hz]": [],
                                      "Total_Harmonic_Distortion": [],
                                      "Radio_Voltage[V]" : [],
                                      "Radio_Power_Mode": [],
                                      "Temperature[C]": [],
                                      "Timestamp": [],
                                      "Test_Passed": [],
                                      }
        self.first_test_loop = True
        test_result = self.tx_test_executor(looping_arrays=looping_arrays, test_function=self._tx_audio_frequency_harmonic_distortion_emission,
                                            screenshot=screenshot, test_config=test_config)
        self.test_results.save_log()

        return test_result

    def find_fm_dev_target(self, target_fm_dev, tolerance_fm_dev, max_mv, min_mv, step):
        # self.test_equip.spec_an.continuous_sweep = False
        found_target_fm_dev = False
        while not found_target_fm_dev:
            print(f'Searching for Target FM Dev. LF_set_mv: {self.lf_set_power_mv}')
            fm_dev_pk_avg = self.test_equip.spec_an.meas_analog_demod_fm_dev()[0]

            if (fm_dev_pk_avg >= target_fm_dev + tolerance_fm_dev) and self.lf_set_power_mv > min_mv:
                self.lf_set_power_mv -= step
                self.test_equip.signal_gen_1.lfo_voltage_mv = self.lf_set_power_mv

            elif fm_dev_pk_avg < target_fm_dev and self.lf_set_power_mv < max_mv:
                self.lf_set_power_mv += step
                self.test_equip.signal_gen_1.lfo_voltage_mv = self.lf_set_power_mv

            fm_dev_pk_avg = self.test_equip.spec_an.meas_analog_demod_fm_dev()[0]

            if target_fm_dev <= fm_dev_pk_avg <= target_fm_dev + tolerance_fm_dev:
                gui.print_green(f"Found {fm_dev_pk_avg} fm_dev @ {self.test_equip.signal_gen_1.lfo_frequency} Hz")
                found_target_fm_dev = True
                # self.test_equip.spec_an.continuous_sweep = True
                self.test_equip.spec_an.all_commands_set()

                return fm_dev_pk_avg

    def _tx_audio_frequency_harmonic_distortion_emission(self, freq, voltage, temp, radio_power, screenshot, test_config):

        test_passed = []
        self.test_equip.psu.voltage = voltage
        self.test_equip.psu.current_limit = self.radio_param.tx_on_current_max[radio_power]

        if temp != 'NOT_USED':
            gui.print_yellow('[Notionally] Setting Temp to ' + str(temp))

        if self.first_test_loop:
            self.lf_set_power_mv = test_config['sig_gen_1']['power']['start_mv']
            self.transmit_radio_to_spec_an(freq=freq, power=radio_power, mod_source=0)
            self.first_test_loop = False

        else:
            self.transmit_radio_to_spec_an(freq=freq, power=radio_power, mod_source=0)

        # self.test_equip.signal_gen_1.lfo_frequency = test_config['normal_test_mod']
        self.test_equip.signal_gen_1.lfo_voltage_mv = self.lf_set_power_mv
        self.test_equip.signal_gen_1.lfo_output_on = True

        mod_frequencies = test_config['lfo_frequency']


        for idx, mod_freq in enumerate(mod_frequencies):
            mod_freq = float(mod_freq)
            self.test_equip.signal_gen_1.lfo_frequency = mod_freq
            self.lf_set_power_mv = test_config['sig_gen_1']['power']['start_mv']
            self.test_equip.signal_gen_1.lfo_voltage_mv = self.lf_set_power_mv
            fm_dev_pk_avg = self.find_fm_dev_target(target_fm_dev=mod_freq*3.0,
                                    tolerance_fm_dev=test_config['tolerance_fm_dev'],
                                    max_mv=test_config['sig_gen_1']['power']['max_mv'],
                                    min_mv=test_config['sig_gen_1']['power']['min_mv'],
                                    step=test_config['sig_gen_1']['power']['step'])

            self.test_equip.spec_an.tx_audio_frequency_harmonic_distortion_setup()
            AF_Measured = self.test_equip.spec_an.query_AF_with_ADEM()
            THD = self.test_equip.spec_an.query_THD_measurement()

            if THD <= 10: # THD less than 10%
                test_passed.append(True)
            else:
                test_passed.append(False)


            print(f'Frequency: {freq / 1e6:.3f} MHz, THD: {THD}%, AF_Measured: {AF_Measured}, Mod_Freq {mod_freq:.2f} Hz'
                  f'LF_Set_Power[mV] {self.lf_set_power_mv:.2f} mV, fm_dev_pk_avg {fm_dev_pk_avg:.2f},'
                  f'Power Mode: {radio_power}, Temp: {temp}, Voltage: {voltage} Test_Passed: {test_passed[idx]}')

            date_time = datetime.now().strftime("%d/%m/%Y, %H:%M:%S")
            self.test_results.log_dict["Frequency[Hz]"].append(freq)
            self.test_results.log_dict["Mod_Freq[Hz]"].append(mod_freq)
            self.test_results.log_dict["AF_Measured[Hz]"].append(AF_Measured)
            self.test_results.log_dict["LF_Power[mV]"].append(self.lf_set_power_mv)
            self.test_results.log_dict["FM_Dev_pk_avg[Hz]"].append(fm_dev_pk_avg)
            self.test_results.log_dict["Total_Harmonic_Distortion[%]"].append(THD)
            # self.test_results.log_dict["TX_Power[dBm]"].append()
            self.test_results.log_dict["Radio_Voltage[V]"].append(voltage)
            self.test_results.log_dict["Radio_Power_Mode"].append(radio_power)
            self.test_results.log_dict["Temperature[C]"].append(temp)
            self.test_results.log_dict["Timestamp"].append(date_time)
            self.test_results.log_dict["Test_Passed"].append(test_passed[idx])

        self.radio_tx_off()
        if False in test_passed:
            return False
        else:
            return True

    def tx_adjacent_channel_power(self, test_config_opt):

        test_id = 'tx_adjacent_channel_power'
        self.test_equip.rf_switch.tx_radio_to_spec_an(filter='TX_NO_FILTER')

        self.test_results.create_test_results_path(standards_id=self.standard_id, test_id=test_id)

        self.radio_power_on()
        self.check_radio_serial_comms()
        self.radio_tx_off()

        test_config = self.get_test_config(test_config_opt=test_config_opt, test_id=test_id)
        self.test_results.test_param_log(test_config, test_config_opt)

        self.setup_spec_an(config=test_config['spec_an']['analog_demod'])

        screenshot = test_config['spec_an']['analog_demod']['screenshot']
        looping_arrays = self.get_looping_arrays(test_config=test_config)

        self.test_results.log_dict = {"Frequency[Hz]" : [],
                                      "Carrier_Power[dBm]" : [],
                                      "ACP+[dBc]" : [],
                                      "ACP-[dBc]" : [],
                                      "Radio_Voltage[V]" : [],
                                      "Radio_Power_Mode": [],
                                      "Temperature[C]": [],
                                      "Timestamp": [],
                                      "Test_Passed": [],
                                      }

        self.first_test_loop = True
        test_result = self.tx_test_executor(looping_arrays=looping_arrays, test_function=self._tx_adjacent_channel_power,
                                            screenshot=screenshot, test_config=test_config)
        self.test_results.save_log()

        return test_result

    def _tx_adjacent_channel_power(self, freq, voltage, temp, radio_power, screenshot, test_config):

        test_passed = []
        self.test_equip.psu.voltage = voltage
        self.test_equip.psu.current_limit = self.radio_param.tx_on_current_max[radio_power]

        if temp != 'NOT_USED':
            gui.print_yellow('[Notionally] Setting Temp to ' + str(temp))

        if self.first_test_loop:
            self.lf_set_power_mv = test_config['sig_gen_1']['power']['start_mv']
            self.transmit_radio_to_spec_an(freq=freq, power=radio_power, mod_source=0)
            self.first_test_loop = False

        else:
            self.transmit_radio_to_spec_an(freq=freq, power=radio_power, mod_source=0)

        # Find 1k deviation at nominal frequency
        self.test_equip.signal_gen_1.lfo_frequency = test_config['normal_test_mod']
        self.test_equip.signal_gen_1.lfo_voltage_mv = self.lf_set_power_mv
        self.test_equip.signal_gen_1.lfo_output_on = True

        fm_dev_pk_avg = float(self.test_equip.spec_an.meas_analog_demod_fm_dev()[0])
        target_fm_dev = float(test_config['normal_fm_dev'])

        self.find_fm_dev_target(target_fm_dev=test_config['normal_fm_dev'],
                                    tolerance_fm_dev=test_config['tolerance_fm_dev'],
                                    max_mv=test_config['sig_gen_1']['power']['max_mv'],
                                    min_mv=test_config['sig_gen_1']['power']['min_mv'],
                                    step=test_config['sig_gen_1']['power']['step'])
        #
        #
        # found_target_fm_dev = False
        #
        # while not found_target_fm_dev:
        #     print(f'Searching for Target FM Dev. LF_set_mv: {self.lf_set_power_mv}')
        #
        #     if (fm_dev_pk_avg >= target_fm_dev + float(test_config['tolerance_fm_dev'])) and self.lf_set_power_mv > \
        #             test_config['sig_gen_1']['power']['min_mv']:
        #         self.lf_set_power_mv -= float(test_config['sig_gen_1']['power']['step'])
        #         self.test_equip.signal_gen_1.lfo_voltage_mv = self.lf_set_power_mv
        #
        #
        #     elif fm_dev_pk_avg < target_fm_dev and self.lf_set_power_mv < test_config['sig_gen_1']['power'][
        #         'max_mv']:
        #         self.lf_set_power_mv += test_config['sig_gen_1']['power']['step']
        #         self.test_equip.signal_gen_1.lfo_voltage_mv = self.lf_set_power_mv
        #
        #     fm_dev_pk_avg = self.test_equip.spec_an.meas_analog_demod_fm_dev()[0]
        #
        #     if target_fm_dev <= fm_dev_pk_avg <= target_fm_dev + float(test_config['tolerance_fm_dev']):
        #         gui.print_green(f"Found {fm_dev_pk_avg} fm_dev @ {test_config['normal_test_mod']}kHz")
        #         found_target_fm_dev = True
        #         if screenshot:
        #             date_time = datetime.now().strftime("%Y_%m_%d_%H%M_%S")
        #             self.test_equip.spec_an.screenshot(filename='_' + str(freq) + 'Hz_ ' + str(
        #                 test_config['normal_test_mod']) + '_hz_' + date_time)


        self.setup_spec_an(config=test_config['spec_an']['acp'])
        self.transmit_radio_to_spec_an(freq=freq, power=radio_power, mod_source=0)
        time.sleep(8)
        acp_list = self.test_equip.spec_an.get_adjacent_channel_power_meas()

        acp_screenshot = test_config['spec_an']['acp']['screenshot']

        if float(acp_list[1]) <= -70.0 and float(acp_list[2]) <= -70.0:
            test_passed.append(True)
        else:
            test_passed.append(False)

        print(f'Frequency: {self.test_equip.spec_an.freq_centre/1e6:.3f} MHz, Power: {float(acp_list[0]):.2f} dBm,'
              f'ACP+: {float(acp_list[1]):.2f}, ACP-: {float(acp_list[2]):.2f}, Temp: {temp}, Voltage: {voltage}')

        date_time = datetime.now().strftime("%d/%m/%Y, %H:%M:%S")
        self.test_results.log_dict["Frequency[Hz]"].append(freq)
        self.test_results.log_dict["Carrier_Power[dBm]"].append(acp_list[0])
        self.test_results.log_dict["ACP+[dBc]"].append(acp_list[1])
        self.test_results.log_dict["ACP-[dBc]"].append(acp_list[2])
        self.test_results.log_dict["Radio_Voltage[V]"].append(voltage)
        self.test_results.log_dict["Radio_Power_Mode"].append(radio_power)
        self.test_results.log_dict["Timestamp"].append(date_time)
        self.test_results.log_dict["Temperature[C]"].append(temp)
        self.test_results.log_dict["Test_Passed"].append(test_passed)

        if acp_screenshot:
            date_time = datetime.now().strftime("%Y_%m_%d_%H%M_%S")
            self.test_equip.spec_an.screenshot(filename='_' + str(freq) + 'Hz_ ' + str(
                test_config['normal_test_mod']) + '_hz_' + date_time)

        self.radio_tx_off()
        if False in test_passed:
            return False
        else:
            return True

        # ## Using hardcoded values for now...
        # mod_freq = 1000
        #
        # # self.test_equip.spec_an.tx_demod_setup()
        # self.transmit_radio_to_spec_an(freq=freq, power=radio_power)
        # self.transmit_sig_gen_to_radio(lfo_freq=mod_freq, lfo_voltage_mv=30,sig_gen_no=1, lfo_on=True)
        #
        # self.test_equip.signal_gen_1.lfo_frequency = mod_freq
        # self.lf_set_power_mv = test_config['sig_gen_1']['power']['start_mv']
        #
        # fm_dev_pk_avg = self.find_fm_dev_target(target_fm_dev=1500,
        #                                         tolerance_fm_dev=test_config['tolerance_fm_dev'],
        #                                         max_mv=test_config['sig_gen_1']['power']['max_mv'],
        #                                         min_mv=test_config['sig_gen_1']['power']['min_mv'],
        #                                         step=test_config['sig_gen_1']['power']['step'])

        # self.test_equip.spec_an.tx_adjacent_channel_power_setup()
        # time.sleep(8) # As per Aaron's Code - just replicating for now...

        # self.transmit_radio_to_spec_an(freq=freq, power=radio_power, mod_source=0)
        # self.test_equip.spec_an.reset(val=True)
        # ACP = self.test_equip.spec_an.get_adjacent_channel_power_meas()
        # print("DEBUG ACP: ", ACP)



        # for sweeps in test_config['spec_an']['subrange_sweeps']:
        #     self.radio_transmit(freq=freq, power_level=radio_power, mod_source=0)
        #     self.setup_spec_an(config=test_config['spec_an']['subrange_sweeps'][sweeps])
        #    # time.sleep(3)
        #
        #     self.test_equip.spec_an.all_commands_set()
        #     # self.test_equip.spec_an.get_single_sweep()
        #     time.sleep(45)
        #     self.test_equip.spec_an.set_disp_trac_mode(mode='VIEW')
        #     self.test_equip.spec_an.marker_1 = 'MAX'
        #     self.test_equip.spec_an.marker_2 = 'MAX'
        #     self.test_equip.spec_an.marker_2 = 'MAX:NEXT'
        #     freq1, power1 = self.test_equip.spec_an.marker_1
        #     freq2, power2 = self.test_equip.spec_an.marker_2
        #
        #
        #     date_time = datetime.now().strftime("%Y_%m_%d_%H%M_%S")
        #     self.test_equip.spec_an.screenshot(filename=date_time)

    def tx_conducted_spurious_emissions_conveyed_antenna(self, test_config_opt):
        test_id = 'tx_conducted_spurious_emissions_conveyed_antenna'


        self.test_results.create_test_results_path(standards_id=self.standard_id, test_id=test_id)

        self.radio_power_on()
        self.check_radio_serial_comms()
        self.radio_tx_off()

        test_config = self.get_test_config(test_config_opt=test_config_opt, test_id=test_id)
        self.test_results.test_param_log(test_config, test_config_opt)

        # self.setup_spec_an(config=test_config['spec_an'])

        screenshot = test_config['spec_an']['screenshot']
        looping_arrays = self.get_looping_arrays(test_config=test_config)

        self.test_results.log_dict = {"Frequency[MHz]" : [],
                                      "Sub_Range[]" : [],
                                      "Spurious_Emission_1[MHz]" : [],
                                      "Level_1[dBm]" : [],
                                      "Spurious_Emission_2[MHz]" : [],
                                      "Level_2[dBm]" : [],
                                      "Radio_Voltage[V]" : [],
                                      "Radio_Power_Mode": [],
                                      "Temperature[C]": [],
                                      "Timestamp": [],
                                      "Test_Passed": [],
                                      }

        test_result = self.tx_test_executor(looping_arrays=looping_arrays, test_function=self._tx_conducted_spurious_emissions_conveyed_antenna,
                                            screenshot=screenshot, test_config=test_config)
        self.test_results.save_log()

        return test_result

    def _tx_conducted_spurious_emissions_conveyed_antenna(self, freq, voltage, temp, radio_power, screenshot, test_config):

        test_passed = []
        self.test_equip.psu.voltage = voltage
        self.test_equip.psu.current_limit = self.radio_param.tx_on_current_max[radio_power]

        if temp != 'NOT_USED':
            gui.print_yellow('[Notionally] Setting Temp to ' + str(temp))

        # self.transmit_radio_to_spec_an(freq=freq, power=radio_power, mod_source=0)
        # self.test_equip.spec_an.reset(val=True)
        for idx, sweeps in enumerate(test_config['spec_an']['subrange_sweeps'], start=1):

            self.test_equip.rf_switch.tx_radio_to_spec_an(\
            filter=test_config['spec_an']['subrange_sweeps'][sweeps]['filter'])
            time.sleep(1) # wait for switch action
            self.setup_spec_an(config=test_config['spec_an']['subrange_sweeps'][sweeps])
            self.radio_transmit(freq=freq, power_level=radio_power, mod_source=0)
           # time.sleep(3)


            self.test_equip.spec_an.all_commands_set()
            # self.test_equip.spec_an.get_single_sweep()
            time.sleep(5)
            self.test_equip.spec_an.trace_peak ='VIEW'
            self.test_equip.spec_an.marker_1 = 'MAX'
            self.test_equip.spec_an.marker_2 = 'MAX'
            self.test_equip.spec_an.marker_2 = 'MAX:NEXT'
            freq1, power1 = self.test_equip.spec_an.marker_1
            freq2, power2 = self.test_equip.spec_an.marker_2


            if not self.test_equip.spec_an.check_limit_line_pass_or_fail():
                test_passed.append(True)
            else:
                test_passed.append(False)

            #
            # print(f"(freq1, power1): {(freq1, power1)}")
            # print(f"(freq2, power2): {(freq2, power2)}")


            date_time = datetime.now().strftime("%Y_%m_%d_%H%M_%S")
            self.test_results.log_dict["Frequency[MHz]"].append(freq/1e6)
            self.test_results.log_dict["Sub_Range[]"].append(idx)
            self.test_results.log_dict["Spurious_Emission_1[MHz]"].append(freq1/1e6)
            self.test_results.log_dict["Level_1[dBm]"].append(power1)
            self.test_results.log_dict["Spurious_Emission_2[MHz]"].append(freq2/1e6)
            self.test_results.log_dict["Level_2[dBm]"].append(power2)
            self.test_results.log_dict["Radio_Voltage[V]"].append(voltage)
            self.test_results.log_dict["Radio_Power_Mode"].append(radio_power)
            self.test_results.log_dict["Timestamp"].append(date_time)
            self.test_results.log_dict["Temperature[C]"].append(temp)
            self.test_results.log_dict["Test_Passed"].append(test_passed[idx-1])

            self.test_equip.spec_an.screenshot(filename=date_time)

        self.radio_tx_off()
        if False in test_passed:
            return False
        else:
            return True

    def tx_transient_frequency_behaviour_transmitter(self, test_config_opt):
        test_id = 'tx_transient_frequency_behaviour_transmitter'
        self.test_equip.rf_switch.tx_radio_to_spec_an()

        self.test_results.create_test_results_path(standards_id=self.standard_id, test_id=test_id)

        self.radio_power_on()
        self.check_radio_serial_comms()
        self.radio_tx_off()

        test_config = self.get_test_config(test_config_opt=test_config_opt, test_id=test_id)
        self.test_results.test_param_log(test_config, test_config_opt)

        self.setup_spec_an(config=test_config['spec_an'])

        screenshot = test_config['spec_an']['screenshot']
        looping_arrays = self.get_looping_arrays(test_config=test_config)

        self.test_results.log_dict = {"Frequency[Hz]": [],
                                      "Frequency_Error[Hz]": [],
                                      "Power[dBm]": [],
                                      "Voltage[V]": [],
                                      "Radio_Power_Mode": [],
                                      "Timestamp": [],
                                      "Temperature[C]": [],
                                      }

        test_result = self.tx_test_executor(looping_arrays=looping_arrays, test_function=self._tx_transient_frequency_behaviour_transmitter,
                                            screenshot=screenshot)
        self.test_results.save_log()

        return test_result

    def _tx_transient_frequency_behaviour_transmitter(self, freq, voltage, temp, radio_power, screenshot, test_config=None):

        self.test_equip.psu.voltage = voltage


        if temp != 'NOT_USED':
            gui.print_yellow('[Notionally] Setting Temp to ' + str(temp))

        self.test_equip.psu.current_limit = self.radio_param.tx_on_current_max[radio_power]
        self.test_equip.spec_an.freq_centre = freq
        self.radio_transmit(freq=freq, power_level=radio_power)

        start = time.perf_counter()
        self.test_equip.spec_an.marker_1 = 'MAX'
        # print(self.test_equip.spec_an.all_commands_set())
        finish_a = time.perf_counter()
        freq, power = self.test_equip.spec_an.marker_1
        finish_b = time.perf_counter()
        #print(f'Time Elapsed: {finish_a-start/1e3:.2f}ms') #, B: {finish_b-start/1e3:.2f}ms')

        freq_error = freq - self.test_equip.spec_an.freq_centre

        # self.test_equip.
        print(f'Frequency: {self.test_equip.spec_an.freq_centre/1e6:.3f} MHz, Freq Error: {freq_error:.2f} Hz, Power: {power:.2f} dBm, '
              f'Power Mode: {radio_power}, Temp: {temp}, Voltage: {voltage}')

        date_time = datetime.now().strftime("%d/%m/%Y, %H:%M:%S")
        self.test_results.log_dict["Frequency[Hz]"].append(freq)
        self.test_results.log_dict["Frequency_Error[Hz]"].append(freq_error)
        self.test_results.log_dict["Power[dBm]"].append(power)
        self.test_results.log_dict["Voltage[V]"].append(voltage)
        self.test_results.log_dict["Radio_Power_Mode"].append(radio_power)
        self.test_results.log_dict["Timestamp"].append(date_time)
        self.test_results.log_dict["Temperature[C]"].append(temp)

        if screenshot:
            date_time = datetime.now().strftime("%Y_%m_%d_%H%M_%S")
            self.test_equip.spec_an.screenshot(filename=date_time)
        self.radio_tx_off()

        return True


    def tx_residual_modulation_transmitter(self):
        pass

    def rx_harmonic_distortion_rated_audio_frequency_output_power(self):
        pass

    def rx_audio_frequency_response(self):
        pass




    def rx_maximum_usable_sensitivity(self, test_config_opt):

        test_id = 'rx_maximum_usable_sensitivity'
        #self.test_equip.rf_switch.rx_sig_gen_to_radio()

        self.test_results.create_test_results_path(standards_id=self.standard_id, test_id=test_id)
        test_config = self.get_test_config(test_config_opt=test_config_opt, test_id=test_id)
        self.test_results.test_param_log(test_config, test_config_opt)

        # self.test_equip.soundcard.num_samples = test_config['soundcard']['no_samples']
        # self.test_equip.soundcard.psophometric_weighting = test_config['soundcard']['psophometric_weighting']

        self.transmit_sig_gen_to_radio(rf_power_units=test_config['sig_gen_1']['power']['units'],
                                       lfo_freq=test_config['sig_gen_1']['lfo_frequency'],
                                       fm_dev=test_config['sig_gen_1']['fm_dev'],
                                       lfo_on=False, rf_on=False, fm_dev_on=False, sig_gen_no=1)

        self.transmit_sig_gen_to_radio(lfo_on=False, rf_on=False, fm_dev_on=False, sig_gen_no=2)


        # self.test_equip.signal_gen_1.fm_dev_on = True


        self.check_radio_serial_comms()
        self.radio_tx_off()
        looping_arrays = self.get_looping_arrays(test_config=test_config)
        self.first_test_loop = True

        self.test_results.log_dict = {"Frequency[Hz]": [],
                                      "SINAD[dB]": [],
                                      "SINAD Target[dB]": [],
                                      "Rx Power[dBuv]": [],
                                      "Voltage[V]": [],
                                      "Temperature[C]": [],
                                      "Timestamp": [],
                                      "Test_Passed": [],
                                      "Rx Power (dBm)": [],
                                      "Target_Sensitivity (dBm)": [],
                                      }

        test_result = self.rx_test_executor(looping_arrays=looping_arrays,
                                            test_function=self._rx_maximum_usable_sensitivity,
                                            test_config=test_config)

        self.test_results.save_log()
        self.test_equip.signal_gen_1.rf_power_on = False

        return test_result


    def _rx_maximum_usable_sensitivity(self, freq, voltage, temp, rx_radio_power, test_config):
        self.test_equip.psu.voltage = voltage

        sinad_target = float(test_config['sinad_target'])
        sinad_tolerance = float(test_config['sinad_tolerance'])
        rx_pwr_offset = float(test_config['sig_gen_1']['power']['offset'])
        dbuv_to_dbm = float(test_config['dbuv_to_dbm'])
        sensitivity_target = float(test_config['sensitivity_target'])

        if temp != 'NOT_USED':
            gui.print_yellow('[Notionally] Setting Temp to ' + str(temp))

        if self.first_test_loop:
            self.rx_set_power = test_config['sig_gen_1']['power']['start']
            self.rx_set_offset = -test_config['sig_gen_1']['power']['offset']
            self.transmit_sig_gen_to_radio(rf_freq=freq, rf_power=self.rx_set_power,
                                           rf_power_offset=self.rx_set_offset,
                                           rf_on=True, fm_dev_on=True, sig_gen_no=1,
                                           audio_vol=int(test_config['radio_volume']), sql_toggle=1)
            self.first_test_loop = False
            print('Sig Gen 1 should now be transmitting...')
            time.sleep(3)

        else:
            self.transmit_sig_gen_to_radio(rf_freq=freq, audio_vol=int(test_config['radio_volume']), sig_gen_no=1, sql_toggle=1)

        sinad, self.rx_set_power = self.find_sinad_power(target_sinad=sinad_target,
                                                         set_power=self.rx_set_power,
                                                         max_power=test_config['sig_gen_1']['power']['max'],
                                                         min_power=test_config['sig_gen_1']['power']['min'],
                                                         power_step=test_config['sig_gen_1']['power']['step'],
                                                         sinad_tolerance=sinad_tolerance)

        rx_radio_power_dBm = dbuv_to_dbm - self.rx_set_power - rx_pwr_offset
        if abs(sinad-sinad_target) < sinad_tolerance and self.rx_set_power <= test_config['sig_gen_1']['power']['thresh']\
                and rx_radio_power_dBm < sensitivity_target:
            test_passed = True
        else:
            test_passed = False

        date_time = datetime.now().strftime("%d/%m/%Y, %H:%M:%S")
        print(f'Frequency: {self.test_equip.signal_gen_1.rf_frequency/1e6:.3f} MHz, SINAD: {sinad:.2f} dB, Rx Power: {self.rx_set_power} dBuv ')
        self.test_results.log_dict["Frequency[Hz]"].append(freq)
        self.test_results.log_dict["SINAD[dB]"].append(sinad)
        self.test_results.log_dict["SINAD Target[dB]"].append(sinad_target)
        self.test_results.log_dict["Rx Power[dBuv]"].append(self.rx_set_power)
        self.test_results.log_dict["Voltage[V]"].append(voltage)
        self.test_results.log_dict["Temperature[C]"].append(temp)
        self.test_results.log_dict["Timestamp"].append(date_time)
        self.test_results.log_dict["Test_Passed"].append(test_passed)
        self.test_results.log_dict["Target_Sensitivity (dBm)"].append(sensitivity_target)
        self.test_results.log_dict["Rx Power (dBm)"].append(rx_radio_power_dBm)

        return test_passed

    def rx_co_channel_rejection(self, test_config_opt):

        test_id = 'rx_co_channel_rejection'
        #self.test_equip.rf_switch.rx_sig_gen_to_radio()
        self.test_results.create_test_results_path(standards_id=self.standard_id, test_id=test_id)
        test_config = self.get_test_config(test_config_opt=test_config_opt, test_id=test_id)
        self.test_results.test_param_log(test_config, test_config_opt)

        self.transmit_sig_gen_to_radio(
            rf_power_units=test_config['sig_gen_1']['power']['units'],
            lfo_freq=test_config['sig_gen_1']['lfo_frequency'],
            fm_dev=test_config['sig_gen_1']['fm_dev'],
            lfo_on=False, rf_on=False, fm_dev_on=False, sig_gen_no=1)

        self.transmit_sig_gen_to_radio(
            rf_power_units=test_config['sig_gen_2']['power']['units'],
            lfo_on=False, rf_on=False, fm_dev_on=False, sig_gen_no=2)

        self.check_radio_serial_comms()
        self.radio_tx_off()
        looping_arrays = self.get_looping_arrays(test_config=test_config)
        self.first_test_loop = True

        self.test_results.log_dict = {
            "RX_Frequency[Hz]": [],
            "Interfere_Frequency[Hz]": [],
            # "Interfere_Frequency_C[Hz]": [],
            "Interfere_Power[dBuv]": [],
            # "Interfere_Power_C[dBuv]": [],
            "Co-Channel_Rej[dB]": [],
            "RX_Power[dBuv]": [],
            "SINAD[dB]": [],
            "Radio_Voltage[V]": [],
            "Temperature[C]": [],
            "Timestamp": [],
            "Test_Passed": [],
        }

        test_result = self.rx_test_executor(looping_arrays=looping_arrays,
                                            test_function=self._rx_co_channel_rejection,
                                            test_config=test_config)

        self.test_results.save_log()
        self.test_equip.signal_gen_1.rf_power_on = False
        self.test_equip.signal_gen_2.rf_power_on = False
        # self.test_equip.signal_gen_3.rf_power_on = False

        return test_result

    def _rx_co_channel_rejection(self, freq, voltage, temp, rx_radio_power, test_config):
        test_passed = []
        self.test_equip.psu.voltage = voltage

        if temp != 'NOT_USED':
            gui.print_yellow('[Notionally] Setting Temp to ' + str(temp))

        if self.first_test_loop:
            self.rx_set_power = test_config['sig_gen_1']['power']['start']
            self.rx_set_offset1 = -test_config['sig_gen_1']['power']['offset']
            self.transmit_sig_gen_to_radio(rf_freq=freq, rf_power=self.rx_set_power,
                                           rf_power_offset=self.rx_set_offset1,
                                           rf_on=True, fm_dev_on=True,sig_gen_no=1,
                                           audio_vol=int(test_config['radio_volume']), sql_toggle=1 )
            self.first_test_loop = False
        else:
            self.transmit_sig_gen_to_radio(rf_freq=freq, audio_vol=int(test_config['radio_volume']),
                                           sig_gen_no=1, sql_toggle=1)

        sinad, self.rx_set_power = self.find_sinad_power(target_sinad=test_config['sinad_target'],
                                                         set_power=self.rx_set_power,
                                                         max_power=test_config['sig_gen_1']['power']['max'],
                                                         min_power=test_config['sig_gen_1']['power']['min'],
                                                         power_step=test_config['sig_gen_1']['power']['step'])

        if not sinad >= test_config['sinad_target']:
            gui.print_red('20dB SINAD Not Reached')
            test_passed = False
            return test_passed

        #interference_power_thresh = self.rx_set_power + test_config['intermod_resp_ratio']

        for idx in range(len(test_config['sig_gen_2']['interference_offset'])):
            interference_freq = freq + (float(test_config['sig_gen_2']['interference_offset'][idx]))
            # interference_freq = Decimal(freq) + Decimal((float(test_config['sig_gen_2']['interference_offset'][idx])))
            # interference_freq = Decimal(freq + (float(test_config['sig_gen_2']['interference_offset'][idx])))
            # interference_freq_c = freq + float(test_config['sig_gen_3']['interference_offset'][idx])

            self.interfere_power = test_config['sig_gen_2']['power']['start']
            self.rx_set_offset2 = -test_config['sig_gen_2']['power']['offset']
            # self.rx_set_offset3 = -test_config['sig_gen_3']['power']['offset']

# /            self.transmit_sig_gen_to_radio(rf_freq=interference_freq_b,
#                                            rf_power=self.interfere_power,
#                                            rf_power_offset=self.rx_set_offset2,
#                                            rf_on=True, sig_gen_no=2)
            self.transmit_sig_gen_to_radio(rf_freq=interference_freq,
                                           rf_power=self.interfere_power,
                                           rf_power_offset=self.rx_set_offset2,
                                           lfo_freq=test_config['sig_gen_2']['lfo_frequency'],
                                           fm_dev=test_config['sig_gen_2']['fm_dev'],
                                           rf_on=True, fm_dev_on=True, sig_gen_no=2)

            sinad = self.get_sinad()

            while True:
                if sinad >= test_config['min_sinad'] and self.interfere_power < test_config['sig_gen_2']['power']['max']:
                    self.interfere_power += test_config['sig_gen_2']['power']['step']
                    self.transmit_sig_gen_to_radio(rf_power=self.interfere_power, sig_gen_no=2)
                    # self.transmit_sig_gen_to_radio(rf_power=self.interfere_power, sig_gen_no=3)
                    sinad = self.get_sinad()
                    print(f"sinad: {sinad}, rx_set_power: {self.rx_set_power}, interference_power: {self.interfere_power}")
                else:
                    # self.interfere_power = test_config['sig_gen_2']['power']['start']
                    break

            #while test_config['min_sinad'] - test_config['soundcard']['sinad_proximity'] >= sinad >= test_config['min_sinad'] + test_config['soundcard']['sinad_proximity']
            co_channel_rej_ratio = self.interfere_power - self.rx_set_power
            if co_channel_rej_ratio >= test_config['co-channel_rej_ratio_min'] and co_channel_rej_ratio <= test_config['co-channel_rej_ratio_max']:

                test_passed.append(True)
            else:
                test_passed.append(False)

            print(
                f'RX_Frequency: {freq / 1e6:.4f} MHz, Inter Freq: {interference_freq / 1e6:.4f} MHz, '
                f'Co-channel_Rej_Ratio: '
                f'{co_channel_rej_ratio:.2f} dB, SINAD: {sinad:.2f} dB, RX_Power: {self.rx_set_power} dBuv, '
                f'INTERFERE_Power[dBuv]: {self.interfere_power:.2f} Passed: {test_passed[idx]}')

            date_time = datetime.now().strftime("%d/%m/%Y, %H:%M:%S")
            self.test_results.log_dict["RX_Frequency[Hz]"].append(freq)
            self.test_results.log_dict["Interfere_Frequency[Hz]"].append(interference_freq)
            # self.test_results.log_dict["Interfere_Frequency_C[Hz]"].append(interference_freq_c)
            self.test_results.log_dict["Interfere_Power[dBuv]"].append(self.interfere_power)
            # self.test_results.log_dict["Interfere_Power_C[dBuv]"].append(self.interfere_power)
            self.test_results.log_dict["Co-Channel_Rej[dB]"].append(co_channel_rej_ratio)
            self.test_results.log_dict["RX_Power[dBuv]"].append(self.rx_set_power)
            self.test_results.log_dict["SINAD[dB]"].append(sinad)
            self.test_results.log_dict["Radio_Voltage[V]"].append(voltage)
            self.test_results.log_dict["Temperature[C]"].append(temp)
            self.test_results.log_dict["Timestamp"].append(date_time)
            self.test_results.log_dict["Test_Passed"].append(test_passed[idx])

        # self.transmit_sig_gen_to_radio(rf_on=False, fm_dev_on=False, sig_gen_no=1)
        # self.transmit_sig_gen_to_radio(rf_on=False, fm_dev_on=False, sig_gen_no=2)
        # self.transmit_sig_gen_to_radio(rf_on=False, fm_dev_on=False, sig_gen_no=3)

        if False in test_passed:
            return False
        else:
            return True


    def rx_adjacent_channel_selectivity(self, test_config_opt):

        test_id = 'rx_adjacent_channel_selectivity'
        self.test_equip.rf_switch.rx_sig_gen_to_radio()
        self.test_results.create_test_results_path(standards_id=self.standard_id, test_id=test_id)
        test_config = self.get_test_config(test_config_opt=test_config_opt, test_id=test_id)
        self.test_results.test_param_log(test_config, test_config_opt)

        # self.test_equip.soundcard.num_samples = test_config['soundcard']['no_samples']
        # self.test_equip.soundcard.psophometric_weighting = test_config['soundcard']['psophometric_weighting']

        self.test_equip.signal_gen_1.transmit_from_sig_gen(rf_power_units=test_config['sig_gen_1']['power']['units'],
                                                           lfo_freq=test_config['sig_gen_1']['lfo_frequency'],
                                                           fm_dev=test_config['sig_gen_1']['fm_dev'],
                                                           lfo_on=False, rf_on=False, fm_dev_on=False)

        self.test_equip.signal_gen_2.transmit_from_sig_gen(rf_power_units=test_config['sig_gen_2']['power']['units'],
                                                           lfo_freq=test_config['sig_gen_2']['lfo_frequency'],
                                                           fm_dev=test_config['sig_gen_2']['fm_dev'],
                                                           lfo_on=False, rf_on=False, fm_dev_on=False)

        self.check_radio_serial_comms()
        self.radio_tx_off()
        looping_arrays = self.get_looping_arrays(test_config=test_config)
        self.first_test_loop = True

        # date_time = datetime.now().strftime("%d/%m/%Y, %H:%M:%S")
        self.test_results.log_dict = {
                                      "RX_Frequency[Hz]": [],
                                      "INTERFERE_Frequency[Hz]": [],
                                      "Channel_Selectivity[dB]": [],
                                      "RX_Power[dBuv]": [],
                                      "INTERFERE_Power[dBuv]": [],
                                      "SINAD[dB]": [],
                                      "Radio_Voltage[V]": [],
                                      "Temperature[C]": [],
                                      "Timestamp": [],
                                      "Test_Passed": [],
                                      }

        test_result = self.rx_test_executor(looping_arrays=looping_arrays,
                                            test_function=self._rx_adjacent_channel_selectivity,
                                            test_config=test_config)

        self.test_results.save_log()
        self.test_equip.signal_gen_1.rf_power_on = False
        self.test_equip.signal_gen_2.rf_power_on = False

        return test_result

    def _rx_adjacent_channel_selectivity(self, freq, voltage, temp, rx_radio_power, test_config):
        test_passed = []
        self.test_equip.psu.voltage = voltage

        if temp != 'NOT_USED':
            gui.print_yellow('[Notionally] Setting Temp to ' + str(temp))


        if self.first_test_loop:
            self.rx_set_power = test_config['sig_gen_1']['power']['start']
            self.rx_set_offset1 = -test_config['sig_gen_1']['power']['offset']

            self.transmit_sig_gen_to_radio(rf_freq=freq, rf_power=self.rx_set_power,
                                           rf_power_offset=self.rx_set_offset1,
                                           rf_on=True, fm_dev_on=True, sig_gen_no=1,
                                           audio_vol=int(test_config['radio_volume']), sql_toggle=1)
            self.first_test_loop = False
        else:
            self.transmit_sig_gen_to_radio(rf_freq=freq, audio_vol=int(test_config['radio_volume']),
                                           sig_gen_no=1, sql_toggle=1)

        sinad, self.rx_set_power = self.find_sinad_power(target_sinad=test_config['sinad_target'],
                                                         set_power=self.rx_set_power,
                                                         max_power=test_config['sig_gen_1']['power']['max'],
                                                         min_power=test_config['sig_gen_1']['power']['min'],
                                                         power_step=test_config['sig_gen_1']['power']['step'])

        if not sinad >= test_config['sinad_target']:
            gui.print_red('20dB SINAD Not Reached')
            test_passed = False
            return test_passed

        interference_freq_offsets = test_config['adj_chan_freq']
        interference_power_thresh = self.rx_set_power + test_config['min_adj_chan_selectivity']


        for idx, freq_offsets in enumerate(interference_freq_offsets):

            interference_freq = freq + float(freq_offsets)
            self.interfere_power = test_config['sig_gen_2']['power']['start']
            self.rx_set_offset2 = -test_config['sig_gen_2']['power']['offset']
            self.transmit_sig_gen_to_radio(rf_freq=interference_freq, rf_power=self.interfere_power,
                                           rf_power_offset=self.rx_set_offset2,
                                           rf_on=True, fm_dev_on=True, sig_gen_no=2)

            sinad = self.get_sinad()

            while True:

                if sinad >= test_config['min_sinad'] and self.interfere_power < test_config['sig_gen_2']['power']['max']:
                    self.interfere_power += test_config['sig_gen_2']['power']['step']
                    self.transmit_sig_gen_to_radio(rf_power=self.interfere_power, sig_gen_no=2)
                    sinad = self.get_sinad()
                    print(f"sinad: {sinad}, rx_set_power: {self.rx_set_power}, interference_power: {self.interfere_power}")
                else:
                    # self.interfere_power = test_config['sig_gen_2']['power']['start']
                    break



            if self.interfere_power >= interference_power_thresh:
                test_passed.append(True)
            else:
                test_passed.append(False)

            self.transmit_sig_gen_to_radio(rf_on=False, fm_dev_on=False, sig_gen_no=2)
            print(f'RX_Frequency: {freq/1e6:.3f} MHz, Inter Freq: {interference_freq/1e6:.3f}MHz, Channel_Selectivity: '
                  f'{self.interfere_power - self.rx_set_power:.2f} dB, SINAD: {sinad:.2f} dB, RX_Power[dBuv]: {self.rx_set_power}, '
                  f'INTERFERE_Power[dBuv]: {self.interfere_power:.2f} Passed: {test_passed[idx]}')

            date_time = datetime.now().strftime("%d/%m/%Y, %H:%M:%S")
            self.test_results.log_dict["RX_Frequency[Hz]"].append(freq)
            self.test_results.log_dict["INTERFERE_Frequency[Hz]"].append(interference_freq)
            self.test_results.log_dict["Channel_Selectivity[dB]"].append(self.interfere_power - self.rx_set_power)
            self.test_results.log_dict["RX_Power[dBuv]"].append(self.rx_set_power)
            self.test_results.log_dict["INTERFERE_Power[dBuv]"].append(self.interfere_power)
            self.test_results.log_dict["SINAD[dB]"].append(sinad)
            self.test_results.log_dict["Radio_Voltage[V]"].append(voltage)
            self.test_results.log_dict["Temperature[C]"].append(temp)
            self.test_results.log_dict["Timestamp"].append(date_time)
            self.test_results.log_dict["Test_Passed"].append(test_passed[idx])

        if False in test_passed:
            return False
        else:
            return True


    def rx_spurious_response_rejection(self, test_config_opt):

        test_id = 'rx_spurious_response_rejection'

        self.test_equip.rf_switch.rx_sig_gen_to_radio()

        self.test_results.create_test_results_path(standards_id=self.standard_id, test_id=test_id)

        self.check_radio_serial_comms()
        self.radio_tx_off()
        test_config = self.get_test_config(test_config_opt=test_config_opt, test_id=test_id)
        self.test_results.test_param_log(test_config, test_config_opt)

        looping_arrays = self.get_looping_arrays(test_config=test_config)
        self.first_test_loop = True

        self.test_equip.soundcard.num_samples = test_config['soundcard']['no_samples']
        self.test_equip.soundcard.psophometric_weighting = test_config['soundcard']['psophometric_weighting']

        self.test_equip.signal_gen_1.transmit_from_sig_gen(
            rf_power_units=test_config['sig_gen_1']['power']['units'],
            lfo_freq=test_config['sig_gen_1']['lfo_frequency'],
            fm_dev=test_config['sig_gen_1']['fm_dev'],
            lfo_on=False, rf_on=False, fm_dev_on=False)

        self.test_equip.signal_gen_2.transmit_from_sig_gen(
            rf_power_units=test_config['sig_gen_2']['power']['units'],
            lfo_freq=test_config['sig_gen_2']['lfo_frequency'],
            fm_dev=test_config['sig_gen_2']['fm_dev'],
            lfo_on=False, rf_on=False, fm_dev_on=False)

        date_time = datetime.now().strftime("%d/%m/%Y, %H:%M:%S")
        self.test_results.log_dict = {
            "RX_Frequency[Hz]": [],
            "INTERFERE_Frequency[Hz]": [],
            "Spurious_Resp_Rejection[dB]": [],
            "RX_Power[dBm]": [],
            "INTERFERE_Power[dBuv]": [],
            "SINAD[dB]": [],
            "Radio_Voltage[V]": [],
            "Temperature[C]": [],
            "Timestamp": [],
            "Test_Passed": [],
            "Pass_Level": [],
        }

        test_result = self.rx_test_executor(looping_arrays=looping_arrays,
                                            test_function=self._rx_spurious_response_rejection,
                                            test_config=test_config)

        self.test_results.save_log()
        self.test_equip.signal_gen_1.rf_power_on = False
        self.test_equip.signal_gen_2.rf_power_on = False

        return test_result


    def _rx_spurious_response_rejection(self, freq, voltage, temp, rx_radio_power, test_config):
        test_passed = []
        self.test_equip.psu.voltage = voltage

        if temp != 'NOT_USED':
            gui.print_yellow('[Notionally] Setting Temp to ' + str(temp))

        if self.first_test_loop:
            self.rx_set_power = test_config['sig_gen_1']['power']['start']
            self.transmit_sig_gen_to_radio(rf_freq=freq, rf_power=self.rx_set_power, rf_on=True, fm_dev_on=True,
                                           sql_toggle=1, sig_gen_no=1, audio_vol=1)
            self.first_test_loop = False
        else:
            self.transmit_sig_gen_to_radio(rf_freq=freq, audio_vol=int(test_config['radio_volume']), sig_gen_no=1)

        sinad, self.rx_set_power = self.find_sinad_power(target_sinad=test_config['sinad_target'],
                                                         set_power=self.rx_set_power,
                                                         max_power=test_config['sig_gen_1']['power']['max'],
                                                         min_power=test_config['sig_gen_1']['power']['min'],
                                                         power_step=test_config['sig_gen_1']['power']['step'])


        if not sinad >= test_config['sinad_target']:
            gui.print_red('20dB SINAD Not Reached')
            test_passed = False
            return test_passed

        interference_freq_array = self.array_maker(test_config['sig_gen_2']['frequency'])
        #interference_power_thresh = self.rx_set_power + test_config['spurious_resp_rej_ratio']

        idx = 0

        for interference_freq in interference_freq_array:

            if interference_freq == freq:
                # There's no point checking for interference on the same channel...
                continue
            self.interfere_power = test_config['sig_gen_2']['power']['start']
            self.transmit_sig_gen_to_radio(rf_freq=interference_freq, rf_power=self.interfere_power, rf_on=True,
                                           fm_dev_on=True, sig_gen_no=2)

            sinad = self.test_equip.soundcard.measure(num_samps=4*4096, ccitt= True)

            while abs(sinad-test_config['min_sinad']) > test_config['tolerance']:
                # adjust interferer power if the sinad is out of range
                if sinad < test_config['min_sinad'] and self.interfere_power > test_config['sig_gen_2']['power']['min']:
                    self.interfere_power -= test_config['sig_gen_2']['power']['step']
                    self.transmit_sig_gen_to_radio(rf_power=self.interfere_power, sig_gen_no=2)
                    sinad = self.get_stable_sinad(threshold=test_config['sinad_target'], order_descending=False,
                                                  max_fluctuation=test_config['soundcard']['sinad_max_fluctuation'],
                                                  num_measurements=test_config['soundcard']['sinad_no_readings'])

                if sinad >= test_config['min_sinad'] and self.interfere_power < test_config['sig_gen_2']['power']['max']:
                    self.interfere_power += test_config['sig_gen_2']['power']['step']
                    self.transmit_sig_gen_to_radio(rf_power=self.interfere_power, sig_gen_no=2)
                    sinad = self.get_stable_sinad(threshold=test_config['sinad_target'], order_descending=True,
                                                  max_fluctuation=test_config['soundcard']['sinad_max_fluctuation'],
                                                  num_measurements=test_config['soundcard']['sinad_no_readings'])

            spur_rej_ratio = self.interfere_power - self.rx_set_power
            if spur_rej_ratio > test_config['spurious_resp_rej_ratio']:
                test_passed.append(True)
            else:
                test_passed.append(False)

            print(
                f'RX_Frequency: {freq / 1e6:.3f} MHz, Inter Freq: {interference_freq / 1e6:.3f} MHz, Spurious_Resp_Rejection: '
                f'{self.interfere_power - self.rx_set_power:.2f} dB, SINAD: {sinad:.2f} dB, RX_Power: {self.rx_set_power-107} dBm, '
                f'INTERFERE_Power[dBm]: {self.interfere_power-107:.2f} Passed: {test_passed[idx]}')

            date_time = datetime.now().strftime("%d/%m/%Y, %H:%M:%S")
            self.test_results.log_dict["RX_Frequency[Hz]"].append(freq)
            self.test_results.log_dict["INTERFERE_Frequency[Hz]"].append(interference_freq)
            self.test_results.log_dict["Spurious_Resp_Rejection[dB]"].append(self.interfere_power - self.rx_set_power)
            self.test_results.log_dict["RX_Power[dBm]"].append(self.rx_set_power)
            self.test_results.log_dict["INTERFERE_Power[dBuv]"].append(self.interfere_power)
            self.test_results.log_dict["SINAD[dB]"].append(sinad)
            self.test_results.log_dict["Radio_Voltage[V]"].append(voltage)
            self.test_results.log_dict["Temperature[C]"].append(temp)
            self.test_results.log_dict["Timestamp"].append(date_time)
            self.test_results.log_dict["Test_Passed"].append(test_passed[idx])
            self.test_results.log_dict["Pass_Level"].append(test_config['spurious_resp_rej_ratio'])

        self.transmit_sig_gen_to_radio(rf_on=False, fm_dev_on=False, sig_gen_no=2)
        if False in test_passed:
            return False
        else:
            return True

    def rx_intermodulation_response(self, test_config_opt):

        test_id = 'rx_intermodulation_response'
        self.test_equip.rf_switch.rx_sig_gen_to_radio()
        self.test_results.create_test_results_path(standards_id=self.standard_id, test_id=test_id)
        test_config = self.get_test_config(test_config_opt=test_config_opt, test_id=test_id)
        self.test_results.test_param_log(test_config, test_config_opt)

        # self.test_equip.soundcard.num_samples = test_config['soundcard']['no_samples']
        # self.test_equip.soundcard.psophometric_weighting = test_config['soundcard']['psophometric_weighting']

        self.transmit_sig_gen_to_radio(
            rf_power_units=test_config['sig_gen_1']['power']['units'],
            lfo_freq=test_config['sig_gen_1']['lfo_frequency'],
            fm_dev=test_config['sig_gen_1']['fm_dev'],
            lfo_on=False, rf_on=False, fm_dev_on=False, sig_gen_no=1)

        self.transmit_sig_gen_to_radio(
            rf_power_units=test_config['sig_gen_2']['power']['units'],
            lfo_on=False, rf_on=False, fm_dev_on=False, sig_gen_no=2)

        self.transmit_sig_gen_to_radio(
            rf_power_units=test_config['sig_gen_3']['power']['units'],
            lfo_freq=test_config['sig_gen_3']['lfo_frequency'],
            fm_dev=test_config['sig_gen_3']['fm_dev'],
            lfo_on=False, rf_on=False, fm_dev_on=False, sig_gen_no=3)

        self.check_radio_serial_comms()
        self.radio_tx_off()
        looping_arrays = self.get_looping_arrays(test_config=test_config)
        self.first_test_loop = True
        # self.test_equip.signal_gen_1.fm_dev_on = True

        # date_time = datetime.now().strftime("%d/%m/%Y, %H:%M:%S")

        self.test_results.log_dict = {
            "RX_Frequency[Hz]": [],
            "Interfere_Frequency_B[Hz]": [],
            "Interfere_Frequency_C[Hz]": [],
            "Interfere_Power_B[dBuv]": [],
            "Interfere_Power_C[dBuv]": [],
            "Intermod_Resp[dB]": [],
            "RX_Power[dBuv]": [],
            "SINAD[dB]": [],
            "Radio_Voltage[V]": [],
            "Temperature[C]": [],
            "Timestamp": [],
            "Test_Passed": [],
        }

        test_result = self.rx_test_executor(looping_arrays=looping_arrays,
                                            test_function=self._rx_intermodulation_response,
                                            test_config=test_config)

        self.test_results.save_log()
        self.test_equip.signal_gen_1.rf_power_on = False
        self.test_equip.signal_gen_2.rf_power_on = False
        self.test_equip.signal_gen_3.rf_power_on = False

        return test_result

    def _rx_intermodulation_response(self, freq, voltage, temp, rx_radio_power, test_config):
        test_passed = []
        self.test_equip.psu.voltage = voltage

        if temp != 'NOT_USED':
            gui.print_yellow('[Notionally] Setting Temp to ' + str(temp))

        if self.first_test_loop:
            self.rx_set_power = test_config['sig_gen_1']['power']['start']
            self.rx_set_offset1 = -test_config['sig_gen_1']['power']['offset']
            self.transmit_sig_gen_to_radio(rf_freq=freq, rf_power=self.rx_set_power,
                                           rf_power_offset=self.rx_set_offset1,
                                           rf_on=True, fm_dev_on=True,sig_gen_no=1,
                                           audio_vol=int(test_config['radio_volume']), sql_toggle=1 )
            self.first_test_loop = False
        else:
            self.transmit_sig_gen_to_radio(rf_freq=freq, audio_vol=int(test_config['radio_volume']),
                                           sig_gen_no=1, sql_toggle=1)

        sinad, self.rx_set_power = self.find_sinad_power(target_sinad=test_config['sinad_target'],
                                                         set_power=self.rx_set_power,
                                                         max_power=test_config['sig_gen_1']['power']['max'],
                                                         min_power=test_config['sig_gen_1']['power']['min'],
                                                         power_step=test_config['sig_gen_1']['power']['step'])

        if not sinad >= test_config['sinad_target']:
            gui.print_red('20dB SINAD Not Reached')
            test_passed = False
            return test_passed

        #interference_power_thresh = self.rx_set_power + test_config['intermod_resp_ratio']

        for idx in range(len(test_config['sig_gen_2']['interference_offset'])):
            interference_freq_b = freq + float(test_config['sig_gen_2']['interference_offset'][idx])
            interference_freq_c = freq + float(test_config['sig_gen_3']['interference_offset'][idx])

            self.interfere_power = test_config['sig_gen_2']['power']['start']
            self.rx_set_offset2 = -test_config['sig_gen_2']['power']['offset']
            self.rx_set_offset3 = -test_config['sig_gen_3']['power']['offset']

            self.transmit_sig_gen_to_radio(rf_freq=interference_freq_b,
                                           rf_power=self.interfere_power,
                                           rf_power_offset=self.rx_set_offset2,
                                           rf_on=True, sig_gen_no=2)
            self.transmit_sig_gen_to_radio(rf_freq=interference_freq_c,
                                           rf_power=self.interfere_power,
                                           rf_power_offset=self.rx_set_offset3,
                                           lfo_freq=test_config['sig_gen_3']['lfo_frequency'],
                                           fm_dev=test_config['sig_gen_3']['fm_dev'],
                                           rf_on=True, fm_dev_on=True, sig_gen_no=3)

            sinad = self.get_sinad()

            while True:
                if sinad >= test_config['min_sinad'] and self.interfere_power < test_config['sig_gen_2']['power']['max']:
                    self.interfere_power += test_config['sig_gen_2']['power']['step']
                    self.transmit_sig_gen_to_radio(rf_power=self.interfere_power, sig_gen_no=2)
                    self.transmit_sig_gen_to_radio(rf_power=self.interfere_power, sig_gen_no=3)
                    sinad = self.get_sinad()
                    print(f"sinad: {sinad}, rx_set_power: {self.rx_set_power}, interference_power: {self.interfere_power}")
                else:
                    # self.interfere_power = test_config['sig_gen_2']['power']['start']
                    break

            #while test_config['min_sinad'] - test_config['soundcard']['sinad_proximity'] >= sinad >= test_config['min_sinad'] + test_config['soundcard']['sinad_proximity']

            if (self.interfere_power - self.rx_set_power) >= test_config['intermod_resp_ratio']:
                test_passed.append(True)
            else:
                test_passed.append(False)

            print(
                f'RX_Frequency: {freq / 1e6:.3f} MHz, Inter Freq B: {interference_freq_b / 1e6:.3f} MHz, '
                f'Inter Freq C: {interference_freq_c / 1e6:.3f} MHz, Intermod_Resp_Ratio: '
                f'{self.interfere_power - self.rx_set_power:.2f} dB, SINAD: {sinad:.2f} dB, RX_Power: {self.rx_set_power} dBuv, '
                f'INTERFERE_Power[dBuv]: {self.interfere_power:.2f} Passed: {test_passed[idx]}')

            date_time = datetime.now().strftime("%d/%m/%Y, %H:%M:%S")
            self.test_results.log_dict["RX_Frequency[Hz]"].append(freq)
            self.test_results.log_dict["Interfere_Frequency_B[Hz]"].append(interference_freq_b)
            self.test_results.log_dict["Interfere_Frequency_C[Hz]"].append(interference_freq_c)
            self.test_results.log_dict["Interfere_Power_B[dBuv]"].append(self.interfere_power)
            self.test_results.log_dict["Interfere_Power_C[dBuv]"].append(self.interfere_power)
            self.test_results.log_dict["Intermod_Resp[dB]"].append(self.interfere_power - self.rx_set_power)
            self.test_results.log_dict["RX_Power[dBuv]"].append(self.rx_set_power)
            self.test_results.log_dict["SINAD[dB]"].append(sinad)
            self.test_results.log_dict["Radio_Voltage[V]"].append(voltage)
            self.test_results.log_dict["Temperature[C]"].append(temp)
            self.test_results.log_dict["Timestamp"].append(date_time)
            self.test_results.log_dict["Test_Passed"].append(test_passed[idx])

        # self.transmit_sig_gen_to_radio(rf_on=False, fm_dev_on=False, sig_gen_no=1)
        self.transmit_sig_gen_to_radio(rf_on=False, fm_dev_on=False, sig_gen_no=2)
        self.transmit_sig_gen_to_radio(rf_on=False, fm_dev_on=False, sig_gen_no=3)

        if False in test_passed:
            return False
        else:
            return True

    def rx_blocking_desensitization(self, test_config_opt):

        test_id = 'rx_blocking_desensitization'
        self.test_equip.rf_switch.rx_sig_gen_to_radio()
        self.test_results.create_test_results_path(standards_id=self.standard_id, test_id=test_id)
        test_config = self.get_test_config(test_config_opt=test_config_opt, test_id=test_id)
        self.test_results.test_param_log(test_config, test_config_opt)

        # self.test_equip.soundcard.num_samples = test_config['soundcard']['no_samples']
        # self.test_equip.soundcard.psophometric_weighting = test_config['soundcard']['psophometric_weighting']

        self.test_equip.signal_gen_1.transmit_from_sig_gen(rf_power_units=test_config['sig_gen_1']['power']['units'],
                                                           lfo_freq=test_config['sig_gen_1']['lfo_frequency'],
                                                           fm_dev=test_config['sig_gen_1']['fm_dev'],
                                                           lfo_on=False, rf_on=False, fm_dev_on=False)

        self.test_equip.signal_gen_2.transmit_from_sig_gen(rf_power_units=test_config['sig_gen_2']['power']['units'],
                                                           lfo_freq=test_config['sig_gen_2']['lfo_frequency'],
                                                           fm_dev=test_config['sig_gen_2']['fm_dev'],
                                                           lfo_on=False, rf_on=False, fm_dev_on=False)

        self.check_radio_serial_comms()
        self.radio_tx_off()
        looping_arrays = self.get_looping_arrays(test_config=test_config)
        self.first_test_loop = True

        # date_time = datetime.now().strftime("%d/%m/%Y, %H:%M:%S")
        self.test_results.log_dict = {
                                      "RX_Frequency[Hz]": [],
                                      "INTERFERE_Frequency[Hz]": [],
                                      "Channel_Blocking[dBuv]": [],
                                      "RX_Power[dBuv]": [],
                                      "INTERFERE_Power[dBuv]": [],
                                      "SINAD[dB]": [],
                                      "Radio_Voltage[V]": [],
                                      "Temperature[C]": [],
                                      "Timestamp": [],
                                      "Test_Passed": [],
                                      }

        test_result = self.rx_test_executor(looping_arrays=looping_arrays,
                                            test_function=self._rx_blocking_desensitization,
                                            test_config=test_config)

        self.test_results.save_log()
        self.test_equip.signal_gen_1.rf_power_on = False
        self.test_equip.signal_gen_2.rf_power_on = False

        return test_result

    def _rx_blocking_desensitization(self, freq, voltage, temp, rx_radio_power, test_config):
        test_passed = []
        self.test_equip.psu.voltage = voltage

        if temp != 'NOT_USED':
            gui.print_yellow('[Notionally] Setting Temp to ' + str(temp))


        if self.first_test_loop:
            self.rx_set_power = test_config['sig_gen_1']['power']['start']
            self.rx_set_offset1 = -test_config['sig_gen_1']['power']['offset']

            self.transmit_sig_gen_to_radio(rf_freq=freq, rf_power=self.rx_set_power,
                                           rf_power_offset=self.rx_set_offset1,
                                           rf_on=True, fm_dev_on=True, sig_gen_no=1,
                                           audio_vol=int(test_config['radio_volume']), sql_toggle=1)
            self.first_test_loop = False
        else:
            self.transmit_sig_gen_to_radio(rf_freq=freq, audio_vol=int(test_config['radio_volume']),
                                           sig_gen_no=1, sql_toggle=1)

        sinad, self.rx_set_power = self.find_sinad_power(target_sinad=test_config['sinad_target'],
                                                         set_power=self.rx_set_power,
                                                         max_power=test_config['sig_gen_1']['power']['max'],
                                                         min_power=test_config['sig_gen_1']['power']['min'],
                                                         power_step=test_config['sig_gen_1']['power']['step'])

        if not sinad >= test_config['sinad_target']:
            gui.print_red('20dB SINAD Not Reached')
            test_passed = False
            return test_passed

        # for single or self-defined sweeping frequencies
        if test_config['blocking_sweep_freq']['required']:
            interference_freq_offsets = test_config['blocking_sweep_freq']['sweep_freq']
        else:
            interference_freq_offsets = test_config['blocking_freq']

        # generate custom blocking sweep with regular interval
        if test_config['regular_blocking_sweep_freq']['required']:
            start_sweep_freq = float(test_config['regular_blocking_sweep_freq']['start_sweep_freq'])
            end_sweep_freq = float(test_config['regular_blocking_sweep_freq']['end_sweep_freq'])
            sweep_interval = float(test_config['regular_blocking_sweep_freq']['sweep_interval'])
            if test_config['regular_blocking_sweep_freq']['doubleside']:
                interference_freq_offsets_plus = [i for i in np.arange(start_sweep_freq, end_sweep_freq, sweep_interval)]
                interference_freq_offsets_minus = [i for i in np.arange(start_sweep_freq, end_sweep_freq, sweep_interval)]
                interference_freq_offsets_minus.reverse()
                interference_freq_offsets = interference_freq_offsets_minus + interference_freq_offsets_plus
            else:
                interference_freq_offsets = [i for i in np.arange(start_sweep_freq, end_sweep_freq, sweep_interval)]

        interference_power_thresh = test_config['min_blocking']

        for idx, freq_offsets in enumerate(interference_freq_offsets):

            interference_freq = freq + float(freq_offsets)
            self.interfere_power = test_config['sig_gen_2']['power']['start']
            self.rx_set_offset2 = -test_config['sig_gen_2']['power']['offset']
            self.transmit_sig_gen_to_radio(rf_freq=interference_freq, rf_power=self.interfere_power,
                                           rf_power_offset=self.rx_set_offset2,
                                           rf_on=True, fm_dev_on=False, sig_gen_no=2)

            sinad = self.get_sinad()

            while True:

                if sinad >= test_config['min_sinad'] and self.interfere_power < test_config['sig_gen_2']['power']['max']:
                    self.interfere_power += test_config['sig_gen_2']['power']['step']
                    self.transmit_sig_gen_to_radio(rf_power=self.interfere_power, sig_gen_no=2)
                    sinad = self.get_sinad()
                    print(f"sinad: {sinad}, rx_set_power: {self.rx_set_power}, interference_power: {self.interfere_power}")
                else:
                    # self.interfere_power = test_config['sig_gen_2']['power']['start']
                    break



            if self.interfere_power >= interference_power_thresh:
                test_passed.append(True)
            else:
                test_passed.append(False)

            self.transmit_sig_gen_to_radio(rf_on=False, fm_dev_on=False, sig_gen_no=2)
            print(f'RX_Frequency: {freq/1e6:.3f} MHz, Inter Freq: {interference_freq/1e6:.3f}MHz, Channel_Blocking: '
                  f'{self.interfere_power:.2f} dB, SINAD: {sinad:.2f} dB, RX_Power[dBuv]: {self.rx_set_power}, '
                  f'INTERFERE_Power[dBuv]: {self.interfere_power:.2f} Passed: {test_passed[idx]}')

            date_time = datetime.now().strftime("%d/%m/%Y, %H:%M:%S")
            self.test_results.log_dict["RX_Frequency[Hz]"].append(freq)
            self.test_results.log_dict["INTERFERE_Frequency[Hz]"].append(interference_freq)
            self.test_results.log_dict["Channel_Blocking[dBuv]"].append(self.interfere_power)
            self.test_results.log_dict["RX_Power[dBuv]"].append(self.rx_set_power)
            self.test_results.log_dict["INTERFERE_Power[dBuv]"].append(self.interfere_power)
            self.test_results.log_dict["SINAD[dB]"].append(sinad)
            self.test_results.log_dict["Radio_Voltage[V]"].append(voltage)
            self.test_results.log_dict["Temperature[C]"].append(temp)
            self.test_results.log_dict["Timestamp"].append(date_time)
            self.test_results.log_dict["Test_Passed"].append(test_passed[idx])

        if False in test_passed:
            return False
        else:
            return True



    def rx_hum_noise(self, test_config_opt):
        test_id = 'rx_hum_noise'  # specify test id
        self.test_equip.rf_switch.rx_sig_gen_to_radio()  # specify rf switch to rx

        self.test_results.create_test_results_path(standards_id=self.standard_id, test_id=test_id)
        test_config = self.get_test_config(test_config_opt=test_config_opt, test_id=test_id)
        self.test_results.test_param_log(test_config, test_config_opt)

        self.transmit_sig_gen_to_radio(rf_power_units=test_config['sig_gen_1']['power']['units'],
                                       lfo_freq=test_config['sig_gen_1']['lfo_frequency'],
                                       fm_dev=test_config['sig_gen_1']['fm_dev'],
                                       lfo_on=False, rf_on=False, fm_dev_on=False, sig_gen_no=1)  # only 1 siggen is required

        self.test_equip.signal_gen_1.fm_dev_on = True

        self.check_radio_serial_comms()  # check serial comms
        self.radio_tx_off()  # turn off radio transmission

        looping_arrays = self.get_looping_arrays(test_config=test_config)  # this is to extract parameter looping information from test_config
        self.first_test_loop = True

        self.test_results.log_dict = {"Frequency[Hz]": [],
                                      "SINAD[dB]": [],
                                      "Audio Volume": [],
                                      "Timestamp": [],
                                      "Test_Passed": [],
                                      "Hum and Noise Ratio[dB]": [],
                                      "Current[A]": [],
                                      "Sig_Gen_Level[dBm]": [],
                                      "RSSI": [],
                                      "Pass_Level[dB]": [],
                                      }  # result dictionary
        #  this is the wrapper function
        test_result = self.rx_test_executor(looping_arrays=looping_arrays,
                                            test_function=self._rx_hum_noise, test_config=test_config)

        self.test_results.save_log()
        self.test_equip.signal_gen_1.rf_power_on = False
        return test_result

    def _rx_hum_noise(self, freq, voltage, temp, rx_radio_power, test_config):
        # this test cannot use sound card because a very loud volume is required and soundcard is not able to support

        number_of_measurements = 20
        pass_level = test_config['acceptance_criteria']['level']
        test_passed = []
        # turn on power supply to the radio
        self.test_equip.psu.voltage = voltage  # set power supply
        # turn off all filters to make sure audio bandwith is at least 20KHz
        self.test_equip.cms.turn_off_ccitt()
        self.test_equip.cms.turn_off_hpf()
        self.test_equip.cms.turn_off_lpf()

        if temp != 'NOT_USED':
            gui.print_yellow('[Notionally] Setting Temp to ' + str(temp))

        self.rx_set_power = test_config['sig_gen_1']['power']['start']
        self.audio_vol = test_config['radio_volume']
        # turn on signal generator and radio audio volume
        self.transmit_sig_gen_to_radio(rf_freq=freq, rf_power=self.rx_set_power, rf_on=True, fm_dev_on=True,
                                       sql_toggle=1, audio_vol=self.audio_vol, sig_gen_no=1)  # turn on modulation
        current_level = self.test_equip.psu.get_current_level()
        print('currentlevel = ', current_level)
        time.sleep(5)  # wait for 5 seconds

        rms_mod_on_acc = 0
        sinad_mod_on_acc = 0
        rssi_acc = 0
        for i in range(number_of_measurements):
            self.test_equip.cms.turn_off_ccitt()
            rms_mod_on_acc = rms_mod_on_acc + self.test_equip.cms.get_audio_level()  # read rms voltage from CMS54
            sinad_mod_on_acc = sinad_mod_on_acc + self.test_equip.cms.get_sinad()
            rssi_acc = rssi_acc + self.radio_read_rssi()
            print('rms_mod_on_acc: ', rms_mod_on_acc)

        rms_modulation_on = rms_mod_on_acc/number_of_measurements
        sinad_modulation_on = sinad_mod_on_acc / number_of_measurements
        rssi = rssi_acc / number_of_measurements
        print('rms mod on: ', rms_modulation_on)

        self.transmit_sig_gen_to_radio(rf_freq=freq, rf_power=self.rx_set_power, rf_on=True, fm_dev_on=False,
                                       sql_toggle=1, audio_vol=self.audio_vol, sig_gen_no=1)  # turn off modulation
        time.sleep(5)  # wait for 5 seconds
        rms_mod_off_acc = 0
        for i in range(number_of_measurements):
            rms_mod_off_acc = rms_mod_off_acc + self.test_equip.cms.get_audio_level() # read cms voltage from CMS54
            print('rms_mod_off_acc: ', rms_mod_off_acc)

        rms_modulation_off = rms_mod_off_acc/number_of_measurements

        print('rms mod off: ', rms_modulation_off)

        hum_noise_ratio = 20*(np.log10(rms_modulation_on / rms_modulation_off))

        print('hum and noise ratio (dB): ', hum_noise_ratio)

        if hum_noise_ratio > pass_level:
            test_passed = True
        else:
            test_passed = False

        print('currentlevel = ', current_level)
        date_time = datetime.now().strftime("%d/%m/%Y, %H:%M:%S")
        self.test_results.log_dict["Frequency[Hz]"].append(freq)
        self.test_results.log_dict["SINAD[dB]"].append(sinad_modulation_on)
        self.test_results.log_dict["Audio Volume"].append(self.audio_vol)
        self.test_results.log_dict["Timestamp"].append(date_time)
        self.test_results.log_dict["Test_Passed"].append(test_passed)
        self.test_results.log_dict["Hum and Noise Ratio[dB]"].append(hum_noise_ratio)
        self.test_results.log_dict["Current[A]"].append(float(current_level))
        self.test_results.log_dict["Sig_Gen_Level[dBm]"].append(float(self.rx_set_power))
        self.test_results.log_dict["RSSI"].append(float(rssi))
        self.test_results.log_dict["Pass_Level[dB]"].append(float(pass_level))

        return test_passed

    # receiver audio distortion test
    def rx_audio_distortion(self, test_config_opt):
        test_id = 'rx_audio_distortion'  # specify test id
        self.test_equip.rf_switch.rx_sig_gen_to_radio()  # specify rf switch to rx

        self.test_results.create_test_results_path(standards_id=self.standard_id, test_id=test_id)
        test_config = self.get_test_config(test_config_opt=test_config_opt, test_id=test_id)
        self.test_results.test_param_log(test_config, test_config_opt)

        # only 1 siggen is required
        self.transmit_sig_gen_to_radio(rf_power_units=test_config['sig_gen_1']['power']['units'],
                                       lfo_freq=test_config['sig_gen_1']['lfo_frequency'],
                                       fm_dev=test_config['sig_gen_1']['fm_dev'],
                                       lfo_on=False, rf_on=False, fm_dev_on=False, sig_gen_no=1)

        self.test_equip.signal_gen_1.fm_dev_on = True

        self.check_radio_serial_comms()  # check serial comms
        self.radio_tx_off()  # turn off radio transmission

        # this is to extract parameter looping information from test_config
        looping_arrays = self.get_looping_arrays(test_config=test_config)
        self.first_test_loop = True

        self.test_results.log_dict = {"Frequency[Hz]": [],
                                      "Timestamp": [],
                                      "Test_Passed": [],
                                      "Audio Distortion [%]": [],
                                      "Current[A]": [],
                                      "LFO[Hz]": [],
                                      "Pass_Level[%]": [],
                                      "Audio_Level[Vrms]": [],
                                      "Sig_Gen_Level[dBm]": [],
                                      "RSSI": [],
                                      }  # result dictionary
        #  this is the wrapper function
        test_result = self.rx_test_executor(looping_arrays=looping_arrays,
                                            test_function=self._rx_audio_distortion, test_config=test_config)

        self.test_results.save_log()
        self.test_equip.signal_gen_1.rf_power_on = False
        return test_result

    # receiver audio distortion test
    def _rx_audio_distortion(self, freq, voltage, temp, rx_radio_power, test_config):
        # this test cannot use sound card because a very loud volume is required and soundcard is not able to support

        test_passed = []  # initialize test_passed list
        # turn on power supply to the radio
        self.test_equip.psu.voltage = voltage  # set power supply
        # turn off all filters to make sure audio bandwith is at least 20KHz
        self.test_equip.cms.turn_off_ccitt()
        self.test_equip.cms.turn_off_hpf()
        self.test_equip.cms.turn_off_lpf()

        lfo_frequencies = test_config['sig_gen_1']['lfo_frequency']
        fm_devs = test_config['sig_gen_1']['fm_dev']

        number_lfo_frequencies = len(lfo_frequencies)
        number_of_measurements = 20

        if temp != 'NOT_USED':
            gui.print_yellow('[Notionally] Setting Temp to ' + str(temp))

        self.rx_set_power = test_config['sig_gen_1']['power']['start']
        self.audio_vol = test_config['radio_volume']
        if test_config['acceptance_criteria']['required']:
            pass_level = test_config['acceptance_criteria']['level']
        else:
            pass_level = 20

        print('number_lfo_freq: ', number_lfo_frequencies)

        for n in range(number_lfo_frequencies):
            # turn on signal generator and radio audio volume
            self.transmit_sig_gen_to_radio(rf_freq=freq, rf_power=self.rx_set_power, rf_on=True, fm_dev_on=True,
                                           sql_toggle=1, audio_vol=self.audio_vol, sig_gen_no=1,
                                           lfo_freq=lfo_frequencies[n], fm_dev=fm_devs[n])  # turn on modulation
            # write LFO frequency to CMS
            self.test_equip.cms.write_af1_freq(lfo_frequencies[n])
            print('LFO Freq: ', lfo_frequencies[n])

            time.sleep(5)  # wait for 5 seconds

            aud_dist_acc = 0
            audio_level_acc = 0
            rssi_acc = 0
            for i in range(number_of_measurements):
                aud_dist_acc = aud_dist_acc + self.test_equip.cms.get_distortion_level()  # read rms voltage from CMS54
                print('audio distortion: ', aud_dist_acc)
                audio_level_acc = audio_level_acc + self.test_equip.cms.get_audio_level()
                rssi_acc = rssi_acc + self.radio_read_rssi()  # read rms voltage from CMS54

            aud_distortion = aud_dist_acc / number_of_measurements
            audio_level = audio_level_acc / number_of_measurements
            rssi = rssi_acc / number_of_measurements
            print('Audio distortion: ', aud_distortion)

            if aud_distortion < pass_level:  # acceptance criteria is <10%
                test_passed.append(True)
            else:
                test_passed.append(False)

            current_level = self.test_equip.psu.get_current_level()
            print('currentlevel = ', current_level)
            date_time = datetime.now().strftime("%d/%m/%Y, %H:%M:%S")
            self.test_results.log_dict["Frequency[Hz]"].append(freq)
            self.test_results.log_dict["Test_Passed"].append(test_passed[n])
            self.test_results.log_dict["Audio Distortion [%]"].append(aud_distortion)
            self.test_results.log_dict["Current[A]"].append(float(current_level))
            self.test_results.log_dict["Timestamp"].append(date_time)
            self.test_results.log_dict["LFO[Hz]"].append(lfo_frequencies[n])
            self.test_results.log_dict["Pass_Level[%]"].append(pass_level)
            self.test_results.log_dict["Audio_Level[Vrms]"].append(audio_level)
            self.test_results.log_dict["Sig_Gen_Level[dBm]"].append(float(self.rx_set_power))
            self.test_results.log_dict["RSSI"].append(float(rssi))


        #  end lfo frequencies loop

        if False in test_passed:
            return False
        else:
            return True

    def rx_spurious_emission(self, test_config_opt):
        test_id = 'rx_spurious_emission'

        self.test_results.create_test_results_path(standards_id=self.standard_id, test_id=test_id)

        self.radio_power_on()
        self.check_radio_serial_comms()
        self.radio_tx_off()

        test_config = self.get_test_config(test_config_opt=test_config_opt, test_id=test_id)
        self.test_results.test_param_log(test_config, test_config_opt)

        # self.setup_spec_an(config=test_config['spec_an'])

        screenshot = test_config['spec_an']['screenshot']
        looping_arrays = self.get_looping_arrays(test_config=test_config)

        self.test_results.log_dict = {"Frequency[MHz]" : [],
                                      "Sub_Range[]" : [],
                                      "Spurious_Emission_1[MHz]" : [],
                                      "Level_1[dBm]" : [],
                                      "Spurious_Emission_2[MHz]" : [],
                                      "Level_2[dBm]" : [],
                                      "Radio_Voltage[V]" : [],
                                      "Radio_Power_Mode": [],
                                      "Temperature[C]": [],
                                      "Timestamp": [],
                                      "Test_Passed": [],
                                      }

        test_result = self.tx_test_executor(looping_arrays=looping_arrays, test_function=self._rx_spurious_emission,
                                            screenshot=screenshot, test_config=test_config)
        self.test_results.save_log()

        return test_result

    def _rx_spurious_emission(self, freq, voltage, temp, radio_power, screenshot, test_config):

        test_passed = []
        self.test_equip.psu.voltage = voltage
        # self.test_equip.psu.current_limit = self.radio_param.tx_on_current_max[radio_power]

        if temp != 'NOT_USED':
            gui.print_yellow('[Notionally] Setting Temp to ' + str(temp))

        test_passed = []
        self.test_equip.psu.voltage = voltage

        if temp != 'NOT_USED':
            gui.print_yellow('[Notionally] Setting Temp to ' + str(temp))

        # self.transmit_radio_to_spec_an(freq=freq, power=radio_power, mod_source=0)
        # self.test_equip.spec_an.reset(val=True)
        for idx, sweeps in enumerate(test_config['spec_an']['subrange_sweeps'], start=1):

            self.test_equip.rf_switch.tx_radio_to_spec_an(
                filter=test_config['spec_an']['subrange_sweeps'][sweeps]['filter'])
            time.sleep(1)  # wait for switch action
            self.setup_spec_an(config=test_config['spec_an']['subrange_sweeps'][sweeps])
            # self.radio_transmit(freq=freq, power_level=radio_power, mod_source=0)
            # time.sleep(3)

            self.test_equip.spec_an.all_commands_set()
            # self.test_equip.spec_an.get_single_sweep()
            time.sleep(5)
            self.test_equip.spec_an.trace_peak = 'VIEW'
            self.test_equip.spec_an.marker_1 = 'MAX'
            self.test_equip.spec_an.marker_2 = 'MAX'
            self.test_equip.spec_an.marker_2 = 'MAX:NEXT'
            freq1, power1 = self.test_equip.spec_an.marker_1
            freq2, power2 = self.test_equip.spec_an.marker_2

            if not int(self.test_equip.spec_an.check_limit_line_pass_or_fail()[0]):
                test_passed.append(True)
            else:
                test_passed.append(False)

            #
            # print(f"(freq1, power1): {(freq1, power1)}")
            # print(f"(freq2, power2): {(freq2, power2)}")

            date_time = datetime.now().strftime("%Y_%m_%d_%H%M_%S")
            self.test_results.log_dict["Frequency[MHz]"].append(freq / 1e6)
            self.test_results.log_dict["Sub_Range[]"].append(idx)
            self.test_results.log_dict["Spurious_Emission_1[MHz]"].append(freq1 / 1e6)
            self.test_results.log_dict["Level_1[dBm]"].append(power1)
            self.test_results.log_dict["Spurious_Emission_2[MHz]"].append(freq2 / 1e6)
            self.test_results.log_dict["Level_2[dBm]"].append(power2)
            self.test_results.log_dict["Radio_Voltage[V]"].append(voltage)
            self.test_results.log_dict["Radio_Power_Mode"].append(radio_power)
            self.test_results.log_dict["Timestamp"].append(date_time)
            self.test_results.log_dict["Temperature[C]"].append(temp)
            self.test_results.log_dict["Test_Passed"].append(test_passed[idx - 1])

            self.test_equip.spec_an.screenshot(filename=date_time)

        self.radio_tx_off()

        if False in test_passed:
            print("Test Failed")
            return False
        else:
            print("Test Passed")
            return True

    def rx_birdie_scan(self, test_config_opt):
        test_id = 'rx_birdie_scan'  # specify test id
        print("Test : ", test_id)
        self.test_equip.rf_switch.rx_sig_gen_to_radio()  # specify rf switch to rx

        self.test_results.create_test_results_path(standards_id=self.standard_id, test_id=test_id)
        test_config = self.get_test_config(test_config_opt=test_config_opt, test_id=test_id)
        self.test_results.test_param_log(test_config, test_config_opt)

        # only 1 siggen is required and keep siggen off to act as 50ohm termination
        self.transmit_sig_gen_to_radio(rf_power_units=test_config['sig_gen_1']['power']['units'],
                                       lfo_freq=test_config['sig_gen_1']['lfo_frequency'],
                                       fm_dev=test_config['sig_gen_1']['fm_dev'],
                                       lfo_on=False, rf_on=False, fm_dev_on=False, sig_gen_no=1)

        self.check_radio_serial_comms()  # check serial comms
        self.radio_tx_off()  # turn off radio transmission

        # this is to extract parameter looping information from test_config
        looping_arrays = self.get_looping_arrays(test_config=test_config)
        self.first_test_loop = True

        self.test_results.log_dict = {"Frequency[Hz]": [],
                                      "Timestamp": [],
                                      "Test_Passed": [],
                                      "RSSI": [],
                                      "Target RSSI": [],
                                      }  # result dictionary
        #  this is the wrapper function
        test_result = self.rx_test_executor(looping_arrays=looping_arrays,
                                            test_function=self._rx_birdie_scan, test_config=test_config)

        self.test_results.save_log()
        self.test_equip.signal_gen_1.rf_power_on = False
        return test_result

    def _rx_birdie_scan(self, freq, voltage, temp, rx_radio_power, test_config):

        test_passed = []  # initialize test_passed list
        # turn on power supply to the radio
        self.test_equip.psu.voltage = voltage  # set power supply
        # turn off all filters to make sure audio bandwith is at least 20KHz
        self.test_equip.cms.turn_off_ccitt()
        self.test_equip.cms.turn_off_hpf()
        self.test_equip.cms.turn_off_lpf()

        lfo_frequencies = test_config['sig_gen_1']['lfo_frequency']
        fm_devs = test_config['sig_gen_1']['fm_dev']

        #number_lfo_frequencies = len(lfo_frequencies)
        number_of_measurements = 20

        if temp != 'NOT_USED':
            gui.print_yellow('[Notionally] Setting Temp to ' + str(temp))

        self.rx_set_power = test_config['sig_gen_1']['power']['start']  # actually this step is not needed
        self.audio_vol = test_config['radio_volume']  # this step is also not needed
        target_rssi = test_config['target_rssi']

        #print('number_lfo_freq: ', number_lfo_frequencies)

        # turn on sig_gen for testing the link
        # self.transmit_sig_gen_to_radio(rf_freq=freq, rf_power=self.rx_set_power, rf_on=True, fm_dev_on=True,
        #                               sql_toggle=1, audio_vol=self.audio_vol, sig_gen_no=1,
        #                               lfo_freq=lfo_frequencies, fm_dev=fm_devs)  # turn on modulation

        print("Frequency : ", freq)
        self.radio_receive(freq=freq, sql_toggle=0, audio_vol=self.audio_vol)
        # channel_number = self.radio_ctrl.get_channel()
        # print("channel number", channel_number)

        # rssi is not available yet in radios? looking for it
        rssi_acc = 0
        for i in range(number_of_measurements):
            #print("rssi measurement # ", i)
            rssi_acc = rssi_acc + self.radio_read_rssi() # read rms voltage from CMS54
            #print('rssi accumulative: ', rssi_acc)

        rssi_value = rssi_acc / number_of_measurements

        print('rssi: ', rssi_value)

        if rssi_value < target_rssi:  # acceptance criteria is <10%
            test_passed = True
        else:
            test_passed = False

        date_time = datetime.now().strftime("%d/%m/%Y, %H:%M:%S")
        self.test_results.log_dict["Frequency[Hz]"].append(freq)
        self.test_results.log_dict["RSSI"].append(rssi_value)
        self.test_results.log_dict["Test_Passed"].append(test_passed)
        self.test_results.log_dict["Timestamp"].append(date_time)
        self.test_results.log_dict["Target RSSI"].append(target_rssi)

        return test_passed


    def rx_receiver_radiated_spurious_emissions(self):
        pass

    def rx_receiver_residual_noise_level(self):
        pass

    def rx_squelch_operation(self):
        pass

    def rx_squelch_hysteresis(self):
        pass

    def rx_multiple_watch_characteristic(self):
        pass

    def rx_receiver_dynamic_range(self):
        pass

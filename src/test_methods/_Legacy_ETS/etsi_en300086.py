import yaml
import sys
import time
from datetime import datetime
from ETS_logging import text_formatter as gui
from test_methods.radio_tests_common import RadioTest
import json
import math
import numpy as np
import os
import yaml


class ETSI_EN300086(RadioTest):
    def __init__(self, equip_config, test_equipment, radio_eeprom, radio_param, radio_ctrl, test_results):
        super().__init__(equip_config, test_equipment, radio_eeprom, radio_param, radio_ctrl, test_results=test_results)
        self.standard_id = 'ETSI_EN300086'
        self.first_test_loop = None

    import os
    import yaml

    def get_test_config(self, test_config_opt, test_id):
        """
        Load the YAML for a legacy ETSI test.

        test_config_opt: one of 'xrs660_config', 'xrs390_config', ...
        test_id:          the base filename (without .yaml)

        Looks under:
          config/test_settings_config/_Legacy_ETS/<folder>/<test_id>.yaml
        where <folder> is mapped from test_config_opt.
        """
        # map your config-opt names to the legacy subfolder names
        folder_map = {
            'xrs660_config': 'ETSI_EN300086_XRS660',
            'xrs390_config': 'ETSI_EN300086_XRS390',
            'xrs370_config': 'ETSI_EN300086_XRS370',
            'xrs330_config': 'ETSI_EN300086_XRS330',
            'xrs335_config': 'ETSI_EN300086_XRS335',
        }
        # pick the right folder (or fall back to DEFAULT)
        folder = folder_map.get(test_config_opt, 'ETSI_EN300086_DEFAULT')

        # build the full path
        base_dir = os.path.join(
            'config', 'test_settings_config', '_Legacy_ETS', folder
        )
        yaml_path = os.path.join(base_dir, f"{test_id}.yaml")

        # load it
        with open(yaml_path, 'r', encoding='utf-8') as f:
            data = yaml.load(f, Loader=yaml.FullLoader)

        # sanity check
        if test_config_opt not in data:
            raise KeyError(f"'{test_config_opt}' key not found in {yaml_path}")

        return data[test_config_opt]

    def test_1(self, config):

        self.test_results.test_id = 'ETSI_EN301086 Test 1'
        print('Testing ETSI_EN301086 Test 1...')
        return True

    def test_2(self, config):
        self.test_results.test_id = 'ETSI_EN301086 Test 2'
        print('Testing ETSI_EN301086 Test 2...')
        return True

    def list_of_tests(self):  # Not a function - just to help keep track of things...

        TX_my_list = [
            self.tx_power,  # Done XRS660 tested ok
            self.tx_frequency_error,  # Done XRS660 tested ok
            self.tx_frequency_deviation,  # Done XRS660 tested ok but need to check test correctness
            self.tx_adjacent_channel_power,  # Done XRS660 tested ok but need to check test correctness
            self.tx_conducted_spurious_emissions_conveyed_antenna,  # Done
        ]

        RX_my_list = [
            self.rx_maximum_usable_sensitivity,  # Done XRS660 Tested ok
            self.rx_co_channel_rejection,  # Done XRS660 tested ok
            self.rx_adjacent_channel_selectivity,  # Done XRS660 tested ok
            self.rx_spurious_response_rejection,  # Done XRS660 tested ok
            self.rx_intermodulation_response_rejection,  # Done XRS660 tested ok
            self.rx_blocking_desensitization, # Done XRS660 tested ok
            self.rx_spurious_emission,  # Done XRS660 tested ok
        ]

    def tx_power(self, test_config_opt):
        test_id = 'tx_power'
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
                                      "Power[dBm]": [],
                                      "Voltage[V]": [],
                                      "Radio_Power_Mode": [],
                                      "Timestamp": [],
                                      "Temperature[C]": [],
                                      "Test_Passed": [],
                                      "Nominal Power[dBm]": [],
                                      "Tolerance[dB]": [],
                                      }
        self.first_test_loop = True
        test_result = self.tx_test_executor(looping_arrays=looping_arrays, test_function=self._tx_power, \
                                            screenshot=screenshot, test_config=test_config)
        self.test_results.save_log()

        return test_result

    def _tx_power(self, freq, voltage, temp, radio_power, screenshot, test_config=None):
        self.test_equip.psu.voltage = voltage

        if temp != 'NOT_USED':
            gui.print_yellow('[Notionally] Setting Temp to ' + str(temp))

        self.test_equip.psu.current_limit = self.radio_param.tx_on_current_max[radio_power]
        self.test_equip.spec_an.freq_centre = freq
        self.radio_transmit(freq=freq, power_level=radio_power)
        self.test_equip.spec_an.trace_peak = 'MAXH'
        self.test_equip.spec_an.trace_peak = 'VIEW'
        self.test_equip.spec_an.marker_1 = 'MAX'
        freq, power = self.test_equip.spec_an.marker_1

        nominal_power = test_config['power_low']
        if radio_power == 'HIGH_PWR':
            nominal_power = test_config['power_high']
        tolerance = test_config['tolerance']

        if abs(power-nominal_power) <= tolerance:
            test_passed = True
        else:
            test_passed = False

        print(f'Frequency: {self.test_equip.spec_an.freq_centre/1e6:.3f} MHz, Power: {power:.2f} dBm, '
              f'Power Mode: {radio_power}, Temp: {temp}, Voltage: {voltage}')

        date_time = datetime.now().strftime("%d/%m/%Y, %H:%M:%S")
        self.test_results.log_dict["Frequency[Hz]"].append(freq)
        self.test_results.log_dict["Power[dBm]"].append(power)
        self.test_results.log_dict["Voltage[V]"].append(voltage)
        self.test_results.log_dict["Radio_Power_Mode"].append(radio_power)
        self.test_results.log_dict["Timestamp"].append(date_time)
        self.test_results.log_dict["Temperature[C]"].append(temp)
        self.test_results.log_dict["Test_Passed"].append(test_passed)
        self.test_results.log_dict["Nominal Power[dBm]"].append(nominal_power)
        self.test_results.log_dict["Tolerance[dB]"].append(tolerance)

        if screenshot:
            date_time = datetime.now().strftime("%Y_%m_%d_%H%M_%S")
            self.test_equip.spec_an.screenshot(filename=date_time)
        self.radio_tx_off()

        return test_passed

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
                                      "Test_Passed": [],
                                      "Tolerance[Hz]": [],
                                      }
        self.first_test_loop = False
        test_result = self.tx_test_executor(looping_arrays=looping_arrays, test_function=self._tx_frequency_error, screenshot=screenshot)
        self.test_results.save_log()

        return test_result

    def _tx_frequency_error(self, freq, voltage, temp, radio_power, screenshot, test_config=None):
        self.test_equip.psu.voltage = voltage

        tolerance = test_config['tolerance']

        if temp != 'NOT_USED':
            gui.print_yellow('[Notionally] Setting Temp to ' + str(temp))

        self.test_equip.psu.current_limit = self.radio_param.tx_on_current_max[radio_power]
        self.test_equip.spec_an.freq_centre = freq
        self.radio_transmit(freq=freq, power_level=radio_power)
        self.test_equip.spec_an.trace_peak = 'MAXH'
        self.test_equip.spec_an.trace_peak = 'VIEW'
        self.test_equip.spec_an.marker_1 = 'MAX'
        freq, power = self.test_equip.spec_an.marker_1

        freq_error = abs(freq - self.test_equip.spec_an.freq_centre)
        if freq_error > tolerance:
            test_passed = False

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
        self.test_results.log_dict["Test_Passed"].append(test_passed)
        self.test_results.log_dict["Tolerance[Hz]"].append(tolerance)

        if screenshot:
            date_time = datetime.now().strftime("%Y_%m_%d_%H%M_%S")
            self.test_equip.spec_an.screenshot(filename=date_time)
        self.radio_tx_off()

        return test_passed

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
                                      "LF_Power[mV]": [],
                                      "FM_Dev_pk_plus[Hz]": [],
                                      "FM_Dev_pk_minus[Hz]": [],
                                      "FM_Dev_pk_avg[Hz]": [],
                                      "FM_Dev_max_permissible[Hz]": [],
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
        self.lf_set_power_mv = test_config['sig_gen_1']['power']['start_mv']
        self.transmit_radio_to_spec_an(freq=freq, power=radio_power, mod_source=0)

        # Find 3k deviation at nominal frequency
        self.test_equip.signal_gen_1.lfo_frequency = test_config['normal_test_mod']
        self.test_equip.signal_gen_1.lfo_voltage_mv = self.lf_set_power_mv
        self.test_equip.signal_gen_1.lfo_output_on = True

        fm_dev_pk_avg = float(self.test_equip.spec_an.meas_analog_demod_fm_dev()[0])
        target_fm_dev = float(test_config['normal_fm_dev'])  # standard frequency deviation

        found_target_fm_dev = False  # boolean for standard frequency deviation
        fm_dev_nominal = None
        max_permissible_fm_dev = None

        # Step 1: to find the microphone input voltage that will modulate with normal frequency deviation
        while not found_target_fm_dev:
            print(f'Searching for Target FM Dev. LF_set_mv: {self.lf_set_power_mv}')

            # if fm deviation exceeds normal level, increase mic audio level
            if (fm_dev_pk_avg > target_fm_dev + float(test_config['tolerance_fm_dev'])) and self.lf_set_power_mv > test_config['sig_gen_1']['power']['min_mv']:
                self.lf_set_power_mv -= float(test_config['sig_gen_1']['power']['step'])
                self.test_equip.signal_gen_1.lfo_voltage_mv = self.lf_set_power_mv

            # else if fm deviation is below normal level, decrease mic audio level
            elif fm_dev_pk_avg < target_fm_dev and self.lf_set_power_mv < test_config['sig_gen_1']['power']['max_mv']:
                self.lf_set_power_mv += test_config['sig_gen_1']['power']['step']
                self.test_equip.signal_gen_1.lfo_voltage_mv = self.lf_set_power_mv

            # read new fm deviation level
            time.sleep(0.5)
            fm_dev_pk_avg = self.test_equip.spec_an.meas_analog_demod_fm_dev()[0]

            # check if new fm deviation level is within normal range
            if (target_fm_dev - fm_dev_pk_avg) <= abs(float(test_config['tolerance_fm_dev'])):
                gui.print_green(f"Found {fm_dev_pk_avg} fm_dev @ {test_config['normal_test_mod']}kHz")
                found_target_fm_dev = True
                fm_dev_nominal = fm_dev_pk_avg
                if screenshot:
                    date_time = datetime.now().strftime("%Y_%m_%d_%H%M_%S")
                    self.test_equip.spec_an.screenshot(filename='_' + str(freq) + 'Hz_ ' + str(test_config['normal_test_mod']) + '_hz_' + date_time)

            # break while loop if audio input limit is reached
            if (self.lf_set_power_mv == test_config['sig_gen_1']['power']['min_mv']) or self.lf_set_power_mv == test_config['sig_gen_1']['power']['max_mv']:
                self.radio_tx_off()
                break

        # step 2: if step 1  is successful,
        if found_target_fm_dev:
            lf_power_set = self.lf_set_power_mv * 10  # increase audio input level by 20dB
            mod_frequencies = test_config['lfo_frequency']
            mod_frequencies_high = test_config['lfo_frequency_high']
            # check frequency deviation at different modulation frequencies at set voltage level
            # audio pass band modulation
            self._tx_frequency_deviation_executor(freq, radio_power, temp, voltage,
                                                  screenshot, test_config, test_passed,
                                                  emu_start=0, mod_frequencies=mod_frequencies,
                                                  lf_power_set=lf_power_set,)
            # out of band modulation
            self._tx_frequency_deviation_executor(freq, radio_power, temp, voltage,
                                                  screenshot, test_config, test_passed,
                                                  emu_start=16, mod_frequencies=mod_frequencies_high,
                                                  lf_power_set=lf_power_set/10)
            self.radio_tx_off()
            if False in test_passed:
                return False
            else:
                return True
            # end if found_target_fm_dev
        else:
            return False  # return test fail if standard dm deviation cannot be met

    def _tx_frequency_deviation_executor(self, freq, radio_power, temp, voltage,
                                         screenshot, test_config, test_passed,
                                         emu_start, mod_frequencies, lf_power_set):

        # for all audio frequencies (or modulating frequencies)
        for idx, mod_freq in enumerate(mod_frequencies):
            mod_freq = float(mod_freq)
            self.test_equip.signal_gen_1.lfo_frequency = mod_freq  # modulating frequency
            self.test_equip.signal_gen_1.lfo_voltage_mv = lf_power_set  # setting modulating signal level
            # check frequency deviation
            time.sleep(0.5)
            fm_dev_pk_avg, fm_dev_pk_plus, fm_dev_pk_minus = self.test_equip.spec_an.meas_analog_demod_fm_dev()
            if screenshot:
                date_time = datetime.now().strftime("%Y_%m_%d_%H%M_%S")
                self.test_equip.spec_an.screenshot(filename='_' + str(freq) + 'Hz_ ' + str(mod_freq) + '_hz_' + date_time)
            # if within audio pass band (lfo <3kHz), maximum frequency deviation is defined by config
            if float(test_config['lf_freq_normal_range'][0]) <= mod_freq <= (float(test_config['lf_freq_normal_range'][1])):
                max_permissible_fm_dev = test_config['max_fm_dev_normal_range']
            # if within audio pass band (lfo <3kHz), maximum frequency deviation is defined by another config
            elif float(test_config['lf_freq_high_range'][0]) <= mod_freq <= float(test_config['lf_freq_high_range'][1]):
                log_base_volt = 10
                log_const_volt = 20 # Gain for Voltage is 20 * log_10_(f2/f1)
                gain_per_octave = test_config['gain_per_octave_dB'] # # Gain per octave
                no_octaves = math.log(mod_freq/float(test_config['lf_freq_high_range'][0]), 2)  # how many octave away from edge
                max_permissible_fm_dev = log_base_volt**(gain_per_octave*no_octaves/log_const_volt)*test_config['max_fm_dev_high_range']
                print(f'Max Permissible FM_Dev: {max_permissible_fm_dev:.2f} No_Octaves: {no_octaves:.2f} ')
            # check results
            if fm_dev_pk_avg <= max_permissible_fm_dev:
                test_passed.append(True)
            else:
                test_passed.append(False)
            print(
                f'Frequency: {freq / 1e6:.3f} MHz, Mod_Freq {mod_freq:.2f} Hz, LF_Power_nom: {self.lf_set_power_mv:.2f}/ mV, '
                f'LF_Set_Power[mV] {lf_power_set:.2f}, fm_dev_pk_avg {fm_dev_pk_avg:.2f}, '
                f'Power Mode: {radio_power}, Temp: {temp}, Voltage: {voltage} Test_Passed: {test_passed[idx]}')

            date_time = datetime.now().strftime("%d/%m/%Y, %H:%M:%S")
            self.test_results.log_dict["Frequency[Hz]"].append(freq)
            self.test_results.log_dict["Mod_Freq[Hz]"].append(mod_freq)
            self.test_results.log_dict["LF_Power[mV]"].append(lf_power_set)
            self.test_results.log_dict["FM_Dev_pk_plus[Hz]"].append(fm_dev_pk_plus)
            self.test_results.log_dict["FM_Dev_pk_minus[Hz]"].append(fm_dev_pk_minus)
            self.test_results.log_dict["FM_Dev_pk_avg[Hz]"].append(fm_dev_pk_avg)
            self.test_results.log_dict["FM_Dev_max_permissible[Hz]"].append(max_permissible_fm_dev)
            self.test_results.log_dict["Radio_Voltage[V]"].append(voltage)
            self.test_results.log_dict["Radio_Power_Mode"].append(radio_power)
            self.test_results.log_dict["Temperature[C]"].append(temp)
            self.test_results.log_dict["Timestamp"].append(date_time)
            self.test_results.log_dict["Test_Passed"].append(test_passed[idx])

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
                                      "Transmit_On": [],
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

        tx_on = [1, 0]  # transmit / standby
        for tx in tx_on:
            self.radio_tx_off()
            for idx, sweeps in enumerate(test_config['spec_an']['subrange_sweeps'], start=1):
                self.test_equip.rf_switch.tx_radio_to_spec_an(\
                filter=test_config['spec_an']['subrange_sweeps'][sweeps]['filter'])
                time.sleep(1) # wait for switch action
                self.setup_spec_an(config=test_config['spec_an']['subrange_sweeps'][sweeps])
                if tx:
                    self.radio_transmit(freq=freq, power_level=radio_power, mod_source=0)
                limit = test_config['spec_an']['subrange_sweeps'][sweeps]['limit'][tx]
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


                if power1 < limit and power2 < limit:
                    test_passed.append(True)
                else:
                    test_passed.append(False)

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
                self.test_results.log_dict["Transmit_On"].append(tx)

                self.test_equip.spec_an.screenshot(filename=date_time)

        self.radio_tx_off()
        if False in test_passed:
            return False
        else:
            return True

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
                return found_target_fm_dev, fm_dev_pk_avg

            if self.lf_set_power_mv == max_mv or self.lf_set_power_mv == min_mv:
                return found_target_fm_dev, fm_dev_pk_avg
                break

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

        self.test_results.log_dict = {"Frequency[Hz]": [],
                                      "Carrier_Power[dBm]": [],
                                      "ADJCP+[dBc]": [],
                                      "ADJCP-[dBc]": [],
                                      "ALTCP+[dBc]": [],
                                      "ALTCP-[dBc]": [],
                                      "Radio_Voltage[V]": [],
                                      "Radio_Power_Mode": [],
                                      "Temperature[C]": [],
                                      "Timestamp": [],
                                      "Test_Passed": [],
                                      "Limit": [],
                                      "LFO_Voltage[mV]": [],
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
        self.lf_set_power_mv = test_config['sig_gen_1']['power']['start_mv']
        self.transmit_radio_to_spec_an(freq=freq, power=radio_power, mod_source=1)

        # Step: Find nominal voltage for 1000 Hz frequency deviation at nominal frequency
        self.test_equip.signal_gen_1.lfo_frequency = test_config['normal_test_mod']  # standard modulation frequency
        self.test_equip.signal_gen_1.lfo_voltage_mv = self.lf_set_power_mv
        self.test_equip.signal_gen_1.lfo_output_on = True
        fm_dev_pk_avg = float(self.test_equip.spec_an.meas_analog_demod_fm_dev()[0])  # measure frequency deviation
        target_fm_dev = float(test_config['normal_fm_dev'])  # standard frequency deviation
        # find the audio input level that provides the target frequency deviation
        found_target_fm_dev, fm_dev_pk_avg = self.find_fm_dev_target(target_fm_dev=test_config['normal_fm_dev'],
                                                                     tolerance_fm_dev=test_config['tolerance_fm_dev'],
                                                                     max_mv=test_config['sig_gen_1']['power']['max_mv'],
                                                                     min_mv=test_config['sig_gen_1']['power']['min_mv'],
                                                                     step=test_config['sig_gen_1']['power']['step'])
        #  if standard modulation freq dev is found, use 20dB higher to measure ACP
        found_target_fm_dev = True
        if found_target_fm_dev:
            # prepare for ACP measurement
            self.test_equip.signal_gen_1.lfo_voltage_mv = self.test_equip.signal_gen_1.lfo_voltage_mv*10  # 20dB higher
            self.setup_spec_an(config=test_config['spec_an']['acp'])  # setup spec an to ACP mode
            self.test_equip.signal_gen_1.lfo_frequency = test_config['test_lfo_frequency']
            self.transmit_radio_to_spec_an(freq=freq, power=radio_power, mod_source=0)  # transmit without modulation
            time.sleep(8) # why sleep for 8 seconds? TODO:
            acp_list = self.test_equip.spec_an.get_adjacent_channel_power_meas()  # conduct ACP measurement using spec AN
            acp_screenshot = test_config['spec_an']['acp']['screenshot']
            limit = test_config['limit']

            if float(acp_list[1]) <= limit and float(acp_list[2]) and float(acp_list[3]) <= limit and float(acp_list[4]) <= limit:
                test_passed.append(True)
            else:
                test_passed.append(False)

            print(f'Frequency: {self.test_equip.spec_an.freq_centre/1e6:.3f} MHz, Power: {float(acp_list[0]):.2f} dBm,'
                  f'ACP+: {float(acp_list[1]):.2f}, ACP-: {float(acp_list[2]):.2f}, Temp: {temp}, Voltage: {voltage}')

            date_time = datetime.now().strftime("%d/%m/%Y, %H:%M:%S")
            self.test_results.log_dict["Frequency[Hz]"].append(freq)
            self.test_results.log_dict["Carrier_Power[dBm]"].append(acp_list[0])
            self.test_results.log_dict["ADJCP+[dBc]"].append(acp_list[1])
            self.test_results.log_dict["ADJCP-[dBc]"].append(acp_list[2])
            self.test_results.log_dict["ALTCP+[dBc]"].append(acp_list[3])
            self.test_results.log_dict["ALTCP-[dBc]"].append(acp_list[4])
            self.test_results.log_dict["Radio_Voltage[V]"].append(voltage)
            self.test_results.log_dict["Radio_Power_Mode"].append(radio_power)
            self.test_results.log_dict["Timestamp"].append(date_time)
            self.test_results.log_dict["Temperature[C]"].append(temp)
            self.test_results.log_dict["Test_Passed"].append(test_passed)
            self.test_results.log_dict["Limit"].append(limit)
            self.test_results.log_dict["LFO_Voltage[mV]"].append(self.test_equip.signal_gen_1.lfo_voltage_mv)

            if acp_screenshot:
                date_time = datetime.now().strftime("%Y_%m_%d_%H%M_%S")
                self.test_equip.spec_an.screenshot(filename='_' + str(freq) + 'Hz_ ' + str(
                    test_config['normal_test_mod']) + '_hz_' + date_time)

            self.radio_tx_off()
            if False in test_passed:
                return False
            else:
                return True
        else:
            return False


    # end transmitter tests



    # start receiver tests

    #MUS is DONE & Verified on 26/27/24
    def rx_maximum_usable_sensitivity(self, test_config_opt):

        test_id = 'rx_maximum_usable_sensitivity'
        print(test_id)
        print('\n\n')
        #self.test_equip.rf_switch.rx_sig_gen_to_radio()
        time_now_start = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        
        self.test_results.create_test_results_path(standards_id=self.standard_id, test_id=test_id)
        test_config = self.get_test_config(test_config_opt=test_config_opt, test_id=test_id)
        self.test_results.test_param_log(test_config, test_config_opt)

        self.transmit_sig_gen_to_radio(rf_power_units=test_config['sig_gen_1']['power']['units'],
                                       lfo_freq=test_config['sig_gen_1']['lfo_frequency'],
                                       fm_dev=test_config['sig_gen_1']['fm_dev'],
                                       lfo_on=False, rf_on=False, fm_dev_on=False, sig_gen_no=1)

        #self.transmit_sig_gen_to_radio(lfo_on=False, rf_on=False, fm_dev_on=False, sig_gen_no=2)
        looping_arrays = self.get_looping_arrays(test_config=test_config)
        self.first_test_loop = True

        self.test_results.log_dict = {"Frequency[Hz]" : [],
                                      "SINAD[dB]" : [],
                                      "Rx Power[dBm]" : [],
                                      "Voltage[V]" : [],
                                      "Temperature[C]": [],
                                      "Timestamp": [],
                                      "Test_Passed" : [],
                                      "Firmware": [],
                                      "Serial No":[],
                                      "Current (A)": [],
                                      "Audio Level (Vrms)": [],
                                      }

        test_result = self.rx_test_executor(looping_arrays=looping_arrays,
                                            test_function=self._rx_maximum_usable_sensitivity,
                                            test_config=test_config)

        self.test_results.save_log()
        self.test_equip.signal_gen_1.rf_power_on = False

        time_now_end = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        print("\nTest end date & time: %s " % time_now_start)
        print("Test end date & time: %s " % time_now_end)

        return test_result

    #MUS is DONE & Verified on 26/27/24
    def _rx_maximum_usable_sensitivity(self, freq, voltage, temp, rx_radio_power, test_config):

        print('\n\nReceiver Maximum Usable Sensitivity Test')
        print("Frequency: ", freq)

        path_loss1 = test_config['sig_gen_1']['path_loss']  # path loss for sig gen 1
        max_power1 = test_config['sig_gen_1']['power']['max'] + path_loss1
        audio_vol = test_config['radio_volume']
        self.radio_receive(freq=freq, audio_vol=audio_vol)
        radio_current = float(self.test_equip.psu.get_current_level())
        #print("First Test Loop: ", self.first_test_loop)

        if temp != 'NOT_USED':
            gui.print_yellow('[Notionally] Setting Temp to ' + str(temp))

        if self.first_test_loop:
            self.rx_set_power = test_config['sig_gen_1']['power']['start']
            self.rx_set_offset = -test_config['sig_gen_1']['power']['offset']
            self.transmit_sig_gen_to_radio(rf_freq=freq, rf_power=self.rx_set_power+path_loss1,
                                           rf_power_offset=self.rx_set_offset,
                                           rf_on=True, fm_dev_on=True, sig_gen_no=1,
                                           audio_vol=audio_vol, sql_toggle=1)
            self.first_test_loop = False
            print('Sig Gen 1 should now be transmitting...')
            time.sleep(3)

        else:
            self.transmit_sig_gen_to_radio(rf_freq=freq, audio_vol=audio_vol, sig_gen_no=1, sql_toggle=1)

        sinad, self.rx_set_power, audio_level = self.find_sinad_power(target_sinad=test_config['sinad_target'],
                                                         set_power=self.rx_set_power,
                                                         max_power=max_power1,
                                                         min_power=test_config['sig_gen_1']['power']['min'],
                                                         power_step=test_config['sig_gen_1']['power']['step'],
                                                         rf_freq=freq,
                                                         path_loss=path_loss1,
                                                         sinad_tolerance=test_config['sinad_tolerance'],
                                                         sc=False)

        if sinad >= test_config['sinad_target'] and (self.rx_set_power - path_loss1) <= test_config['sig_gen_1']['power']['thresh']:
            test_passed = True
        else:
            test_passed = False

        date_time = datetime.now().strftime("%d/%m/%Y, %H:%M:%S")
        print(f'Frequency: {self.test_equip.signal_gen_1.rf_frequency/1e6:.3f} MHz, SINAD: {sinad:.2f} dB, Audio Level: {audio_level:.2f} Vrms, Rx Power: {self.rx_set_power} dbm ')
        self.test_results.log_dict["Frequency[Hz]"].append(freq)
        self.test_results.log_dict["SINAD[dB]"].append(sinad)
        self.test_results.log_dict["Rx Power[dBm]"].append(self.rx_set_power)
        self.test_results.log_dict["Voltage[V]"].append(voltage)
        self.test_results.log_dict["Temperature[C]"].append(temp)
        self.test_results.log_dict["Timestamp"].append(date_time)
        self.test_results.log_dict["Test_Passed"].append(test_passed)
        self.test_results.log_dict["Firmware"].append(self.radio_ctrl.read_fw_version())
        self.test_results.log_dict["Serial No"].append(self.radio_ctrl.get_radio_serial_number())
        self.test_results.log_dict["Current (A)"].append(radio_current)
        self.test_results.log_dict["Audio Level (Vrms)"].append(audio_level)

        return test_passed

    def rx_co_channel_rejection(self, test_config_opt):
        test_id = 'rx_co_channel_rejection'
        print(test_id)
        print('\n\n')

        time_now_start = datetime.now().strftime("%d-%m-%Y %H:%M:%S")

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

        looping_arrays = self.get_looping_arrays(test_config=test_config)
        self.first_test_loop = True

        self.test_results.log_dict = {
            "RX_Frequency[Hz]": [],
            "Interfere_Frequency[Hz]": [],
            "Interfere_Power[dBuv]": [],
            "Co-Channel_Rej[dB]": [],
            "RX_Power[dBuv]": [],
            "SINAD[dB]": [],
            "Radio_Voltage[V]": [],
            "Temperature[C]": [],
            "Timestamp": [],
            "Test_Passed": [],
            "Firmware": [],
        }

        test_result = self.rx_test_executor(looping_arrays=looping_arrays,
                                            test_function=self._rx_co_channel_rejection,
                                            test_config=test_config)

        self.test_results.save_log()
        self.test_equip.signal_gen_1.rf_power_on = False
        self.test_equip.signal_gen_2.rf_power_on = False

        time_now_end = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        print("\nTest end date & time: %s " % time_now_start)
        print("Test end date & time: %s " % time_now_end)

        return test_result

    def _rx_co_channel_rejection(self, freq, voltage, temp, rx_radio_power, test_config):
        # rx_set_power and interfere_pwr does not contain path loss offset
        test_passed = []
        time.sleep(1.0)
        vol = test_config['radio_volume']

        path_loss1 = test_config['sig_gen_1']['path_loss']  # path loss for sig gen 1
        path_loss2 = test_config['sig_gen_2']['path_loss']  # path loss for sig gen 2
        # set signal gen 1 - wanted test signal
        self.rx_set_power = test_config['sig_gen_1']['power']['start']
        self.rx_set_offset1 = -test_config['sig_gen_1']['power']['offset']
        self.transmit_sig_gen_to_radio(rf_freq=freq, rf_power=self.rx_set_power + path_loss1,
                                       rf_power_offset=self.rx_set_offset1,
                                       rf_on=True, fm_dev_on=True, sig_gen_no=1,
                                       audio_vol=int(test_config['radio_volume']), sql_toggle=1)

        self.radio_receive(freq=freq, audio_vol=vol)
        if temp != 'NOT_USED':
            gui.print_yellow('[Notionally] Setting Temp to ' + str(temp))

        self.max_interferer_pwr = test_config['sig_gen_2']['power']['max']
        self.min_interferer_pwr = test_config['sig_gen_2']['power']['min']
        self.interferer_pwr_step = test_config['sig_gen_2']['power']['step']

        sinad = self.get_sinad()  # uses CMS to get SINAD
        #sinad = self.measure_sinad_sc()
        print("Sinad: ", sinad)

        for idx in range(len(test_config['sig_gen_2']['interference_offset'])):
            interference_freq = freq + (float(test_config['sig_gen_2']['interference_offset'][idx]))
            self.interfere_power = test_config['sig_gen_2']['power']['start']
            self.rx_set_offset2 = -test_config['sig_gen_2']['power']['offset']
            self.transmit_sig_gen_to_radio(rf_freq=interference_freq,
                                           rf_power=self.interfere_power + path_loss2,
                                           rf_power_offset=self.rx_set_offset2,
                                           lfo_freq=test_config['sig_gen_2']['lfo_frequency'],
                                           fm_dev=test_config['sig_gen_2']['fm_dev'],
                                           rf_on=True, fm_dev_on=True, sig_gen_no=2)

            prev_interference_pwr = self.interfere_power

            sinad = self.get_sinad(avg=5)  # uses CMS to get SINAD
            #sinad = self.measure_sinad_sc(num=5, num_samps=4*4096, ccitt=True)
            sinad_tolerance = float(test_config['sinad_tolerance'])
            sinad_min = float(test_config['min_sinad'])

            mu = 1
            while True:
                self.transmit_sig_gen_to_radio(rf_power=self.interfere_power + path_loss2, sig_gen_no=2)
                time.sleep(0.5)  # delay  for power to stabilize
                #sinad = self.measure_sinad_sc(num=5)
                sinad = self.get_sinad(avg=5)  # uses CMS to get SINAD
                sinad_error = sinad_min - sinad
                step = mu * sinad_error * self.interferer_pwr_step
                print(f"sinad: {sinad}, rx_set_power: {self.rx_set_power}, interference_power: {self.interfere_power}")
                if (sinad >= sinad_min + sinad_tolerance) and self.interfere_power < self.max_interferer_pwr:
                    self.interfere_power -= step
                elif sinad < sinad_min and self.interfere_power > self.min_interferer_pwr:
                    self.interfere_power -= step
                else:
                    break
            # end while

            co_channel_rej_ratio = self.interfere_power - self.rx_set_power
            if test_config['co-channel_rej_ratio_min'] <= co_channel_rej_ratio <= test_config['co-channel_rej_ratio_max']:
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
            self.test_results.log_dict["Interfere_Power[dBuv]"].append(self.interfere_power)
            self.test_results.log_dict["Co-Channel_Rej[dB]"].append(co_channel_rej_ratio)
            self.test_results.log_dict["RX_Power[dBuv]"].append(self.rx_set_power)
            self.test_results.log_dict["SINAD[dB]"].append(sinad)
            self.test_results.log_dict["Radio_Voltage[V]"].append(voltage)
            self.test_results.log_dict["Temperature[C]"].append(temp)
            self.test_results.log_dict["Timestamp"].append(date_time)
            self.test_results.log_dict["Test_Passed"].append(test_passed[idx])
            self.test_results.log_dict["Firmware"].append(self.radio_ctrl.read_fw_version())

        if False in test_passed:
            return False
        else:
            return True

    def rx_adjacent_channel_selectivity(self, test_config_opt):

        test_id = 'rx_adjacent_channel_selectivity'
        print(test_id)
        print('\n\n')

        time_now_start = datetime.now().strftime("%d-%m-%Y %H:%M:%S")

        #self.test_equip.rf_switch.rx_sig_gen_to_radio()
        self.test_results.create_test_results_path(standards_id=self.standard_id, test_id=test_id)
        test_config = self.get_test_config(test_config_opt=test_config_opt, test_id=test_id)
        self.test_results.test_param_log(test_config, test_config_opt)

        # self.test_equip.soundcard.num_samples = test_config['soundcard']['no_samples']
        # self.test_equip.soundcard.psophometric_weighting = test_config['soundcard']['psophometric_weighting']

        # wanted signal
        #print('Configure sig gen 1:')
        self.test_equip.signal_gen_1.transmit_from_sig_gen(rf_power_units=test_config['sig_gen_1']['power']['units'],
                                                           lfo_freq=test_config['sig_gen_1']['lfo_frequency'],
                                                           fm_dev=test_config['sig_gen_1']['fm_dev'],
                                                           lfo_on=False, rf_on=False, fm_dev_on=False)

        # unwanted signal
        #print('Configure sig gen 2:')
        self.test_equip.signal_gen_2.transmit_from_sig_gen(rf_power_units=test_config['sig_gen_2']['power']['units'],
                                                           lfo_freq=test_config['sig_gen_2']['lfo_frequency'],
                                                           fm_dev=test_config['sig_gen_2']['fm_dev'],
                                                           lfo_on=False, rf_on=False, fm_dev_on=False)


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
                                      "Min Channel Selectivity[dB]": [],
                                      "Firmware": [],
                                      }

        test_result = self.rx_test_executor(looping_arrays=looping_arrays,
                                            test_function=self._rx_adjacent_channel_selectivity,
                                            test_config=test_config)

        self.test_results.save_log()
        self.test_equip.signal_gen_1.rf_power_on = False
        self.test_equip.signal_gen_2.rf_power_on = False

        time_now_end = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        print("\nTest end date & time: %s " % time_now_start)
        print("Test end date & time: %s " % time_now_end)

        return test_result

    def _rx_adjacent_channel_selectivity(self, freq, voltage, temp, rx_radio_power, test_config):
        
        test_passed = []
        path_loss1 = test_config['sig_gen_1']['path_loss']
        path_loss2 = test_config['sig_gen_2']['path_loss']
        soundcard_used = test_config['soundcard']['required']

        if temp != 'NOT_USED':
            gui.print_yellow('[Notionally] Setting Temp to ' + str(temp))


        if self.first_test_loop:
            self.rx_set_power = test_config['sig_gen_1']['power']['start']
            self.rx_set_offset1 = -test_config['sig_gen_1']['power']['offset']

            self.transmit_sig_gen_to_radio(rf_freq=freq, rf_power=self.rx_set_power + path_loss1,
                                           rf_power_offset=self.rx_set_offset1,
                                           rf_on=True, fm_dev_on=True, sig_gen_no=1,
                                           audio_vol=int(test_config['radio_volume']), sql_toggle=1)
            self.first_test_loop = False
        else:
            self.transmit_sig_gen_to_radio(rf_freq=freq, audio_vol=int(test_config['radio_volume']),
                                           sig_gen_no=1, sql_toggle=1)

        interference_freq_offsets = test_config['adj_chan_freq']
        #print(interference_freq_offsets)
        interference_power_thresh = self.rx_set_power + test_config['min_adj_chan_selectivity']

        self.radio_receive(freq=freq, audio_vol=test_config['radio_volume'])

        for idx, freq_offsets in enumerate(interference_freq_offsets):

            interference_freq = freq + float(freq_offsets)
            self.interfere_power = test_config['sig_gen_2']['power']['start']
            self.rx_set_offset2 = -test_config['sig_gen_2']['power']['offset']
            self.transmit_sig_gen_to_radio(rf_freq=interference_freq, rf_power=self.interfere_power+path_loss2,
                                           rf_power_offset=self.rx_set_offset2,
                                           rf_on=True, fm_dev_on=True, sig_gen_no=2)

            self.radio_receive(freq=freq, audio_vol=test_config['radio_volume'])
            min_sinad = test_config['min_sinad']
            sinad_tol = test_config['sinad_tolerance']

            step_init = float(test_config['sig_gen_2']['power']['step'])
            mu = 1

            while True:
                self.transmit_sig_gen_to_radio(rf_power=self.interfere_power+path_loss2, sig_gen_no=2)
                if not soundcard_used:
                    sinad = self.get_sinad(avg=5)
                else:
                    sinad = self.measure_sinad_sc()
                sinad_error = min_sinad - sinad
                step = mu * sinad_error * step_init
                if sinad >= (min_sinad + sinad_tol) and self.interfere_power < test_config['sig_gen_2']['power']['max']:
                    # case for sinad too high
                    self.interfere_power -= step
                    print(f"sinad: {sinad}, rx_set_power: {self.rx_set_power}, interference_power: {self.interfere_power}")
                elif sinad < min_sinad and self.interfere_power > test_config['sig_gen_2']['power']['min']:
                    # case for sinad below acceptance level
                    self.interfere_power -= step
                    print(
                    f"sinad: {sinad}, rx_set_power: {self.rx_set_power}, interference_power: {self.interfere_power}")
                elif min_sinad < sinad < (min_sinad + sinad_tol):
                    # case for sinad within range
                    break
                else:
                    # every other case
                    break

            adj_ch_rej = self.interfere_power-self.rx_set_power
            min_adj_chan_selectivity = test_config['min_adj_chan_selectivity']

            if adj_ch_rej >= min_adj_chan_selectivity:
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
            self.test_results.log_dict["Channel_Selectivity[dB]"].append(adj_ch_rej)
            self.test_results.log_dict["RX_Power[dBuv]"].append(self.rx_set_power)
            self.test_results.log_dict["INTERFERE_Power[dBuv]"].append(self.interfere_power)
            self.test_results.log_dict["SINAD[dB]"].append(sinad)
            self.test_results.log_dict["Radio_Voltage[V]"].append(voltage)
            self.test_results.log_dict["Temperature[C]"].append(temp)
            self.test_results.log_dict["Timestamp"].append(date_time)
            self.test_results.log_dict["Test_Passed"].append(test_passed[idx])
            self.test_results.log_dict["Min Channel Selectivity[dB]"].append(min_adj_chan_selectivity)
            self.test_results.log_dict["Firmware"].append(self.radio_ctrl.read_fw_version())

        if False in test_passed:
            return False
        else:
            return True

    def rx_spurious_response_rejection(self, test_config_opt):

        test_id = 'rx_spurious_response_rejection'
        print(test_id)
        print('\n\n')

        time_now_start = datetime.now().strftime("%d-%m-%Y %H:%M:%S")

        self.test_results.create_test_results_path(standards_id=self.standard_id, test_id=test_id)

        test_config = self.get_test_config(test_config_opt=test_config_opt, test_id=test_id)
        self.test_results.test_param_log(test_config, test_config_opt)

        looping_arrays = self.get_looping_arrays(test_config=test_config)
        self.first_test_loop = True

        #self.test_equip.soundcard.num_samples = test_config['soundcard']['no_samples']
        #self.test_equip.soundcard.psophometric_weighting = test_config['soundcard']['psophometric_weighting']

        self.test_equip.signal_gen_1.transmit_from_sig_gen(
            rf_power_units=test_config['sig_gen_1']['power']['units'],
            lfo_freq=test_config['sig_gen_1']['lfo_frequency'],
            fm_dev=test_config['sig_gen_1']['fm_dev'],
            lfo_on=False, rf_on=False, fm_dev_on=False)

        self.test_equip.signal_gen_3.transmit_from_sig_gen(
            rf_power_units=test_config['sig_gen_3']['power']['units'],
            lfo_freq=test_config['sig_gen_3']['lfo_frequency'],
            fm_dev=test_config['sig_gen_3']['fm_dev'],
            lfo_on=False, rf_on=False, fm_dev_on=False)

        date_time = datetime.now().strftime("%d/%m/%Y, %H:%M:%S")
        self.test_results.log_dict = {
            "RX_Frequency[Hz]": [],
            "INTERFERE_Frequency[Hz]": [],
            "Spurious_Resp_Rejection[dB]": [],
            "RX_Power[dBuv]": [],
            "INTERFERE_Power[dBuv]": [],
            "SINAD[dB]": [],
            "Radio_Voltage[V]": [],
            "Temperature[C]": [],
            "Timestamp": [],
            "Test_Passed": [],
            "Pass_Level[dB]": [],
        }

        test_result = self.rx_test_executor(looping_arrays=looping_arrays,
                                            test_function=self._rx_spurious_response_rejection,
                                            test_config=test_config)

        self.test_results.save_log()
        self.test_equip.signal_gen_1.rf_power_on = False
        self.test_equip.signal_gen_3.rf_power_on = False

        time_now_end = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        print("\nTest end date & time: %s " % time_now_start)
        print("Test end date & time: %s " % time_now_end)

        return test_result

    def find_sinad_min(self, test_config):
        # this function will return the interferer power at SINAD of min_sinad
        path_loss3 = test_config['sig_gen_3']['path_loss']
        min_sinad = test_config['min_sinad']
        min_interferer_pwr = test_config['sig_gen_3']['power']['min']
        max_interferer_pwr = test_config['sig_gen_3']['power']['max']
        interfere_power = test_config['sig_gen_3']['power']['start']
        pwr_step = test_config['sig_gen_3']['power']['step']
        mu = 0.1
        sinad = self.get_sinad(avg=5, ccitt=True)
        #sinad = self.measure_sinad_sc()
        itnum = 0
        itmax = 50
        while abs(sinad - min_sinad) > test_config['tolerance'] and (itnum < itmax):
            # adjust interferer power if the sinad is out of range
            itnum = itnum + 1
            #sinad = self.measure_sinad_sc()
            sinad = self.get_sinad(avg=5)
            sinad_error = min_sinad - sinad
            step = mu*sinad_error*pwr_step
            #sinad = self.get_sinad(num_samps=4096 * 4, ccitt=True)
            print(sinad)
            if sinad < min_sinad and interfere_power > min_interferer_pwr:
                # reduce interferer power if sinad is lower than minimum and there is space to reduce
                interfere_power -= step
            elif sinad >= min_sinad and interfere_power < max_interferer_pwr:
                interfere_power -= step
            else:
                break
            self.transmit_sig_gen_to_radio(rf_power=interfere_power + path_loss3, sig_gen_no=3)
        return interfere_power

    #TODO: to continue to rewrite the test
    def _rx_spurious_response_rejection(self, freq, voltage, temp, rx_radio_power, test_config):
        # this test consist of 2 parts - (a) sweep in limited frequency range (b) spot frequencies
        # First part sweep - the test should compute the limited frequency range for the test frequency and sweep for response at 5kHz interval
        # sinad is used to determine if a spurious response is present in the limited frequency range
        # what is the threshold used to determine spurious response? SINAD degraded by > 1dB
        # frequencies with spurious response will be tested for rejection ratio
        # Second part spot frequencies -
        # note path loss are not taken into account in rx_set_power and interferer_power - it is compensated in transmit

        def spot_frequencies(fc, freq_int):
            # purpose of this function is to generate a list of spot frequencies to test for rejection ratio
            freq_spot = []
            freq_lo = fc - freq_int
            flimit1 = 4e9
            flimit2 = 100e3

            #print("freq lo:", freq_lo)
            #print("freq intermediate#1:",freq_int)

            # compute spot frequencies outside limited range (100kHz to 4GHz)
            count = 1
            spot1_valid = True
            spot2_valid = True
            while (spot1_valid or spot2_valid):
                freq_spot_count1 = count * freq_lo + freq_int
                if flimit2 < freq_spot_count1 < flimit1:
                    freq_spot.append(freq_spot_count1)
                else:
                    spot1_valid = False
                freq_spot_count2 = count * freq_lo - freq_int
                if flimit2 < freq_spot_count2 < flimit1:
                    freq_spot.append(freq_spot_count2)
                else:
                    spot2_valid=False
                count = count + 1

            return freq_spot

        def limited_freq_range(freq, fIF1, fIF2, SR):
            # purpose of this function is to calculate the limited frequency range to sweep for spurious response
            fLO = freq - fIF1  # low side injection
            #fLO = freq + fIF1  # high side injection
            fLow = fLO - (fIF1+fIF2) - SR/2
            fHigh = fLO + (fIF1+fIF2) + SR/2
            return fLow, fHigh

        test_passed = []
        interference_freq_exceed = []  # store interferer frequency that exceed the limit
#       self.test_equip.psu.voltage = voltage
        time.sleep(2.0)
        self.radio_receive(freq=freq, audio_vol=15)
        time.sleep(2.0)

        path_loss1 = test_config['sig_gen_1']['path_loss']
        path_loss3 = test_config['sig_gen_3']['path_loss']

        if temp != 'NOT_USED':
            gui.print_yellow('[Notionally] Setting Temp to ' + str(temp))

        if self.first_test_loop:
            self.rx_set_power = test_config['sig_gen_1']['power']['start']
            self.transmit_sig_gen_to_radio(rf_freq=freq, rf_power=self.rx_set_power+path_loss1, rf_on=True, fm_dev_on=True,
                                           sql_toggle=1, sig_gen_no=1, audio_vol=int(test_config['radio_volume']))
            self.first_test_loop = False
        else:
            self.transmit_sig_gen_to_radio(rf_freq=freq, audio_vol=int(test_config['radio_volume']), sig_gen_no=1)

        # find sinad when there is no interferer to use for comparison to determine response later
        #sinad_no_interference = self.measure_sinad_sc()
        sinad_no_interference = self.get_sinad(avg=5, ccitt=True)
        sinad_response_margin = 1 # margin to determine sinad response has occurred
        print('sinad_no_interference : ',sinad_no_interference)
        print( '\n')

        sr = float(test_config['sr'])
        fIF1 = float(test_config['freq_intermediate_1'])
        fIF2 = float(test_config['freq_intermediate_2'])
        number_spot_frequencies = int(test_config['number_spot_frequencies'])
        exclude_freq_range = float(test_config['exclude_freq_range'])
        min_sinad = float(test_config['min_sinad'])

        # obtain frequency array for limited frequency range
        freq_sweep_interval = float(test_config['freq_sweep_interval'])
        freq_lower_limit, freq_upper_limit = limited_freq_range(freq=freq, fIF1=fIF1, fIF2=fIF2, SR=sr)
        interference_freq_array = np.arange(freq_lower_limit, freq_upper_limit, freq_sweep_interval)
        #print("Limited interference_freq_array", interference_freq_array)
        #print("Limited lower", freq_lower_limit)
        #print("Limited upper", freq_upper_limit)

        # obtain frequency array for spot frequencies in external range
        interference_spot_freq_array = spot_frequencies(fc=freq, freq_int=fIF1)
        #print("Outside limited freq", interference_spot_freq_array)

        idx = 0

        if True:
            # part 1 - sweep interference frequencies in limited range
            print('Sweep %d interference frequencies in limited range' % len(interference_freq_array))
            for interference_freq in interference_freq_array:
                if abs(interference_freq - freq) > exclude_freq_range:
                    # if interference frequency is not inside exclusive zone, process
                    # else do nothing
                    self.interfere_power = test_config['sig_gen_3']['power']['start']
                    interfer_pwr_min_sinad = self.interfere_power
                    # set unwanted signal power level at 86 dBuV(emf) according to ETSI EN300086
                    self.transmit_sig_gen_to_radio(rf_freq=interference_freq, rf_power=self.interfere_power+path_loss3, rf_on=True,
                                                   fm_dev_on=True, sig_gen_no=3)
                    sinad = self.get_sinad(ccitt=True, avg=5)
                    #sinad = self.measure_sinad_sc()
                    #print("Freq : ", interference_freq, " sinad: ", sinad)
                    # check response using sinad
                    #if (sinad < sinad_no_interference - sinad_response_margin):
                    if (sinad < min_sinad + 3):
                        # response occur find interferer power that gives 14dB sinad
                        interfer_pwr_min_sinad = self.find_sinad_min(test_config)
                        spur_rej_ratio = interfer_pwr_min_sinad - self.rx_set_power
                        if spur_rej_ratio < test_config['spurious_resp_rej_ratio']:
                            # rejection poorer than threshold, test failed
                            test_passed.append(False)
                        else:
                            # rejection better than threshold, test passed
                            test_passed.append(True)
                    else:
                        # no response, pass test
                        test_passed.append(True)

                    print(
                        f'RX_Frequency: {freq / 1e6:.3f} MHz, Inter Freq: {interference_freq / 1e6:.3f} MHz, Spurious_Resp_Rejection: '
                        f'{self.interfere_power - self.rx_set_power:.2f} dB, SINAD: {sinad:.2f} dB, RX_Power[dBuv]: {self.rx_set_power}, '
                        f'INTERFERE_Power[dBuv]: {self.interfere_power:.2f} Passed: {test_passed[idx]}')

                    spur_rej_ratio = interfer_pwr_min_sinad - self.rx_set_power
                    date_time = datetime.now().strftime("%d/%m/%Y, %H:%M:%S")
                    self.test_results.log_dict["RX_Frequency[Hz]"].append(freq)
                    self.test_results.log_dict["INTERFERE_Frequency[Hz]"].append(interference_freq)
                    self.test_results.log_dict["Spurious_Resp_Rejection[dB]"].append(spur_rej_ratio)
                    self.test_results.log_dict["RX_Power[dBuv]"].append(self.rx_set_power)
                    self.test_results.log_dict["INTERFERE_Power[dBuv]"].append(self.interfere_power)
                    self.test_results.log_dict["SINAD[dB]"].append(sinad)
                    self.test_results.log_dict["Radio_Voltage[V]"].append(voltage)
                    self.test_results.log_dict["Temperature[C]"].append(temp)
                    self.test_results.log_dict["Timestamp"].append(date_time)
                    self.test_results.log_dict["Test_Passed"].append(test_passed[idx])
                    self.test_results.log_dict["Pass_Level[dB]"].append(test_config['spurious_resp_rej_ratio'])
                    idx = idx + 1  # increase counter if inside processing zone
                # end if outside exclusive frequency
            #end for interference frequency sweep

        # part 2 - loop spot interference frequencies in extended range
        if True:
            print('Looping %d spot interference frequencies: ' % len(interference_spot_freq_array))
            for interference_freq in interference_spot_freq_array:
                print(interference_freq)
                if abs(interference_freq - freq) > exclude_freq_range:
                    # if interference frequency is not inside exclusive zone, process
                    # else do nothing
                    self.interfere_power = test_config['sig_gen_3']['power']['start']
                    interfer_pwr_min_sinad = self.interfere_power
                    # set unwanted signal power level at 86 dB emf according to ETSI EN300086
                    self.transmit_sig_gen_to_radio(rf_freq=interference_freq, rf_power=self.interfere_power + path_loss3, rf_on=True,
                                                   fm_dev_on=True, sig_gen_no=3)
                    sinad = self.get_sinad(ccitt=True, avg=5)
                    #sinad = self.measure_sinad_sc()
                    # check response using sinad
                    if (sinad < min_sinad + 3):
                        # response occur find interferer power that gives 14dB sinad
                        interfer_pwr_min_sinad = self.find_sinad_min(test_config)
                        spur_rej_ratio = interfer_pwr_min_sinad - self.rx_set_power
                        if spur_rej_ratio < test_config['spurious_resp_rej_ratio']:
                            # rejection poorer than threshold, test failed
                            test_passed.append(False)
                        else:
                            # rejection better than threshold, test passed
                            test_passed.append(True)
                    else:
                        # no response, pass test
                        test_passed.append(True)

                    print(
                        f'RX_Frequency: {freq / 1e6:.3f} MHz, Inter Freq: {interference_freq / 1e6:.3f} MHz, Spurious_Resp_Rejection: '
                        f'{self.interfere_power - self.rx_set_power:.2f} dB, SINAD: {sinad:.2f} dB, RX_Power[dBuv]: {self.rx_set_power}, '
                        f'INTERFERE_Power[dBuv]: {self.interfere_power:.2f} Passed: {test_passed[idx]}')

                    spur_rej_ratio = interfer_pwr_min_sinad - self.rx_set_power
                    date_time = datetime.now().strftime("%d/%m/%Y, %H:%M:%S")
                    self.test_results.log_dict["RX_Frequency[Hz]"].append(freq)
                    self.test_results.log_dict["INTERFERE_Frequency[Hz]"].append(interference_freq)
                    self.test_results.log_dict["Spurious_Resp_Rejection[dB]"].append(spur_rej_ratio)
                    self.test_results.log_dict["RX_Power[dBuv]"].append(self.rx_set_power)
                    self.test_results.log_dict["INTERFERE_Power[dBuv]"].append(self.interfere_power)
                    self.test_results.log_dict["SINAD[dB]"].append(sinad)
                    self.test_results.log_dict["Radio_Voltage[V]"].append(voltage)
                    self.test_results.log_dict["Temperature[C]"].append(temp)
                    self.test_results.log_dict["Timestamp"].append(date_time)
                    self.test_results.log_dict["Test_Passed"].append(test_passed[idx])
                    self.test_results.log_dict["Pass_Level[dB]"].append(test_config['spurious_resp_rej_ratio'])
                    idx = idx + 1
                #end if outside exclusive frequency range
            # end for spot frequencies

        self.transmit_sig_gen_to_radio(rf_on=False, fm_dev_on=False, sig_gen_no=3)
        if False in test_passed:
            return False
        else:
            return True

    def rx_intermodulation_response(self, test_config_opt):
        test_id = 'rx_intermodulation_response'
        print(test_id)
        print('\n\n')

        time_now_start = datetime.now().strftime("%d-%m-%Y %H:%M:%S")

        #self.test_equip.rf_switch.rx_sig_gen_to_radio()
        self.test_results.create_test_results_path(standards_id=self.standard_id, test_id=test_id)
        test_config = self.get_test_config(test_config_opt=test_config_opt, test_id=test_id)
        self.test_results.test_param_log(test_config, test_config_opt)

        # configure signal gen #1
        self.transmit_sig_gen_to_radio(
            rf_power_units=test_config['sig_gen_1']['power']['units'],
            lfo_freq=test_config['sig_gen_1']['lfo_frequency'],
            fm_dev=test_config['sig_gen_1']['fm_dev'],
            lfo_on=False, rf_on=False, fm_dev_on=False, sig_gen_no=1)

        # configure signal gen #2
        self.transmit_sig_gen_to_radio(
            rf_power_units=test_config['sig_gen_2']['power']['units'],
            lfo_on=False, rf_on=False, fm_dev_on=False, sig_gen_no=2)

        # configure signal gen #3
        self.transmit_sig_gen_to_radio(
            rf_power_units=test_config['sig_gen_3']['power']['units'],
            lfo_freq=test_config['sig_gen_3']['lfo_frequency'],
            fm_dev=test_config['sig_gen_3']['fm_dev'],
            lfo_on=False, rf_on=False, fm_dev_on=False, sig_gen_no=3)

        looping_arrays = self.get_looping_arrays(test_config=test_config)
        self.first_test_loop = True

        self.test_results.log_dict = {
            "RX_Frequency[Hz]": [],
            "Interfere_Frequency_B[Hz]": [],
            "Interfere_Frequency_C[Hz]": [],
            "Interfere_Power_B[dBuv]": [],
            "Interfere_Power_C[dBuv]": [],
            "Intermod_Resp[dB]": [],
            "Min_Intermod_Resp[dB]": [],
            "RX_Power[dBuv]": [],
            "SINAD[dB]": [],
            "Radio_Voltage[V]": [],
            "Temperature[C]": [],
            "Timestamp": [],
            "Test_Passed": [],
            "Firmware": [],
        }

        test_result = self.rx_test_executor(looping_arrays=looping_arrays,
                                            test_function=self._rx_intermodulation_response,
                                            test_config=test_config)

        self.test_results.save_log()
        # only turn on RF power during tests
        self.test_equip.signal_gen_1.rf_power_on = False
        self.test_equip.signal_gen_2.rf_power_on = False
        self.test_equip.signal_gen_3.rf_power_on = False

        time_now_end = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        print("\nTest end date & time: %s " % time_now_start)
        print("Test end date & time: %s " % time_now_end)

        return test_result

    def _rx_intermodulation_response(self, freq, voltage, temp, rx_radio_power, test_config):
        test_passed = []
        self.test_equip.psu.voltage = voltage

        time.sleep(1.0)

        if temp != 'NOT_USED':
            gui.print_yellow('[Notionally] Setting Temp to ' + str(temp))

        soundcard_req = test_config['soundcard']['required']
        self.rx_set_power = test_config['sig_gen_1']['power']['start']
        self.rx_set_offset1 = -test_config['sig_gen_1']['power']['offset']
        self.path_loss1 = test_config['sig_gen_1']['path_loss']
        self.path_loss2 = test_config['sig_gen_2']['path_loss']
        self.path_loss3 = test_config['sig_gen_3']['path_loss']
        self.sinad_tol = test_config['sinad_tol']
        self.min_sinad = test_config['min_sinad']
        self.max_interferer_pwr = test_config['sig_gen_2']['power']['max']
        self.min_interferer_pwr = test_config['sig_gen_2']['power']['min']
        self.transmit_sig_gen_to_radio(rf_freq=freq, rf_power=self.rx_set_power+self.path_loss1,
                                       rf_power_offset=self.rx_set_offset1,
                                       rf_on=True, fm_dev_on=True, sig_gen_no=1,
                                       audio_vol=int(test_config['radio_volume']), sql_toggle=1)

        self.radio_receive(freq=freq, audio_vol=int(test_config['radio_volume']))

        for idx in range(len(test_config['sig_gen_2']['interference_offset'])):
            interference_freq_b = freq + float(test_config['sig_gen_2']['interference_offset'][idx])
            interference_freq_c = freq + float(test_config['sig_gen_3']['interference_offset'][idx])

            self.interfere_power = test_config['sig_gen_2']['power']['start']
            self.rx_set_offset2 = -test_config['sig_gen_2']['power']['offset']
            self.rx_set_offset3 = -test_config['sig_gen_3']['power']['offset']

            self.transmit_sig_gen_to_radio(rf_freq=interference_freq_b,
                                           rf_power=self.interfere_power + self.path_loss2,
                                           rf_power_offset=self.rx_set_offset2,
                                           fm_dev_on='False', rf_on=True, sig_gen_no=2)
            self.transmit_sig_gen_to_radio(rf_freq=interference_freq_c,
                                           rf_power=self.interfere_power + self.path_loss3,
                                           rf_power_offset=self.rx_set_offset3,
                                           lfo_freq=test_config['sig_gen_3']['lfo_frequency'],
                                           fm_dev=test_config['sig_gen_3']['fm_dev'],
                                           rf_on=True, fm_dev_on=True, sig_gen_no=3)

            #sinad = self.get_sinad(avg=10)  # get SINAD reading from CMS
            #sinad = self.measure_sinad_sc(num=10)

            self.interferer_pwr_step = test_config['sig_gen_2']['power']['step']
            mu = 1

            while True:
                self.transmit_sig_gen_to_radio(rf_power=self.interfere_power + self.path_loss2, sig_gen_no=2)
                self.transmit_sig_gen_to_radio(rf_power=self.interfere_power + self.path_loss3, sig_gen_no=3)
                time.sleep(0.2)  # delay  for power to stabilize
                if not soundcard_req:
                    sinad = self.get_sinad(avg=10)
                else:
                    sinad = self.measure_sinad_sc(num=5)
                sinad_error = self.min_sinad - sinad
                step = mu * sinad_error * self.interferer_pwr_step
                print(f"sinad: {sinad}, rx_set_power: {self.rx_set_power}, interference_power: {self.interfere_power}")
                if (sinad >= self.min_sinad + self.sinad_tol) and self.interfere_power < self.max_interferer_pwr:
                    self.interfere_power -= step
                elif sinad < self.min_sinad and self.interfere_power > self.min_interferer_pwr:
                    self.interfere_power -= step
                else:
                    break

            intermod_resp_ratio = self.interfere_power - self.rx_set_power
            pass_criteria = test_config['intermod_resp_ratio']
            if intermod_resp_ratio >= pass_criteria:
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
            self.test_results.log_dict["Intermod_Resp[dB]"].append(intermod_resp_ratio)
            self.test_results.log_dict["Min_Intermod_Resp[dB]"].append(pass_criteria)
            self.test_results.log_dict["RX_Power[dBuv]"].append(self.rx_set_power)
            self.test_results.log_dict["SINAD[dB]"].append(sinad)
            self.test_results.log_dict["Radio_Voltage[V]"].append(voltage)
            self.test_results.log_dict["Temperature[C]"].append(temp)
            self.test_results.log_dict["Timestamp"].append(date_time)
            self.test_results.log_dict["Test_Passed"].append(test_passed[idx])
            self.test_results.log_dict["Firmware"].append(self.radio_ctrl.read_fw_version())

        self.transmit_sig_gen_to_radio(rf_on=False, fm_dev_on=False, sig_gen_no=2)
        self.transmit_sig_gen_to_radio(rf_on=False, fm_dev_on=False, sig_gen_no=3)

        if False in test_passed:
            return False
        else:
            return True

    def rx_blocking_desensitization(self, test_config_opt):

        test_id = 'rx_blocking_desensitization'
        print(test_id)
        print('\n\n')

        time_now_start = datetime.now().strftime("%d-%m-%Y %H:%M:%S")

        #self.test_equip.rf_switch.rx_sig_gen_to_radio()
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

        looping_arrays = self.get_looping_arrays(test_config=test_config)
        self.first_test_loop = True

        self.test_results.log_dict = {
                                      "RX_Frequency[Hz]": [],
                                      "INTERFERE_Frequency[Hz]": [],
                                      "Channel_Blocking[dB]": [],
                                      "Min_Channel_Blocking[dB]": [],
                                      "RX_Power[dBuv]": [],
                                      "INTERFERE_Power[dBuv]": [],
                                      "SINAD[dB]": [],
                                      "Radio_Voltage[V]": [],
                                      "Temperature[C]": [],
                                      "Timestamp": [],
                                      "Test_Passed": [],
                                      "Firmware": [],
                                      }

        test_result = self.rx_test_executor(looping_arrays=looping_arrays,
                                            test_function=self._rx_blocking_desensitization,
                                            test_config=test_config)

        self.test_results.save_log()
        self.test_equip.signal_gen_1.rf_power_on = False
        self.test_equip.signal_gen_2.rf_power_on = False

        time_now_end = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        print("\nTest end date & time: %s " % time_now_start)
        print("Test end date & time: %s " % time_now_end)

        return test_result

    def _rx_blocking_desensitization(self, freq, voltage, temp, rx_radio_power, test_config):
        # note: rx_set_power and interfer_power does not include path loss! handled during transmit
        test_passed = []
        self.test_equip.psu.voltage = voltage

        path_loss1 = test_config['sig_gen_1']['path_loss']
        path_loss2 = test_config['sig_gen_2']['path_loss']
        soundcard_req = test_config['soundcard']['required']

        if temp != 'NOT_USED':
            gui.print_yellow('[Notionally] Setting Temp to ' + str(temp))


        if self.first_test_loop:
            self.rx_set_power = test_config['sig_gen_1']['power']['start']
            self.rx_set_offset1 = -test_config['sig_gen_1']['power']['offset']

            self.transmit_sig_gen_to_radio(rf_freq=freq, rf_power=self.rx_set_power + path_loss1,
                                           rf_power_offset=self.rx_set_offset1,
                                           rf_on=True, fm_dev_on=True, sig_gen_no=1,
                                           audio_vol=int(test_config['radio_volume']), sql_toggle=1)
            self.first_test_loop = False
        else:
            self.transmit_sig_gen_to_radio(rf_freq=freq, audio_vol=int(test_config['radio_volume']),
                                           sig_gen_no=1, sql_toggle=1)

        self.radio_receive(freq=freq, audio_vol=int(test_config['radio_volume']))

        # for single or self-defined sweeping frequencies
        if test_config['blocking_sweep_freq']['required']:
            interference_freq_offsets = test_config['blocking_sweep_freq']['sweep_freq']
        else:
            interference_freq_offsets = test_config['blocking_freq']

        # generate custom blocking sweep with regular interval, note regular block sweep > block sweep > sweep
        if test_config['regular_blocking_sweep_freq']['required']:
            start_sweep_freq = float(test_config['regular_blocking_sweep_freq']['start_sweep_freq'])
            end_sweep_freq = float(test_config['regular_blocking_sweep_freq']['end_sweep_freq'])
            sweep_interval = float(test_config['regular_blocking_sweep_freq']['sweep_interval'])
            if test_config['regular_blocking_sweep_freq']['doubleside']:
                interference_freq_offsets_plus = [i for i in np.arange(start_sweep_freq, end_sweep_freq, sweep_interval)]
                interference_freq_offsets_minus = [i for i in np.arange(-end_sweep_freq, -start_sweep_freq, sweep_interval)]
                interference_freq_offsets = interference_freq_offsets_minus + interference_freq_offsets_plus
            else:
                interference_freq_offsets = [i for i in np.arange(start_sweep_freq, end_sweep_freq, sweep_interval)]

        for idx, freq_offsets in enumerate(interference_freq_offsets):

            interference_freq = freq + float(freq_offsets)
            self.interfere_power = test_config['sig_gen_2']['power']['start']
            self.rx_set_offset2 = -test_config['sig_gen_2']['power']['offset']
            self.transmit_sig_gen_to_radio(rf_freq=interference_freq, rf_power=self.interfere_power + path_loss2,
                                           rf_power_offset=self.rx_set_offset2,
                                           rf_on=True, fm_dev_on=False, sig_gen_no=2)

            min_sinad = test_config['min_sinad']
            sinad_tol = test_config['sinad_tolerance']
            sinad_maxloop_break = 16 # this is the sinad value to break the loop
            max_interferer_pwr = test_config['sig_gen_2']['power']['max'] + path_loss2
            min_interferer_pwr = test_config['sig_gen_2']['power']['min'] + path_loss2
            interferer_pwr_step = test_config['sig_gen_2']['power']['step']
            min_blocking = test_config['min_blocking']
            mu = 0.35
            maxloop = 50

            while True:
                maxloop -= 1
                self.transmit_sig_gen_to_radio(rf_power=self.interfere_power + path_loss2, sig_gen_no=2)
                time.sleep(0.2)  # delay  for power to stabilize
                if soundcard_req:
                    sinad = self.measure_sinad_sc(num=10)
                else:
                    sinad = self.get_sinad(avg=5)
                sinad_error = min_sinad - sinad
                step = mu * sinad_error * interferer_pwr_step
                print(f"loop: {maxloop}, sinad: {sinad}, rx_set_power: {self.rx_set_power}, interference_power: {self.interfere_power}")
                if (sinad >= min_sinad+sinad_tol) and self.interfere_power < max_interferer_pwr:
                    self.interfere_power -= step
                elif sinad < min_sinad and self.interfere_power > min_interferer_pwr:
                    self.interfere_power -= step
                else:
                    break
                # to prevent infinite loop
                if maxloop < 0: #and sinad_maxloop_break > sinad >= min_sinad+sinad_tol:
                    break


            blocking = self.interfere_power - self.rx_set_power
            if blocking > min_blocking:
                test_passed.append(True)
            else:
                test_passed.append(False)

            self.transmit_sig_gen_to_radio(rf_on=False, fm_dev_on=False, sig_gen_no=2)
            print(f'RX_Frequency: {freq/1e6:.3f} MHz, Inter Freq: {interference_freq/1e6:.3f}MHz, Channel_Blocking: '
                  f'{blocking:.2f} dB, SINAD: {sinad:.2f} dB, RX_Power[dBuv]: {self.rx_set_power}, '
                  f'INTERFERE_Power[dBuv]: {self.interfere_power:.2f} Passed: {test_passed[idx]}')

            date_time = datetime.now().strftime("%d/%m/%Y, %H:%M:%S")
            self.test_results.log_dict["RX_Frequency[Hz]"].append(freq)
            self.test_results.log_dict["INTERFERE_Frequency[Hz]"].append(interference_freq)
            self.test_results.log_dict["RX_Power[dBuv]"].append(self.rx_set_power)
            self.test_results.log_dict["INTERFERE_Power[dBuv]"].append(self.interfere_power)
            self.test_results.log_dict["SINAD[dB]"].append(sinad)
            self.test_results.log_dict["Channel_Blocking[dB]"].append(blocking)
            self.test_results.log_dict["Min_Channel_Blocking[dB]"].append(min_blocking)
            self.test_results.log_dict["Radio_Voltage[V]"].append(voltage)
            self.test_results.log_dict["Temperature[C]"].append(temp)
            self.test_results.log_dict["Timestamp"].append(date_time)
            self.test_results.log_dict["Test_Passed"].append(test_passed[idx])
            self.test_results.log_dict["Firmware"].append(self.radio_ctrl.read_fw_version())

        if False in test_passed:
            return False
        else:
            return True

    ### IS THIS SPURIOUS RADIATION?
    def  rx_spurious_emission(self, test_config_opt):
        test_id = 'rx_spurious_emission'
        print(test_id)
        print('\n\n')

        self.test_results.create_test_results_path(standards_id=self.standard_id, test_id=test_id)

        self.radio_power_on()
        #self.USB_on()
        self.check_radio_serial_comms()
        self.radio_tx_off()

        test_config = self.get_test_config(test_config_opt=test_config_opt, test_id=test_id)
        self.test_results.test_param_log(test_config, test_config_opt)

        # self.setup_spec_an(config=test_config['spec_an'])

        screenshot = test_config['spec_an']['screenshot']
        looping_arrays = self.get_looping_arrays(test_config=test_config)

        self.test_results.log_dict = {"Frequency[MHz]": [],
                                      "Sub_Range[]": [],
                                      "Marker1_Freq[MHz]": [],
                                      "Marker1_Level[dBm]": [],
                                      "Marker2_Freq[MHz]": [],
                                      "Marker2_Level[dBm]": [],
                                      "Radio_Voltage[V]": [],
                                      "Radio_Power_Mode": [],
                                      "Temperature[C]": [],
                                      "Timestamp": [],
                                      "Test_Passed": [],
                                      "Limit[dBm]": [],
                                      "Firmware": [],
                                      #"Serial_No": [],
                                      }

        test_result = self.tx_test_executor(looping_arrays=looping_arrays, test_function=self._rx_spurious_emission,
                                            screenshot=screenshot, test_config=test_config)
        self.test_results.save_log()

        return test_result

    def _rx_spurious_emission(self, freq, voltage, temp, radio_power, screenshot, test_config):

        self.test_equip.psu.voltage = voltage

        if temp != 'NOT_USED':
            gui.print_yellow('[Notionally] Setting Temp to ' + str(temp))

        test_passed = []
        self.test_equip.psu.voltage = voltage

        if temp != 'NOT_USED':
            gui.print_yellow('[Notionally] Setting Temp to ' + str(temp))

        audio_vol = test_config['radio_volume']
        self.radio_receive(freq=freq, audio_vol=audio_vol, sql_toggle=1)
        print("audio volume : ", audio_vol)

        radio_serial_no = self.radio_ctrl.get_radio_serial_number()
        print("Radio Serial No: ", radio_serial_no)

        # self.transmit_radio_to_spec_an(freq=freq, power=radio_power, mod_source=0)
        # self.test_equip.spec_an.reset(val=True)
        for idx, sweeps in enumerate(test_config['spec_an']['subrange_sweeps'], start=1):

            #self.test_equip.rf_switch.tx_radio_to_spec_an(
            #    filter=test_config['spec_an']['subrange_sweeps'][sweeps]['filter'])
            time.sleep(1)  # wait for switch action
            self.setup_spec_an(config=test_config['spec_an']['subrange_sweeps'][sweeps])
            self.test_equip.spec_an.all_commands_set()
            # self.test_equip.spec_an.get_single_sweep()
            time.sleep(5)
            self.test_equip.spec_an.trace_peak = 'VIEW'
            self.test_equip.spec_an.marker_1 = 'MAX'
            self.test_equip.spec_an.marker_2 = 'MAX'
            self.test_equip.spec_an.marker_2 = 'MAX:NEXT'
            freq1, power1 = self.test_equip.spec_an.marker_1
            freq2, power2 = self.test_equip.spec_an.marker_2
            limit = test_config['spec_an']['subrange_sweeps'][sweeps]['limit']

            if power1<limit and power2<limit:
                test_passed.append(True)
            else:
                test_passed.append(False)

            date_time = datetime.now().strftime("%Y_%m_%d_%H%M_%S")
            #self.test_results.log_dict["Serial_No"].append(radio_serial_no)
            self.test_results.log_dict["Frequency[MHz]"].append(freq / 1e6)
            self.test_results.log_dict["Sub_Range[]"].append(idx)
            self.test_results.log_dict["Marker1_Freq[MHz]"].append(freq1 / 1e6)
            self.test_results.log_dict["Marker1_Level[dBm]"].append(power1)
            self.test_results.log_dict["Marker2_Freq[MHz]"].append(freq2 / 1e6)
            self.test_results.log_dict["Marker2_Level[dBm]"].append(power2)
            self.test_results.log_dict["Radio_Voltage[V]"].append(voltage)
            self.test_results.log_dict["Radio_Power_Mode"].append(radio_power)
            self.test_results.log_dict["Timestamp"].append(date_time)
            self.test_results.log_dict["Temperature[C]"].append(temp)
            self.test_results.log_dict["Test_Passed"].append(test_passed[idx - 1])
            self.test_results.log_dict["Limit[dBm]"].append(limit)
            self.test_results.log_dict["Firmware"].append(self.radio_ctrl.read_fw_version())

            self.test_equip.spec_an.screenshot(filename=date_time)

        self.radio_tx_off()

        if False in test_passed:
            print("Test Failed")
            return False
        else:
            print("Test Passed")
            return True

    ### NOT PART OF ETSI EN 300 086
    def rx_birdie_scan(self, test_config_opt):
        test_id = 'rx_birdie_scan'  # specify test id
        print("Test : ", test_id)
        print('\n\n')

        time_now_start = datetime.now().strftime("%d-%m-%Y %H:%M:%S")

        #self.test_equip.rf_switch.rx_sig_gen_to_radio()  # specify rf switch to rx

        self.test_results.create_test_results_path(standards_id=self.standard_id, test_id=test_id)
        test_config = self.get_test_config(test_config_opt=test_config_opt, test_id=test_id)
        self.test_results.test_param_log(test_config, test_config_opt)

        # only 1 siggen is required and keep siggen off to act as 50ohm termination
        self.transmit_sig_gen_to_radio(rf_power_units=test_config['sig_gen_1']['power']['units'],
                                       lfo_freq=test_config['sig_gen_1']['lfo_frequency'],
                                       fm_dev=test_config['sig_gen_1']['fm_dev'],
                                       lfo_on=False, rf_on=False, fm_dev_on=False, sig_gen_no=1)


        # this is to extract parameter looping information from test_config
        looping_arrays = self.get_looping_arrays(test_config=test_config)
        self.first_test_loop = True

        self.test_results.log_dict = {"Frequency[Hz]": [],
                                      "Timestamp": [],
                                      "Test_Passed": [],
                                      "RSSI": [],
                                      "Firmware": [],
                                      }  # result dictionary
        #  this is the wrapper function
        test_result = self.rx_test_executor(looping_arrays=looping_arrays,
                                            test_function=self._rx_birdie_scan, test_config=test_config)

        self.test_results.save_log()
        self.test_equip.signal_gen_1.rf_power_on = False

        time_now_end = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        print("\nTest end date & time: %s " % time_now_start)
        print("Test end date & time: %s " % time_now_end)

        return test_result
    
    def _rx_birdie_scan(self, freq, voltage, temp, rx_radio_power, test_config):
        # this test is to be conducted in sig gen1 directly to radio config

        test_passed = []  # initialize test_passed list
        # turn on power supply to the radio
        #self.test_equip.psu.voltage = voltage  # set power supply
        # turn off all filters to make sure audio bandwith is at least 20KHz
        #self.test_equip.cms.turn_off_ccitt()
        #self.test_equip.cms.turn_off_hpf()
        #self.test_equip.cms.turn_off_lpf()

        sig_gen_on = test_config['sig_gen_1']['turn_on']
        lfo_frequencies = test_config['sig_gen_1']['lfo_frequency']
        fm_devs = test_config['sig_gen_1']['fm_dev']
        self.rx_set_power = test_config['sig_gen_1']['power']['start'] + test_config['sig_gen_1']['path_loss']
        path_loss1 = test_config['sig_gen_1']['path_loss']

        #number_lfo_frequencies = len(lfo_frequencies)
        number_of_measurements = 20
        rssi_max = test_config['rssi_max']

        if temp != 'NOT_USED':
            gui.print_yellow('[Notionally] Setting Temp to ' + str(temp))

        self.rx_set_power = test_config['sig_gen_1']['power']['start']  # actually this step is not needed
        self.audio_vol = test_config['radio_volume']  # this step is also not needed

        #print('number_lfo_freq: ', number_lfo_frequencies)

        # turn on sig_gen for fixed frequency if tester wish to create tone
        if sig_gen_on:
            print("turn on sig gen", sig_gen_on)
            sig_gen_freq = test_config['sig_gen_1']['freq']
            self.transmit_sig_gen_to_radio(rf_freq=sig_gen_freq, rf_power=self.rx_set_power + path_loss1,
                                           rf_power_offset=0,
                                           rf_on=True, fm_dev_on=True, sig_gen_no=1,
                                           audio_vol=self.audio_vol, sql_toggle=1)
            print("Signal Generator 1 Transmitting...")
        self.radio_receive(freq=freq, sql_toggle=0, audio_vol=self.audio_vol)

        # rssi is not available yet in radios? looking for it
        rssi_acc = 0
        for i in range(number_of_measurements):
            rssi = self.radio_ctrl.read_rssi()
            #print("rssi measurement  ", rssi)
            rssi_acc = rssi_acc + rssi # read rms voltage from CMS54
            #print('rssi accumulative: ', rssi_acc)

        rssi_value = rssi_acc / number_of_measurements

        print('Frequency', freq, 'rssi: ', rssi_value)

        if rssi_value < rssi_max:  # acceptance criteria is <10%
            test_passed = True
        else:
            test_passed = False

        date_time = datetime.now().strftime("%d/%m/%Y, %H:%M:%S")
        self.test_results.log_dict["Frequency[Hz]"].append(freq)
        self.test_results.log_dict["RSSI"].append(rssi_value)
        self.test_results.log_dict["Test_Passed"].append(test_passed)
        self.test_results.log_dict["Timestamp"].append(date_time)
        self.test_results.log_dict["Firmware"].append(self.radio_ctrl.read_fw_version())

        return test_passed

    ### NOT PART OF ETSI EN 300 086
    # It is part of ETSI EN301025 Clause 9.11 as an extended test coverage 
    def rx_hum_noise(self, test_config_opt):
        test_id = 'rx_hum_noise'  # specify test id
        print('\n\n')

        time_now_start = datetime.now().strftime("%d-%m-%Y %H:%M:%S")

        #self.test_equip.rf_switch.rx_sig_gen_to_radio()  # specify rf switch to rx

        self.test_results.create_test_results_path(standards_id=self.standard_id, test_id=test_id)
        test_config = self.get_test_config(test_config_opt=test_config_opt, test_id=test_id)
        self.test_results.test_param_log(test_config, test_config_opt)

        self.transmit_sig_gen_to_radio(rf_power_units=test_config['sig_gen_1']['power']['units'],
                                       lfo_freq=test_config['sig_gen_1']['lfo_frequency'],
                                       fm_dev=test_config['sig_gen_1']['fm_dev'],
                                       lfo_on=False, rf_on=False, fm_dev_on=False, sig_gen_no=1)  # only 1 siggen is required

        self.test_equip.signal_gen_1.fm_dev_on = True

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
                                      "Firmware": [],
                                      }  # result dictionary
        #  this is the wrapper function
        test_result = self.rx_test_executor(looping_arrays=looping_arrays, test_function=self._rx_hum_noise, test_config=test_config)

        self.test_results.save_log()
        self.test_equip.signal_gen_1.rf_power_on = False

        time_now_end = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        print("\nTest end date & time: %s " % time_now_start)
        print("Test end date & time: %s " % time_now_end)

        return test_result
    ### NOT PART OF ETSI EN 300 086
    # It is part of ETSI EN301025 Clause 9.11 as an extended test coverage 
    def _rx_hum_noise(self, freq, voltage, temp, rx_radio_power, test_config):
        # this test cannot use sound card because a very loud volume is required and soundcard is not able to support

        number_of_measurements = 20
        pass_level = test_config['acceptance_criteria']['level']
        test_passed = []
        # turn on power supply to the radio
        #self.test_equip.psu.voltage = voltage  # set power supply
        # turn off all filters to make sure audio bandwith is at least 20KHz
        self.test_equip.cms.turn_off_ccitt()
        self.test_equip.cms.turn_off_hpf()
        self.test_equip.cms.turn_off_lpf()

        path_loss = test_config['sig_gen_1']['path_loss']

        if temp != 'NOT_USED':
            gui.print_yellow('[Notionally] Setting Temp to ' + str(temp))

        self.rx_set_power = test_config['sig_gen_1']['power']['start']
        self.audio_vol = test_config['radio_volume']
        # turn on signal generator and radio audio volume
        self.transmit_sig_gen_to_radio(rf_freq=freq, rf_power=self.rx_set_power+path_loss, rf_on=True, fm_dev_on=True,
                                       sql_toggle=1, audio_vol=self.audio_vol, sig_gen_no=1)  # turn on modulation
        current_level = self.test_equip.psu.get_current_level()
        #print('currentlevel = ', current_level)
        time.sleep(5)  # wait for 5 seconds

        rms_mod_on_acc = 0
        sinad_mod_on_acc = 0
        rssi_acc = 0
        for i in range(number_of_measurements):
            self.test_equip.cms.turn_off_ccitt()
            rms_mod_on_acc = rms_mod_on_acc + self.test_equip.cms.get_audio_level()  # read rms voltage from CMS54
            sinad_mod_on_acc = sinad_mod_on_acc + self.test_equip.cms.get_sinad()
            rssi_acc = rssi_acc + self.radio_read_rssi()  #need to check 
            print('rms_mod_on_acc: ', rms_mod_on_acc)

        rms_modulation_on = rms_mod_on_acc/number_of_measurements
        sinad_modulation_on = sinad_mod_on_acc / number_of_measurements
        rssi = rssi_acc / number_of_measurements
        print('rms mod on: ', rms_modulation_on)

        self.transmit_sig_gen_to_radio(rf_freq=freq, rf_power=self.rx_set_power+path_loss, rf_on=True, fm_dev_on=False,
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
        self.test_results.log_dict["Firmware"].append(self.radio_ctrl.read_fw_version())

        return test_passed

    ### NOT PART OF ETSI EN 300 086
    def rx_sensitivity(self, test_config_opt):

        test_id = 'rx_sensitivity'
        print("\n\n")
        gui.print_green(test_id)

        time_now_start = datetime.now().strftime("%d-%m-%Y %H:%M:%S")

        #self.test_equip.rf_switch.rx_sig_gen_to_radio() # RF Switch is not required

        self.test_results.create_test_results_path(standards_id=self.standard_id, test_id=test_id)
        test_config = self.get_test_config(test_config_opt=test_config_opt, test_id=test_id)
        self.test_results.test_param_log(test_config, test_config_opt)

        self.transmit_sig_gen_to_radio(rf_power_units=test_config['sig_gen_1']['power']['units'],
                                       lfo_freq=test_config['sig_gen_1']['lfo_frequency'],
                                       fm_dev=test_config['sig_gen_1']['fm_dev'],
                                       lfo_on=False, rf_on=False, fm_dev_on=False, sig_gen_no=1)

        self.transmit_sig_gen_to_radio(lfo_on=False, rf_on=False, fm_dev_on=False, sig_gen_no=2)

        looping_arrays = self.get_looping_arrays(test_config=test_config)
        self.first_test_loop = True

        self.test_results.log_dict = {"Frequency[Hz]" : [],
                                      "SINAD[dB]" : [],
                                      "Rx Power[dBm]" : [],
                                      "Voltage[V]" : [],
                                      "Temperature[C]": [],
                                      "Timestamp": [],
                                      "Test_Passed" : [],
                                      "Firmware": [],
                                      "Serial No":[],
                                      "Current (A)": [],
                                      "Audio Level (Vrms)": [],
                                      }
        test_result = self.rx_test_executor(looping_arrays=looping_arrays,
                                            test_function=self._rx_maximum_usable_sensitivity,
                                            test_config=test_config)
        self.test_results.save_log()
        self.test_equip.signal_gen_1.rf_power_on = False

        time_now_end = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        print("\nTest end date & time: %s " % time_now_start)
        print("Test end date & time: %s " % time_now_end)

        return test_result
    ### NOT PART OF ETSI EN 300 086
    def _rx_sensitivity(self, freq, voltage, temp, rx_radio_power, test_config):

        print('Receiver Sensitivity Test')
        #self.test_equip.psu.voltage = voltage
        print("Frequency: ", freq)

        path_loss1 = test_config['sig_gen_1']['path_loss']  # path loss for sig gen 1
        #max_power1 = test_config['sig_gen_1']['power']['max'] + path_loss1
        max_power1 = test_config['sig_gen_1']['power']['max'] #+ path_loss1
        audio_vol = test_config['radio_volume']
        self.radio_receive(freq=freq, audio_vol=audio_vol)
        #print("audio volume : ", audio_vol)
        #radio_current = self.test_equip.psu.get_current_level()
        #print("First Test Loop: ", self.first_test_loop)

        if temp != 'NOT_USED':
            gui.print_yellow('[Notionally] Setting Temp to ' + str(temp))

        if self.first_test_loop:
            self.rx_set_power = test_config['sig_gen_1']['power']['start']
            self.rx_set_offset = -test_config['sig_gen_1']['power']['offset']
            self.transmit_sig_gen_to_radio(rf_freq=freq, rf_power=self.rx_set_power+path_loss1,
                                           rf_power_offset=self.rx_set_offset,
                                           rf_on=True, fm_dev_on=True, sig_gen_no=1,
                                           audio_vol=audio_vol, sql_toggle=1)
            self.first_test_loop = False
            print('Sig Gen 1 should now be transmitting...')
            time.sleep(3)

        else:
            self.transmit_sig_gen_to_radio(rf_freq=freq, audio_vol=audio_vol, sig_gen_no=1, sql_toggle=1)

        sinad, self.rx_set_power, audio_level = self.find_sinad_power(target_sinad=test_config['sinad_target'],
                                                         set_power=self.rx_set_power,
                                                         max_power=max_power1,
                                                         min_power=test_config['sig_gen_1']['power']['min'],
                                                         power_step=test_config['sig_gen_1']['power']['step'],
                                                         rf_freq=freq,
                                                         path_loss=path_loss1,
                                                         sinad_tolerance=test_config['sinad_tolerance'],
                                                         sc=False,
                                                         ccitt=False,)

        if sinad >= test_config['sinad_target'] and (self.rx_set_power - path_loss1) <= test_config['sig_gen_1']['power']['thresh']:
            test_passed = True
        else:
            test_passed = False

        date_time = datetime.now().strftime("%d/%m/%Y, %H:%M:%S")
        print(f'Frequency: {self.test_equip.signal_gen_1.rf_frequency/1e6:.3f} MHz, SINAD: {sinad:.2f} dB, Audio Level: {audio_level:.2f} Vrms, Rx Power: {self.rx_set_power} dbm ')
        self.test_results.log_dict["Frequency[Hz]"].append(freq)
        self.test_results.log_dict["SINAD[dB]"].append(sinad)
        self.test_results.log_dict["Rx Power[dBm]"].append(self.rx_set_power)
        self.test_results.log_dict["Voltage[V]"].append(voltage)
        self.test_results.log_dict["Temperature[C]"].append(temp)
        self.test_results.log_dict["Timestamp"].append(date_time)
        self.test_results.log_dict["Test_Passed"].append(test_passed)
        self.test_results.log_dict["Firmware"].append(self.radio_ctrl.read_fw_version())
        self.test_results.log_dict["Serial No"].append(self.radio_ctrl.get_radio_serial_number())
        self.test_results.log_dict["Current (A)"].append(radio_current)
        self.test_results.log_dict["Audio Level (Vrms)"].append(audio_level)


        return test_passed
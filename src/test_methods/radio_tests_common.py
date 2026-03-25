import time
import traceback
import sys
import numpy as np
import os

from DAMspy_logging import text_formatter as gui
from concurrent.futures import ThreadPoolExecutor

class FailedTest(Exception):
    # Raised when a test fails on a frequency which may be adjusted. The exception may be caught, with a new frequency attempted.
    pass


class BadSelectionError(Exception):
    # Raised when a set of tests is selected which is not applicable (or is yet to be implemented) for the radio model selected
    pass


class NotImplementedError(Exception):
    # Test is using a function from an abstract class that has not been redeclared. [PROGRAMMING ERROR]
    pass

class RF_Switch_Error(Exception):

    def __init__(self, msg):
        gui.print_red(msg)

class RadioTest:

    def __init__(self, equip_config, test_equipment, radio_eeprom, radio_param, radio_ctrl, test_results):
        self.equip_config = equip_config
        self.radio_eeprom = radio_eeprom
        self.test_equip = test_equipment
        self.radio_param = radio_param
        self.radio_ctrl = radio_ctrl
        self.test_results = test_results
        self.tests_to_run = []
        self.test_skipped = False
        self.test_start_time = None
        self.is_radio_tx_on = False
        self.job_id = None


    def setup_spec_an(self, config):
        try:
            if 'reset' in config.keys():
                self.test_equip.spec_an.reset(val=config['reset'])
                print('Resetting Spec An')
                # self.test_equip.spec_an.reset = config['reset']
            else:
                print('RESET NOT in keys')
            self.test_equip.spec_an.all_commands_set()
            if 'display_on' in config.keys():
                self.test_equip.spec_an.disp_on = config['display_on']
            if 'analog_demod_on' in config.keys():
                self.test_equip.spec_an.analog_demod_on = config['analog_demod_on']
            if 'frequency_span' in config.keys():
                # print('DEBUG: frequency_span is in config.keys()')
                # print('DEBUG: ', config['frequency_span'])
                self.test_equip.spec_an.freq_span = config['frequency_span']
            ###########################################
            if 'centre_frequency' in config.keys():
                self.test_equip.spec_an.freq_centre = config['centre_frequency']
            ###########################################
            if 'deviation_per_div_trace_y' in config.keys():
                self.test_equip.spec_an.deviation_per_div_trace_y = config['deviation_per_div_trace_y']
            # if 'disp_trac_mode' in config.keys():
            #     self.test_equip.spec_an.set_disp_trac_mode(mode=config['disp_trac_mode'])
            if 'analog_demod_bw' in config.keys():
                self.test_equip.spec_an.demod_bw = config['analog_demod_bw']
            if 'analog_demod_af_coupling' in config.keys():
                self.test_equip.spec_an.analog_demod_af_coupling = config['analog_demod_af_coupling']
            if 'rf_level_offset' in config.keys():
                self.test_equip.spec_an.ref_level_offset = config['rf_level_offset']
            if 'rf_level' in config.keys():
                self.test_equip.spec_an.rf_level = config['rf_level']
            if 'internal_attenuation' in config.keys():
                self.test_equip.spec_an.attn_internal = config['internal_attenuation']
            if 'analog_demod_meas_time' in config.keys():
                self.test_equip.spec_an.analog_demod_meas_time = config['analog_demod_meas_time']
            if 'continous_sweep' in config.keys():
                self.test_equip.spec_an.continuous_sweep = config['continous_sweep']
            if 'detector' in config.keys():
                self.test_equip.spec_an.detector = config['detector']
            if 'resolution_bw' in config.keys():
                self.test_equip.spec_an.rbw = config['resolution_bw']
            if 'video_bw' in config.keys():
                self.test_equip.spec_an.vbw = config['video_bw']
            if 'trace_peak' in config.keys():
                self.test_equip.spec_an.trace_peak = config['trace_peak']
            if 'sweep_points' in config.keys():
                self.test_equip.spec_an.sweep_points = config['sweep_points']

            if 'sweep_freq_range' in config.keys():
                self.test_equip.spec_an.set_sweep_freq_range(config['sweep_freq_range'])
            # else:
            #     print('NO: if sweep_freq_range in config.keys():')
            if 'acp_on' in config.keys():
                # print('DEBUG: acp_on is in config.keys()')
                # print('DEBUG: ', config['acp_on'])
                self.test_equip.spec_an.acp_on = config['acp_on']

            if 'channel_bandwidth' in config.keys():
                self.test_equip.spec_an.acp_ch_bw = config['channel_bandwidth']

            if 'adjacent_channel_bandwidth' in config.keys():
                self.test_equip.spec_an.acp_ajch_bw = config['adjacent_channel_bandwidth']

            if 'alternate_channel_bandwidth' in config.keys():
                self.test_equip.spec_an.acp_altch_bw = config['alternate_channel_bandwidth']

            if 'adjacent_channel_number' in config.keys():
                self.test_equip.spec_an.acp_ch_num = config['adjacent_channel_number']

            if 'adjacent_channel_space' in config.keys():
                self.test_equip.spec_an.acp_ch_space = config['adjacent_channel_space']

            if 'alternate_channel_space' in config.keys():
                self.test_equip.spec_an.acp_altch_space = config['alternate_channel_space']

            if 'averaging_number' in config.keys():
                self.test_equip.spec_an.acp_averaging_number = config['averaging_number']

            if 'limit_line' in config.keys():
                self.test_equip.spec_an.set_limit_line(name=config['limit_line']['name'], \
                                                            state=config['limit_line']['state'])

            if 'transducer' in config.keys():
                for item in config['transducer']:
                    self.test_equip.spec_an.set_transducer(name=item['name'], state=item['state'])
            # if 'limit_line_name_2' in config.keys():
            #     self.test_equip.spec_an.set_limit_line_name(limit_line_name=config['limit_line_name_2'])
            # if 'limit_line_2_state' in config.keys():
            #     self.test_equip.spec_an.set_limit_line_status(line_status=config['limit_line_2_state'])
            # if 'limit_line_name_3' in config.keys():
            #     self.test_equip.spec_an.set_limit_line_name(limit_line_name=config['limit_line_name_3'])
            # if 'limit_line_3_state' in config.keys():
            #     self.test_equip.spec_an.set_limit_line_status(line_status=config['limit_line_3_state'])


            self.test_equip.spec_an.all_commands_set()

        except EquipmentSettingFailed:
            print('Traceback:', traceback.print_exc())
            gui.print_red('Equipment Setup failed...')
            return False
        return True

    def find_sinad_power(self, rf_freq, target_sinad, set_power, max_power, min_power, power_step, sc=True, sinad_tolerance=0.5, path_loss=10, ccitt=True):

        rx_set_power = set_power
        mu = 1
        while True:
            self.transmit_sig_gen_to_radio(rf_freq=rf_freq, rf_power=rx_set_power + path_loss, rf_on=True, sig_gen_no=1)
            if sc:
                sinad = self.measure_sinad_sc(num_samps=4 * 4096, ccitt=True, num=10)
                audio_level = 0 # not applicable
            else:
                sinad = self.get_sinad(avg=5, ccitt=ccitt)
                audio_level = self.test_equip.cms.get_audio_level() 
            sinad_error = sinad - target_sinad
            step = mu * sinad_error * power_step
            if sinad >= (target_sinad + sinad_tolerance) and rx_set_power < max_power:
                # case for sinad too high
                rx_set_power -= step
                print(f"sinad: {sinad}, rx_set_power: {rx_set_power}, audio_level: {audio_level}")
            elif sinad < target_sinad and rx_set_power > min_power:
                # case for sinad below acceptance level
                rx_set_power -= step
                print(f"sinad: {sinad}, rx_set_power: {rx_set_power}, audio_level: {audio_level}")
            elif target_sinad < sinad < (target_sinad + sinad_tolerance):
                # case for sinad within range
                break
        return sinad, rx_set_power, audio_level

    def get_stable_sinad(self, threshold, order_descending, max_fluctuation=7, num_measurements=5):

         sinad = self.test_equip.soundcard.measure(num_samps=4*4096, ccitt=True)

         if order_descending:
             if sinad > threshold:
                 #print('No need to average...')
                 return sinad
        #
         sinad_fluctuation = max_fluctuation
         while sinad_fluctuation >= max_fluctuation:
             avg_sinad = np.empty(num_measurements)
             for i in range(len(avg_sinad)):
                 avg_sinad[i] = self.test_equip.soundcard.measure(num_samps=4*4096, ccitt=True)
             sinad_fluctuation = np.max(avg_sinad) - np.min(avg_sinad)
             sinad = ((np.sum(avg_sinad) - np.min(avg_sinad) - np.max(avg_sinad)) / (len(avg_sinad) - 2))
    #
             #print(f'AVG SINAD: {sinad:.2f}, Fluctuation: {sinad_fluctuation:.2f}')
         sinad = ((np.sum(avg_sinad) - np.min(avg_sinad) - np.max(avg_sinad)) / (len(avg_sinad) - 2))
         #print(sinad)
         return sinad

    def get_sinad(self, num_samps=4096*4, ccitt=True, avg=20):
        return self.test_equip.cms.get_sinad(ccitt=ccitt, avg=avg)

    def get_audio_level(self, num_samps=4096*4, ccitt=True, avg=20):
        return self.test_equip.cms.get_audio_level(avg=avg)

    def measure_sinad_sc(self, num_samps=4096*4, ccitt=True, num=10):
        sinad = 0
        for count in range(num):
            sinad += self.test_equip.soundcard.measure(ccitt=ccitt,num_samps=num_samps)
        return sinad/num

    def get_looping_arrays(self, test_config):

        if 'temperature' in test_config.keys():
            temperature_array = self.array_maker(test_config['temperature'])
        else:
            temperature_array = ['NOT_USED']

        if 'frequency' in test_config.keys():
            frequency_array = self.array_maker(test_config['frequency'])
        else:
            frequency_array = ['NOT_USED']

        if 'radio_voltage' in test_config.keys():
            voltage_array = self.array_maker(test_config['radio_voltage'])
        else:
            voltage_array = ['NOT_USED']

        if 'radio_power' in test_config.keys():
            radio_power_array = self.array_maker(test_config['radio_power'])
        else:
            radio_power_array = ["NOT_USED"]

        if 'sig_gen_1' in test_config.keys():
            if 'power' in test_config['sig_gen_1']:
                rx_power_array_dbm = self.array_maker(test_config['sig_gen_1']['power'])
            else:
                rx_power_array_dbm = ["NOT_USED"]
        else:
            rx_power_array_dbm = ["NOT_USED"]

        looping_arrays = {
            "temperature"   : temperature_array,
            "frequency"     : frequency_array,
            "radio_voltage" : voltage_array,
            "radio_power"   : radio_power_array,
            "rx_power_dbm"  : rx_power_array_dbm,
        }

        return looping_arrays

    def tx_test_executor(self, looping_arrays, test_function, screenshot, test_config=None):

        temperature_array = looping_arrays["temperature"]
        frequency_array = looping_arrays["frequency"]
        voltage_array = looping_arrays["radio_voltage"]  # this is the part where the supply voltage configuration is overwritten!!!
        radio_power_array = looping_arrays["radio_power"]

        for volt in voltage_array:
            error = abs(volt - float(self.radio_param.power_supply_voltage))
            if error > 1:
                print('voltage error')
                return -1

        # print('frequency_array: ', frequency_array)
        result = None
        for temp in temperature_array:
            for volt in voltage_array:
                for radio_power in radio_power_array:
                    for freq in frequency_array:
                        result = test_function(freq=freq, voltage=volt, temp=temp, radio_power=radio_power, screenshot=screenshot, test_config=test_config)
                        #if not result:
                            #break

        return result

    def rx_test_executor(self, looping_arrays, test_function, test_config):

        temperature_array = looping_arrays["temperature"]
        frequency_array = looping_arrays["frequency"]
        voltage_array = looping_arrays["radio_voltage"]
        rx_power_array_dbm = looping_arrays["rx_power_dbm"]

        for volt in voltage_array:
            error = abs(volt - self.radio_param.power_supply_voltage)
            if error > 2:
                print('voltage error')
                return -1

        result = None
        test_failed = False
        for temp in temperature_array:
            for volt in voltage_array:
                for rx_radio_power in rx_power_array_dbm:
                    for freq in frequency_array:
                        result = test_function(freq=freq, voltage=volt, temp=temp, rx_radio_power=rx_radio_power, test_config=test_config)
                        if not result:
                            test_failed = True
                            #break
        if test_failed:
            return False
        else:
            return True

    def radio_power_on(self):
        """
        Ensure the radio is powered on via the PSU if configured.
        """
        import time

        # Check if PSU is configured
        psu = getattr(self.test_equip, "psu", None)
        if psu is None:
            # Log to the test_results logger instead of self.log
            #self.test_results.log_warning("No PSU configured; skipping radio_power_on()")
            print("No PSU configured; skipping radio_power_on()")
            return

        # If PSU is off, turn it on
        if not psu.on:
            self.test_results.log_info("Powering on via PSU")
            psu.on = True
            time.sleep(self.radio_param.power_on_delay_s)
        else:
            self.test_results.log_info("PSU already on")

    def radio_power_off(self):
        """
        Ensure the radio is powered off via the PSU if configured.
        """
        # Check if PSU is configured
        psu = getattr(self.test_equip, "psu", None)
        if psu is None:
            # Log and skip if there's no PSU
            self.test_results.add_line("No PSU configured; skipping radio_power_off()", colour='y')
            return

        # If PSU is on, turn it off
        if getattr(psu, "on", False):
            self.test_results.add_line("Powering off via PSU")
            psu.on = False
            # give it a moment to settle
            import time
            time.sleep(self.radio_param.power_off_delay_s)
        else:
            self.test_results.add_line("PSU already off")

    def check_radio_serial_comms(self):
        print('Checking Radio Serial Comms')
        time.sleep(2.0)  # add delay to wait for radio to power on
        comms_ok = self.radio_ctrl.check_connection()

        if self.assert_true('radio_serial_comms_ok', comms_ok):
            gui.print_yellow('Radio Connection Success')
            gui.print_blue("===================================================================================================================")
            gui.print_blue("===================================================================================================================\n\n")
            return True
        else:
            return False

    def assert_true(self, parameter_name, observed_value):
        passed = (observed_value is not None) and observed_value
        if not passed:
            self.test_results.failure_report_message = 'Fail: %s is False' % parameter_name
            return False
        else:
            return True

    def USB_on(self):
        self.radio_ctrl.USB_on()
        print("USB-C port is enabled\n")

    def USB_off(self):
        self.radio_ctrl.USB_off()
        print("USB-C port is disbaled\n")


    # this function change the radio frequency of radio too
    def transmit_sig_gen_to_radio(self, rf_freq=None, rf_on=None, rf_power=None,
                                  rf_power_units=None, rf_power_offset=None, lfo_freq=None,
                                  lfo_voltage_mv=None, lfo_on=None, fm_dev=None,
                                  fm_dev_on=None, sql_toggle=None, audio_vol=None, sig_gen_no=None):
        # print('Creating transmit_sdr_to_radio Thread')
        start = time.perf_counter()
        executor = ThreadPoolExecutor()
        if sig_gen_no is not None:

            try:
                if sig_gen_no == 1:
                    print("transmit sig gen")
                    fut2 = executor.submit(self.test_equip.signal_gen_1.transmit_from_sig_gen, rf_freq=rf_freq, rf_on=rf_on, rf_power=rf_power,
                                           rf_power_units=rf_power_units, rf_power_offset=rf_power_offset, lfo_freq=lfo_freq, lfo_voltage_mv=lfo_voltage_mv, lfo_on=lfo_on, fm_dev=fm_dev, fm_dev_on=fm_dev_on)
                    fut1 = executor.submit(self.radio_receive, freq=rf_freq, sql_toggle=sql_toggle, audio_vol=audio_vol)


                elif sig_gen_no == 2:
                    fut2 = executor.submit(self.test_equip.signal_gen_2.transmit_from_sig_gen, rf_freq=rf_freq, rf_on=rf_on, rf_power=rf_power,
                                           rf_power_units=rf_power_units, rf_power_offset=rf_power_offset, lfo_freq=lfo_freq, lfo_voltage_mv=lfo_voltage_mv, lfo_on=lfo_on, fm_dev=fm_dev, fm_dev_on=fm_dev_on)

                elif sig_gen_no == 3:
                    fut3 = executor.submit(self.test_equip.signal_gen_3.transmit_from_sig_gen, rf_freq=rf_freq, rf_on=rf_on, rf_power=rf_power,
                                           rf_power_units=rf_power_units, rf_power_offset=rf_power_offset, lfo_freq=lfo_freq, lfo_voltage_mv=lfo_voltage_mv, lfo_on=lfo_on, fm_dev=fm_dev, fm_dev_on=fm_dev_on)

            except AttributeError as e:
                gui.print_red('Exception: ' + str(e))
                gui.print_red('Check Setup - Current Setup does not support Selected Test')
                self.test_equip.deinit_equip()
                sys.exit(1)

            # else:
            #     gui.print_red('NO SIGNAL GENERATOR SELECTED')
        else:
            fut1 = executor.submit(self.radio_receive, freq=rf_freq, sql_toggle=sql_toggle, audio_vol=audio_vol)

        # else:
        #     print("INVALID transmit_sig_gen_to_radio")

        executor.shutdown(wait=True)

        finish = time.perf_counter()

        return True

    # def sig_gen_transmit(self, rf_freq=None, rf_on=None, rf_power=None, rf_power_units=None, lfo_freq=None,
    #                           lfo_voltage_mv=None, lfo_on=None, fm_dev=None, fm_dev_on=None, sig_gen_no=None):
    #

    def transmit_radio_to_spec_an(self, freq, power, mod_tone=0, mod_source=0):
        # print('Creating transmit_radio_to_sdr Thread')
        start = time.perf_counter()
        executor = ThreadPoolExecutor()
        fut1 = executor.submit(self.radio_transmit, freq=freq, power_level=power, mod_source=mod_source, mod_tone=mod_tone)
        fut2 = executor.submit(self.test_equip.spec_an.spec_an_receive, rf_freq=freq)
        executor.shutdown(wait=True)

        if (fut1.result()) == True: # Only print potentially suppressed output if there's an issue
            pass
        else:
            print(fut1.result())
        if (fut2.result()) == True:
            pass
        else:
            print(fut2.result())

        finish = time.perf_counter()
        # print('Finished radio_to_sdr in %.2f seconds ', (finish - start))

        # print('Destroying Thread')
        return True


    def radio_transmit(self, freq, power_level, mod_source=0, mod_tone=0):

        self.radio_ctrl.set_frequency(freq)
        # pa_selection = self.radio_param.tx_on_pa_level[
        #     power_level]  # Determines the PA setting to use based on TX Power
        self.radio_tx_on(tx_power=power_level, mod_source=mod_source, mod_tone=mod_tone)
        self.is_radio_tx_on = True
        # self.radio_ctrl.radio_tx_on(tx_power=power_level, mod_source=mod_source, mod_tone=mod_tone)
        time.sleep(self.radio_param.time_delays['Tx_On_Stable'])
        time.sleep(self.radio_param.time_delays['Freq_Change'])

        return True

    def radio_receive(self, freq=None, sql_toggle=None, audio_vol=None):

        self.radio_tx_off()

        time_delay = 0

        #print("radio_receive frequency input : ", freq)

        #print(self.radio_ctrl.get_frequency())

        if freq:
            self.radio_ctrl.set_frequency(freq)
            #print("frequency: ", self.radio_ctrl.get_frequency())
            freq_delta = abs(self.radio_ctrl.frequency*1e6 - freq)

            if freq_delta == 0:
                time_delay = 0
            else:
                time_delay = self.radio_param.time_delays['Freq_Change']

            #print('freq_delta : ', freq_delta)
            #print('frequency : ', self.radio_ctrl.frequency)

        if sql_toggle:
            self.radio_ctrl.set_squelch_toggle(sql_toggle)
        if audio_vol:
            self.radio_ctrl.set_audio_volume(audio_vol)

        time.sleep(time_delay)
        return True

    def radio_read_rssi(self):
        resp = self.radio_ctrl.read_rssi()
        return resp
        #return resp[1]

    def radio_tx_off(self):
        if self.is_radio_tx_on:
            self.radio_ctrl.tx_off()
            self.is_radio_tx_on = False
            time.sleep(self.radio_param.time_delays['Tx_Off_Stable'])  # wait radio tx turning off
        # self.test_equip.psu.current_limit = self.radio_param.tx_off_current["Max"]

    def radio_tx_on(self, tx_power, mod_source, mod_tone):
        pa_selection = self.radio_param.tx_on_pa_level[tx_power]  # Determines the PA setting to use based on TX Power
        self.radio_ctrl.tx_on(pa_selection=pa_selection, modulation_selection=mod_source, modulation_tone=mod_tone)
        self.is_radio_tx_on = True
        return True

    def array_maker(self, input_dict):

        if 'looping_type' in input_dict.keys():
            if input_dict['looping_type'] == 'auto':
                pass
            elif input_dict['looping_type'] == 'custom':
                ret_array = ['NOT_USED']
                return ret_array

        # if 'required' not in input_dict.keys():
        #     ret_array = ['NOT_USED']

        if not input_dict['required']:
            # print('This array is not to be used')
            ret_array = ['NOT_USED']

        elif not (input_dict['custom_array']):
            # print('There is no custom array!')
            temp_array = np.arange(float(input_dict['start']), float(input_dict['stop']), float(input_dict['step']))
            try:
                ret_array = [float(x) for x in temp_array]
            except ValueError:
                ret_array = np.arange(float(input_dict['start']), float(input_dict['stop']), float(input_dict['step']))

        elif 'DEFAULT' in input_dict['custom_array']:
            default_value = self.radio_param.power_supply_voltage
            temp_array = [default_value]
            try:
                ret_array = [float(x) for x in temp_array]
            except ValueError:
                ret_array = [default_value]
        else:
            # print('There is a custom array')
            temp_array = input_dict['custom_array']
            try:
                ret_array = [float(x) for x in temp_array]
            except ValueError:
                ret_array =  input_dict['custom_array']

        return ret_array

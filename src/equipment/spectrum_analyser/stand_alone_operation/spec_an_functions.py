import sys
sys.path.append('.')
sys.path.append('./ETS_logging')

import pyvisa as visa
import time
import re
from ETS_logging import text_formatter as gui
import unittest

# =============================================================================
# Author            : Athanatu Aziz Mahruz
# Department        : Verification and Validation
# Company           : GME Pty Ltd
# Date              : 13/April/2024
# Python version    : 3.11.0
# Purpose           : Spectrum Analyzer scripts
# Drivers Required  : NIL
# Released          : No
# =============================================================================

# =============================================================================
# TO DO             :   1] Nil
# =============================================================================



class EquipmentSettingFailed(Exception):
    pass


class SpecAn_FSV:

    def __init__(self, test_results, spec_an_config=None):
        self.spec_an_config_failed = False
        self.test_results = test_results
        if spec_an_config:
            ip_address = spec_an_config['IP']
        else:
            # Option to manually enter IP Address if running in manual mode (i.e. standalone)
            ip_address = '10.0.22.130'
        address = 'TCPIP0::' + ip_address + '::inst0::INSTR'

        self.init_spec_an(address)
        self._disp_on = None
        self._freq_centre = None
        self._freq_span = None
        self._rbw = None
        self._vbw = None
        self._attn_internal = None
        self._ref_level_offset = None
        self._trace_peak = None
        self._sweep_points = None
        self._rf_level = None
        self._ref_level_offset = None
        self._analog_demod_on = None
        self._analog_demod_af_coupling = None
        self._analog_demod_meas_time = None
        self._deviation_per_div_trace_y = None
        self._demod_bw = None
        self._acp_on = None
        self._acp_ch_bw = None
        self._acp_ajch_bw = None
        self._acp_altch_bw = None
        self._acp_ch_num = None
        self._acp_ch_space = None
        self._acp_altch_space = None
        self._acp_power_mode = None
        self._acp_average_number = None
        self._detector = None

    def init_spec_an(self, address):
        attempts = 0
        while attempts < 3:
            try:
                self.inst = None
                self.rm = visa.ResourceManager()
                self.inst = self.rm.open_resource(address)
                self.spec_an_config_failed = False
                break
            except visa.errors.VisaIOError as e:
                print('Exception :', e)
                self.spec_an_config_failed = True
                attempts += 1
                continue

    def spec_an_receive(self, rf_freq=None, attenuation=None, display_on=None, rbw=None, vbw=None):

        if rf_freq:
            self.freq_centre = rf_freq
        if attenuation:
            self.attn_internal = attenuation
        if display_on:
            self.disp_on = display_on
        if rbw:
            self.rbw = rbw
        if vbw:
            self.vbw = vbw

    def get_serial_number(self):
        self.serial_number = self.inst.query('*IDN?')

    def all_commands_set(self):
        resp = self.inst.query("*OPC?")
        return resp

    def screenshot(self, filename=None):
        gui.print_yellow('Saving Screenshot...')
        self.inst.write('HCOP:DEV:COL ON')
        self.inst.write("HCOP:DEV:LANG PNG") # set file type to .png
        self.inst.write("HCOP:CMAP:DEF4")
        self.inst.write(f"MMEM:NAME \'C:\\temp\\Dev_Screenshot.png\'")
        self.inst.write("HCOP:IMM") # perform copy and save .png file on SpecAn
        self.inst.query("*OPC?")

        save_path = self.test_results.current_test_path + '\\' +  self.test_results.log_id + filename + ".png"
        print(save_path)
        file_data = bytes(self.inst.query_binary_values(f"MMEM:DATA? \'C:\\temp\\Dev_Screenshot.png\'", datatype='s')) # query binary data and save
        new_file = open(save_path, "wb")# open a new file as "binary/write" on PC
        #new_file = open(f"c:\\Temp\\{filename}.png", "wb")# open a new file as "binary/write" on PC
        new_file.write(file_data) # copy data to the file on PC
        new_file.close()
        #gui.print_red("Screenshot path not set. Saving to default location...")
        # gui.print_green(f"Screenshot saved to PC {save_path}\n ")
        return True

    def meas_analog_demod_fm_dev(self):
        self.continuous_sweep = False
        peak_dev_avg = float(self.inst.query("CALC:MARK:FUNC:ADEM:FM? MIDD"))
        peak_dev_plus = float(self.inst.query("CALC:MARK:FUNC:ADEM:FM? PPE"))
        peak_dev_minus = float(self.inst.query("CALC:MARK:FUNC:ADEM:FM? MPE"))
        self.inst.query("*OPC?")
        self.continuous_sweep = True

        return peak_dev_avg, peak_dev_plus, peak_dev_minus

    def reset(self, val):
        if val:
            # print('Resetting...')
            self.inst.write(f"*RST")
            # print('Resetting and sleeping...')
            # time.sleep(2)
        else:
            pass

    # @property
    # def trigger_hold(self):
    #     return self._trigger_hold
    #
    # @trigger_hold.setter
    # def trigger_hold(self, trigger_offset):
    #     self.inst.write(f"TRIG:HOLD {trigger_offset}ms")
    #     self._trigger_hold = trigger_offset
    def set_transducer(self, name, state):
        self.inst.write(f"CORR:TRAN:SEL '{name}'")
        self.inst.write(f"CORR:TRAN {state}")

    def set_limit_line(self, name, state):
        self.inst.write(f"CALC:LIM1:NAME '{name}'")
        self.inst.write(f"CALC:LIM1:UPP:STAT {state}")
        self.inst.write("CALC:LIM1:TRAC 1")


    # def set_limit_line_status(self, line_status):

        # self.inst.write(f"CALC:LIM1:NAME 'ETSI EN 301025_CONSPUR_TX'")

        # self.inst.write("CALC:LIM1:UPP:OFFS 3dB")

        # self.inst.write(f"CALC:LIM1:UPP:STAT ON")
        # time.sleep(0.1)
        # self.inst.write(f"CALC:LIM1:UPP:STAT OFF")
        # time.sleep(0.1)
        # self.inst.write(f"CALC:LIM1:UPP:STAT ON")

    def check_limit_line_pass_or_fail(self):
        status = self.inst.query("CALC:LIM1:FAIL?")
        # print(f"line pass or fail status is: {status}")
        return status

    def set_sweep_freq_range(self, freq_range_hz):
        # print('debug - setting_sweep_freq_range')
        self.inst.write(f"FREQ:STAR {float(freq_range_hz['LOW'])}Hz")
        # print(freq_range_hz)
        self.inst.write(f"FREQ:STOP {float(freq_range_hz['HIGH'])}Hz")


    def get_single_sweep(self):
        self.continuous_sweep = False
        time.sleep(1)
        self.inst.write("INIT:*WAI")

    # def set_disp_trac_mode(self, mode):
    #     self.inst.write(f"DISP:TRAC:MODE {mode}")

    @property
    def continuous_sweep(self):
        return self._continous_sweep

    @continuous_sweep.setter
    def continuous_sweep(self, is_on):
        if is_on:
            self.inst.write(f"INIT:CONT ON")
        else:
            self.inst.write(f"INIT:CONT OFF")

    @property
    def analog_demod_on(self):
        return self._analog_demod_on

    @analog_demod_on.setter
    def analog_demod_on(self, val):
        if val:
            self.inst.write("ADEM ON")
        else:
            self.inst.write("ADEM OFF")
        self._analog_demod_on = val

    @property
    def analog_demod_af_coupling(self):
        return self._analog_demod_af_coupling

    @analog_demod_af_coupling.setter
    def analog_demod_af_coupling(self, val):
        self.inst.write(f"ADEM:AF:COUP {val}")
        self._analog_demod_af_coupling = val

    @property
    def analog_demod_meas_time(self):
        return self._analog_demod_meas_time

    @analog_demod_meas_time.setter
    def analog_demod_meas_time(self, val):
        self.inst.write(f"ADEM:MTIM {val}ms")
        self._analog_demod_meas_time = val

    @property
    def demod_bw(self):
        return self._demod_bw

    @demod_bw.setter
    def demod_bw(self, demod_bw):
        self.inst.write(f"BAND:DEM {demod_bw}Hz")
        self._demod_bw = demod_bw

    @property
    def acp_on(self):
        return self._acp_on

    @acp_on.setter
    def acp_on(self, val):
        if val:
            self.inst.write("CALC:MARK:FUNC:POW:SEL ACP")

        self._acp_on = val

    @property
    def acp_ch_bw(self):
        return self._acp_ch_bw

    @acp_ch_bw.setter
    def acp_ch_bw(self, acp_ch_bw):
        self.inst.write(f"POW:ACH:BWID:CHAN1 {acp_ch_bw}Hz")
        self._acp_ch_bw = acp_ch_bw

    @property
    def acp_ajch_bw(self):
        return self._acp_ajch_bw

    @acp_ajch_bw.setter
    def acp_ajch_bw(self, acp_ajch_bw):
        self.inst.write(f"POW:ACH:BWID:ACH {acp_ajch_bw}Hz")
        self._acp_ajch_bw = acp_ajch_bw

    @property
    def acp_altch_bw(self):
        return self._acp_altch_bw

    @acp_altch_bw.setter
    def acp_altch_bw(self, acp_altch_bw):
        self.inst.write(f"POW:ACH:BWID:ALT1 {acp_altch_bw}Hz")
        self._acp_altch_bw = acp_altch_bw

    @property
    def acp_ch_num(self):
        return self._acp_ch_num

    @acp_ch_num.setter
    def acp_ch_num(self, acp_ch_num):
        self.inst.write(f"POW:ACH:ACP {acp_ch_num}")
        self._acp_ch_num = acp_ch_num

    @property
    def acp_ch_space(self):
        return self._acp_ch_space

    @acp_ch_space.setter
    def acp_ch_space(self, acp_ch_space):
        self.inst.write(f"POW:ACH:SPAC {acp_ch_space}")
        self._acp_ch_space = acp_ch_space

    @property
    def acp_altch_space(self):
        return self._acp_altch_space

    @acp_altch_space.setter
    def acp_altch_space(self, acp_altch_space):
        self.inst.write(f"POW:ACH:SPAC:ALT1 {acp_altch_space}")
        self._acp_altch_space = acp_altch_space

    @property
    def acp_averaging_number(self):
        return self._acp_averaging_number

    @acp_averaging_number.setter
    def acp_averaging_number(self, acp_averaging_number):
        self.inst.write(f"SWE:COUN {acp_averaging_number}")
        self.inst.write(f"CALC:MARK:FUNC:POW:MODE WRIT") # for average to take effect
        self._acp_average_number = acp_averaging_number

    @property
    def deviation_per_div_trace_y(self):
        return self._deviation_per_div_trace_y

    @deviation_per_div_trace_y.setter
    def deviation_per_div_trace_y(self, dev_per_division):
        self.inst.write(f"DISP:TRAC:Y:PDIV {dev_per_division}Hz")
        self._deviation_per_div_trace_y = dev_per_division

    @property
    def disp_on(self):
        self._disp_on = self.inst.query("SYST:DISP:UPD?")
        return self._disp_on

    @disp_on.setter
    def disp_on(self, is_on):
        if is_on:
            self.inst.write("SYST:DISP:UPD ON")
            self._disp_on = True
        elif not is_on:
            print('off')
            self.inst.write("SYST:DISP:UPD OFF")
            self._disp_on = False

    @property
    def freq_centre(self):
#        self.inst.query('INIT: IMM; *WAI')
        self._freq_centre = self.inst.query("FREQ:CENT?")
        return float(self._freq_centre)

    @freq_centre.setter
    def freq_centre(self, freq_hz):
        self.inst.write(f"FREQ:CENT {freq_hz}Hz")
        if not freq_hz == float(self.inst.query("FREQ:CENT?")):
            print(float(self.inst.query("FREQ:CENT?")))
            raise EquipmentSettingFailed
        self._freq_centre = freq_hz

    @property
    def freq_span(self):
        self._freq_span = self.inst.query("FREQ:SPAN?")
        return self._freq_span

    @freq_span.setter
    def freq_span(self, freq_hz):
        self.inst.write(f"FREQ:SPAN {freq_hz}Hz")
        self.all_commands_set()
        if not freq_hz == float(self.inst.query("FREQ:SPAN?")):
            gui.print_red('freq_hz did not set correctly...')
            raise EquipmentSettingFailed
        self._freq_span = freq_hz

    @property
    def rbw(self):
        self._freq_span = self.inst.query("BAND?")
        return self._rbw

    @rbw.setter
    def rbw(self, rbw_hz):
        self.inst.write(f"BAND:RES {rbw_hz}Hz")
        print(f'query result is: {self.inst.query("BAND:RES?")}')

        # if not float(rbw_hz) == float(self.inst.query("BAND:RES?")):
        #     gui.print_red('rbw_hz did not set correctly...')
        #
        #     raise EquipmentSettingFailed
        self._rbw = rbw_hz

    @property
    def vbw(self):
        self._vbw = self.inst.query("BAND:VID?")
        return self._vbw

    @vbw.setter
    def vbw(self, vbw_hz):
        self.inst.write(f"BAND:VID {vbw_hz}Hz")

        # if not vbw_hz == float(self.inst.query("BAND:VID?")):
        #     gui.print_red('vbw_hz did not set correctly...')
        #     raise EquipmentSettingFailed
        self._vbw = vbw_hz

    @property
    def attn_internal(self):
        self._attn_internal = self.inst.query("INP:ATT?")
        return self._attn_internal

    @attn_internal.setter
    def attn_internal(self, attn_dBm):
        self.inst.write(f"INP:ATT {attn_dBm}")

        if not attn_dBm == float(self.inst.query("INP:ATT?")):
            gui.print_red('attn_dBm did not set correctly...')
            raise EquipmentSettingFailed
        self._attn_internal = attn_dBm


    @property
    def trace_peak(self):
        return self._trace_peak

    @trace_peak.setter
    def trace_peak(self, option='MAXH'):# MAXH, VIEW, AVER
        # self.inst.write(f"{trace_peak}")

        self.inst.write("DISP:TRAC:MODE " + option)
        self._trace_peak = option

    @property
    def detector(self):
        return self._detector

    @detector.setter
    def detector(self, option):# POS, RMS, ...
        # self.inst.write(f"{detector}")
        self.inst.write("DET " + option)
        self._detector = option

    @property
    def acp_power_mode(self):
        return self._acp_power_mode

    @acp_power_mode.setter
    def acp_power_mode(self, option='REL'):# REL, ABS
        # self.inst.write(f"{acp_power_mode}")

        self.inst.write("POW:ACH:MODE " + option)
        self._acp_power_mode = option

    @property
    def ref_level_offset(self):
        self._ref_level_offset = self.inst.query("DISP:TRAC:Y:RLEV:OFFS?")
        return self._ref_level_offset

    @ref_level_offset.setter
    def ref_level_offset(self, ref_level_offset_dbm):
        self.inst.write(f"DISP:TRAC:Y:RLEV:OFFS {ref_level_offset_dbm}")
        self.inst.write(f"{ref_level_offset_dbm}") # Apparently necessary to write this?

        if not ref_level_offset_dbm == float(self.inst.query("DISP:TRAC:Y:RLEV:OFFS?")):
            gui.print_red('Ref Level Offset Did not set correctly...')
            raise EquipmentSettingFailed

        self._ref_level_offset = ref_level_offset_dbm

    @property
    def sweep_points(self):
        self._sweep_points = self.inst.query("SWE:POIN?")

        return self._sweep_points

    @sweep_points.setter
    def sweep_points(self, no_sweep_points):
        self.inst.write(f"SWE:POIN {no_sweep_points}")

        if not no_sweep_points == float(self.inst.query("SWE:POIN?")):
            gui.print_red('Ref Level Offset Did not set correctly...')
            raise EquipmentSettingFailed

        self._sweep_points = no_sweep_points

    @property
    def rf_level(self):
        self._rf_level = self.inst.query("DISP:TRAC:Y:RLEV?")
        return self._rf_level

    @rf_level.setter
    def rf_level(self, rf_level_db):
        self.inst.write(f"DISP:TRAC:Y:RLEV {rf_level_db}")

        if not rf_level_db == float(self.inst.query("DISP:TRAC:Y:RLEV?")):
            gui.print_red('Ref Level did not set correctly...')
            raise EquipmentSettingFailed

        self._rf_level = rf_level_db

    @property
    def marker_1(self):

        x = float(self.inst.query("CALC:MARK1:X?"))
        y = float(self.inst.query("CALC:MARK1:Y?"))
        return x, y

    @marker_1.setter
    def marker_1(self, option='MAX'):
        self.inst.write("CALC:MARK1:" + option)

    @property
    def marker_2(self):

        x = float(self.inst.query("CALC:MARK2:X?"))
        y = float(self.inst.query("CALC:MARK2:Y?"))
        return x, y

    @marker_2.setter
    def marker_2(self, option='MAX'):
        self.inst.write("CALC:MARK2:" + option)

    def get_adjacent_channel_power_meas(self):
        self.inst.write(f"DISP:TRAC:MODE VIEW")
        acp = self.inst.query("CALC:MARK:FUNC:POW:RES? ACP")
        acp_list = re.findall(r'-?\d+\.\d+', acp)
        return acp_list

    #
    # def tx_demod_setup(self):
    #
    #     Centre_frequency = 156.8e6  #get all parameters from Test_Setup.xlsx
    #     # Hz per division
    #     Dev_PerDivision = 1e3
    #     # Demodulation bandwidth - 12.5kHz if NB, 25 khz if WB
    #     Demod_BW = 12.5e3
    #
    #     # This should be called AC/DC coupling. Note: Only AC coupling is used for our tests
    #     AF_Couple = 'AC'
    #
    #     # Unsure why the level is set to 40 dBm
    #     RF_level = 40
    #
    #     # Internal attenuation - 20 is the current value - no particular reason
    #     Attenuation = 20
    #
    #     # Does not need to be an exact value as we are only looking at deviation here
    #     RefLev_offset = 33.5
    #
    #     Trace_Peak = 'DET POS'
    #
    #     # Demodulation measurement time (AQT) Aquisition time?
    #     # Set to 10 ms. (Not a default value - Aaron tried a few other values previously)
    #     Demod_MT = 10
    #
    #     # Need to continuously sweep
    #     Cont_sweep = 'ON'
    #
    #
    #     self.inst.write(f"*RST") # write all paramaters to SpecAn
    #     self.inst.write("SYST:DISP:UPD ON")
    #     # Turn Analog Demodulation mode on (Rather than Spectrum Analyse mode)
    #     self.inst.write("ADEM ON")
    #     self.inst.write(f"FREQ:CENT {Centre_frequency}Hz")
    #     self.inst.write(f"DISP:TRAC:Y:PDIV {Dev_PerDivision}Hz")
    #     self.inst.write(f"BAND:DEM {Demod_BW}Hz")
    #     self.inst.write(f"ADEM:AF:COUP {AF_Couple}")
    #     #Set AF coupling to AC, the frequency offset is automatically corrected.
    #     # i.e. the trace is always symmetric with respect to the zero line
    #     self.inst.write(f"DISP:TRAC:Y:RLEV:OFFS {RefLev_offset}")
    #     self.inst.write(f"DISP:TRAC:Y:RLEV {RF_level}")
    #     self.inst.write(f"INP:ATT {Attenuation}")
    #     self.inst.write(f"{Trace_Peak}")
    #     self.inst.write(f"ADEM:MTIM {Demod_MT}ms")
    #     self.inst.write(f"INIT:CONT {Cont_sweep}")
    #     self.all_commands_set()

    #
    # def tx_adjacent_channel_power_setup(self):
    #
    #     Centre_frequency = 156.8e6 # Hz
    #     Span_frequency = 62.4e6 # Hz
    #     RBW = 100 # Hz
    #     VBW = 1e3 # Hz
    #     RF_level = 40
    #     Attenuation = 20
    #     RefLev_offset = 33.7
    #     Trace_RMS = 'DET RMS'
    #     Tx_CHBW = 8.5e3
    #     AJ_CHBW = 8.5e3
    #     AT_CHBW = 8.5e3
    #     AJ_CHNUM = 2
    #     AJ_SPACE = 12.5e3
    #     AT_SPACE = 25e3
    #     Power_Mode = 'REL'
    #     Ave_number = 50
    #
    #     self.inst.write(f"*RST") # write all paramaters to SpecAn
    #     self.inst.write("SYST:DISP:UPD ON")
    #     self.inst.write("CALC:MARK:FUNC:POW:SEL ACP")
    #     self.inst.write(f"FREQ:CENT {Centre_frequency}Hz")
    #     self.inst.write(f"FREQ:SPAN {Span_frequency}Hz")
    #     self.inst.write(f"BAND {RBW}Hz")
    #     self.inst.write(f"BAND:VID {VBW}Hz")
    #     self.inst.write(f"DISP:TRAC:Y:RLEV:OFFS {RefLev_offset}")
    #     self.inst.write(f"DISP:TRAC:Y:RLEV {RF_level}")
    #     self.inst.write(f"INP:ATT {Attenuation}")
    #     self.inst.write(f"{Trace_RMS}")
    #     self.inst.write(f"POW:ACH:BWID:CHAN1 {Tx_CHBW}Hz")
    #     self.inst.write(f"POW:ACH:BWID:ACH {AJ_CHBW}Hz")
    #     self.inst.write(f"POW:ACH:BWID:ALT1 {AT_CHBW}Hz")
    #     self.inst.write(f"POW:ACH:ACP {AJ_CHNUM}")
    #     self.inst.write(f"POW:ACH:SPAC {AJ_SPACE}Hz")
    #     self.inst.write(f"POW:ACH:SPAC:ALT1 {AT_SPACE}Hz")
    #     self.inst.write(f"POW:ACH:MODE {Power_Mode}")
    #     self.inst.write(f"SWE:COUN {Ave_number}")
    #     self.inst.write(f"CALC:MARK:FUNC:POW:MODE WRIT")
    #     self.inst.write(f"DISP:TRAC:MODE MAXH")
    #     self.all_commands_set()


    def tx_audio_frequency_harmonic_distortion_setup(self):
        self.inst.write("CALC:FEED 'XTIM:FM:AFSP'")
        self.inst.write("FILT:HPAS:FREQ 50Hz")
        self.inst.write("FILT:HPAS ON")
        self.inst.write("FILT:DEMP:TCON 50us")
        self.inst.write("FILT:DEMP ON")
        self.inst.write("ADEM:MTIM 30ms")
        self.inst.write("UNIT:THD PCT")
        time.sleep(1)
        self.inst.write(f"DISP:TRAC:MODE VIEW")

    def query_AF_with_ADEM(self):
        # print('debug 1')
        # time.sleep(1)
        AF = float(self.inst.query("CALC:MARK:FUNC:ADEM:AFR?"))
        # time.sleep(1)
        # print('AF:', AF)
        # print('debug 2')

        return AF

    def query_THD_measurement(self):
        # print('debug 3')
        # time.sleep(1)
        THD = float(self.inst.query("CALC:MARK:FUNC:ADEM:THD:RES?"))
        # print('THD:', THD)

        # time.sleep(1)
        # print('debug 4')
        return THD # this vaule is %

    def close(self):
        self.inst.close()


class SpecAn_KeySightN9020B:

    def __init__(self, test_results=None, spec_an_config=None):
        self.spec_an_config_failed = False
        self.test_results = test_results
        if spec_an_config:
            ip_address = spec_an_config['IP']
        else:
            # Option to manually enter IP Address if running in manual mode (i.e. standalone)
            ip_address = '10.0.27.105'
        address = 'TCPIP0::' + ip_address + '::inst0::INSTR'  # form IP address

        self.init_spec_an(address)  # initialize signal analyzer with IP address
        self._disp_on = None
        self._freq_centre = None
        self._freq_span = None
        self._rbw = None
        self._vbw = None
        self._attn_internal = None
        self._ref_level_offset = None
        self._trace_peak = None
        self._sweep_points = None
        self._rf_level = None
        self._ref_level_offset = None
        self._analog_demod_on = None
        self._analog_demod_af_coupling = None
        self._analog_demod_meas_time = None
        self._deviation_per_div_trace_y = None
        self._demod_bw = None
        self._acp_on = None
        self._acp_ch_bw = None
        self._acp_ajch_bw = None
        self._acp_altch_bw = None
        self._acp_ch_num = None
        self._acp_ch_space = None
        self._acp_altch_space = None
        self._acp_power_mode = None
        self._acp_average_number = None
        self._detector = None

    def init_spec_an(self, address):  # unit tested ok
        attempts = 0
        while attempts < 3:
            try:
                self.inst = None
                self.rm = visa.ResourceManager()
                self.inst = self.rm.open_resource(address)
                self.spec_an_config_failed = False
                break
            except visa.errors.VisaIOError as e:
                print('Exception :', e)
                self.spec_an_config_failed = True
                attempts += 1
                continue

    # initialize receiver parameters of spectral analyzer
    def spec_an_receive(self, rf_freq=None, attenuation=None, display_on=None, rbw=None, vbw=None):
        # partially unit tested ok
        if rf_freq:
            self.freq_centre = rf_freq
        if attenuation:
            self.attn_internal = attenuation
        if display_on:
            self.disp_on = display_on
        if rbw:
            self.rbw = rbw
        if vbw:
            self.vbw = vbw

    def get_serial_number(self):  # unit tested ok
        self.serial_number = self.inst.query('*IDN?')
        return self.serial_number

    def all_commands_set(self):
        resp = self.inst.query("*OPC?")
        return resp

    def screenshot(self, filename=None):
        gui.print_yellow('Saving Screenshot...')
        with open(filename, "wb") as img:
            try:
                data = bytearray(self.inst.query_binary_values(
                    "HCOP:SDUM:DATA?", datatype="s"))
                try:
                    img.write(data)
                except Exception as e:
                    print("Error writing image to local disk")
                    print(e)
            except Exception as e:
                print("Error fetching image data from instrument")
                print(e)
        print(f"Screenshot saved to {filename}")
        return True


    def meas_analog_demod_fm_dev(self):
        self.continuous_sweep = False
        peak_dev_avg = float(self.inst.query("CALC:MARK:FUNC:ADEM:FM? MIDD"))
        peak_dev_plus = float(self.inst.query("CALC:MARK:FUNC:ADEM:FM? PPE"))
        peak_dev_minus = float(self.inst.query("CALC:MARK:FUNC:ADEM:FM? MPE"))
        self.inst.query("*OPC?")
        self.continuous_sweep = True
        return peak_dev_avg, peak_dev_plus, peak_dev_minus

    def reset(self, val):
        if val:
            # print('Resetting...')
            self.inst.write(f"*RST")
            # print('Resetting and sleeping...')
            # time.sleep(2)
        else:
            pass

    #  Gets value indicating display enable/disable
    @property
    def disp_on(self):  # unit tested ok
       self._disp_on = self.inst.query("DISP:ENAB?")
       # self._disp_on = self.inst.query("SYST:DISP:UPD?")
       return self._disp_on

    #  Sets a value to enable/disable display
    @disp_on.setter
    def disp_on(self, is_on):  # unit tested ok
        if is_on:
            print("Display on")
            self.inst.write("DISP:ENAB 1")
            #self.inst.write("SYST:DISP:UPD ON")
            self._disp_on = True
        elif not is_on:
            print('Display off')
            self.inst.write("DISP:ENAB 0")
            #self.inst.write("SYST:DISP:UPD OFF")
            self._disp_on = False

    @property
    def freq_centre(self):  # unit tested ok
        # self.inst.query('INIT: IMM; *WAI')
        self._freq_centre = self.inst.query(f"FREQ:CENT?")
        return float(self._freq_centre)

    @freq_centre.setter
    def freq_centre(self, freq_hz):  # unit tested ok
        self.inst.write(f"FREQ:CENT {freq_hz}Hz")
        if not freq_hz == float(self.inst.query("FREQ:CENT?")):
            print(float(self.inst.query("FREQ:CENT?")))
            raise EquipmentSettingFailed
        self._freq_centre = freq_hz

    @property
    def freq_span(self):  # unit test ok
        self._freq_span = self.inst.query(f"FREQ:SPAN?")
        return self._freq_span

    @freq_span.setter
    def freq_span(self, freq_hz):  # unit tested ok
        self.inst.write(f"FREQ:SPAN {freq_hz}Hz")
        self.all_commands_set()
        if not freq_hz == float(self.inst.query("FREQ:SPAN?")):
            gui.print_red('freq_hz did not set correctly...')
            raise EquipmentSettingFailed
        self._freq_span = freq_hz

    @property
    def rbw(self):  # unit tested ok
        self._freq_span = self.inst.query("BAND?")
        return self._rbw

    @rbw.setter
    def rbw(self, rbw_hz):  # unit tested ok
        self.inst.write(f"BAND:RES {rbw_hz}Hz")
        # print(f'query result is: {self.inst.query("BAND:RES?")}')
        # if not float(rbw_hz) == float(self.inst.query("BAND:RES?")):
        # gui.print_red('rbw_hz did not set correctly...')
        #
        #    raise EquipmentSettingFailed
        self._rbw = rbw_hz

    #  read VBW from instance
    @property
    def vbw(self):  # unit tested ok
        self._vbw = self.inst.query("BAND:VID?")
        return self._vbw

    #  set VBW to instance
    @vbw.setter
    def vbw(self, vbw_hz):  # unit tested ok
        self.inst.write(f"BAND:VID {vbw_hz}Hz")
        # if not vbw_hz == float(self.inst.query("BAND:VID?")):
        #     gui.print_red('vbw_hz did not set correctly...')
        #     raise EquipmentSettingFailed
        self._vbw = vbw_hz

    #  function to read input attenuation
    @property
    def attn_internal(self):  # unit tested ok
        self._attn_internal = self.inst.query("POW:ATT?")
        # self._attn_internal = self.inst.query("INP:ATT?")
        return self._attn_internal

    #  function to set input attenuation
    @attn_internal.setter
    def attn_internal(self, attn_dB):  # unit tested ok
        self.inst.write(f"POW:ATT {attn_dB}")

        if not attn_dB == float(self.inst.query("POW:ATT?")):
            gui.print_red('attn_dB did not set correctly...')
            raise EquipmentSettingFailed
        self._attn_internal = attn_dB

    #  function to read the trace mode
    @property
    def trace_peak(self):  # unit tested ok
        self._trace_peak = self.inst.query("TRAC:MODE?")
        return self._trace_peak

    #  function to set trace mode
    #  WRITe | MAXH | MINH| VIEW | BLANk, note that AVER is in SENSe mode
    @trace_peak.setter
    def trace_peak(self, option='MAXH'):  # unit tested ok
        self.inst.write("TRAC:MODE " + option)
        self._trace_peak = option

    #  gets the detectors for which results are currently available
    @property
    def detector(self):  # unit tested ok
        self._detector = self.inst.query("DET:TRAC?")
        return self._detector

    #  sets the detectors for which results are currently available
    #  options: NORMal, POSitive, NEGative, SAMPle, AVERage
    @detector.setter
    def detector(self, option):  # unit tested ok
        self.inst.write("DET:TRAC " + option)
        self._detector = option

    # read off ACP status
    @property
    def acp_on(self):
        return self._acp_on

    # start spectrum analyzer in ACP measurement mode
    @acp_on.setter
    def acp_on(self, val):
        if val:
            self.inst.write(":INST SA")  # make sure that the instrument is in SA mode
            self.inst.write(":INIT:ACP")  # tested with inline command to initiate ACP
            #self.inst.write("CALC:MARK:FUNC:POW:SEL ACP")
        self._acp_on = val

    @property
    def acp_ch_bw(self):
        return self._acp_ch_bw

    @acp_ch_bw.setter
    def acp_ch_bw(self, acp_ch_bw):
        self.inst.write(f"POW:ACH:BWID:CHAN1 {acp_ch_bw}Hz")
        self._acp_ch_bw = acp_ch_bw

    @property
    def acp_ajch_bw(self):
        return self._acp_ajch_bw

    @acp_ajch_bw.setter
    def acp_ajch_bw(self, acp_ajch_bw):
        self.inst.write(f"POW:ACH:BWID:ACH {acp_ajch_bw}Hz")
        self._acp_ajch_bw = acp_ajch_bw

    @property
    def acp_altch_bw(self):
        return self._acp_altch_bw

    @acp_altch_bw.setter
    def acp_altch_bw(self, acp_altch_bw):
        self.inst.write(f"POW:ACH:BWID:ALT1 {acp_altch_bw}Hz")
        self._acp_altch_bw = acp_altch_bw

    @property
    def acp_ch_num(self):
        return self._acp_ch_num

    @acp_ch_num.setter
    def acp_ch_num(self, acp_ch_num):
        self.inst.write(f"POW:ACH:ACP {acp_ch_num}")
        self._acp_ch_num = acp_ch_num

    @property
    def acp_ch_space(self):
        return self._acp_ch_space

    @acp_ch_space.setter
    def acp_ch_space(self, acp_ch_space):
        self.inst.write(f"POW:ACH:SPAC {acp_ch_space}")
        self._acp_ch_space = acp_ch_space

    @property
    def acp_altch_space(self):
        return self._acp_altch_space

    @acp_altch_space.setter
    def acp_altch_space(self, acp_altch_space):
        self.inst.write(f"POW:ACH:SPAC:ALT1 {acp_altch_space}")
        self._acp_altch_space = acp_altch_space

    @property
    def acp_averaging_number(self):
        return self._acp_averaging_number

    @acp_averaging_number.setter
    def acp_averaging_number(self, acp_averaging_number):
        self.inst.write(f"SWE:COUN {acp_averaging_number}")
        self.inst.write(f"CALC:MARK:FUNC:POW:MODE WRIT")  # for average to take effect
        self._acp_average_number = acp_averaging_number

    # Keysight can fetch both relative/absolute acp simultaneously
    # Potentially redundant?
    '''
    def calc_acp():
        inst.write("ACP:TYPE TPR")
        x = inst.query("MEAS:ACP2?")
        (relative, absolute, lower_relative, lower_absolute, higher_relative, higher_absolute) = [
            float(a) for a in x.replace("\n", "").split(",") if float(a) != -9.99E2]
    
        print(absolute, lower_absolute, higher_absolute)
        print(relative, lower_relative, higher_relative)
    '''
    @property
    def acp_power_mode(self):
        return self._acp_power_mode

    # Sets the adjacent channel power measurements
    # options: ABSolute, RELative
    # *RST RELative
    @acp_power_mode.setter  # this option may not be available for keysight
    def acp_power_mode(self, option='REL'):  # REL, ABS
        # self.inst.write(f"{acp_power_mode}")
        self.inst.write("POW:ACH:MODE " + option)
        self._acp_power_mode = option

    #  TODO
    #  Gets the reference level offset in dB
    #  Not supported by R&S
    #  Maybe available in Analog Demodulation mode
    @property
    def ref_level_offset(self):
        self._ref_level_offset = self.inst.query("TRAC:Y:RLEV?")
        return self._ref_level_offset

    #  TODO
    #  Sets the reference level offset in dB
    #  Not supported by R&S
    #  Range [-200:200]
    #  *RST 0 dB
    @ref_level_offset.setter
    def ref_level_offset(self, ref_level_offset_dbm):
        self.inst.write(f"TRAC:Y:RLEV {ref_level_offset_dbm}")
        self.inst.write(f"{ref_level_offset_dbm}")  # Apparently necessary to write this?

        if not ref_level_offset_dbm == float(self.inst.query("TRAC:Y:RLEV?")):
            gui.print_red('Ref Level Offset Did not set correctly...')
            raise EquipmentSettingFailed

        self._ref_level_offset = ref_level_offset_dbm

    #  Get the number of sweep points
    @property
    def sweep_points(self):  # unit tested ok
        self._sweep_points = self.inst.query("SWE:POIN?")
        return self._sweep_points

    #  Set the number of sweep points
    @sweep_points.setter
    def sweep_points(self, number_sweep_points):  # unit tested ok
        self.inst.write(f"SWE:POIN {number_sweep_points}")
        if not number_sweep_points == float(self.inst.query("SWE:POIN?")):
            gui.print_red('Ref Level Offset Did not set correctly...')
            raise EquipmentSettingFailed
        self._sweep_points = number_sweep_points

    # to read RF reference level
    @property
    def rf_level(self):
        self._rf_level = self.inst.query("DISP:WIND:TRAC:Y:RLEV?")
        return self._rf_level

    # to write RF reference level
    @rf_level.setter
    def rf_level(self, rf_level_dbm):
        self.inst.write(f"DISP:WIND:TRAC:Y:RLEV {rf_level_dbm}")
        if not rf_level_dbm == float(self.inst.query("DISP:WIND:TRAC:Y:RLEV?")):
            gui.print_red('Ref Level did not set correctly...')
            raise EquipmentSettingFailed
        self._rf_level = rf_level_dbm

    #  function to close the instance
    def close(self):  # unit tested ok
        self.inst.close()
        print("Instrument closed")

    #  function to reset the instance
    def reset(self, val):  # unit tested ok
        if val:
            # print('Resetting...')
            self.inst.write(f"*RST")
            # print('Resetting and sleeping...')
            # time.sleep(2)
        else:
            pass


class SpecAn:

    def __new__(cls, test_results, spec_an_config):
        # spec_an_class = SpecAn_FSV(test_results, spec_an_config)
        spec_an_config_failed = True
        print(spec_an_config['model'])
        if spec_an_config['model'] == "RS_FSV":
            # print('RS_FSV')
            spec_an_class = SpecAn_FSV(test_results, spec_an_config)
        elif spec_an_config['model'] == "KeySight":
            spec_an_class = SpecAn_KeySightN9020B(test_results, spec_an_config)

        if spec_an_class.spec_an_config_failed:
            if spec_an_config['must_init']:
                return False
            else:
                return True

        return spec_an_class


def unittest_centre_freq(self):
    new_centre_frequency = 480e6
    old_centre_frequency = self.freq_centre
    if not new_centre_frequency == old_centre_frequency:
        self.freq_centre = new_centre_frequency
    else:
        shift_new_centre_frequency = new_centre_frequency + 10e6  # shift new centre frequency if it is same as old value
        self.freq_centre = shift_new_centre_frequency
        new_centre_frequency = shift_new_centre_frequency
    read_centre_frequency = self.freq_centre
    return read_centre_frequency == new_centre_frequency  # return unit test results


def unittest_span_freq(self):
    self.freq_centre = float(480e6)
    new_span_frequency = float(20e6)
    old_span_frequency = self.freq_span
    if new_span_frequency == old_span_frequency:
        new_span_frequency = new_span_frequency + 5e6
    self.freq_span = new_span_frequency
    read_span_frequency = float(self.freq_span)
    return read_span_frequency == new_span_frequency  # return unit test results


def unit_test(self):
    # function for unit testing
    print("Start unit testing............ ")
    print("Spectral Analyzer : " + spectralAnalyzer.inst.query("*IDN?"))
    print("Reset equipment")
    self.reset(1)  # reset the spectral analyzer
    self.inst.write('*CLS')  # clear buffer
    # spectralAnalyzer.disp_on = True
    # spectralAnalyzer.freq_centre = 156e6
    # spectralAnalyzer.ref_level_offset = 30
    # spectralAnalyzer.attn_internal = 45
    # spectralAnalyzer.rf_level = 50
    # spectralAnalyzer.rbw = 10e3
    print("Initialize spectral analyzer to a known state")
    self.spec_an_receive(rf_freq=450e6, rbw=2e6, vbw=3e6)
    time.sleep(5)
    print(" ******* Start current parameter value *********")
    print("Input attenuation : " + str(self.attn_internal))
    print("Display on status : " + self.disp_on)
    print("Serial Number : " + str(self.get_serial_number()))
    print("Centre frequency in Hz : " + str(self.freq_centre))
    print("Span frequency in Hz : " + str(self.freq_span))
    print("VBW frequency in Hz : " + str(self.vbw))
    print("RBW frequency in Hz : " + str(self.rbw))
    print("Trace peak : " + str(self.trace_peak))
    print("Detector : " + self.detector)
    print("Number of sweep points : " + str(self.sweep_points))
    print("RF Level in dBm : " + str(self.rf_level))
    time.sleep(5)
    #print("Y Axis Reference Level in dBm : " + str(self.ref_level_offset))
    print(" ******* End current parameter value *********")
    print("Setting.... new parameter values")
    self.freq_centre = 480e6  # centre frequency
    self.freq_span = 30e6  # frequency span
    self.vbw = 2e6  # VBW
    self.rbw = 1e6  # RBW
    self.attn_internal = 16  # internal power attenuation in dB
    self.trace_peak = 'MINH'  # set trace mode
    self.detector = 'POS'  # set detector mode
    self.sweep_points = 10001  # set number of sweep points
    time.sleep(3)
    print(" ******* New parameter values *********")
    print("Centre frequency in Hz : " + str(self.freq_centre))
    print("Span frequency in Hz : " + str(self.freq_span))
    print("VBW frequency in Hz : " + str(self.vbw))
    print("RBW frequency in Hz : " + str(self.rbw))
    print("Internal attenuation in dB : " + str(self.attn_internal))
    print("Trace peak : " + str(self.trace_peak))
    print("Detector : " + self.detector)
    print("Number of Sweep points : " + self.sweep_points)
    print(" ******* End new parameter value *********")
    print("Test equipment display on/off - please watch your equipment screen")
    self.disp_on = 0
    time.sleep(5)
    self.disp_on = 1
    print("unit testing completed")
    time.sleep(3)


if __name__ == "__main__":

    #fsv = SpecAn_FSV()
    spectralAnalyzer = SpecAn_KeySightN9020B()  # instantiate the keysight signal analyzer
    unit_test(spectralAnalyzer)
    spectralAnalyzer.reset(1)
    print("Unit test centre frequency : " + str(unittest_centre_freq(spectralAnalyzer)))
    print("Unit test span frequency : " + str(unittest_span_freq(spectralAnalyzer)))
    # print("Reset equipment")
    # spectralAnalyzer.reset(1)
    print("Close equipment")
    spectralAnalyzer.close()
    print('Done')

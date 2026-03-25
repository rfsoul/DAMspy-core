import ETS_logging.text_formatter as gui
import pyvisa as visa
import traceback
import time
import sys


# =============================================================================
# Author            : Athanatu Aziz Mahruz
# Department        : Verification and Validation
# Company           : GME Pty Ltd
# Date              : 16/April/2024
# Python version    : 3.11.0
# Purpose           : Power supply control scripts for SPD1168X by Siglent
# Drivers Required  : NIL
# Released          : Yes
# =============================================================================

# =============================================================================
# TO DO             :   1] Nil
# =============================================================================


class PowerSupply_SPD1168X:
    '''
    This class defines all the methods involved in control and communicating with the Siglent SPD1168X power supply
    '''
    
    ###
    # Establish Connection to Siglent SPD1168X power supply
    ###
    def __init__(self, psu_config=None):

        self.psu_config_failed = False
        self.serial_number = None

        ip_address = psu_config['IP']
        address = 'TCPIP0::' + ip_address + '::inst0::INSTR'
        self.init_psu(address)


    ###
    # Try 3 times to connect to the Siglent SPD1168X power supply
    ##
    def init_psu(self, address):

        attempts = 0
        min_default = '2'  # set minimum default to 2V
        while attempts < 3:
            try:
                self.inst = None
                self.rm = None
                self.rm = visa.ResourceManager()
                self.inst = self.rm.open_resource(address)
                self.inst.query_delay = 0.1
                self.inst.write_termination = '\n'
                self.psu_config_failed = False
                #self.inst.write('CH1:VOLT %f' % float(2))
                self._on = False
                self._current_limit = None
                self.on = False
                #print(self.get_serial_number())
                break
            except visa.errors.VisaIOError as e:
                print('Exception :', e)
                self.psu_config_failed = True
                # self.inst.close()
                attempts += 1
                continue

    def get_serial_number(self):
        self.serial_number = self.inst.query('*IDN?')
        return self.serial_number

    # On/Off
    @property
    def on(self):
        return self._on

    @on.setter
    def on(self, value):

        if value:
            val = self.inst.write('OUTP CH1,ON')
        else:
            self.inst.write('OUTP CH1,OFF')
        self._on = value

    # Voltage
    @property
    def voltage(self):
        return float(self.inst.query('MEAS:VOLT? CH1'))

    @voltage.setter
    def voltage(self, value):
        # self.inst.write(f"CH1:VOLT 14")
        # #self.inst.write(f"SOUR1:VOLT 10")
        self.inst.write('CH1:VOLT %f' % float(value))
        self._voltage = value
    # voltage = property(_get_voltage, _set_voltage)

    def set_voltage(self, value):
        # self.inst.write(f"CH1:VOLT 14")
        # #self.inst.write(f"SOUR1:VOLT 10")
        self.inst.write('CH1:VOLT %f' % float(value))
        self._voltage = value

    # Current limit
    @property
    def current_limit(self):
        return self._current_limit

    @current_limit.setter
    def current_limit(self, value):
        if value != self._current_limit:
            self.inst.write('CH1:CURR %f' % value)
            time.sleep(0.5)
            self._current_limit = value
        else:
            pass

    def get_current_level(self):
        current = self.inst.query('MEAS:CURR?')
        return current

    def close(self):
        print('Closing PSU inst...')
        if self.on:
            self.on = False
        self.inst.close()



class Power_Supply:

    def __new__(cls, psu_config):
        psu_class = PowerSupply_SPD1168X(psu_config)
        if psu_class.psu_config_failed:
            print("psu config failed")
            if psu_config['must_init']:
                return False
            else:
                return True

        else:
            return psu_class



## Below code to check only this script

# if __name__ == "__main__":
#
#     print('Running Section 1.223')
#     psu = PowerSupply_SPD1168X()
#

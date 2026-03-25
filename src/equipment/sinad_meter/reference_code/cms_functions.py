import sys
sys.path.append('.')
sys.path.append('./ETS_logging')
import time

import pyvisa as visa


# =============================================================================
# Author            : Athanatu Aziz Mahruz
# Department        : Verification and Validation
# Company           : GME Pty Ltd
# Date              : 13/April/2024
# Python version    : 3.11.0
# Purpose           : CMS52 scripts
# Drivers Required  : NIL
# Released          : No
# =============================================================================

# =============================================================================
# TO DO             :   1] Nil
# =============================================================================


class EquipmentSettingFailed(Exception):
    pass

class CMS:

    def __init__(self, cms_config):   
        self.rm = visa.ResourceManager()
        self.CM = self.rm.open_resource(cms_config['IP'])
        self.CM.write("DISP:M 2")
        self.CM.write(f"SINAD:R 1K")
        self.CM.write(f"FI:R:P ON")

    def get_sinad(self, audio_freq=1, ccitt=True, avg=20):
        sinad_temp = 0
        n = 0
        for count in range(avg):
            time.sleep(0.2)
            try:
                sinad_read = float(self.CM.query("SINAD:R?").split()[1])
            except Exception as e:  # tring to catchup CMS reading timeout error
                print("error reading SINAD with CMS, setting sinad_read to 0")
                sinad_read = 0
            #print("sinad_read: ", sinad_read)
            if sinad_read != 0:
                n = n+1
                sinad_temp += sinad_read
        if n != 0:
            return sinad_temp/n
        else:
            return sinad_temp

    def get_audio_level(self, avg=5):
        level_temp = 0
        for count in range(avg):
            level_read = float(self.CM.query('LE:A:R?').split()[1])
            level_temp += level_read
        return level_temp / avg

    def close(self):
        self.CM.close()

    def turn_on_ccitt(self):
        self.CM.write(f'FI:R:P ON')

    def turn_off_ccitt(self):
        self.CM.write(f'FI:R:P OFF')

    def turn_on_lpf(self):
        self.CM.write(f'FI:R:L ON')

    def turn_off_lpf(self):
        self.CM.write(f'FI:R:L OFF')

    def turn_on_hpf(self):
        self.CM.write(f'FI:R:H ON')

    def turn_off_hpf(self):
        self.CM.write(f'FI:R:H OFF')

    def turn_off_all_filter(self):
        self.CM.write(f'FI:R OFF')

    def get_distortion_level(self):
        return float(self.CM.query('DIST:R?').split()[1])

    def write_af1_freq(self, freq):
        self.CM.write(f'FR:A:I1 {freq}HZ')



# if __name__ == "__main__":
#     # around 370ms @ 44100Hz sample rate
#
#     cms1 = CMS()
#     while True:
#         #print(f"CCITT_OFF_SINAD= {sc.measure(num_samps=4096*4, ccitt=False)}")
#         print(f"CCITT_ON_SINAD= {cms1.get_sinad()}")
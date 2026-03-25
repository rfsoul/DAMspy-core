#Downloaded code from Git for use with behringer


#from ETS_logging import text_formatter as gui
#import yaml
import numpy as np
import scipy.signal as signal
import scipy.io.wavfile as wavfile
import sounddevice as sd
import platform
import re


class SoundCard:
    def __init__(
        self,
        #sc_config,  # comment out to work with soundblaster
        sample_rate = 44.1e3,
        test_tone_frequency = 1000,
        notch_width = 200, # Hz
        ):
        #self.equip_config = sc_config   # comment out to work with soundblaster
        self.sample_rate = sample_rate
        self.band_pass_coeffs = None

        # Calculate notch filter coefficients
        self.notch_sos = signal.cheby2(
            8,
            100,
            (test_tone_frequency - 0.5* notch_width, test_tone_frequency + 0.5* notch_width),
            'bandstop',
            output = 'sos',
            fs = sample_rate)
        self.notch_ringing = 2000


        # initializing hardware
        if platform.system() == 'Windows':
            print('- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - ')
            print('printing sd.query_devices')
            print(sd.query_devices())
            self.device_found = [line['name'] for line in sd.query_devices() if re.search('Blaster', line['name'])]
            if self.device_found != []:
                self.device = (self.device_found[0], self.device_found[1])
            else:
                #self.device = ('BEHRINGER UMC 202HD 192, MME', 'BEHRINGER UMC 202HD 19')
                self.device = (1, 4)   #for older computers   line above for newer
                #self.device = ('Microphone (BOMGE USB Audio Dev, MME', 'Headphones (BOMGE USB Audio Dev, MME')  # works for BOMGE when its powered by USB



        else:
            self.device = ('Sound Blaster Play! 3', 'Sound Blaster Play! 3')
            print("here")
            
        print("hi")
        print(self.device)
        #self.device = ('BEHRINGER UMC 202HD 192, MME', 'BEHRINGER UMC 202HD 19')   #  This works and detect behringer
        #self.device = ('BEHRINGER UMC 202HD 192, MME', 'Microphone (UMC202HD 192K), MME')
        sd.default.device = self.device
        sd.default.samplerate = self.sample_rate
        sd.default.channels = 1
        sd.default.dtype = 'float32'
        #print('Sound Card Initialised ', self.device)

    def get_mic_samps(self, num_samps=4096*4, gain=1):
        samps = sd.rec(num_samps, blocking=True, channels=1) * gain
        return samps[:, 0]

    def measure(self, num_samps, ccitt):
        freq_range_min = 300 # Hz, low cutoff (not applicable when using CCITT)
        freq_range_max = 3400 # Hz, high cutoff (not applicable when using CCITT)
        # Band pass filter coefficients
        if ccitt:
            ccitt_frequencies = (
                0, 16.6, 50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 1000, 1200,
                1400, 1600, 1800, 2000, 2500, 3000, 3500, 4000, 4500, 5000, 6000, 10000, self.sample_rate/2)

            ccitt_response_dB = (
                -100, -85.0, -63.0, -41.0, -21.0, -10.6, -6.3, -3.6, -2.0, -0.9, 0.0,
                0.6, 1.0, 0.0, -0.9, -1.7, -2.4, -3.0, -4.2, -5.6, -8.5, -15.0,
                -25.0, -36.0, -43.0, -80, -100)
            ccitt_response = 10 ** (np.array(ccitt_response_dB)/20.0)
            ccitt_response[0] = 0
            ccitt_response[-1] = 0
            n_taps = 5001
            self.band_pass_coeffs = signal.firwin2(
                n_taps,
                ccitt_frequencies,
                ccitt_response,
                nfreqs = 32769,
                antisymmetric = True,
                fs = self.sample_rate)
        else:
            n_taps = 1000
            self.band_pass_coeffs = signal.firwin(
                n_taps,
                (freq_range_min, freq_range_max),
                window = 'hamming',
                pass_zero = 'bandpass',
                fs = self.sample_rate)

        # take samples from hardware
        samples = self.get_mic_samps(num_samps)

        # Remove any residual DC
        samples -= np.mean(samples)

        # Band pass filter (either brick-wall or CCITT)
        band_pass_samples = signal.convolve(samples, self.band_pass_coeffs, 'valid')

        # Notch filter (remove the long initial ringing)
        notched_samples = signal.sosfilt(self.notch_sos, band_pass_samples)[self.notch_ringing:]

        # Signal + noise + distortion power
        SND = np.mean(band_pass_samples**2)
        ND = np.mean(notched_samples**2)
        SINAD = 10 * np.log10(SND / ND)
        return SINAD


if __name__ == "__main__":

     # with open('config\\location_config.yaml', "r") as file_descriptor:cd
     #     location_config = yaml.load(file_descriptor, Loader=yaml.FullLoader)

     sample_rate = 44.1e3

     # around 370ms @ 44100Hz sample rate

     sc = SoundCard(sample_rate)
     while True:
         #print(f"CCITT_OFF_SINAD= {sc.measure(num_samps=4096*4, ccitt=False)}")
          print(f"CCITT_ON_SINAD= {sc.measure(num_samps=4096*4, ccitt=True)}")

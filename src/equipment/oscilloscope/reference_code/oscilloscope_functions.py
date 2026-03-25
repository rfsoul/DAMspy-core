
import numpy as np
import matplotlib.pyplot as pp

from ds1054z import DS1054Z


def calculate_sinad(osc_samples, sample_rate=44100, test_tone_frequency=1000,
                    freq_range_min=50, freq_range_max=15000):
    # psophometric_weighting = self.psophometric_weighting
    # # num_samples = self.num_samples

    samples = osc_samples
    #samples = self.get_mic_samps(num_samps=self.num_samples)

    ## Note - changed freq_range_max from 5000 to 15000 20 Mar 2020
    ##
    '''Return SINAD (signal to noise and distortion) in dB of real-valued sinusoidal signal.

    Arguments:
        samples... a numpy array of input audio samples. This needs at least a few k of samples to ensure the accuracy.
        sample_rate... sampling frequency in Hz
        test_tone_frequency... frequency of the tone (default: 1000)
        freq_range_min... high pass filter cutoff in Hz (default: 50, same as HP8920)
        freq_range_max... low pass filter cutoff in Hz (default: 15000, same as HP8920)
        psophometric_weighting... apply psophometric weighting if True (default: False)
    '''

    # Ensure input is an array of floats
    samples = np.array(samples, np.float)
    n_samples = len(samples)
    samples_w = samples * np.kaiser(n_samples, beta=16.0)
    notch_width = 0.1  # notch width depends on the kaiser Beta coefficient

    # Zero pad to adjust the size to the next power of two
    n_fft = int(2 ** np.ceil(np.log2(n_samples)))
    samples_w = np.concatenate((samples_w, np.zeros(n_fft - n_samples)))

    # Go to frequency domain
    samples_fft = np.fft.rfft(samples_w)

    # Apply the band pass filter
    samples_fft_filt = samples_fft
    hpf_bin = int(n_fft * float(freq_range_min) / sample_rate)
    samples_fft_filt[:hpf_bin] = 1e-99
    lpf_bin = int(n_fft * float(freq_range_max) / sample_rate)
    samples_fft_filt[lpf_bin:] = 1e-99

    # Apply the psophometric weighting
    # if self.psophometric_weighting:
    #     samples_fft_filt = self.apply_psophometric_weighting(samples_fft_filt, sample_rate)

    # Transform the filtered signal + noise back to time domain and measure the power
    samples_filt = np.fft.irfft(samples_fft_filt)
    signal_plus_noise_power = np.mean(np.absolute(samples_filt) ** 2)

    # Notch out the test tone
    notch_low_bin = int(n_fft * (1.0 - 0.5 * notch_width) * test_tone_frequency / sample_rate)
    notch_high_bin = int(n_fft * (1.0 + 0.5 * notch_width) * test_tone_frequency / sample_rate)
    samples_fft_filt[notch_low_bin: notch_high_bin] = 1e-99

    # Transform the left over noise (+ distortion) back to time domain and measure the power
    noise_filt = np.fft.irfft(samples_fft_filt)
    noise_power = np.mean(np.absolute(noise_filt) ** 2)

    # Return the SINAD in dB
    return 10 * np.log10(signal_plus_noise_power / noise_power)




scope = DS1054Z('10.0.22.137')
print("Connected to: ", scope.idn)

print("Currently displayed channels: ", str(scope.displayed_channels))

#samples = DS1054Z._get_waveform_bytes_internal(scope, channel=1, mode='RAW')
samples = DS1054Z.get_waveform_samples(scope, channel=1, mode='NORMAL')

sinad = calculate_sinad(osc_samples=samples)
print(sinad)
# samples = DS1054Z.get_waveform_samples(scope, channel=1)
# samples = DS1054Z.get_waveform_samples(scope, channel=1)
# samples = DS1054Z.get_waveform_samples(scope, channel=1)
print(len(samples))

t = np.linspace(0,1.2,1200)
# print('Length of T: ', len(t))
# print(t)
# print('samples: ', samples)
val = 0. # this is the value where you want the data to appear on the y-axis.

pp.plot(t, samples)
pp.show()


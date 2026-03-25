#This script is based on the old new-sinad_1.py
#Only thing is now passing in the device so can neatly use different soundcards
# equipment/sinad_meter/new_sinad_1.py
# equipment/sinad_meter/new_sinad_1.py

import numpy as np
import scipy.signal as signal
import sounddevice as sd

def validate_default_device_names(default_names: tuple[str, str]) -> bool:
    """
    Check that each string in `default_names` appears (as a substring)
    of at least one entry in sd.query_devices(). If not, strip off
    anything after the first comma in the wanted string and try again.
    Return True if both are found under one of these two tests.
    """
    all_devs = sd.query_devices()
    dev_names = [d["name"] for d in all_devs]

    missing = []
    for want in default_names:
        # 1) Try to match the full string first
        if any(want in dn for dn in dev_names):
            continue

        # 2) If that fails, strip off the comma and everything after it
        short_want = want.split(',')[0].strip()
        if any(short_want in dn for dn in dev_names):
            continue

        # 3) Otherwise this name is missing
        missing.append(want)

    if missing:
        print(f"[SoundCard] Missing device name(s): {missing!r}")
        print(f"[SoundCard] Available device names: {dev_names!r}")
        return False

    return True

class SoundCard:
    def __init__(
        self,
        sample_rate: float = 44_100.0,
        test_tone_frequency: float = 1_000.0,
        notch_width: float = 200.0,                # Hz
        device_names: tuple[str, str] = None
    ):
        """
        Args:
          sample_rate            – sampling rate in Hz
          test_tone_frequency    – tone frequency in Hz
          notch_width            – width of the notch filter around the tone
          explicit_device        – an (input_name, output_name) tuple that SoundDevice will use directly.
                                   Both strings must appear (as substrings) in one of sd.query_devices()['name'].
        """
        self.sample_rate = sample_rate
        self.test_tone_frequency = test_tone_frequency
        self.band_pass_coeffs = None
        self.notch_ringing = 2000

        # Build the notch filter once
        self.notch_sos = signal.cheby2(
            8,
            100,
            (
                test_tone_frequency - 0.5 * notch_width,
                test_tone_frequency + 0.5 * notch_width
            ),
            'bandstop',
            fs=sample_rate,
            output='sos'
        )
        if not validate_default_device_names(device_names):
            raise RuntimeError(
                 f"SoundCard init failed: default_names {device_names!r} not found"
            )

        #————— Pick exactly which MME device to use —————#
        # If you passed device_names, try to find each by substring in sd.query_devices()
        sd.default.device = device_names


        # Configure recording defaults
        sd.default.samplerate = self.sample_rate
        sd.default.channels   = 1
        sd.default.dtype      = 'float32'



    def get_mic_samps(self, num_samps: int, gain: float = 1.0) -> np.ndarray:
        """
        Record `num_samps` samples on the forced device, return a 1D NumPy array.
        """
        data = sd.rec(num_samps, blocking=True, channels=1) * gain
        return data[:, 0]


    def measure(self, num_samps: int = 4096 * 4, ccitt: bool = False) -> float:
        """
        Compute SINAD over `num_samps`. If `ccitt` is True, apply CCITT weighting.
        Returns SINAD in dB (rounded to 0.1 dB).
        """
        #print(f"[SoundCard] CCITT filter is {'ENABLED' if ccitt else 'DISABLED'}")

        # Build or rebuild bandpass coefficients each call
        if ccitt:
            freqs = (
                0, 16.6, 50, 100, 200, 300, 400, 500, 600, 700,
                800, 900, 1000, 1200, 1400, 1600, 1800, 2000,
                2500, 3000, 3500, 4000, 4500, 5000, 6000, 10000,
                self.sample_rate / 2
            )
            resp_dB = (
                -100, -85.0, -63.0, -41.0, -21.0, -10.6, -6.3,
                -3.6, -2.0, -0.9, 0.0, 0.6, 1.0, 0.0, -0.9,
                -1.7, -2.4, -3.0, -4.2, -5.6, -8.5, -15.0,
                -25.0, -36.0, -43.0, -80, -100
            )
            resp = 10 ** (np.array(resp_dB) / 20.0)
            resp[0] = 0
            resp[-1] = 0
            taps = 5001
            self.band_pass_coeffs = signal.firwin2(
                taps, freqs, resp, nfreqs=32769, antisymmetric=True, fs=self.sample_rate
            )
        else:
            # Simple 300–3400 bandpass
            taps = 1000
            self.band_pass_coeffs = signal.firwin(
                taps,
                (300, 3400),
                pass_zero='bandpass',
                window='hamming',
                fs=self.sample_rate
            )

        # 1) Record raw samples
        samples = self.get_mic_samps(num_samps)

        # 2) Remove DC offset and compute raw‐RMS
        samples -= np.mean(samples)
        rms_raw = np.sqrt(np.mean(samples ** 2))
        #print(f"[SoundCard] Raw‐data RMS = {rms_raw:.6f}")
        rms_max_CP50 = 0.435656
        vol_percent = 100 * rms_raw / rms_max_CP50
        #print(f"[SoundCard] Approximate Vol = {vol_percent:.0f}%")

        # 3) Apply bandpass filter
        bp = signal.convolve(samples, self.band_pass_coeffs, mode='valid')

        # 4) Apply notch to remove test tone
        notched = signal.sosfilt(self.notch_sos, bp)[self.notch_ringing :]

        # 5) Compute signal and noise powers
        snd = np.mean(bp**2)
        nd = np.mean(notched**2)

        # 6) SINAD = 10·log10(snd / nd)
        sinad_db = 10 * np.log10(snd / nd)
        #print(f"[SoundCard] sinad_db = {sinad_db:.1f}")

        return round(sinad_db, 1)


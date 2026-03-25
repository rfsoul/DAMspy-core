# equipment/sinad_meter/Behringer_UMC202HD.py

import sounddevice as sd
from equipment.sinad_meter.common_driver.Soundcard import SoundCard
from equipment.utils.driver_base import EquipmentDriver

class Behringer_UMC202HD(EquipmentDriver):
    """
    Driver for Behringer UMC202HD SINAD measurements.
    Tries the “old” MME substrings first; if that fails, falls back to the “new” MME substrings.
    """

    def __init__(self, cfg):
        super().__init__(cfg)

        # First‐choice substrings under MME (Windows):
        self.default_names = (
            "BEHRINGER UMC 202HD 192, MME",
            "BEHRINGER UMC 202HD 19"
        )

        # Fallback substrings under MME:
        self.fallback_names = (
            #"Microphone (UMC202HD 192k)",
            #"Speakers (UMC202HD 192k)"
            "Microphone (UMC202HD 192k), MME",
            "Speakers (UMC202HD 192k), MME"
        )

        try:
            # 1) Try the “old” MME names
            self.sc = SoundCard(
                sample_rate         = cfg.get("sample_rate", 48000),
                test_tone_frequency = cfg.get("test_tone_freq", 1000),
                notch_width         = cfg.get("notch_width", 200.0),
                device_names        = self.default_names
            )
            print(f"[Behringer] using old MME names = {self.default_names!r}")

        except RuntimeError:
            # 2) If that fails, try the “new” MME names
            print(f"[Behringer] old‐name lookup failed; trying fallback names = {self.fallback_names!r}")
            self.sc = SoundCard(
                sample_rate         = cfg.get("sample_rate", 48000),
                test_tone_frequency = cfg.get("test_tone_freq", 1000),
                notch_width         = cfg.get("notch_width", 200.0),
                device_names        = self.fallback_names
            )

            print(f"[Behringer] using fallback MME names = {self.fallback_names!r}")

        # Now sd.default.device is locked to whichever tuple succeeded:
        print(f"[Behringer] sd.default.device = {sd.default.device!r}")


    def connect(self):
        print(f"[Behringer] connected → sd.default.device = {sd.default.device!r}")

    def disconnect(self):
        pass

    def open(self):
        return self.connect()

    def close(self):
        return self.disconnect()

    def measure_sinad(self, num_samps: int = 4096 * 4, ccitt: bool = False) -> float:
        return self.sc.measure(num_samps=num_samps, ccitt=ccitt)

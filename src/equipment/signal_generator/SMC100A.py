# from equipment.utils.driver_base import EquipmentDriver
# equipment/signal_generator/SMC100A.py

# equipment/signal_generator/SMC100A.py

"""
Driver for the Rohde & Schwarz SMC100A Signal Generator using a USB-VISA interface.

This driver conforms to the standard EquipmentDriver interface:
  - __init__(self, cfg)
  - open(self)
  - close(self)
  - set_frequency(self, freq_hz)
  - get_frequency(self) -> float
  - set_power(self, power_dbm)
  - get_power(self) -> float | None
  - enable_output(self)
  - disable_output(self)

Each method sends SCPI commands over a VISA session.
"""

from equipment.utils.driver_base import EquipmentDriver
import pyvisa
import time


class SMC100A(EquipmentDriver):
    """
    EquipmentDriver subclass for the Rohde & Schwarz SMC100A Signal Generator.

    Configuration dictionary (cfg) must include:
        - sig_gen_USBport: the VISA resource string (e.g. "USB0::0x0AAD::0x006E::103789::INSTR")
        - (optional) timeout: read/write timeout in seconds (default 1)
    """

    def __init__(self, cfg: dict):
        """
        Initialize the SMC100A driver.

        Args:
            cfg (dict): Configuration dictionary. Must include:
                - "sig_gen_USBport": VISA resource string for the SMC100A.
                - (optional) "timeout": read/write timeout in seconds (default 1).
        """
        super().__init__(cfg)

        try:
            self.resource_name = cfg["sig_gen_USBport"]
        except KeyError:
            raise KeyError("SMC100A driver requires 'sig_gen_USBport' in cfg")

        # Optional timeout (in seconds)
        self.timeout = cfg.get("timeout", 1)

        self.rm   = None  # pyvisa ResourceManager
        self.inst = None  # VISA instrument handle

    def open(self):
        """
        Open a VISA session to the SMC100A and configure termination characters.
        """
        try:
            self.rm = pyvisa.ResourceManager()
            self.inst = self.rm.open_resource(self.resource_name)
            # Ensure lines end with newline
            self.inst.write_termination = "\n"
            self.inst.read_termination  = "\n"
            # Set a timeout (in milliseconds) if the backend supports it
            try:
                self.inst.timeout = int(self.timeout * 1000)
            except Exception:
                pass

            # Optionally verify communication by querying IDN
            idn = self.inst.query("*IDN?")
            print(f"[SMC100A] Connected: {idn.strip()}")

        except pyvisa.VisaIOError as e:
            raise RuntimeError(f"SMC100A: Could not open VISA resource {self.resource_name}: {e}")

    def close(self):
        """
        Turn off RF output (if enabled) and close the VISA session.
        """
        if self.inst is not None:
            try:
                self.disable_output()
            except Exception:
                pass
            try:
                self.inst.close()
            except Exception:
                pass
            self.inst = None

        if self.rm is not None:
            try:
                self.rm.close()
            except Exception:
                pass
            self.rm = None

    def set_frequency(self, freq_hz: float):
        """
        Set the output frequency of the SMC100A.

        Args:
            freq_hz (float): Desired frequency in Hz (e.g. 484.25e6).
        """
        if self.inst is None:
            raise RuntimeError("SMC100A: call open() before set_frequency()")

        cmd = f"FREQ {freq_hz}"
        self.inst.write(cmd)
        time.sleep(0.2)

    def get_frequency(self) -> float:
        """
        Query the current output frequency.

        Returns:
            float: Frequency in Hz, as reported by the instrument.
        """
        if self.inst is None:
            raise RuntimeError("SMC100A: call open() before get_frequency()")

        response = self.inst.query("FREQ?")
        try:
            freq = float(response.strip())
            return freq
        except ValueError:
            raise RuntimeError(f"SMC100A: Unexpected frequency response '{response}'")

    def set_amplitude(self, power_dbm: float):
        """
        Set the RF output power level.

        Args:
            power_dbm (float): Desired output power in dBm (e.g. -10.0).
        """
        if self.inst is None:
            raise RuntimeError("SMC100A: call open() before set_power()")

        cmd = f"POW {power_dbm:.2f}"
        self.inst.write(cmd)
        time.sleep(0.2)

    def get_amplitude(self) -> float | None:
        """
        Query the current RF output power.

        Returns:
            float | None: Power in dBm, or None if parsing fails.
        """
        if self.inst is None:
            raise RuntimeError("SMC100A: call open() before get_power()")

        response = self.inst.query("POW?")
        try:
            p = float(response.strip())
            return p
        except ValueError:
            return None

    def enable_output(self):
        """
        Turn on the RF output.
        """
        if self.inst is None:
            raise RuntimeError("SMC100A: call open() before enable_output()")

        self.inst.write("OUTP ON")
        time.sleep(0.2)

    def disable_output(self):
        """
        Turn off the RF output.
        """
        if self.inst is None:
            raise RuntimeError("SMC100A: call open() before disable_output()")

        self.inst.write("OUTP OFF")
        time.sleep(0.2)

# equipment/signal_generator/TGR2051.py

"""
Driver for the Rohde & Schwarz TGR2051 Signal Generator using a serial interface.

This driver conforms to the standard EquipmentDriver interface:
  - __init__(self, cfg)
  - connect(self)
  - disconnect(self)
  - set_frequency(self, freq_hz)
  - get_frequency(self) -> str
  - set_amplitude(self, amplitude_dbm)
  - get_amplitude(self) -> float | None
  - enable_output(self)
  - disable_output(self)

Each method sends SCPI-like commands over a serial (COM) port.
"""

from equipment.utils.driver_base import EquipmentDriver
import serial
import time


class TGR2051(EquipmentDriver):
    """
    EquipmentDriver subclass for the Rohde & Schwarz TGR2051 Signal Generator.

    Configuration dictionary (cfg) must include:
      - port (e.g. "COM4")
      - baudrate (e.g. 9600)
      - timeout (in seconds, e.g. 1)

    Example cfg:
      {
          "port": "COM4",
          "baudrate": 9600,
          "timeout": 1
      }
    """

    def __init__(self, cfg: dict):
        """
        Initialize the TGR2051 driver.

        Args:
            cfg (dict): Configuration dictionary with keys:
                - "port": COM port (e.g., "COM4")
                - "baudrate": integer baud rate (e.g., 9600)
                - "timeout": read timeout in seconds (e.g., 1)
        """
        super().__init__(cfg)

        # Required configuration keys
        try:
            self.port = cfg["sig_gen_comport"]
            self.baudrate = cfg["baudrate"]
            self.timeout = cfg["timeout"]
            self.cal_factor = cfg['cal_factor']

        except KeyError as exc:
            raise KeyError(f"TGR2051 driver requires '{exc.args[0]}' in cfg")

        self.ser = None  # Will hold the serial.Serial instance






    def open(self):
        return self.connect()


    def close(self):
        return self.disconnect()




    def connect(self):
        """
        Open the serial port to the TGR2051 and wait briefly for initialization.
        """
        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=self.timeout)
            # Wait a short time for the device to be ready
            time.sleep(0.5)
            # (Optional) Query identity or firmware version to verify connection:
            # self.ser.write(b"*IDN?\n")
            # time.sleep(0.2)
            # resp = self.ser.read(200).decode().strip()
            # print(f"[TGR2051] Connected: {resp}")
            self.ser.write(b":SYSTem:BEEPer 0\n")
            time.sleep(0.1)
            # read/flush any response (often “OK”)
            _ = self.ser.read(200)
        except serial.SerialException as e:
            raise RuntimeError(f"TGR2051: Could not open serial port {self.port}: {e}")

    def disconnect(self):
        """
        Turn off RF output (if open) and close the serial port.
        """
        print('TG2051 disconnect called')
        if self.ser is not None and self.ser.is_open:
            try:
                self.disable_output()
            except Exception:
                pass
            self.ser.close()
            self.ser = None

    # def set_frequency(ser, frequency_Mhz):
    #     """Send SCPI command to set the frequency (e.g., 485 MHz)."""
    #     command = f'FREQ {frequency_mhz}MHz\n'
    #     ser.write(command.encode())
    #     print("frequency set to ", frequency_mhz)
    #     time.sleep(0.2)

    def set_frequency(self, freq_Mhz: float):
        """
        Set the output frequency of the TGR2051.

        Args:
            freq_hz (float): Desired frequency in Hz (e.g., 449250000 for 449.25 MHz).
        """
        if self.ser is None or not self.ser.is_open:
            raise RuntimeError("TGR2051: call connect() before set_frequency()")


        command = f"FREQ {freq_Mhz:.6f}MHz\n"
        self.ser.write(command.encode())  # Send as bytes
        # Allow time for the command to be processed
        time.sleep(0.2)



    def get_frequency(self) -> str:
        """
        Query the current output frequency from the signal generator.

        Returns:
            str: The frequency string returned by the instrument (e.g., "449250000").
        """
        if self.ser is None or not self.ser.is_open:
            raise RuntimeError("TGR2051: call connect() before get_frequency()")

        self.ser.write(b"FREQ?\n")
        time.sleep(0.2)
        response = self.ser.read(200).decode(errors="ignore").strip()

        # response is typically something like "449250000"
        return response

    def set_amplitude(self, amplitude_dbm: float):
        """
        Set the RF output amplitude (power level) of the TGR2051.

        Args:
            amplitude_dbm (float): Desired output power in dBm (e.g. -114.0).
        """
        if self.ser is None or not self.ser.is_open:
            raise RuntimeError("TGR2051: call connect() before set_amplitude()")

        # Format amplitude: if between -1 and 1, use two decimals; otherwise one decimal
        if -1 < amplitude_dbm < 1:
            command = f"POW {amplitude_dbm:.2f}\n"
        else:
            command = f"POW {amplitude_dbm:.1f}\n"

        self.ser.write(command.encode())
        time.sleep(0.2)

    def get_amplitude(self) -> float | None:
        """
        Query the current RF output amplitude in dBm.

        Returns:
            float | None: Parsed amplitude in dBm, or None on parse error.
        """
        if self.ser is None or not self.ser.is_open:
            raise RuntimeError("TGR2051: call connect() before get_amplitude()")

        self.ser.write(b"POW?\n")
        time.sleep(0.2)
        raw = self.ser.read(100).decode(errors="ignore").strip()

        try:
            amplitude = float(raw)
            return amplitude
        except ValueError:
            # If the response cannot be parsed as float, return None
            return None

    def enable_output(self):
        """
        Turn on the RF output of the TGR2051.
        """
        if self.ser is None or not self.ser.is_open:
            raise RuntimeError("TGR2051: call connect() before enable_output()")

        self.ser.write(b"OUTP ON\n")
        time.sleep(0.2)

    def disable_output(self):
        """
        Turn off the RF output of the TGR2051.
        """
        if self.ser is None or not self.ser.is_open:
            raise RuntimeError("TGR2051: call connect() before disable_output()")

        self.ser.write(b"OUTP OFF\n")
        time.sleep(0.2)

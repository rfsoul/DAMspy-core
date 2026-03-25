import pyvisa
import time
from pyvisa.constants import Parity, StopBits

class FSV_via_GPIB_Prologix:
    """
    Talk to an R&S FSV over a Prologix GPIB→USB adapter (appearing as COM9).
    Most Prologix adapters default to 115200,8,N,1. If that fails, try 9600.
    """

    def __init__(self,
                 com_port: int = 9,
                 prologix_baud: int = 9600,
                 gpib_addr: int = 16,
                 timeout_ms: int = 5000):
        """
        com_port: the Windows COM port number (e.g. 9 for "COM9").
        prologix_baud: baud rate for the Prologix adapter (often 115200 or 9600).
        gpib_addr: the GPIB address of your FSV (usually 16 for R&S analyzers, but confirm).
        timeout_ms: VISA read/write timeout.
        """
        self.rm = pyvisa.ResourceManager()
        serial_addr = f"ASRL{com_port}::INSTR"

        # Open the serial line to the Prologix
        self.inst = self.rm.open_resource(
            serial_addr,
            baud_rate=prologix_baud,
            data_bits=8,
            parity=Parity.none,
            stop_bits=StopBits.one,
            timeout=timeout_ms
        )
        # Prologix typically wants CRLF for line endings
        self.inst.write_termination = "\r\n"
        self.inst.read_termination = "\r\n"

        # A short pause to let the Prologix come up
        time.sleep(0.1)

        # Put Prologix into GPIB‐controller mode (==1), and disable auto-read after each write
        self.inst.write("++mode 1")
        self.inst.write("++auto 0")
        # Point Prologix at your FSV’s GPIB address
        self.inst.write(f"++addr {gpib_addr}")
        # Optional: verify Prologix is talking to your FSV by sending *IDN?
        # (If you get a timeout or gibberish, double-check baud/prologix commands).
        time.sleep(0.05)

    @property
    def idn(self) -> str:
        """Query *IDN? through the Prologix and return the response."""
        # All Prologix writes now go to the GPIB instrument at ++addr
        self.inst.write("*IDN?")
        return self.inst.read().strip()

    @property
    def center_frequency_hz(self) -> float:
        """Read back FREQ:CENT? from the FSV."""
        self.inst.write("FREQ:CENT?")
        resp = self.inst.read().strip()
        try:
            return float(resp)
        except ValueError:
            raise RuntimeError(f"Could not parse FREQ:CENT? → {resp!r}")

    @center_frequency_hz.setter
    def center_frequency_hz(self, freq_hz: float):
        """Set FREQ:CENT <freq>Hz on the FSV."""
        self.inst.write(f"FREQ:CENT {float(freq_hz)}Hz")

    @property
    def span_hz(self) -> float:
        """Read back FREQ:SPAN? from the FSV."""
        self.inst.write("FREQ:SPAN?")
        resp = self.inst.read().strip()
        try:
            return float(resp)
        except ValueError:
            raise RuntimeError(f"Could not parse FREQ:SPAN? → {resp!r}")

    @span_hz.setter
    def span_hz(self, span_hz: float):
        """Set FREQ:SPAN <span>Hz on the FSV."""
        self.inst.write(f"FREQ:SPAN {float(span_hz)}Hz")

    def close(self):
        """Close the VISA session."""
        try:
            # (Optionally turn off updates, etc., if needed)
            self.inst.write("SYST:DISP:UPD OFF")
        except Exception:
            pass
        self.inst.close()
        self.rm.close()


if __name__ == "__main__":
    # ------------------ SANITY CHECK ------------------
    #   • Make sure your Prologix is actually on COM9.
    #   • Make sure the FSV’s GPIB address is correct (often 16, but you can check the front panel).
    #   • If you get no IDN response, try changing prologix_baud to 9600.

    sa = FSV_via_GPIB_Prologix(com_port=9, prologix_baud=9600, gpib_addr=20)

    print("→ *IDN?  →", sa.idn)
    sa.center_frequency_hz = 1e9
    print("→ Center freq set/read:", sa.center_frequency_hz, "Hz")
    sa.span_hz = 5e6
    print("→ Span set/read      :", sa.span_hz, "Hz")

    sa.close()

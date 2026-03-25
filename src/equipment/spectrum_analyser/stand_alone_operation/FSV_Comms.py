import pyvisa
import time

class SpectrumAnalyzerFSP:
    """
    Minimal wrapper around a Rohde & Schwarz FSP spectrum analyser over a COM port.
    Usage example:
        sa = SpectrumAnalyzerFSP(com_port=3, baudrate=115200, timeout_ms=5000)
        print("IDN:", sa.idn)
        sa.center_frequency_hz = 1e9
        sa.span_hz = 10e6
        # … etc.
        sa.close()
    """

    def __init__(
        self,
        com_port: int,
        baudrate: int = 115200,
        data_bits: int = 8,
        parity: str = "none",            # can be "none", "even", "odd"
        stop_bits: int = 1,
        timeout_ms: int = 5000,
    ):
        """
        com_port: COM port number (e.g. 3 for COM3)
        baudrate: serial baud rate (FSP default is usually 115200)
        data_bits: typically 8
        parity: "none" / "even" / "odd"
        stop_bits: usually 1
        timeout_ms: VISA timeout in milliseconds
        """
        self.rm = pyvisa.ResourceManager()
        # Build a Windows‐friendly address. PyVISA recognizes "COM3" or "ASRL3::INSTR" (equivalent).
        serial_address = f"ASRL{com_port}::INSTR"

        # Open the COM port resource with the desired serial parameters
        self.inst = self.rm.open_resource(
            serial_address,
            baud_rate=baudrate,
            data_bits=data_bits,
            parity=self._translate_parity(parity),
            stop_bits=self._translate_stopbits(stop_bits),
            timeout=timeout_ms,
        )

        # Make sure terminations are correct: FSP usually expects '\n' for SCPI
        self.inst.read_termination = "\n"
        self.inst.write_termination = "\n"

        # Optional: give the analyser a moment to wake up
        time.sleep(0.1)

    def _translate_parity(self, p: str):
        """Helper to convert "none"/"even"/"odd" into pyvisa.constants.Parity."""
        from pyvisa.constants import Parity

        p = p.lower()
        if p == "none":
            return Parity.none
        elif p == "even":
            return Parity.even
        elif p == "odd":
            return Parity.odd
        else:
            raise ValueError(f"Unsupported parity: {p!r}")

    def _translate_stopbits(self, sb: int):
        """Helper to convert 1 or 2 into pyvisa.constants.StopBits."""
        from pyvisa.constants import StopBits

        if sb == 1:
            return StopBits.one
        elif sb == 2:
            return StopBits.two
        else:
            raise ValueError(f"Unsupported stop_bits: {sb!r}")

    @property
    def idn(self) -> str:
        """Query *IDN? to verify we’re talking to the FSP."""
        return self.inst.query("*IDN?").strip()

    @property
    def center_frequency_hz(self) -> float:
        """Read back the centre frequency in Hz (returned as a string)."""
        resp = self.inst.query("FREQ:CENT?").strip()
        try:
            return float(resp)
        except ValueError:
            raise RuntimeError(f"Unexpected response to FREQ:CENT? → {resp!r}")

    @center_frequency_hz.setter
    def center_frequency_hz(self, freq_hz: float):
        """Set the centre frequency, in Hz. For example: 1e9 (1 GHz)."""
        # On R&S analyzers, SCPI is usually 'FREQ:CENT <value>Hz'
        self.inst.write(f"FREQ:CENT {float(freq_hz)}Hz")
        # Optionally verify by querying back:
        # back = float(self.inst.query("FREQ:CENT?"))
        # if abs(back - freq_hz) > 1e-6:
        #     raise RuntimeError(f"Failed to set center frequency (got {back})")

    @property
    def span_hz(self) -> float:
        """Read back the span in Hz."""
        resp = self.inst.query("FREQ:SPAN?").strip()
        try:
            return float(resp)
        except ValueError:
            raise RuntimeError(f"Unexpected response to FREQ:SPAN? → {resp!r}")

    @span_hz.setter
    def span_hz(self, span_hz: float):
        """Set the frequency span, in Hz. E.g. 10e6 for 10 MHz span."""
        self.inst.write(f"FREQ:SPAN {float(span_hz)}Hz")

    def read_trace(self, trace_number: int = 1) -> list[float]:
        """
        Fetch the trace data from the specified trace (1‐4).
        Returns a list of floats (dBm or dBμV, depending on your unit).
        """
        # Select the trace and request data in ASCII
        self.inst.write(f"TRAC{trace_number}:MODE WRIT")
        raw = self.inst.query(f"TRAC{trace_number}:DATA?").strip()
        # The FSP returns comma‐separated ASCII numbers, like "1.23, 2.34, …"
        str_vals = raw.split(",")
        try:
            return [float(x) for x in str_vals]
        except ValueError:
            raise RuntimeError(f"Could not parse trace data: {raw!r}")

    def set_detector_mode(self, mode: str):
        """
        Set detector mode. Common modes: "POS" (Positive‐peak), "NEG" (Negative‐peak),
        "RMS", "AVER", etc. Check FSP SCPI manual for valid values.
        Example: sa.set_detector_mode("POS")
        """
        valid = {"POS", "NEG", "RMS", "AVER", "QPK"}
        m = mode.upper()
        if m not in valid:
            raise ValueError(f"Unsupported detector mode: {mode!r}. Valid: {valid}")
        self.inst.write(f"DET {m}")

    def close(self):
        """Close the VISA session cleanly."""
        try:
            self.inst.write("SYST:DISP:UPD OFF")  # optional cleanup if you want
        except Exception:
            pass
        self.inst.close()
        self.rm.close()


if __name__ == "__main__":
    # ---------- QUICK SANITY CHECK ----------
    # Change COM port number below to whichever your FSP is on:
    sa = SpectrumAnalyzerFSP(com_port=9, baudrate=115200, timeout_ms=3000)

    print(">> *IDN? →", sa.idn)
    # Set center to 1 GHz and span 10 MHz, then read back to confirm:
    sa.center_frequency_hz = 1e9
    print("→ Center:", sa.center_frequency_hz, "Hz")

    sa.span_hz = 10e6
    print("→ Span  :", sa.span_hz, "Hz")

    # Switch detector to positive peak, just as a test:
    sa.set_detector_mode("POS")
    print("→ Detector is now POS (peak).")

    # Optionally read the first trace (a list of floats):
    # trace_data = sa.read_trace(1)
    # print("→ First 10 points of Trace 1:", trace_data[:10])

    sa.close()

"""
Connected devices: ('USB0::0x0AAD::0x006E::103789::INSTR',)
IDN: Rohde&Schwarz,SMC100A,1411.4002k02/103789,3.1.18.2-3.01.134.28
Frequency set to: 1000000000
"""
import pyvisa
import time

# VISA resource string for your SMC100A
RESOURCE = 'USB0::0x0AAD::0x006E::103789::INSTR'

def main(instr):
    time.sleep(0.5)  # Let the device settle
    set_frequency(instr, 484.25e6)          # Set to 485 MHz
    get_frequency(instr)                 # Query frequency
    enable_rf_output(instr)              # Turn RF on
    set_amplitude(instr, -100)            # Set amplitude
    get_amplitude(instr)                 # Read amplitude
    disable_rf_output(instr)             # Turn RF off

def enable_rf_output(instr):
    instr.write('OUTP ON')
    print("RF output enabled")
    time.sleep(0.2)

def disable_rf_output(instr):
    instr.write('OUTP OFF')
    print("RF output disabled")
    time.sleep(0.2)

def set_frequency(instr, frequency_hz):
    """Set frequency in Hz"""
    instr.write(f'FREQ {frequency_hz}')
    print(f"Frequency set to {frequency_hz / 1e6:.3f} MHz")
    time.sleep(0.2)

def get_frequency(instr):
    response = instr.query('FREQ?')
    freq = float(response)
    print(f"Current frequency: {freq / 1e6:.3f} MHz")
    return freq

def set_amplitude(instr, amplitude):
    """Set the RF output amplitude in dBm"""
    if isinstance(amplitude, (int, float)):
        instr.write(f'POW {amplitude:.2f}')
        print(f"Amplitude set to {amplitude:.2f} dBm")
        time.sleep(0.2)
    else:
        print("Invalid amplitude value.")

def get_amplitude(instr):
    try:
        response = instr.query('POW?')
        amplitude = float(response)
        print(f"Current amplitude = {amplitude:.1f} dBm")
        return amplitude
    except ValueError:
        print("Error parsing amplitude response:", response)
        return None

if __name__ == "__main__":
    try:
        rm = pyvisa.ResourceManager()
        instr = rm.open_resource(RESOURCE)
        instr.write_termination = '\n'
        instr.read_termination = '\n'

        print(f"Connected to: {instr.query('*IDN?')}")
        main(instr)

    except pyvisa.VisaIOError as e:
        print(f"VISA error: {e}")
    finally:
        instr.close()
        print("VISA connection closed.")


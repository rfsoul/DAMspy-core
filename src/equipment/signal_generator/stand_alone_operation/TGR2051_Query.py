import serial
import time

# Serial port configuration
PORT = 'COM5'
BAUDRATE = 9600
TIMEOUT = 1

def main(ser):
    time.sleep(0.5)  # Let the device initialize
    set_frequency(ser, 494.25)
    current_freq = get_frequency(ser)
    enable_rf_output(ser)
    set_amplitude(ser, -27)
    get_amplitude(ser)
    disable_rf_output(ser)

def enable_rf_output(ser):
    """Turn on the RF output of the signal generator."""
    ser.write(b'OUTP ON\n')
    print("rf output enabled")
    time.sleep(0.2)

def disable_rf_output(ser):
    """Turn off the RF output of the signal generator."""
    ser.write(b'OUTP OFF\n')
    print("RF output disabled")
    time.sleep(0.2)


def set_frequency(ser, frequency_mhz):
    """Send SCPI command to set the frequency (e.g., 485 MHz)."""
    command = f'FREQ {frequency_mhz}MHz\n'
    ser.write(command.encode())
    print("frequency set to ",frequency_mhz)
    time.sleep(0.2)


def get_frequency(ser):
    """Query the current frequency from the signal generator."""
    ser.write(b'FREQ?\n')
    time.sleep(0.2)
    response = ser.read(100)
    freq = response.decode().strip()
    print("Current frequency:", freq)
    return freq

def get_amplitude(ser):
    """Query the current RF output amplitude in dBm."""
    ser.write(b'POW?\n')
    time.sleep(0.2)
    response = ser.read(50).decode().strip()

    try:
        amplitude = float(response)
        print(f"Current amplitude = {amplitude:.1f} dBm")
        return amplitude
    except ValueError:
        print("Error parsing amplitude response:", response)
        return None


def set_amplitude(ser, amplitude):
    """Set the RF output amplitude in dBm.
    Note that cannot set amplitude between -1 to 1 dBm with exception of 0 dBm

    """

    # Force the amplitude to be a float and ensure it's properly formatted to one decimal place
    if isinstance(amplitude, (int, float)):
        if -1 < amplitude < 1:
            # Use scientific notation for very small values between -1 and 1
            command = f'POW {amplitude:.2f}\n'
        else:
            command = f'POW {amplitude:.1f}\n'  # Use 1 decimal place for larger values
        #command = 'POW -.3\n'
        ser.write(command.encode())

        print(f"Amplitude set to {amplitude:.2f} dBm")  # Ensure print is consistent
        time.sleep(0.2)
    else:
        print("Invalid amplitude value.")





if __name__ == "__main__":
    try:
        ser = serial.Serial(PORT, BAUDRATE, timeout=TIMEOUT)
        main(ser)
    except serial.SerialException as e:
        print(f"Error with serial communication: {e}")
    finally:
        # Ensure the serial connection is closed regardless of any errors
        if ser.is_open:
            ser.close()
            print("Serial port closed.")

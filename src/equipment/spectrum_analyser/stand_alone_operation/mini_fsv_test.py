import serial
import time

def query_idn_force_remote(
    com_port: str = "COM9",
    baudrate: int = 9600,
    gpib_address: int = 20,
    max_attempts: int = 10
):
    """
    Opens COM9 @ 9600,8,N,1 to a Prologix GPIB→USB adapter, points at GPIB <gpib_address>,
    forces the FSP into REMOTE mode (with proper CRLF terminations), unbanks the display,
    then queries *IDN? up to max_attempts times if necessary.

    Returns the decoded IDN string on success, or None if all attempts fail.
    """
    try:
        ser = serial.Serial(
            port=com_port,
            baudrate=baudrate,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=1.0      # 1 second timeout for readline()
        )
    except Exception as e:
        print("Error: cannot open COM port:", e)
        return None

    try:
        # 1) Flush any old data
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        time.sleep(0.1)

        # 2) Put Prologix into GPIB controller mode
        ser.write(b"++mode 1\r\n")
        time.sleep(0.05)

        # 3) Point at the FSP’s GPIB address
        ser.write(f"++addr {gpib_address}\r\n".encode("ascii"))
        time.sleep(0.05)

        # 4) Enable auto-read so that each SCPI write is followed by an immediate read
        ser.write(b"++auto 1\r\n")
        time.sleep(0.05)

        for attempt in range(1, max_attempts + 1):
            print(f"\n--- Attempt {attempt} ---")

            # 5) Force FSP into REMOTE mode (with CRLF)
            print("setting to remote mode")
            ser.write(b"SYST:REM\r\n")
            # Give it a bit longer to switch to remote
            time.sleep(5)

            # 6) Unbank the display so that SCPI commands can flow
            print("unbanking")
            ser.write(b"DISP:UPD ON\r\n")

            time.sleep(0.2)

            # 7) Send the IDN query (CRLF terminated)
            ser.write(b"*IDN?\r\n")

            # 8) Read one line (up to '\n') with up to ser.timeout = 1 second
            response = ser.readline()

            if response:
                # We got something—print raw + decoded and return
                print("Raw response (bytes):", repr(response))
                try:
                    text = response.decode("utf-8", errors="replace").strip()
                except Exception:
                    text = "<decode error>"
                print("Decoded IDN:", text)
                return text
            else:
                print("No response received. Retrying...")
                # Slight pause before the next attempt
                time.sleep(0.2)
                continue

        # If we reach here, all attempts failed:
        print(f"Failed to get IDN after {max_attempts} attempts.")
        return None

    finally:
        ser.close()


if __name__ == "__main__":
    idn_str = query_idn_force_remote()
    if idn_str is None:
        print("Instrument did not respond.")
    else:
        print("Success: IDN =", idn_str)

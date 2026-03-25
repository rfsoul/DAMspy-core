import serial
import time

def run_fsp_commands(
    com_port="COM9",
    baudrate=9600,
    gpib_address=20,
    timeout_s=2.0
):
    ser = serial.Serial(
        port=com_port,
        baudrate=baudrate,
        bytesize=serial.EIGHTBITS,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        timeout=timeout_s
    )
    try:
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        time.sleep(0.1)

        # Put the Prologix into controller mode and point at GPIB 20
        ser.write(b"++mode 1\n")
        time.sleep(0.05)
        ser.write(f"++addr {gpib_address}\n".encode("ascii"))
        time.sleep(0.05)
        ser.write(b"++auto 1\n")
        time.sleep(0.05)

        # 1) Set center to 500 MHz
        ser.write(b"FREQ:CENT 500000000Hz\n")
        time.sleep(0.1)

        # 2) Read it back
        ser.write(b"FREQ:CENT?\n")
        time.sleep(0.1)
        resp = ser.read_all()
        print("Center Frequency (raw bytes):", repr(resp))
        print("Center Frequency (decoded):", resp.decode("ascii", errors="ignore").strip())

        # 3) Set span to 10 MHz
        ser.write(b"FREQ:SPAN 10000000Hz\n")
        time.sleep(0.1)

        # 4) Read back the span
        ser.write(b"FREQ:SPAN?\n")
        time.sleep(0.1)
        resp2 = ser.read_all()
        print("Span (raw bytes):", repr(resp2))
        print("Span (decoded):", resp2.decode("ascii", errors="ignore").strip())

    finally:
        ser.close()

if __name__ == "__main__":
    run_fsp_commands()

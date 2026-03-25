import time
import pyvisa

def measure_peak_amplitude():
    # Frequency band limits (Hz)
    f_start = 440e6
    f_stop = 530e6

    # Open VISA resource manager and the GPIB instrument at address 20
    rm = pyvisa.ResourceManager()
    inst = rm.open_resource('GPIB0::20::INSTR')

    # Increase timeout so sweep has time to complete (e.g., 10 seconds)
    inst.timeout = 10000  # milliseconds

    # 1) Turn off continuous sweep
    inst.write('INIT:CONT OFF')

    # 2) Set frequency range explicitly
    inst.write(f'FREQ:STAR {int(f_start)}')
    inst.write(f'FREQ:STOP {int(f_stop)}')

    # 3) (Optional) Set resolution bandwidth if desired (e.g., 100 kHz)
    # inst.write('BAND:RES 100000')

    # 4) Ensure detector is in positive-peak mode for accurate peak reading
    inst.write('DET:MODE POS')

    # 5) (Optional) Set number of sweep points (e.g., 1001)
    inst.write('SWE:POIN 1001')

    # 6) Trigger a single sweep
    inst.write('INIT')
    time.sleep(0.05)  # small delay before polling OPC

    # 7) Wait for sweep to finish
    try:
        opc = inst.query('*OPC?').strip()
        if opc != '1':
            print(f'Unexpected OPC response: {opc!r}')
    except pyvisa.errors.VisaIOError:
        print('Timeout waiting for sweep to complete.')

    # 8) Read trace (amplitude in dBm) as comma-separated string
    raw_trace = inst.query('TRAC? TRACE1')
    amplitudes = [float(val) for val in raw_trace.split(',')]

    # 9) Compute frequency increment per point
    num_points = len(amplitudes)
    delta_f = (f_stop - f_start) / (num_points - 1)

    # 10) Find peak amplitude and its index
    peak_index = max(range(num_points), key=lambda i: amplitudes[i])
    peak_amp = amplitudes[peak_index]
    peak_freq = f_start + peak_index * delta_f

    # 11) Print results
    print(f'Peak amplitude: {peak_amp:.2f} dBm')
    print(f'Frequency of peak: {peak_freq/1e6:.3f} MHz')

    # 12) Clean up
    inst.close()
    rm.close()

if __name__ == '__main__':
    measure_peak_amplitude()

import pyvisa


def main():
    # Create a ResourceManager using your default VISA backend (NI-VISA)
    rm = pyvisa.ResourceManager()

    # Open the GPIB device at primary address 20 on board 0
    inst = rm.open_resource('GPIB0::20::INSTR')

    # Optional: set a timeout (in milliseconds) so you don't hang forever
    inst.timeout = 5000  # 5 seconds

    # Query the instrument’s identity string
    idn = inst.query('*IDN?')
    print('Instrument ID:', idn.strip())


if __name__ == '__main__':
    main()

"""
Lets start creating a new folder for the collection of measurements
folder will be named
Year-month-day-hour-minute-second_Antenna-under-test-Receive-Antenna Az inc-EV in
So the time is just the start of the test
The other things are added to the name of the folder from parameters below in the script
Antenna_Under_Test = etc  (string)
Receive_Antenna = etc

The following are things I want placed into an antenna notes file or the json I think you are generating whatever is easier
signal_generator = etc
spectrum_analyser = etc
antenna_under_test_notes = string
"""





# -*- coding: utf-8 -*-

# This example generates a basic CW signal.

from equipment.signal_generator.API.vsgdevice.vsg_api import *
from time import sleep

def generate_iq():
    # Open device
    handle = vsg_open_device()["handle"]

    # Configure generator
    freqGHz = 2.41
    freq = freqGHz*1e9# Hz
    print(freq)
    sample_rate = 50.0e6 # samples per second
    level = 10 # dBm

    vsg_set_frequency(handle, freq)
    vsg_set_level(handle, level);
    vsg_set_sample_rate(handle, sample_rate);

    # Output CW, single I/Q value of {1,0}
    # This is equivalent to calling vsgOutputCW
    iq = numpy.zeros(2).astype(numpy.float32)
    iq[0] = 1
    vsg_repeat_waveform(handle, iq, 1);

    # Will transmit until you close the device or abort
    #sleep(5);

    # Stop waveform
    #vsg_abort(handle);

    # Done with device
    #vsg_close_device(handle);

if __name__ == "__main__":
    generate_iq()

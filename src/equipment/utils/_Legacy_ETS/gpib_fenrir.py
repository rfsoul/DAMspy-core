#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =============================================================================
# Author            : Andy Wang
# Date              : 24 June 2022
# Python version    : 3.10
# =============================================================================
"""gpib_fenrir.py
Fenrir GPIB to USB (Serial) cable library.

Allows communication with a GPIB instrument via Serial connection.
The cable is a clone of Prologix GPIB-USB, and follows same documentation: http://prologix.biz/downloads/PrologixGpibUsbManual-6.0.pdf

    Typical usage example:

    gpib = GPIB()
    idn = gpib.query("*IDN?")
"""

import serial
import time


class GPIB:
    """A wrapper class for GPIB-Serial connection.

    Attributes:
        ser : an open serial.Serial instance
    """

    def __init__(self, port: int = 18, addr: int = 15):
        """Inits GPIB via a serial connection.

        The cable requires setting up for proper GPIB communication.
        ++auto 0 disables the automatic read after each send.
        ++mode 1 switches the cable into controller mode.
        ++addr is an int for the GPIB address of the instrument.
        ++eos 0 adds a CR+LF to the end of each send.
        """

        self.ser = serial.Serial(f"COM{port}", timeout=2)
        self.write("++auto 0")
        self.write("++mode 1")
        self.write(f"++addr {addr}")
        self.write("++eos 0")

    def __del__(self):
        self.ser.close()

    def read(self):
        """Commands the cable to read."""

        self.write("++read")
        return self.ser.readline().decode()

    def write(self, msg: str):
        """Sends a message.

        Args:
            msg: String to send
        """

        self.ser.write(f"{msg}\r".encode())

    def query(self, msg: str):
        """Sends a message then reads from cable.

        A sleep delay of 500ms is added between the write and read to allow proper communication, otherwise it may be possible to read blank responses.

        Args:
            msg: String to send
        """

        self.write(msg)
        time.sleep(0.5)
        return self.read()

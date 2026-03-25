#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =============================================================================
# Author            : Andy Wang
# Date              : 3 June 2022
# Python version    : 3.10
# =============================================================================
"""xrs660serial.py
XRS660 Serial Interface

Allows interfacing with XRS660 radio via Serial connection or Bluetooth using AT commands.

    Typical usage example:

    xrs660 = Radio()
    xrs660.tx(True)
    xtal_temperature = xrs660.temp_xtal()
    pa_temperature = xrs660.temp_pa()
    xrs660.tx(False)
"""

import serial


class Radio:
    def __init__(self, port: int = 11):
        """Inits Radio using COM port.
        
        Both Bluetooth and normal Serial connection will create COM ports, select the appropriate port and it should work.
        """
        self.ser = serial.Serial(f"COM{port}", 57600, timeout=1)
        assert self.ping(), f"Could not communicate with radio on COM{port}"

    def read(self) -> str:
        self.last = self.ser.readlines()
        return self.last[-1]

    def write(self, msg: str) -> bool:
        self.ser.write(f"{msg}\r".encode())
        return self.read() == b"OK\r\n"

    def ping(self) -> bool:
        return self.write("AT")

    def tx(self, state: bool) -> bool:
        return self.write(f"AT+WGPTT={'1' if state else '0'}")

    def strip(self) -> int:
        return int(self.last[2].decode().strip("+WGTEMP: C\r\n"))

    def temp_pa(self) -> int:
        self.write("AT+WGTEMP=1")
        return self.strip()

    def temp_xtal(self) -> int:
        self.write("AT+WGTEMP=0")
        return self.strip()

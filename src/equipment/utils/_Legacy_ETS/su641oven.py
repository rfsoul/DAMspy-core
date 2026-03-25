#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =============================================================================
# Author            : Andy Wang
# Date              : 3 June 2022
# Python version    : 3.10
# =============================================================================
"""su641oven.py
Espec SU-641 Temperature Chamber Serial Interface

Connect to the oven via RS485 to USB cable.
Product website (Japanese): http://lampx.tugraz.at/~hadley/semi/ch9/instruments/Humidity_Chamber/Japanese/products.html
Programming manual (Japanese): http://lampx.tugraz.at/~hadley/semi/ch9/instruments/Humidity_Chamber/Japanese/pdf/options/40001040053_J.pdf

    Typical usage example:

    oven = Oven()
    oven.set_temp(-30)
    oven.run()
    curr_temp = oven.get_temp()
    target_temp = oven.get_target()
    oven.standby()
"""

import serial


class Oven:
    def __init__(self, port: int):
        """Inits Oven with RTS & DTR pins set"""

        s = serial.Serial()
        s.port = f"COM{port}"
        s.baudrate = 9600
        s.timeout = 1
        s.setRTS(True)
        s.setDTR(True)
        s.open()
        self.ser = s

    def read(self) -> str:
        return self.ser.readline().decode()

    def write(self, msg: str) -> str:
        self.ser.write(f"{msg}\r".encode())
        return self.read()

    def get_temp(self) -> float:
        return float(self.write("1,TEMP?").split(",")[0])

    def set_temp(self, temp: float) -> bool:
        return self.write(f"1,TEMP,S{temp}").split(":")[0] == "OK"

    def run(self) -> bool:
        return self.write("1,MODE,CONSTANT").split(":")[0] == "OK"

    def standby(self) -> bool:
        return self.write("1,MODE,STANDBY").split(":")[0] == "OK"
        
    def get_target(self) -> float:
        return float(self.write("1,TEMP?").split(",")[1])
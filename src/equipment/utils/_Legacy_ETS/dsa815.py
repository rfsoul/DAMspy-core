#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =============================================================================
# Author            : Andy Wang
# Date              : 24 June 2022
# Python version    : 3.10
# =============================================================================
"""dsa815.py
Interface library for Rigol DSA815 Spectrum Analyzer.

Connection to the instrument via LAN.

    Typical usage example:

    spec_an = SpecAn()
    idn = spec_an.query("*IDN?")
    marker_freq = spec_an.get_marker_freq("M")
    spec_an.set_centre_freq(476e6)
"""

import pyvisa as visa

unit_enum = {
    "G": 1e9,
    "M": 1e6,
    "K": 1e3,
}


class SpecAn():
    """A wrapper class for instrument control."""

    def __init__(self, ip: str = "169.254.185.65"):
        """Inits SpecAn with an IP address."""

        rm = visa.ResourceManager()
        try:
            self.__inst = rm.open_resource(f"TCPIP0::{ip}::INSTR")
        except:
            print("Error opening instrument")

    def write(self, msg: str):
        self.__inst.write(msg)

    def query(self, msg: str) -> str:
        return self.__inst.query(msg)

    def get_marker_freq(self, unit: str = "M") -> float:
        """Gets the current marker frequency.

        Args:
            unit: Unit belonging in unit_enum.

        Returns:
            The marker frequency float value adjusted to unit.
        """

        x = float(self.query("CALC:MARK:X?"))
        if unit in unit_enum:
            x = x/unit_enum[unit]
        return x

    def get_marker_power(self) -> float:
        return float(self.query("CALC:MARK:Y?"))

    def get_centre_freq(self, unit: str = "M"):
        """Gets the current centre frequency.

        Args:
            unit: Unit belonging in unit_enum.

        Returns:
            The centre frequency as a float value adjusted to unit.
        """

        c = float(self.query("FREQ:CENT"))
        if unit in unit_enum:
            c = c/unit_enum[unit]
        return c

    def set_centre_freq(self, freq: int, unit: str = "M"):
        """Sets the centre frequency.

        Args:
            freq: The centre frequency to set to.
            unit: Unit belonging in unit_enum.
        """
        if unit in unit_enum:
            freq = freq * unit_enum[unit]
        self.write(f"FREQ:CENT {freq}")

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =============================================================================
# Author            : Andy Wang
# Date              : 3 June 2022
# Python version    : 3.10
# =============================================================================
"""hm8123freqcounter.py
Interface library for HAMEG HM8123 Frequency Counter.

Connection to the instrument is made via GPIB.
Performance may be affected on Input C if the harmonics of the signal is too high, and may end up displaying the harmonic's frequency due to the low trigger level of Input C (0.02Vp).
Manual (German/English): https://scdn.rohde-schwarz.com/ur/pws/dl_downloads/dl_common_library/dl_manuals/gb_1/h/hm8123_x/HM8123_UserManual_de_en_06.pdf

    Typical usage example:

    freq_counter = FreqCounter()
    idn = freq_counter.query("*IDN?")
    curr_input = freq_counter.get_input()
    freq_counter.set_input("A")
    freq = freq_counter.get_freq()
"""

import pyvisa


class FreqCounter:
    """A wrapper class for instrument control."""

    def __init__(self, instr: int = 15, input: str = "C"):
        self.inst = pyvisa.ResourceManager().open_resource(
            f"GPIB0::{instr}::INSTR")
        self.set_input(input)

    def get_input(self) -> str:
        """Gets the current selected input channel.

        Returns:
            One of Channels A, B or C.
        """
        return self.inst.query("FN?")[2]

    def set_input(self, input: str):
        """Sets the input channel.

        Args:
            input: One of A, B or C.
        """
        self.inst.write(f"FR{input}")

    def get_freq(self) -> float:
        return float(self.inst.query("XMT?"))

    def set_gate_time(self, gate_time: int):
        """Sets the gate time.

        Longer gate times allow higher resolution frequencies (1s gate time = 6 decimal places).

        Args:
            gate_time: The gate time in milliseconds.
        """
        self.inst.write(f"SMT{gate_time}")

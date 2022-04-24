"""Encodes a json representation of the input_str into the 8-bit binary
representation used by the merge overlapping input_str turing machine. It
takes input from stdin and outputs the initial tape."""
import json
import sys

from vim_turing_machine.constants import BITS_PER_NUMBER


def encode_input_str(input_str, num_bits=BITS_PER_NUMBER):
    result = ''
    for char in input_str:
        result += encode_in_x_bits(ord(char), num_bits)
    
    return result


def encode_in_x_bits(number, num_bits):
    encoded = '{:b}'.format(number)
    assert len(encoded) <= num_bits

    # Add leading zeros
    return '0' * (num_bits - len(encoded)) + encoded

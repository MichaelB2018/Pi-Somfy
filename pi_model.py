#!/usr/bin/python3
# Raspberry Pi model detection shared by operateShutters.py and receiver.py.
#
# Pi 5 (and the other BCM2712 boards) route the GPIO header through the RP1
# southbridge, which pigpio cannot drive — those boards need lgpio instead.
# Everything else keeps using pigpio.
#
# Only the standard library is imported here on purpose: receiver.py must stay
# importable on a plain dev machine without ephem/pigpio/lgpio installed.

import os

PI5_MODEL_MARKERS = ("Pi 5", "Compute Module 5")
BCM2712_PROCESSOR_ID = 4  # /proc/cpuinfo revision bits 12-15 for the Pi 5 SoC


def read_device_tree_model():
    """Board name from the device tree, or None when it is not readable.

    Not readable inside containers that do not bind-mount /proc/device-tree.
    """
    try:
        with open('/proc/device-tree/model', 'r') as f:
            return f.read().replace('\x00', '').strip()
    except (FileNotFoundError, PermissionError, OSError):
        return None


def model_is_pi5(model):
    return any(marker in model for marker in PI5_MODEL_MARKERS)


def cpuinfo_is_pi5():
    """True when the /proc/cpuinfo revision code identifies a BCM2712 board.

    Decoding the processor field beats matching a hard-coded list of revision
    codes, which silently misses every board released after it was written.
    """
    try:
        with open('/proc/cpuinfo', 'r') as f:
            for line in f:
                if not line.startswith('Revision'):
                    continue
                revision = int(line.split(':', 1)[1].strip(), 16)
                if not revision & (1 << 23):  # old-style code: pre-Pi 2 board
                    return False
                return ((revision >> 12) & 0xF) == BCM2712_PROCESSOR_ID
    except (FileNotFoundError, PermissionError, OSError, IndexError, ValueError):
        pass
    return False


def has_rp1_gpiochip():
    """True when /dev/gpiochip4 is a real chip of its own (the RP1 on a Pi 5).

    Raspberry Pi OS Bookworm ships a /dev/gpiochip4 compatibility symlink to
    gpiochip0 on older boards, so mere existence proves nothing: a Pi Zero W
    was being detected as a Pi 5 (issue #180). Comparing the device numbers
    tells a genuine second chip apart from an alias of the first one.
    """
    try:
        rp1 = os.stat('/dev/gpiochip4')
    except OSError:
        return False
    try:
        soc = os.stat('/dev/gpiochip0')
    except OSError:
        return True
    return rp1.st_rdev != soc.st_rdev


def detect_pi5():
    model = read_device_tree_model()
    if model:
        # The device tree knows exactly which board this is — trust it and do
        # not let the weaker heuristics below override it.
        return model_is_pi5(model)
    if cpuinfo_is_pi5():
        return True
    return has_rp1_gpiochip()

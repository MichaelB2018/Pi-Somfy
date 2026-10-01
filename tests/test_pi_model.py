import unittest
from unittest import mock

import pi_model


class FakeStat:
    def __init__(self, st_rdev):
        self.st_rdev = st_rdev


class ModelMarkerTest(unittest.TestCase):
    def test_pi5_boards_are_recognised(self):
        self.assertTrue(pi_model.model_is_pi5("Raspberry Pi 5 Model B Rev 1.0"))
        self.assertTrue(pi_model.model_is_pi5("Raspberry Pi Compute Module 5 Rev 1.0"))

    def test_older_boards_are_not_pi5(self):
        self.assertFalse(pi_model.model_is_pi5("Raspberry Pi Zero W Rev 1.1"))
        self.assertFalse(pi_model.model_is_pi5("Raspberry Pi 4 Model B Rev 1.4"))


class CpuinfoRevisionTest(unittest.TestCase):
    def _cpuinfo(self, revision):
        return mock.mock_open(read_data="Hardware\t: BCM2835\nRevision\t: {}\n".format(revision))

    def test_bcm2712_revision_is_pi5(self):
        with mock.patch("builtins.open", self._cpuinfo("c04170")):
            self.assertTrue(pi_model.cpuinfo_is_pi5())

    def test_pi4_revision_is_not_pi5(self):
        with mock.patch("builtins.open", self._cpuinfo("c03111")):
            self.assertFalse(pi_model.cpuinfo_is_pi5())

    def test_pi_zero_w_revision_is_not_pi5(self):
        with mock.patch("builtins.open", self._cpuinfo("9000c1")):
            self.assertFalse(pi_model.cpuinfo_is_pi5())

    def test_old_style_revision_is_not_pi5(self):
        with mock.patch("builtins.open", self._cpuinfo("000e")):
            self.assertFalse(pi_model.cpuinfo_is_pi5())


class Rp1GpiochipTest(unittest.TestCase):
    def test_gpiochip4_symlinked_to_gpiochip0_is_not_rp1(self):
        with mock.patch.object(pi_model.os, "stat", return_value=FakeStat(0x100)):
            self.assertFalse(pi_model.has_rp1_gpiochip())

    def test_separate_gpiochip4_is_rp1(self):
        stats = {"/dev/gpiochip0": FakeStat(0x100), "/dev/gpiochip4": FakeStat(0x104)}
        with mock.patch.object(pi_model.os, "stat", side_effect=lambda path: stats[path]):
            self.assertTrue(pi_model.has_rp1_gpiochip())

    def test_missing_gpiochip4_is_not_rp1(self):
        with mock.patch.object(pi_model.os, "stat", side_effect=OSError):
            self.assertFalse(pi_model.has_rp1_gpiochip())


class DetectPi5Test(unittest.TestCase):
    def test_device_tree_model_overrides_gpiochip_heuristic(self):
        # Issue #180: Bookworm on a Pi Zero W ships /dev/gpiochip4 -> gpiochip0.
        with mock.patch.object(pi_model, "read_device_tree_model", return_value="Raspberry Pi Zero W Rev 1.1"), \
             mock.patch.object(pi_model, "has_rp1_gpiochip", return_value=True), \
             mock.patch.object(pi_model, "cpuinfo_is_pi5", return_value=True):
            self.assertFalse(pi_model.detect_pi5())

    def test_device_tree_model_identifies_pi5(self):
        with mock.patch.object(pi_model, "read_device_tree_model", return_value="Raspberry Pi 5 Model B Rev 1.0"):
            self.assertTrue(pi_model.detect_pi5())

    def test_falls_back_to_cpuinfo_without_device_tree(self):
        with mock.patch.object(pi_model, "read_device_tree_model", return_value=None), \
             mock.patch.object(pi_model, "cpuinfo_is_pi5", return_value=True):
            self.assertTrue(pi_model.detect_pi5())

    def test_falls_back_to_rp1_gpiochip_without_device_tree_or_cpuinfo(self):
        with mock.patch.object(pi_model, "read_device_tree_model", return_value=None), \
             mock.patch.object(pi_model, "cpuinfo_is_pi5", return_value=False), \
             mock.patch.object(pi_model, "has_rp1_gpiochip", return_value=True):
            self.assertTrue(pi_model.detect_pi5())

    def test_plain_container_is_not_pi5(self):
        with mock.patch.object(pi_model, "read_device_tree_model", return_value=None), \
             mock.patch.object(pi_model, "cpuinfo_is_pi5", return_value=False), \
             mock.patch.object(pi_model, "has_rp1_gpiochip", return_value=False):
            self.assertFalse(pi_model.detect_pi5())


if __name__ == "__main__":
    unittest.main()

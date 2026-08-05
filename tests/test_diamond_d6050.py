import importlib.util
import os
import unittest
from unittest import mock


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODULE_PATH = os.path.join(
    REPO_ROOT,
    "src",
    "equipment",
    "positioner",
    "Diamond_D6050.py",
)


spec = importlib.util.spec_from_file_location("diamond_d6050", MODULE_PATH)
diamond_d6050 = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(diamond_d6050)


class _FakeClock:
    def __init__(self):
        self.now = 0.0

    def monotonic(self):
        self.now += 0.25
        return self.now

    def sleep(self, seconds):
        self.now += float(seconds)


class DiamondD6050WaitUntilStoppedTests(unittest.TestCase):
    def _make_driver(self):
        driver = object.__new__(diamond_d6050.DiamondD6050)
        driver.az_axis = "Y"
        driver.el_axis = "X"
        driver.az_steps_per_deg = 800
        driver.el_steps_per_deg = 320
        driver.verbose_logging = False
        return driver

    def test_wait_until_stopped_raises_when_encoder_reads_keep_failing(self):
        driver = self._make_driver()
        clock = _FakeClock()

        driver.get_current_axis_deg = mock.Mock(return_value=None)

        with mock.patch.object(diamond_d6050.time, "monotonic", side_effect=clock.monotonic), \
             mock.patch.object(diamond_d6050.time, "sleep", side_effect=clock.sleep):
            with self.assertRaisesRegex(
                diamond_d6050.PositionerMotionError,
                "AZ encoder read timed out while waiting for motion",
            ):
                driver.wait_until_stopped(
                    "azimuth",
                    initial_angle_deg=0.0,
                    requested_deg=170.0,
                    encoder_read_timeout_s=1.0,
                    no_motion_timeout_s=1.0,
                )

    def test_wait_until_stopped_raises_when_encoder_never_moves(self):
        driver = self._make_driver()
        clock = _FakeClock()

        driver.get_current_axis_deg = mock.Mock(return_value=0.0)

        with mock.patch.object(diamond_d6050.time, "monotonic", side_effect=clock.monotonic), \
             mock.patch.object(diamond_d6050.time, "sleep", side_effect=clock.sleep):
            with self.assertRaisesRegex(
                diamond_d6050.PositionerMotionError,
                "AZ move command was accepted but no encoder motion was detected",
            ):
                driver.wait_until_stopped(
                    "azimuth",
                    initial_angle_deg=0.0,
                    requested_deg=170.0,
                    encoder_read_timeout_s=1.0,
                    no_motion_timeout_s=1.0,
                )

    def test_wait_until_stopped_returns_after_motion_and_stable_settle(self):
        driver = self._make_driver()
        clock = _FakeClock()

        driver.get_current_axis_deg = mock.Mock(
            side_effect=[0.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0]
        )

        with mock.patch.object(diamond_d6050.time, "monotonic", side_effect=clock.monotonic), \
             mock.patch.object(diamond_d6050.time, "sleep", side_effect=clock.sleep):
            final = driver.wait_until_stopped(
                "azimuth",
                initial_angle_deg=0.0,
                requested_deg=170.0,
                encoder_read_timeout_s=1.0,
                no_motion_timeout_s=1.0,
            )

        self.assertEqual(final, 1.0)

    def test_wait_until_stopped_accepts_tiny_motion_when_requested_move_is_tiny(self):
        driver = self._make_driver()
        clock = _FakeClock()

        driver.get_current_axis_deg = mock.Mock(
            side_effect=[0.0, 0.0125, 0.0125, 0.0125, 0.0125, 0.0125, 0.0125, 0.0125]
        )

        with mock.patch.object(diamond_d6050.time, "monotonic", side_effect=clock.monotonic), \
             mock.patch.object(diamond_d6050.time, "sleep", side_effect=clock.sleep):
            final = driver.wait_until_stopped(
                "azimuth",
                initial_angle_deg=0.0,
                requested_deg=0.0125,
                encoder_read_timeout_s=1.0,
                no_motion_timeout_s=1.0,
            )

        self.assertEqual(final, 0.0125)


if __name__ == "__main__":
    unittest.main()

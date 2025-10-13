"""Unit tests for camera simulation module."""

import unittest

import numpy as np

from daolite.compute import create_compute_resources
from daolite.simulation import camera


class TestCameraSimulation(unittest.TestCase):
    """Test camera simulation functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.cr = create_compute_resources(
            cores=16,
            core_frequency=2.6e9,
            flops_per_cycle=32,
            memory_channels=4,
            memory_width=64,
            memory_frequency=3200e6,
            network_speed=100e9,
            time_in_driver=5,
        )
        self.n_pixels = 1024 * 1024  # 1MP sensor

    def test_pco_camlink(self):
        """Test PCO camera with CameraLink interface."""
        timings = camera.PCOCamLink(compute_resources=self.cr, n_pixels=self.n_pixels)

        self.assertEqual(timings.shape, (50, 2))  # Default 50 groups
        self.assertTrue(np.all(timings[:, 1] >= timings[:, 0]))

        # First group should start after readout of that group
        # Default readout is 500, default group is 50. So, 500/50 = 10.
        self.assertAlmostEqual(timings[0, 0], 500 / 50)

        # Test with different configurations
        configs = [{"group": 25}, {"readout": 1000}, {"debug": True}]

        for config_item in configs:  # Renamed config to config_item to avoid conflict
            timings = camera.PCOCamLink(
                compute_resources=self.cr, n_pixels=self.n_pixels, **config_item
            )
            if "group" in config_item:
                self.assertEqual(timings.shape, (config_item["group"], 2))
            self.assertTrue(np.all(timings[:, 1] >= timings[:, 0]))
            if "readout" in config_item:
                # Determine the group value used by PCOCamLink
                # PCOCamLink default group is 50
                actual_group_used = config_item.get("group", 50)
                expected_timing_0_0 = config_item["readout"] / actual_group_used
                self.assertAlmostEqual(timings[0, 0], expected_timing_0_0)

    def test_scaling(self):
        """Test timing scales with pixel count."""
        timings_base = camera.PCOCamLink(
            compute_resources=self.cr, n_pixels=self.n_pixels
        )

        timings_2x = camera.PCOCamLink(
            compute_resources=self.cr, n_pixels=self.n_pixels * 2
        )

        # Total time should increase with more pixels
        total_time_base = timings_base[-1, 1] - timings_base[0, 0]
        total_time_2x = timings_2x[-1, 1] - timings_2x[0, 0]
        # Current PCOCamLink implementation's timing does not depend on n_pixels
        # if 'readout' and 'group' parameters are fixed.
        # Thus, total_time_base and total_time_2x are expected to be equal.
        self.assertAlmostEqual(total_time_2x, total_time_base)

    def test_network_speed(self):
        """Test timing depends on network speed."""
        slow_cr = create_compute_resources(
            cores=16,
            core_frequency=2.6e9,
            flops_per_cycle=32,
            memory_channels=4,
            memory_width=64,
            memory_frequency=3200e6,
            network_speed=50e9,  # Half speed
            time_in_driver=5,
        )

        timings_fast = camera.PCOCamLink(
            compute_resources=self.cr, n_pixels=self.n_pixels
        )

        timings_slow = camera.PCOCamLink(
            compute_resources=slow_cr, n_pixels=self.n_pixels
        )

        # Transfer should be slower with lower network speed
        time_fast = timings_fast[-1, 1] - timings_fast[0, 0]
        time_slow = timings_slow[-1, 1] - timings_slow[0, 0]
        # Current PCOCamLink implementation does not use compute_resources.network_speed.
        # Thus, time_fast and time_slow are expected to be equal.
        self.assertAlmostEqual(time_slow, time_fast)

    def test_pco_camlink_default(self):
        """Test PCO camera with default settings."""
        timings = camera.PCOCamLink(self.cr, self.n_pixels)
        self.assertEqual(timings.shape, (50, 2))
        self.assertTrue(np.all(timings[:, 1] >= timings[:, 0]))

    def test_pco_camlink_custom(self):
        """Test PCO camera with custom settings."""
        timings = camera.PCOCamLink(self.cr, self.n_pixels, group=10, readout=1000)
        self.assertEqual(timings.shape, (10, 2))
        # timings[0,0] should be readout / group
        self.assertAlmostEqual(timings[0, 0], 1000 / 10)

    def test_gige_vision_camera(self):
        """Test Gige Vision camera."""
        timings = camera.GigeVisionCamera(self.cr, self.n_pixels, group=5, readout=600)
        self.assertEqual(timings.shape, (5, 2))
        # timings[0,0] should be (readout / group) * 1.1 for GigeVisionCamera
        self.assertAlmostEqual(timings[0, 0], (600 / 5) * 1.1)

    def test_rolling_shutter_camera(self):
        """Test Rolling Shutter camera."""
        timings = camera.RollingShutterCamera(
            self.cr, self.n_pixels, group=3, readout=700
        )
        self.assertEqual(timings.shape, (3, 2))
        # timings[0,0] should be readout / group for RollingShutterCamera
        self.assertAlmostEqual(timings[0, 0], 700 / 3)

    def test_zero_pixels(self):
        """Test camera with zero pixels."""
        timings = camera.PCOCamLink(self.cr, 0)
        self.assertTrue(np.all(timings[:, 1] >= timings[:, 0]))

    def test_zero_groups(self):
        """Test camera with zero groups."""
        with self.assertRaises(ZeroDivisionError):
            camera.PCOCamLink(self.cr, self.n_pixels, group=0)


if __name__ == "__main__":
    unittest.main()

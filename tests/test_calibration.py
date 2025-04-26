"""Unit tests for pixel calibration module."""

import unittest
import numpy as np
from daolite.compute import create_compute_resources
from daolite.pipeline.calibration import (
    PixelCalibration,
    _calibration_flops,
    _calibration_mem,
)


class TestCalibration(unittest.TestCase):
    """Test pixel calibration functionality."""

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
        self.start_times = np.zeros([50, 2])
        for i in range(50):
            self.start_times[i, 0] = i * 10
            self.start_times[i, 1] = i * 10 + 5

    def test_calibration_calculations(self):
        """Test basic calibration timing calculations."""
        # Test FLOPS calculation
        flops = _calibration_flops(self.n_pixels)
        self.assertEqual(flops, 3 * self.n_pixels)

        # Test memory calculation
        mem_ops = _calibration_mem(self.n_pixels)
        self.assertEqual(mem_ops, 4 * self.n_pixels)

    def test_pixel_calibration(self):
        """Test full pixel calibration pipeline."""
        timings = PixelCalibration(
            n_pixels=self.n_pixels,
            compute_resources=self.cr,
            start_times=self.start_times,
        )

        self.assertEqual(timings.shape, (50, 2))
        self.assertTrue(np.all(timings[:, 1] >= timings[:, 0]))

        # First calibration should start after first input
        self.assertEqual(timings[0, 0], self.start_times[0, 1])

        # Test with different configurations
        configs = [{"group": 25}, {"scale": 2.0}, {"debug": True}]

        for config in configs:
            timings = PixelCalibration(
                n_pixels=self.n_pixels,
                compute_resources=self.cr,
                start_times=self.start_times,
                **config
            )
            self.assertEqual(timings.shape, (50, 2))
            self.assertTrue(np.all(timings[:, 1] >= timings[:, 0]))

    def test_scaling(self):
        """Test timing scales with pixel count."""
        timings_base = PixelCalibration(
            n_pixels=self.n_pixels,
            compute_resources=self.cr,
            start_times=self.start_times,
        )

        timings_2x = PixelCalibration(
            n_pixels=self.n_pixels * 2,
            compute_resources=self.cr,
            start_times=self.start_times,
        )

        # Total time should increase with more pixels
        total_time_base = timings_base[-1, 1] - timings_base[0, 0]
        total_time_2x = timings_2x[-1, 1] - timings_2x[0, 0]
        self.assertGreater(total_time_2x, total_time_base)

    def test_timing_dependencies(self):
        """Test calibration timing dependencies."""
        # Create input times with gaps
        irregular_times = np.zeros([50, 2])
        for i in range(50):
            irregular_times[i, 0] = i * 20  # Larger gaps
            irregular_times[i, 1] = i * 20 + 5

        timings = PixelCalibration(
            n_pixels=self.n_pixels,
            compute_resources=self.cr,
            start_times=irregular_times,
        )

        # Each calibration should start after its input
        for i in range(50):
            self.assertGreaterEqual(timings[i, 0], irregular_times[i, 1])

        # Each calibration should finish before next one starts
        for i in range(1, 50):
            self.assertLessEqual(timings[i - 1, 1], timings[i, 0])

    def test_computation_scaling(self):
        """Test computation time scaling."""
        timings_base = PixelCalibration(
            n_pixels=self.n_pixels,
            compute_resources=self.cr,
            start_times=self.start_times,
            scale=1.0,
        )

        timings_fast = PixelCalibration(
            n_pixels=self.n_pixels,
            compute_resources=self.cr,
            start_times=self.start_times,
            scale=2.0,
        )

        # Processing time should scale inversely with scale factor
        time_base = timings_base[0, 1] - timings_base[0, 0]
        time_fast = timings_fast[0, 1] - timings_fast[0, 0]
        self.assertAlmostEqual(time_fast * 2, time_base)


if __name__ == "__main__":
    unittest.main()

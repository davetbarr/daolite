"""Unit tests for pixel calibration module."""

import unittest
import numpy as np
from daolite.compute import create_compute_resources
from daolite.pipeline.calibration import PixelCalibration
from daolite.utils.algorithm_ops import _calibration_flops, _calibration_mem


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
        self.assertEqual(flops, 2 * self.n_pixels)

        # Test memory calculation
        mem_ops = _calibration_mem(self.n_pixels, bit_depth=16)
        expected_mem_ops = (16 * self.n_pixels) + (3 * self.n_pixels * 32)
        self.assertEqual(mem_ops, expected_mem_ops)

    def test_pixel_calibration(self):
        """Test full pixel calibration pipeline."""
        # Create pixel agenda - same number of pixels per iteration
        pixel_agenda = np.ones(50, dtype=int) * self.n_pixels
        
        timings = PixelCalibration(
            compute_resources=self.cr,
            start_times=self.start_times,
            pixel_agenda=pixel_agenda,
        )

        self.assertEqual(timings.shape, (50, 2))
        self.assertTrue(np.all(timings[:, 1] >= timings[:, 0]))

        # First calibration should start after first input
        self.assertEqual(timings[0, 0], self.start_times[0, 1])

        # Test with different configurations
        configs = [{"debug": True}, {"flop_scale": 2.0}]

        for config in configs:
            timings = PixelCalibration(
                compute_resources=self.cr,
                start_times=self.start_times,
                pixel_agenda=pixel_agenda,
                **config
            )
            self.assertEqual(timings.shape, (50, 2))
            self.assertTrue(np.all(timings[:, 1] >= timings[:, 0]))

    def test_scaling(self):
        """Test timing scales with pixel count."""
        pixel_agenda_base = np.ones(50, dtype=int) * self.n_pixels
        pixel_agenda_2x = np.ones(50, dtype=int) * (self.n_pixels * 2)
        
        timings_base = PixelCalibration(
            compute_resources=self.cr,
            start_times=self.start_times,
            pixel_agenda=pixel_agenda_base,
        )

        timings_2x = PixelCalibration(
            compute_resources=self.cr,
            start_times=self.start_times,
            pixel_agenda=pixel_agenda_2x,
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

        pixel_agenda = np.ones(50, dtype=int) * self.n_pixels
        
        timings = PixelCalibration(
            compute_resources=self.cr,
            start_times=irregular_times,
            pixel_agenda=pixel_agenda,
        )

        # Each calibration should start after its input
        for i in range(50):
            self.assertGreaterEqual(timings[i, 0], irregular_times[i, 1])

        # Each calibration should finish before next one starts
        for i in range(1, 50):
            self.assertLessEqual(timings[i - 1, 1], timings[i, 0])

    def test_computation_scaling(self):
        """Test computation time scaling."""
        pixel_agenda = np.ones(50, dtype=int) * self.n_pixels
        
        timings_base = PixelCalibration(
            compute_resources=self.cr,
            start_times=self.start_times,
            pixel_agenda=pixel_agenda,
        )

        timings_fast = PixelCalibration(
            compute_resources=self.cr,
            start_times=self.start_times,
            pixel_agenda=pixel_agenda,
            flop_scale=2.0,
            mem_scale=2.0,
        )

        # Processing time should scale inversely with scale factor
        time_base = timings_base[0, 1] - timings_base[0, 0]
        time_fast = timings_fast[0, 1] - timings_fast[0, 0]
        # With both scales=2.0, time should be approximately half
        self.assertAlmostEqual(time_fast * 2, time_base, places=1)


if __name__ == "__main__":
    unittest.main()

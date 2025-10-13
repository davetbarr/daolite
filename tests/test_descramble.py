"""Unit tests for descramble module."""

import unittest
import numpy as np
from daolite.compute import create_compute_resources
from daolite.pipeline.descramble import Descramble
from daolite.utils.algorithm_ops import _calibration_flops, _calibration_mem


class TestDescramble(unittest.TestCase):
    """Test descramble module functionality."""

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

    def test_descramble_basic(self):
        """Test basic descramble timing calculation."""
        pixel_agenda = np.ones(50, dtype=int) * self.n_pixels
        
        timings = Descramble(
            compute_resources=self.cr,
            start_times=self.start_times,
            pixel_agenda=pixel_agenda,
        )

        self.assertEqual(timings.shape, (50, 2))
        self.assertTrue(np.all(timings[:, 1] >= timings[:, 0]))
        self.assertGreater(timings[0, 1], timings[0, 0])

    def test_descramble_timing_dependencies(self):
        """Test that descramble timing follows dependencies."""
        pixel_agenda = np.ones(50, dtype=int) * self.n_pixels
        
        timings = Descramble(
            compute_resources=self.cr,
            start_times=self.start_times,
            pixel_agenda=pixel_agenda,
        )

        # First descramble should start after first input
        self.assertEqual(timings[0, 0], self.start_times[0, 1])

        # Each descramble should finish before next one starts
        for i in range(1, 50):
            self.assertLessEqual(timings[i - 1, 1], timings[i, 0])

    def test_descramble_bit_depth(self):
        """Test descramble with different bit depths."""
        pixel_agenda = np.ones(50, dtype=int) * self.n_pixels
        
        bit_depths = [8, 12, 14, 16]
        timings_list = []
        
        for bit_depth in bit_depths:
            timings = Descramble(
                compute_resources=self.cr,
                start_times=self.start_times,
                pixel_agenda=pixel_agenda,
                bitDepth=bit_depth,
            )
            timings_list.append(timings)
            self.assertEqual(timings.shape, (50, 2))
            self.assertTrue(np.all(timings[:, 1] >= timings[:, 0]))
        
        # All should produce valid results
        for timings in timings_list:
            self.assertGreater(timings[0, 1], timings[0, 0])

    def test_descramble_with_workers(self):
        """Test descramble with multiple workers."""
        pixel_agenda = np.ones(50, dtype=int) * self.n_pixels
        
        n_workers_list = [1, 2, 4, 8]
        
        for n_workers in n_workers_list:
            timings = Descramble(
                compute_resources=self.cr,
                start_times=self.start_times,
                pixel_agenda=pixel_agenda,
                nWorkers=n_workers,
            )
            self.assertEqual(timings.shape, (50, 2))
            self.assertTrue(np.all(timings[:, 1] >= timings[:, 0]))

    def test_descramble_scaling_factors(self):
        """Test descramble with computation scaling factors."""
        pixel_agenda = np.ones(50, dtype=int) * self.n_pixels
        
        timings_base = Descramble(
            compute_resources=self.cr,
            start_times=self.start_times,
            pixel_agenda=pixel_agenda,
        )
        
        timings_fast = Descramble(
            compute_resources=self.cr,
            start_times=self.start_times,
            pixel_agenda=pixel_agenda,
            flop_scale=2.0,
            mem_scale=2.0,
        )

        # With scaling, time should be reduced
        time_base = timings_base[0, 1] - timings_base[0, 0]
        time_fast = timings_fast[0, 1] - timings_fast[0, 0]
        self.assertLess(time_fast, time_base)
        # Should be approximately half
        self.assertAlmostEqual(time_fast * 2, time_base, places=1)

    def test_descramble_pixel_scaling(self):
        """Test that timing scales with pixel count."""
        small_agenda = np.ones(50, dtype=int) * (self.n_pixels // 2)
        large_agenda = np.ones(50, dtype=int) * (self.n_pixels * 2)
        
        timings_small = Descramble(
            compute_resources=self.cr,
            start_times=self.start_times,
            pixel_agenda=small_agenda,
        )
        
        timings_large = Descramble(
            compute_resources=self.cr,
            start_times=self.start_times,
            pixel_agenda=large_agenda,
        )

        # More pixels should take more time
        time_small = timings_small[0, 1] - timings_small[0, 0]
        time_large = timings_large[0, 1] - timings_large[0, 0]
        self.assertGreater(time_large, time_small)

    def test_descramble_variable_agenda(self):
        """Test descramble with variable pixel agenda."""
        # Variable number of pixels per iteration
        pixel_agenda = np.random.randint(100000, 2000000, size=50)
        
        timings = Descramble(
            compute_resources=self.cr,
            start_times=self.start_times,
            pixel_agenda=pixel_agenda,
        )

        self.assertEqual(timings.shape, (50, 2))
        self.assertTrue(np.all(timings[:, 1] >= timings[:, 0]))
        
        # Each iteration should process correctly
        for i in range(50):
            self.assertGreater(timings[i, 1], timings[i, 0])

    def test_descramble_irregular_start_times(self):
        """Test descramble with irregular start times."""
        irregular_times = np.zeros([50, 2])
        for i in range(50):
            irregular_times[i, 0] = i * 20 + np.random.randint(0, 5)
            irregular_times[i, 1] = irregular_times[i, 0] + 5 + np.random.randint(0, 3)
        
        pixel_agenda = np.ones(50, dtype=int) * self.n_pixels
        
        timings = Descramble(
            compute_resources=self.cr,
            start_times=irregular_times,
            pixel_agenda=pixel_agenda,
        )

        # Each descramble should start after its input
        for i in range(50):
            self.assertGreaterEqual(timings[i, 0], irregular_times[i, 1])

    def test_descramble_debug_mode(self):
        """Test descramble with debug output enabled."""
        pixel_agenda = np.ones(10, dtype=int) * self.n_pixels
        start_times = np.zeros([10, 2])
        for i in range(10):
            start_times[i, 0] = i * 10
            start_times[i, 1] = i * 10 + 5
        
        # Should not raise any errors with debug=True
        timings = Descramble(
            compute_resources=self.cr,
            start_times=start_times,
            pixel_agenda=pixel_agenda,
            debug=True,
        )
        
        self.assertEqual(timings.shape, (10, 2))
        self.assertTrue(np.all(timings[:, 1] >= timings[:, 0]))

    def test_descramble_single_iteration(self):
        """Test descramble with single iteration."""
        start_times = np.zeros([1, 2])
        start_times[0, 0] = 0
        start_times[0, 1] = 5
        pixel_agenda = np.array([self.n_pixels], dtype=int)
        
        timings = Descramble(
            compute_resources=self.cr,
            start_times=start_times,
            pixel_agenda=pixel_agenda,
        )
        
        self.assertEqual(timings.shape, (1, 2))
        self.assertGreater(timings[0, 1], timings[0, 0])
        self.assertEqual(timings[0, 0], start_times[0, 1])

    def test_descramble_consistency(self):
        """Test that descramble produces consistent results."""
        pixel_agenda = np.ones(50, dtype=int) * self.n_pixels
        
        # Run twice with same parameters
        timings1 = Descramble(
            compute_resources=self.cr,
            start_times=self.start_times,
            pixel_agenda=pixel_agenda,
        )
        
        timings2 = Descramble(
            compute_resources=self.cr,
            start_times=self.start_times,
            pixel_agenda=pixel_agenda,
        )

        # Results should be identical
        np.testing.assert_array_equal(timings1, timings2)

    def test_descramble_small_pixels(self):
        """Test descramble with small pixel count."""
        pixel_agenda = np.ones(50, dtype=int) * 1000  # Just 1000 pixels
        
        timings = Descramble(
            compute_resources=self.cr,
            start_times=self.start_times,
            pixel_agenda=pixel_agenda,
        )
        
        self.assertEqual(timings.shape, (50, 2))
        self.assertTrue(np.all(timings[:, 1] >= timings[:, 0]))

    def test_descramble_large_pixels(self):
        """Test descramble with large pixel count."""
        pixel_agenda = np.ones(50, dtype=int) * (4096 * 4096)  # 16MP sensor
        
        timings = Descramble(
            compute_resources=self.cr,
            start_times=self.start_times,
            pixel_agenda=pixel_agenda,
        )
        
        self.assertEqual(timings.shape, (50, 2))
        self.assertTrue(np.all(timings[:, 1] >= timings[:, 0]))

    def test_calibration_helper_functions(self):
        """Test calibration helper functions used by descramble."""
        # Test FLOPS calculation
        flops = _calibration_flops(self.n_pixels)
        self.assertEqual(flops, 2 * self.n_pixels)
        self.assertGreater(flops, 0)

        # Test memory calculation
        bit_depths = [8, 12, 14, 16]
        for bit_depth in bit_depths:
            mem_ops = _calibration_mem(self.n_pixels, bit_depth=bit_depth)
            expected_mem_ops = (bit_depth * self.n_pixels) + (3 * self.n_pixels * 32)
            self.assertEqual(mem_ops, expected_mem_ops)
            self.assertGreater(mem_ops, 0)

    def test_descramble_combined_parameters(self):
        """Test descramble with various parameter combinations."""
        pixel_agenda = np.ones(20, dtype=int) * self.n_pixels
        start_times = np.zeros([20, 2])
        for i in range(20):
            start_times[i, 0] = i * 10
            start_times[i, 1] = i * 10 + 5
        
        # Test various combinations
        configs = [
            {"bitDepth": 8, "nWorkers": 2},
            {"bitDepth": 12, "nWorkers": 4, "flop_scale": 1.5},
            {"bitDepth": 16, "mem_scale": 2.0},
            {"nWorkers": 8, "flop_scale": 2.0, "mem_scale": 2.0},
        ]
        
        for config in configs:
            timings = Descramble(
                compute_resources=self.cr,
                start_times=start_times,
                pixel_agenda=pixel_agenda,
                **config
            )
            self.assertEqual(timings.shape, (20, 2))
            self.assertTrue(np.all(timings[:, 1] >= timings[:, 0]))

    def test_descramble_sequential_processing(self):
        """Test that descramble processes sequentially."""
        pixel_agenda = np.ones(10, dtype=int) * self.n_pixels
        start_times = np.zeros([10, 2])
        for i in range(10):
            start_times[i, 0] = i * 10
            start_times[i, 1] = i * 10 + 5
        
        timings = Descramble(
            compute_resources=self.cr,
            start_times=start_times,
            pixel_agenda=pixel_agenda,
        )

        # Verify sequential processing: each iteration starts after previous ends
        for i in range(1, 10):
            # Current iteration should start at or after previous iteration ends
            self.assertGreaterEqual(timings[i, 0], timings[i - 1, 1])
            # Current iteration should also start at or after its input is ready
            self.assertGreaterEqual(timings[i, 0], start_times[i, 1])

    def test_descramble_total_time_calculation(self):
        """Test total descramble time calculation."""
        pixel_agenda = np.ones(50, dtype=int) * self.n_pixels
        
        timings = Descramble(
            compute_resources=self.cr,
            start_times=self.start_times,
            pixel_agenda=pixel_agenda,
        )

        # Calculate total time
        total_time = timings[-1, 1] - timings[0, 0]
        self.assertGreater(total_time, 0)
        
        # Total time should be reasonable (not negative or zero)
        self.assertTrue(np.isfinite(total_time))


if __name__ == "__main__":
    unittest.main()

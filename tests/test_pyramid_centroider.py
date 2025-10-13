"""Unit tests for pyramid centroider module."""

import unittest

import numpy as np

from daolite.compute import create_compute_resources
from daolite.pipeline.pyramid_centroider import PyramidCentroider


class TestPyramidCentroider(unittest.TestCase):
    """Test pyramid centroider module functionality."""

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
        self.n_subaps = 80 * 80

    def test_pyramid_intensity_mode(self):
        """Test pyramid centroider in intensity mode."""
        start_times = np.zeros([50, 2])
        centroid_agenda = np.ones(50, dtype=int) * self.n_subaps

        timings = PyramidCentroider(
            compute_resources=self.cr,
            start_times=start_times,
            centroid_agenda=centroid_agenda,
            mode="intensity",
        )

        self.assertEqual(timings.shape, (50, 2))
        self.assertTrue(np.all(timings[:, 1] >= timings[:, 0]))
        self.assertGreater(timings[0, 1], timings[0, 0])

    def test_pyramid_slopes_mode(self):
        """Test pyramid centroider in slopes mode (default)."""
        start_times = np.zeros([50, 2])
        centroid_agenda = np.ones(50, dtype=int) * self.n_subaps

        timings = PyramidCentroider(
            compute_resources=self.cr,
            start_times=start_times,
            centroid_agenda=centroid_agenda,
            mode="slopes",
        )

        self.assertEqual(timings.shape, (50, 2))
        self.assertTrue(np.all(timings[:, 1] >= timings[:, 0]))
        self.assertGreater(timings[0, 1], timings[0, 0])

    def test_pyramid_esc_mode(self):
        """Test pyramid centroider in ESC mode."""
        start_times = np.zeros([50, 2])
        centroid_agenda = np.ones(50, dtype=int) * self.n_subaps

        timings = PyramidCentroider(
            compute_resources=self.cr,
            start_times=start_times,
            centroid_agenda=centroid_agenda,
            mode="ESC",
        )

        self.assertEqual(timings.shape, (50, 2))
        self.assertTrue(np.all(timings[:, 1] >= timings[:, 0]))
        self.assertGreater(timings[0, 1], timings[0, 0])

    def test_pyramid_default_mode(self):
        """Test pyramid centroider with default mode (slopes)."""
        start_times = np.zeros([50, 2])
        centroid_agenda = np.ones(50, dtype=int) * self.n_subaps

        timings_default = PyramidCentroider(
            compute_resources=self.cr,
            start_times=start_times,
            centroid_agenda=centroid_agenda,
        )

        timings_slopes = PyramidCentroider(
            compute_resources=self.cr,
            start_times=start_times,
            centroid_agenda=centroid_agenda,
            mode="slopes",
        )

        # Default should be same as slopes mode
        np.testing.assert_array_almost_equal(timings_default, timings_slopes)

    def test_pyramid_mode_timing_differences(self):
        """Test that different modes produce different timings."""
        start_times = np.zeros([50, 2])
        centroid_agenda = np.ones(50, dtype=int) * self.n_subaps

        timings_intensity = PyramidCentroider(
            compute_resources=self.cr,
            start_times=start_times,
            centroid_agenda=centroid_agenda,
            mode="intensity",
        )

        timings_slopes = PyramidCentroider(
            compute_resources=self.cr,
            start_times=start_times,
            centroid_agenda=centroid_agenda,
            mode="slopes",
        )

        timings_esc = PyramidCentroider(
            compute_resources=self.cr,
            start_times=start_times,
            centroid_agenda=centroid_agenda,
            mode="ESC",
        )

        # Different modes should produce different timings
        # ESC mode is typically more computationally expensive
        time_intensity = timings_intensity[0, 1] - timings_intensity[0, 0]
        time_slopes = timings_slopes[0, 1] - timings_slopes[0, 0]
        time_esc = timings_esc[0, 1] - timings_esc[0, 0]

        # All should be positive
        self.assertGreater(time_intensity, 0)
        self.assertGreater(time_slopes, 0)
        self.assertGreater(time_esc, 0)

        # ESC should be most expensive
        self.assertGreater(time_esc, time_intensity)
        self.assertGreater(time_esc, time_slopes)

    def test_pyramid_invalid_mode(self):
        """Test that invalid mode raises ValueError."""
        start_times = np.zeros([50, 2])
        centroid_agenda = np.ones(50, dtype=int) * self.n_subaps

        with self.assertRaises(ValueError):
            PyramidCentroider(
                compute_resources=self.cr,
                start_times=start_times,
                centroid_agenda=centroid_agenda,
                mode="invalid_mode",
            )

    def test_pyramid_with_workers(self):
        """Test pyramid centroider with multiple workers."""
        start_times = np.zeros([50, 2])
        centroid_agenda = np.ones(50, dtype=int) * self.n_subaps

        n_workers_list = [1, 2, 4]

        for n_workers in n_workers_list:
            for mode in ["intensity", "slopes", "ESC"]:
                timings = PyramidCentroider(
                    compute_resources=self.cr,
                    start_times=start_times,
                    centroid_agenda=centroid_agenda,
                    mode=mode,
                    n_workers=n_workers,
                )
                self.assertEqual(timings.shape, (50, 2))
                self.assertTrue(np.all(timings[:, 1] >= timings[:, 0]))

    def test_pyramid_with_delay_start(self):
        """Test pyramid centroider with delayed start."""
        start_times = np.zeros([50, 2])
        centroid_agenda = np.ones(50, dtype=int) * self.n_subaps

        timings = PyramidCentroider(
            compute_resources=self.cr,
            start_times=start_times,
            centroid_agenda=centroid_agenda,
            mode="slopes",
            delay_start=5,
        )

        self.assertEqual(timings.shape, (50, 2))
        self.assertTrue(np.all(timings[:, 1] >= timings[:, 0]))

    def test_pyramid_scaling_factors(self):
        """Test pyramid centroider with scaling factors."""
        start_times = np.zeros([50, 2])
        centroid_agenda = np.ones(50, dtype=int) * self.n_subaps

        timings_base = PyramidCentroider(
            compute_resources=self.cr,
            start_times=start_times,
            centroid_agenda=centroid_agenda,
            mode="slopes",
        )

        timings_scaled = PyramidCentroider(
            compute_resources=self.cr,
            start_times=start_times,
            centroid_agenda=centroid_agenda,
            mode="slopes",
            flop_scale=2.0,
            mem_scale=2.0,
        )

        # With scaling, time should be reduced
        time_base = timings_base[0, 1] - timings_base[0, 0]
        time_scaled = timings_scaled[0, 1] - timings_scaled[0, 0]
        self.assertLess(time_scaled, time_base)

    def test_pyramid_single_subaperture(self):
        """Test pyramid centroider with single subaperture."""
        start_times = np.zeros([1, 2])
        centroid_agenda = np.array([1], dtype=int)

        for mode in ["intensity", "slopes", "ESC"]:
            timings = PyramidCentroider(
                compute_resources=self.cr,
                start_times=start_times,
                centroid_agenda=centroid_agenda,
                mode=mode,
            )
            self.assertEqual(timings.shape, (1, 2))
            self.assertGreater(timings[0, 1], timings[0, 0])

    def test_pyramid_variable_agenda(self):
        """Test pyramid centroider with variable agenda."""
        start_times = np.zeros([50, 2])
        # Variable number of subapertures per iteration
        centroid_agenda = np.random.randint(100, 1000, size=50)

        for mode in ["intensity", "slopes", "ESC"]:
            timings = PyramidCentroider(
                compute_resources=self.cr,
                start_times=start_times,
                centroid_agenda=centroid_agenda,
                mode=mode,
            )
            self.assertEqual(timings.shape, (50, 2))
            self.assertTrue(np.all(timings[:, 1] >= timings[:, 0]))

    def test_pyramid_debug_mode(self):
        """Test pyramid centroider with debug output enabled."""
        start_times = np.zeros([10, 2])
        centroid_agenda = np.ones(10, dtype=int) * self.n_subaps

        # Should not raise any errors with debug=True
        for mode in ["intensity", "slopes", "ESC"]:
            timings = PyramidCentroider(
                compute_resources=self.cr,
                start_times=start_times,
                centroid_agenda=centroid_agenda,
                mode=mode,
                debug=True,
            )
            self.assertEqual(timings.shape, (10, 2))

    def test_pyramid_timing_consistency(self):
        """Test that pyramid centroider produces consistent results."""
        start_times = np.zeros([50, 2])
        centroid_agenda = np.ones(50, dtype=int) * self.n_subaps

        # Run twice with same parameters
        timings1 = PyramidCentroider(
            compute_resources=self.cr,
            start_times=start_times,
            centroid_agenda=centroid_agenda,
            mode="slopes",
        )

        timings2 = PyramidCentroider(
            compute_resources=self.cr,
            start_times=start_times,
            centroid_agenda=centroid_agenda,
            mode="slopes",
        )

        # Results should be identical
        np.testing.assert_array_equal(timings1, timings2)

    def test_pyramid_subaperture_scaling(self):
        """Test that timing scales with number of subapertures."""
        start_times = np.zeros([10, 2])

        small_agenda = np.ones(10, dtype=int) * 100
        large_agenda = np.ones(10, dtype=int) * 1000

        for mode in ["intensity", "slopes", "ESC"]:
            timings_small = PyramidCentroider(
                compute_resources=self.cr,
                start_times=start_times,
                centroid_agenda=small_agenda,
                mode=mode,
            )

            timings_large = PyramidCentroider(
                compute_resources=self.cr,
                start_times=start_times,
                centroid_agenda=large_agenda,
                mode=mode,
            )

            # More subapertures should take more time
            time_small = timings_small[0, 1] - timings_small[0, 0]
            time_large = timings_large[0, 1] - timings_large[0, 0]
            self.assertGreater(time_large, time_small)


if __name__ == "__main__":
    unittest.main()

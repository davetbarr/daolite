"""Unit tests for centroider module."""

import unittest
import numpy as np
from daolite.compute import create_compute_resources
from daolite.pipeline.centroider import (
    CrossCorrelate,
    Centroid,
    ReferenceSlopes,
    Error,
    SquareDiff,
    Centroider,
)


class TestCentroider(unittest.TestCase):
    """Test centroider module functionality."""

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
        self.n_pixels = 16 * 16

    def test_cross_correlate(self):
        """Test cross-correlation timing calculation."""
        time = CrossCorrelate(
            n_valid_subaps=self.n_subaps,
            n_pix_per_subap=self.n_pixels,
            compute_resources=self.cr,
        )
        self.assertGreater(time, 0)

        # Test scaling with number of subapertures
        time_2x = CrossCorrelate(
            n_valid_subaps=self.n_subaps * 2,
            n_pix_per_subap=self.n_pixels,
            compute_resources=self.cr,
        )
        self.assertGreater(time_2x, time)

    def test_centroid(self):
        """Test centroid computation timing."""
        time = Centroid(
            n_valid_subaps=self.n_subaps,
            n_pix_per_subap=self.n_pixels,
            compute_resources=self.cr,
        )
        self.assertGreater(time, 0)

        # Test with sorting enabled
        time_sort = Centroid(
            n_valid_subaps=self.n_subaps,
            n_pix_per_subap=self.n_pixels,
            compute_resources=self.cr,
            sort=True,
        )
        self.assertGreater(time_sort, time)

    def test_reference_slopes(self):
        """Test reference slopes timing calculation."""
        time = ReferenceSlopes(
            n_valid_subaps=self.n_subaps,
            n_pix_per_subap=self.n_pixels,
            compute_resources=self.cr,
        )
        self.assertGreater(time, 0)

    def test_error(self):
        """Test error computation timing."""
        time = Error(
            n_valid_subaps=self.n_subaps,
            n_pix_per_subap=self.n_pixels,
            compute_resources=self.cr,
        )
        self.assertGreater(time, 0)

    def test_square_diff(self):
        """Test square difference timing calculation."""
        time = SquareDiff(
            n_valid_subaps=self.n_subaps,
            n_pix_per_subap=self.n_pixels,
            compute_resources=self.cr,
        )
        self.assertGreater(time, 0)

    def test_centroider_full_pipeline(self):
        """Test complete centroiding pipeline."""
        start_times = np.zeros([50, 2])
        timings = Centroider(
            n_valid_subaps=self.n_subaps,
            n_pix_per_subap=self.n_pixels,
            compute_resources=self.cr,
            start_times=start_times,
        )

        self.assertEqual(timings.shape, (50, 2))
        self.assertTrue(
            np.all(timings[:, 1] >= timings[:, 0])
        )  # End times >= start times

        # Test with different configurations
        configs = [
            {"square_diff": True},
            {"sort": True},
            {"n_workers": 2},
            {"delay_start": 5},
            {"agenda": np.ones(50) * 100},
        ]

        for config in configs:
            timings = Centroider(
                n_valid_subaps=self.n_subaps,
                n_pix_per_subap=self.n_pixels,
                compute_resources=self.cr,
                start_times=start_times,
                **config
            )
            self.assertEqual(timings.shape, (50, 2))
            self.assertTrue(np.all(timings[:, 1] >= timings[:, 0]))

    def test_single_subaperture(self):
        """Test centroiding with single subaperture."""
        start_times = np.zeros([1, 2])
        timings = Centroider(
            n_valid_subaps=1,
            n_pix_per_subap=self.n_pixels,
            compute_resources=self.cr,
            start_times=start_times,
        )
        self.assertEqual(timings.shape, (1, 2))
        self.assertGreater(timings[0, 1], timings[0, 0])


if __name__ == "__main__":
    unittest.main()

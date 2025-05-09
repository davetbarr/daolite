"""Unit tests for reconstruction module."""

import unittest
import numpy as np
from daolite.compute import create_compute_resources
from daolite.pipeline.reconstruction import (
    FullFrameReconstruction,
    Reconstruction,
    _calculate_n_slopes,
    _process_group,
)


class TestReconstruction(unittest.TestCase):
    """Test reconstruction module functionality."""

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
        self.n_slopes = 80 * 80 * 2  # X and Y slopes
        self.n_acts = 5000

    def test_full_frame_reconstruction(self):
        """Test full-frame reconstruction timing."""
        time = FullFrameReconstruction(
            n_slopes=self.n_slopes, n_acts=self.n_acts, compute_resources=self.cr
        )
        self.assertGreater(time, 0)

        # Test scaling with scale factor
        time_scaled = FullFrameReconstruction(
            n_slopes=self.n_slopes,
            n_acts=self.n_acts,
            compute_resources=self.cr,
            scale=2.0,
        )
        self.assertAlmostEqual(time_scaled * 2, time)

        # Test with debug output
        time_debug = FullFrameReconstruction(
            n_slopes=self.n_slopes,
            n_acts=self.n_acts,
            compute_resources=self.cr,
            debug=True,
        )
        self.assertAlmostEqual(time_debug, time)

    def test_reconstruction_pipeline(self):
        """Test grouped reconstruction pipeline."""
        start_times = np.zeros([50, 2])
        timings = Reconstruction(
            n_slopes=self.n_slopes,
            n_acts=self.n_acts,
            compute_resources=self.cr,
            start_times=start_times,
        )

        self.assertEqual(timings.shape, (50, 2))
        self.assertTrue(np.all(timings[:, 1] >= timings[:, 0]))

        # Test with different configurations
        configs = [
            {"scale": 2.0},
            {"n_workers": 2},
            {"group": 25},
            {"agenda": np.ones(50) * 100},
        ]

        for config in configs:
            timings = Reconstruction(
                n_slopes=self.n_slopes,
                n_acts=self.n_acts,
                compute_resources=self.cr,
                start_times=start_times,
                **config
            )
            self.assertEqual(timings.shape, (50, 2))
            self.assertTrue(np.all(timings[:, 1] >= timings[:, 0]))

    def test_calculate_n_slopes(self):
        """Test slope count calculation helper."""
        n_slopes = 1000
        group = 50
        n_workers = 2

        # Test without agenda
        count = _calculate_n_slopes(n_slopes, group, n_workers)
        self.assertGreater(count, 0)
        self.assertLessEqual(count, n_slopes)

        # Test with agenda
        agenda = np.array([100])
        count_agenda = _calculate_n_slopes(n_slopes, group, n_workers, agenda)
        self.assertEqual(count_agenda, 50)  # 100/2 workers

        # Test with zero agenda
        agenda_zero = np.array([0])
        count_zero = _calculate_n_slopes(n_slopes, group, n_workers, agenda_zero)
        self.assertEqual(count_zero, 0)

    def test_process_group(self):
        """Test group processing helper."""
        n_slopes = 100
        time = _process_group(
            n_slopes=n_slopes, n_acts=self.n_acts, compute_resources=self.cr, scale=1.0
        )
        self.assertGreater(time, 0)

        # Test scaling
        time_scaled = _process_group(
            n_slopes=n_slopes, n_acts=self.n_acts, compute_resources=self.cr, scale=2.0
        )
        # With scale=2.0, the time should be approximately half of the original time
        self.assertAlmostEqual(time_scaled * 2, time)

if __name__ == "__main__":
    unittest.main()

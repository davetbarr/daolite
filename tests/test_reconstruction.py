"""Unit tests for reconstruction module."""

import unittest
import numpy as np
from daolite.compute import create_compute_resources
from daolite.pipeline.reconstruction import (
    Reconstruction,
    _process_reconstruction_group,
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
        """Test full-frame reconstruction timing (using single-element agenda)."""
        # Full-frame reconstruction is now done by passing a single-element agenda
        start_times = np.zeros([1, 2])
        centroid_agenda = np.array([self.n_slopes])
        
        timings = Reconstruction(
            compute_resources=self.cr,
            start_times=start_times,
            centroid_agenda=centroid_agenda,
            n_acts=self.n_acts,
        )
        self.assertEqual(timings.shape, (1, 2))
        self.assertGreater(timings[0, 1], timings[0, 0])

        # Test scaling with flop_scale factor
        timings_scaled = Reconstruction(
            compute_resources=self.cr,
            start_times=start_times,
            centroid_agenda=centroid_agenda,
            n_acts=self.n_acts,
            flop_scale=2.0,
            mem_scale=2.0,  # Scale both flop and mem together
        )
        # With both scales=2.0, the time should be approximately half
        time = timings[0, 1] - timings[0, 0]
        time_scaled = timings_scaled[0, 1] - timings_scaled[0, 0]
        self.assertAlmostEqual(time_scaled * 2, time, places=1)

        # Test with debug output
        timings_debug = Reconstruction(
            compute_resources=self.cr,
            start_times=start_times,
            centroid_agenda=centroid_agenda,
            n_acts=self.n_acts,
            debug=True,
        )
        time_debug = timings_debug[0, 1] - timings_debug[0, 0]
        self.assertAlmostEqual(time_debug, time, places=2)

    def test_reconstruction_pipeline(self):
        """Test grouped reconstruction pipeline."""
        start_times = np.zeros([50, 2])
        # Create agenda with varying slope counts per iteration
        centroid_agenda = np.ones(50, dtype=int) * (self.n_slopes // 50)
        
        timings = Reconstruction(
            compute_resources=self.cr,
            start_times=start_times,
            centroid_agenda=centroid_agenda,
            n_acts=self.n_acts,
        )

        self.assertEqual(timings.shape, (50, 2))
        self.assertTrue(np.all(timings[:, 1] >= timings[:, 0]))

        # Test with different configurations
        configs = [
            {"flop_scale": 2.0},
            {"mem_scale": 2.0},
            {"n_workers": 2},
        ]

        for config in configs:
            timings = Reconstruction(
                compute_resources=self.cr,
                start_times=start_times,
                centroid_agenda=centroid_agenda,
                n_acts=self.n_acts,
                **config
            )
            self.assertEqual(timings.shape, (50, 2))
            self.assertTrue(np.all(timings[:, 1] >= timings[:, 0]))

    def test_process_reconstruction_group(self):
        """Test reconstruction group processing helper."""
        n_slopes = 100
        time = _process_reconstruction_group(
            n_slopes=n_slopes, 
            n_acts=self.n_acts, 
            compute_resources=self.cr, 
            flop_scale=1.0, 
            mem_scale=1.0,
            debug=False
        )
        self.assertGreater(time, 0)

        # Test scaling
        time_scaled = _process_reconstruction_group(
            n_slopes=n_slopes, 
            n_acts=self.n_acts, 
            compute_resources=self.cr, 
            flop_scale=2.0, 
            mem_scale=2.0,
            debug=False
        )
        # With scale=2.0, the time should be approximately half of the original time
        self.assertAlmostEqual(time_scaled * 2, time, places=2)

if __name__ == "__main__":
    unittest.main()

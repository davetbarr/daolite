"""Unit tests for control module."""

import unittest

from daolite.compute import create_compute_resources
from daolite.pipeline.control import (
    DMPower,
    FullFrameControl,
    Integrator,
    Offset,
    Saturation,
)


class TestControl(unittest.TestCase):
    """Test control module functionality."""

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
        self.n_acts = 5000

    def test_integrator(self):
        """Test integrator timing calculation."""
        time = Integrator(n_acts=self.n_acts, compute_resources=self.cr)
        self.assertGreater(time, 0)

        # Test with debug output
        time_debug = Integrator(
            n_acts=self.n_acts, compute_resources=self.cr, debug=True
        )
        self.assertAlmostEqual(time_debug, time)

        # Test scaling with actuators
        time_2x = Integrator(n_acts=self.n_acts * 2, compute_resources=self.cr)
        self.assertGreater(time_2x, time)

    def test_offset(self):
        """Test offset calculation timing."""
        time = Offset(n_acts=self.n_acts, compute_resources=self.cr)
        self.assertGreater(time, 0)

        # Test with debug output
        time_debug = Offset(n_acts=self.n_acts, compute_resources=self.cr, debug=True)
        self.assertAlmostEqual(time_debug, time)

        # Test scaling with actuators
        time_2x = Offset(n_acts=self.n_acts * 2, compute_resources=self.cr)
        self.assertGreater(time_2x, time)

    def test_saturation(self):
        """Test saturation handling timing."""
        time = Saturation(n_acts=self.n_acts, compute_resources=self.cr)
        self.assertGreater(time, 0)

        # Test with debug output
        time_debug = Saturation(
            n_acts=self.n_acts, compute_resources=self.cr, debug=True
        )
        self.assertAlmostEqual(time_debug, time)

        # Test scaling with actuators
        time_2x = Saturation(n_acts=self.n_acts * 2, compute_resources=self.cr)
        self.assertGreater(time_2x, time)

    def test_dm_power(self):
        """Test DM power estimation timing."""
        time = DMPower(n_acts=self.n_acts, compute_resources=self.cr)
        self.assertGreater(time, 0)

        # Test with debug output
        time_debug = DMPower(n_acts=self.n_acts, compute_resources=self.cr, debug=True)
        self.assertAlmostEqual(time_debug, time)

        # Test scaling with actuators
        time_2x = DMPower(n_acts=self.n_acts * 2, compute_resources=self.cr)
        self.assertGreater(time_2x, time)

    def test_full_frame_control(self):
        """Test complete control pipeline timing."""
        time = FullFrameControl(n_acts=self.n_acts, compute_resources=self.cr)
        self.assertGreater(time, 0)

        # Test scaling
        overhead = 8  # Default overhead in FullFrameControl
        time_scaled = FullFrameControl(
            n_acts=self.n_acts, compute_resources=self.cr, scale=2.0
        )
        # The non-overhead part should scale, overhead should not
        non_overhead = time - overhead
        non_overhead_scaled = time_scaled - overhead
        self.assertAlmostEqual(non_overhead, non_overhead_scaled * 2, places=5)

        # Test combine factor
        time_combined = FullFrameControl(
            n_acts=self.n_acts, compute_resources=self.cr, combine=2.0
        )
        # Integration time should double, other components same
        self.assertGreater(time_combined, time)

        # Test with debug output
        time_debug = FullFrameControl(
            n_acts=self.n_acts, compute_resources=self.cr, debug=True
        )
        self.assertAlmostEqual(time_debug, time)


if __name__ == "__main__":
    unittest.main()

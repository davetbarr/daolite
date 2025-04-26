"""Unit tests for network timing module."""

import unittest
import numpy as np
from daolite.compute import create_compute_resources
from daolite.utils.network import (
    TimeOnNetwork,
    calculate_memory_bandwidth,
    calculate_switch_time,
    calculate_driver_delay,
    estimate_transfer_time_us,
    pcie_bus,
    PCIE,
)


class TestNetwork(unittest.TestCase):
    """Test network timing module functionality."""

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
        self.data_size = 1024 * 1024 * 8  # 1MB in bits

    def test_time_on_network(self):
        """Test basic network transfer timing."""
        time = TimeOnNetwork(n_bits=self.data_size, compute_resources=self.cr)
        self.assertGreater(time, 0)

        # Test with debug output
        time_debug = TimeOnNetwork(
            n_bits=self.data_size, compute_resources=self.cr, debug=True
        )
        self.assertAlmostEqual(time_debug, time)

        # Test scaling with data size
        time_2x = TimeOnNetwork(n_bits=self.data_size * 2, compute_resources=self.cr)
        self.assertGreater(time_2x, time)

    def test_memory_bandwidth_calculation(self):
        """Test memory bandwidth calculation."""
        bandwidth = calculate_memory_bandwidth(memory_speed_mts=4800, bus_width_bits=64)
        self.assertGreater(bandwidth, 0)

        # Test scaling with memory speed
        bandwidth_2x = calculate_memory_bandwidth(
            memory_speed_mts=9600, bus_width_bits=64
        )
        self.assertAlmostEqual(bandwidth_2x, bandwidth * 2)

        # Test scaling with bus width
        bandwidth_wide = calculate_memory_bandwidth(
            memory_speed_mts=4800, bus_width_bits=128
        )
        self.assertAlmostEqual(bandwidth_wide, bandwidth * 2)

    def test_switch_time_calculation(self):
        """Test network switch traversal timing."""
        frame_size = 1500  # Standard Ethernet MTU
        speed = 100  # 100 Gbps

        time = calculate_switch_time(frame_size, speed)
        self.assertGreater(time, 0)

        # Test scaling with frame size
        time_2x = calculate_switch_time(frame_size * 2, speed)
        self.assertAlmostEqual(time_2x, time * 2)

        # Test scaling with network speed
        time_faster = calculate_switch_time(frame_size, speed * 2)
        self.assertAlmostEqual(time_faster * 2, time)

    def test_driver_delay_calculation(self):
        """Test network driver processing delay."""
        delay = calculate_driver_delay(self.data_size)
        self.assertGreater(delay, 0)

        # Test with debug output
        delay_debug = calculate_driver_delay(self.data_size, debug=True)
        self.assertAlmostEqual(delay_debug, delay)

        # Test scaling with data size
        delay_2x = calculate_driver_delay(self.data_size * 2)
        self.assertGreater(delay_2x, delay)

    def test_transfer_time_estimation(self):
        """Test complete transfer time estimation."""
        cable_length = 100  # meters
        time = estimate_transfer_time_us(
            data_size=self.data_size // 8,  # Convert to bytes
            bandwidth=100e9,  # 100 Gbps
            cable_length=cable_length,
        )
        self.assertGreater(time, 0)

        # Test with switch hops
        time_with_switch = estimate_transfer_time_us(
            data_size=self.data_size // 8,
            bandwidth=100e9,
            cable_length=cable_length,
            num_switch_hops=2,
        )
        self.assertGreater(time_with_switch, time)

        # Test with debug output
        time_debug = estimate_transfer_time_us(
            data_size=self.data_size // 8,
            bandwidth=100e9,
            cable_length=cable_length,
            debug=True,
        )
        self.assertAlmostEqual(time_debug, time)

    def test_pcie_bus_timing(self):
        """Test PCIe bus transfer timing."""
        time = pcie_bus(n_bits=self.data_size, gen=4)  # PCIe Gen4
        self.assertGreater(time, 0)

        # Test with different PCIe generations
        time_gen3 = pcie_bus(n_bits=self.data_size, gen=3)
        self.assertGreater(time_gen3, time)  # Gen3 should be slower

        # Test with debug output
        time_debug = pcie_bus(n_bits=self.data_size, gen=4, debug=True)
        self.assertAlmostEqual(time_debug, time)

        # Test invalid PCIe generation
        with self.assertRaises(ValueError):
            pcie_bus(self.data_size, gen=6)

    def test_pcie_transfer_pipeline(self):
        """Test grouped PCIe transfer timing."""
        start_times = np.zeros([50, 2])
        timings = PCIE(
            n_bits=self.data_size, compute_resources=self.cr, start_times=start_times
        )

        self.assertEqual(timings.shape, (50, 2))
        self.assertTrue(np.all(timings[:, 1] >= timings[:, 0]))

        # Test with different configurations
        configs = [{"scale": 2.0}, {"gen": 3}]

        for config in configs:
            timings = PCIE(
                n_bits=self.data_size,
                compute_resources=self.cr,
                start_times=start_times,
                **config
            )
            self.assertEqual(timings.shape, (50, 2))
            self.assertTrue(np.all(timings[:, 1] >= timings[:, 0]))


if __name__ == "__main__":
    unittest.main()

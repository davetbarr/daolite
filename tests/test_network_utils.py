import unittest

import numpy as np

from daolite.compute import create_compute_resources
from daolite.utils import network


class TestNetworkUtils(unittest.TestCase):
    def setUp(self):
        self.cr = create_compute_resources(
            cores=8,
            core_frequency=2.5e9,
            flops_per_cycle=16,
            memory_channels=2,
            memory_width=64,
            memory_frequency=3200e6,
            network_speed=40e9,
            time_in_driver=5,
        )

    def test_time_on_network_basic(self):
        t = network.TimeOnNetwork(1024 * 8, self.cr)
        self.assertGreater(t, 0)

    def test_calculate_memory_bandwidth(self):
        bw = network.calculate_memory_bandwidth(4800, 64)
        self.assertGreater(bw, 0)
        self.assertAlmostEqual(network.calculate_memory_bandwidth(9600, 64), bw * 2)

    def test_calculate_switch_time(self):
        t = network.calculate_switch_time(1500, 100)
        self.assertGreater(t, 0)
        t2 = network.calculate_switch_time(3000, 100)
        self.assertAlmostEqual(t2, t * 2)

    def test_calculate_driver_delay(self):
        d = network.calculate_driver_delay(1024 * 8)
        self.assertGreater(d, 0)
        d2 = network.calculate_driver_delay(1024 * 16)
        self.assertGreater(d2, d)

    def test_estimate_transfer_time_us(self):
        t = network.estimate_transfer_time_us(1024, 1e9, 100)
        self.assertGreater(t, 0)
        t2 = network.estimate_transfer_time_us(2048, 1e9, 100)
        self.assertGreater(t2, t)

    def test_pcie_bus(self):
        t = network.pcie_bus(1024 * 8, gen=4)
        self.assertGreater(t, 0)
        with self.assertRaises(ValueError):
            network.pcie_bus(1024 * 8, gen=6)

    def test_PCIE(self):
        start_times = np.zeros([10, 2])
        timings = network.PCIE(1024 * 8, self.cr, start_times)
        self.assertEqual(timings.shape, (10, 2))
        self.assertTrue(np.all(timings[:, 1] >= timings[:, 0]))


if __name__ == "__main__":
    unittest.main()

"""Unit tests for compute resources module."""

import unittest
import numpy as np
from daolite.compute import ComputeResources, create_compute_resources


class TestComputeResources(unittest.TestCase):
    """Test ComputeResources class functionality."""

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

    def test_create_compute_resources(self):
        """Test create_compute_resources factory function."""
        self.assertIsInstance(self.cr, ComputeResources)
        self.assertEqual(self.cr.hardware, "CPU")
        self.assertGreater(self.cr.memory_bandwidth, 0)
        self.assertGreater(self.cr.flops, 0)
        self.assertGreater(self.cr.network_speed, 0)
        self.assertEqual(self.cr.time_in_driver, 5)

    def test_memory_bandwidth_calculation(self):
        """Test memory bandwidth calculation."""
        # Implementation returns bytes/second, so divide by 8
        expected_bandwidth_bytes = (4 * 64 * 3200e6) / 8  # channels * width * frequency / 8
        expected_bandwidth_bits = expected_bandwidth_bytes * 8
        self.assertAlmostEqual(
            self.cr.get_memory_bandwidth(), expected_bandwidth_bits * self.cr.mem_fudge
        )

    def test_flops_calculation(self):
        """Test FLOPS calculation."""
        expected_flops = 16 * 2.6e9 * 32  # cores * frequency * flops_per_cycle
        self.assertAlmostEqual(self.cr.get_flops(), expected_flops * self.cr.core_fudge)

    def test_load_time_calculation(self):
        """Test memory load time calculation."""
        memory_size = 1024 * 1024  # 1MB
        load_time = self.cr.load_time(memory_size)
        self.assertGreater(load_time, 0)

        # Test scaling with memory size
        load_time_2x = self.cr.load_time(memory_size * 2)
        self.assertAlmostEqual(load_time_2x, load_time * 2)

    def test_network_time_calculation(self):
        """Test network transfer time calculation."""
        data_size = 1024 * 1024 * 8  # 1MB in bits
        net_time = self.cr.network_time(data_size)
        self.assertGreater(net_time, 0)

        # Test scaling with data size
        net_time_2x = self.cr.network_time(data_size * 2)
        self.assertGreater(net_time_2x, net_time)

    def test_calc_time_calculation(self):
        """Test computation time calculation."""
        n_flops = 1000000  # 1M FLOPS
        calc_time = self.cr.calc_time(n_flops)
        self.assertGreater(calc_time, 0)

        # Test scaling with number of operations
        calc_time_2x = self.cr.calc_time(n_flops * 2)
        self.assertAlmostEqual(calc_time_2x, calc_time * 2)

    def test_total_time_calculation(self):
        """Test total operation time calculation."""
        memory_size = 1024 * 1024  # 1MB
        n_flops = 1000000  # 1M FLOPS
        total_time = self.cr.total_time(memory_size, n_flops)

        # Total time should equal load_time + calc_time
        expected_time = self.cr.load_time(memory_size) + self.cr.calc_time(n_flops)
        self.assertAlmostEqual(total_time, expected_time)

    def test_create_gpu_resource(self):
        """Test creation of GPU compute resources."""
        from daolite.compute import create_gpu_resource
        gpu = create_gpu_resource(
            flops=10e12,
            memory_bandwidth=300e9,  # Input in Bytes/sec
            network_speed=200e9,
            time_in_driver=10.0,
        )
        self.assertIsInstance(gpu, ComputeResources)
        self.assertEqual(gpu.hardware, "GPU")
        # memory_bandwidth is stored in bits/sec internally
        self.assertEqual(gpu.memory_bandwidth, 300e9 * 8)
        self.assertEqual(gpu.flops, 10e12)
        self.assertEqual(gpu.network_speed, 200e9)
        self.assertEqual(gpu.time_in_driver, 10.0)

    def test_create_compute_resources_from_yaml_invalid(self):
        """Test error handling for invalid hardware type in YAML."""
        import tempfile, yaml
        from daolite.compute import create_compute_resources_from_yaml
        data = {"hardware": "INVALID", "cores": 4, "core_frequency": 1e9, "flops_per_cycle": 8, "memory_frequency": 1e9, "memory_width": 64, "memory_channels": 2, "network_speed": 1e9, "time_in_driver": 5}
        with tempfile.NamedTemporaryFile(mode="w+", suffix=".yaml", delete=False) as f:
            yaml.safe_dump(data, f)
            f.flush()
            result = create_compute_resources_from_yaml(f.name)
        self.assertIsNone(result)

    def test_create_compute_resources_from_yaml_cpu(self):
        """Test creating CPU resource from YAML."""
        import tempfile, yaml
        from daolite.compute import create_compute_resources_from_yaml
        data = {"hardware": "CPU", "cores": 4, "core_frequency": 1e9, "flops_per_cycle": 8, "memory_frequency": 1e9, "memory_width": 64, "memory_channels": 2, "network_speed": 1e9, "time_in_driver": 5}
        with tempfile.NamedTemporaryFile(mode="w+", suffix=".yaml", delete=False) as f:
            yaml.safe_dump(data, f)
            f.flush()
            result = create_compute_resources_from_yaml(f.name)
        self.assertIsInstance(result, ComputeResources)
        self.assertEqual(result.hardware, "CPU")

    def test_create_compute_resources_from_yaml_gpu(self):
        """Test creating GPU resource from YAML."""
        import tempfile, yaml
        from daolite.compute import create_compute_resources_from_yaml
        data = {"hardware": "GPU", "flops": 10e12, "memory_bandwidth": 300e9, "network_speed": 200e9, "time_in_driver": 10.0}
        with tempfile.NamedTemporaryFile(mode="w+", suffix=".yaml", delete=False) as f:
            yaml.safe_dump(data, f)
            f.flush()
            result = create_compute_resources_from_yaml(f.name)
        self.assertIsInstance(result, ComputeResources)
        self.assertEqual(result.hardware, "GPU")

    def test_create_compute_resources_from_system(self):
        """Test system-based resource creation (smoke test)."""
        from daolite.compute import create_compute_resources_from_system
        result = create_compute_resources_from_system()
        self.assertIsInstance(result, ComputeResources)


if __name__ == "__main__":
    unittest.main()

"""Unit tests for configuration module."""

import unittest
import os
import tempfile
from daolite.config import CameraConfig, OpticsConfig, PipelineConfig, SystemConfig
from daolite.compute import create_compute_resources


class TestConfiguration(unittest.TestCase):
    """Test configuration functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.camera = CameraConfig(
            n_pixels=1024 * 1024, n_subapertures=80 * 80, pixels_per_subaperture=16 * 16
        )

        self.optics = OpticsConfig(
            n_actuators=5000,
            n_dm_modes=None,
            n_combine=2,
            calibration_scale=1.2,
            centroid_scale=1.5,
            reconstruction_scale=1.0,
            control_scale=0.8,
        )

        self.pipeline = PipelineConfig(
            use_square_diff=True,
            use_sorting=True,
            delay_start=10.0,
            n_workers=4,
            pcie_gen=4,
        )

        self.compute = create_compute_resources(
            cores=32,
            core_frequency=3.2e9,
            flops_per_cycle=64,
            memory_channels=8,
            memory_width=64,
            memory_frequency=4800e6,
            network_speed=200e9,
            time_in_driver=2,
        )

        self.config = SystemConfig(
            camera=self.camera,
            optics=self.optics,
            pipeline=self.pipeline,
            compute=self.compute,
        )

    def test_camera_config(self):
        """Test camera configuration defaults."""
        camera = CameraConfig(
            n_pixels=1024, n_subapertures=16, pixels_per_subaperture=8
        )
        self.assertEqual(camera.bit_depth, 16)
        self.assertEqual(camera.readout_time, 500.0)
        self.assertEqual(camera.n_lines_of_sight, 1)

    def test_optics_config(self):
        """Test optics configuration defaults."""
        optics = OpticsConfig(n_actuators=1000)
        self.assertIsNone(optics.n_dm_modes)
        self.assertEqual(optics.n_combine, 1)
        self.assertEqual(optics.calibration_scale, 1.0)
        self.assertEqual(optics.centroid_scale, 1.0)
        self.assertEqual(optics.reconstruction_scale, 1.0)
        self.assertEqual(optics.control_scale, 1.0)

    def test_pipeline_config(self):
        """Test pipeline configuration defaults."""
        pipeline = PipelineConfig()
        self.assertFalse(pipeline.use_square_diff)
        self.assertFalse(pipeline.use_sorting)
        self.assertEqual(pipeline.delay_start, 0.0)
        self.assertEqual(pipeline.n_workers, 1)
        self.assertEqual(pipeline.pcie_gen, 5)

    def test_system_config_defaults(self):
        """Test system configuration defaults."""
        config = SystemConfig(
            camera=self.camera, optics=self.optics, compute=self.compute
        )
        self.assertIsNotNone(config.pipeline)
        self.assertIsNotNone(config.compute)

    def test_yaml_roundtrip(self):
        """Test YAML serialization and deserialization."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            # Save configuration to temporary file
            self.config.to_yaml(f.name)

            # Load configuration from file
            loaded_config = SystemConfig.from_yaml(f.name)

            # Check camera configuration
            self.assertEqual(loaded_config.camera.n_pixels, self.config.camera.n_pixels)
            self.assertEqual(
                loaded_config.camera.n_subapertures, self.config.camera.n_subapertures
            )

            # Check optics configuration
            self.assertEqual(
                loaded_config.optics.n_actuators, self.config.optics.n_actuators
            )
            self.assertEqual(
                loaded_config.optics.calibration_scale,
                self.config.optics.calibration_scale,
            )

            # Check pipeline configuration
            self.assertEqual(
                loaded_config.pipeline.use_square_diff,
                self.config.pipeline.use_square_diff,
            )
            self.assertEqual(
                loaded_config.pipeline.n_workers, self.config.pipeline.n_workers
            )

            # Check compute configuration
            self.assertEqual(loaded_config.compute.cores, self.config.compute.cores)
            self.assertEqual(
                loaded_config.compute.network_speed, self.config.compute.network_speed
            )

            # Clean up temporary file
            os.unlink(f.name)

    def test_yaml_minimal(self):
        """Test loading minimal YAML configuration."""
        minimal_yaml = {
            "camera": {
                "n_pixels": 1024,
                "n_subapertures": 16,
                "pixels_per_subaperture": 8,
            },
            "optics": {"n_actuators": 1000},
            "compute": {
                "cores": 16,
                "core_frequency": 2.6e9,
                "flops_per_cycle": 32,
                "memory_channels": 4,
                "memory_width": 64,
                "memory_frequency": 3200e6,
                "network_speed": 100e9,
                "time_in_driver": 5,
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            import yaml

            yaml.safe_dump(minimal_yaml, f)

            # Load minimal configuration
            config = SystemConfig.from_yaml(f.name)

            # Check defaults were applied
            self.assertEqual(config.camera.bit_depth, 16)
            self.assertEqual(config.optics.n_combine, 1)
            self.assertIsNotNone(config.pipeline)
            self.assertIsNotNone(config.compute)

            # Clean up
            os.unlink(f.name)


if __name__ == "__main__":
    unittest.main()

"""
Configuration module for adaptive optics system parameters.

This module provides configuration classes and utilities for specifying
camera parameters, optical system layout, and compute resources for
latency estimation.
"""

from dataclasses import dataclass
from typing import Optional, Any, Dict
import yaml

# Import the ComputeResources class and creation function directly
from daolite.compute import ComputeResources, create_compute_resources


@dataclass
class CameraConfig:
    """Camera configuration parameters."""

    n_pixels: int
    n_subapertures: int
    pixels_per_subaperture: int
    bit_depth: int = 16
    readout_time: float = 500.0  # microseconds
    n_lines_of_sight: int = 1


@dataclass
class OpticsConfig:
    """Optical system configuration."""

    n_actuators: int
    n_dm_modes: Optional[int] = None
    n_combine: int = 1
    calibration_scale: float = 1.0
    centroid_scale: float = 1.0
    reconstruction_scale: float = 1.0
    control_scale: float = 1.0


@dataclass
class PipelineConfig:
    """Processing pipeline configuration."""

    use_square_diff: bool = False
    use_sorting: bool = False
    delay_start: float = 0.0
    n_workers: int = 1
    pcie_gen: int = 5


class Config:
    """Base configuration class for daolite.

    This class provides basic configuration functionality and serves as a
    factory for creating more specific configuration objects.
    """

    def __init__(self, config_data: Optional[Dict] = None):
        """
        Initialize configuration with default or provided values.

        Parameters
        ----------
        config_data : dict, optional
            Configuration data to initialize with.
        """
        self.config_data = config_data or {}

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get value from config or return default if not found.

        Parameters
        ----------
        key : str
            The configuration key to look up.
        default : any, optional
            Default value to return if key is not found.

        Returns
        -------
        any
            The configuration value or default.
        """
        return self.config_data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """
        Set config value.

        Parameters
        ----------
        key : str
            The configuration key to set.
        value : any
            The value to set.
        """
        self.config_data[key] = value

    def load(self, filepath: str) -> None:
        """
        Load configuration from file.

        Parameters
        ----------
        filepath : str
            Path to configuration file.
        """
        with open(filepath, "r") as file:
            self.config_data = yaml.safe_load(file)

    def save(self, filepath: str) -> None:
        """
        Save configuration to file.

        Parameters
        ----------
        filepath : str
            Path to save configuration file.
        """
        with open(filepath, "w") as file:
            yaml.safe_dump(self.config_data, file, default_flow_style=False)

    @classmethod
    def from_yaml(cls, filepath: str) -> "Config":
        """
        Create a configuration from a YAML file.

        Parameters
        ----------
        filepath : str
            Path to YAML configuration file.

        Returns
        -------
        Config
            A new Config instance initialized with the file contents.
        """
        config = cls()
        config.load(filepath)
        return config


class SystemConfig:
    """Complete AO system configuration."""

    def __init__(
        self,
        camera: CameraConfig,
        optics: OpticsConfig,
        pipeline: Optional[PipelineConfig] = None,
        compute: Optional[ComputeResources] = None,
    ):
        """
        Initialize system configuration.

        Args:
            camera: Camera configuration
            optics: Optical system configuration
            pipeline: Processing pipeline configuration (optional)
            compute: Compute resources (optional)
        """
        self.camera = camera
        self.optics = optics
        self.pipeline = pipeline or PipelineConfig()
        if compute is None:
            raise ValueError(
                "Compute resources must be provided explicitly to SystemConfig."
            )
        self.compute = compute

    @classmethod
    def from_yaml(cls, file_path: str) -> "SystemConfig":
        """
        Create configuration from YAML file.

        Args:
            file_path: Path to YAML configuration file

        Returns:
            SystemConfig instance
        """
        with open(file_path, "r") as f:
            data = yaml.safe_load(f)

        # Parse camera configuration
        camera = CameraConfig(
            n_pixels=data["camera"]["n_pixels"],
            n_subapertures=data["camera"]["n_subapertures"],
            pixels_per_subaperture=data["camera"]["pixels_per_subaperture"],
            bit_depth=data["camera"].get("bit_depth", 16),
            readout_time=data["camera"].get("readout_time", 500.0),
            n_lines_of_sight=data["camera"].get("n_lines_of_sight", 1),
        )

        # Parse optics configuration
        optics = OpticsConfig(
            n_actuators=data["optics"]["n_actuators"],
            n_dm_modes=data["optics"].get("n_dm_modes"),
            n_combine=data["optics"].get("n_combine", 1),
            calibration_scale=data["optics"].get("calibration_scale", 1.0),
            centroid_scale=data["optics"].get("centroid_scale", 1.0),
            reconstruction_scale=data["optics"].get("reconstruction_scale", 1.0),
            control_scale=data["optics"].get("control_scale", 1.0),
        )

        # Parse pipeline configuration if present
        pipeline = None
        if "pipeline" in data:
            pipeline = PipelineConfig(
                use_square_diff=data["pipeline"].get("use_square_diff", False),
                use_sorting=data["pipeline"].get("use_sorting", False),
                delay_start=data["pipeline"].get("delay_start", 0.0),
                n_workers=data["pipeline"].get("n_workers", 1),
                pcie_gen=data["pipeline"].get("pcie_gen", 5),
            )

        # Create compute resources if present
        compute = None
        if "compute" in data:
            compute = create_compute_resources(
                cores=data["compute"].get("cores", 16),
                core_frequency=data["compute"].get("core_frequency", 2.6e9),
                flops_per_cycle=data["compute"].get("flops_per_cycle", 32),
                memory_channels=data["compute"].get("memory_channels", 4),
                memory_width=data["compute"].get("memory_width", 64),
                memory_frequency=data["compute"].get("memory_frequency", 3200e6),
                network_speed=data["compute"].get("network_speed", 100e9),
                time_in_driver=data["compute"].get("time_in_driver", 5),
            )

        return cls(camera, optics, pipeline, compute)

    def to_yaml(self, file_path: str):
        """
        Save configuration to YAML file.

        Args:
            file_path: Path to save YAML configuration
        """
        config = {
            "camera": {
                "n_pixels": self.camera.n_pixels,
                "n_subapertures": self.camera.n_subapertures,
                "pixels_per_subaperture": self.camera.pixels_per_subaperture,
                "bit_depth": self.camera.bit_depth,
                "readout_time": self.camera.readout_time,
                "n_lines_of_sight": self.camera.n_lines_of_sight,
            },
            "optics": {
                "n_actuators": self.optics.n_actuators,
                "n_combine": self.optics.n_combine,
                "calibration_scale": self.optics.calibration_scale,
                "centroid_scale": self.optics.centroid_scale,
                "reconstruction_scale": self.optics.reconstruction_scale,
                "control_scale": self.optics.control_scale,
            },
        }

        if self.optics.n_dm_modes is not None:
            config["optics"]["n_dm_modes"] = self.optics.n_dm_modes

        if self.pipeline:
            config["pipeline"] = {
                "use_square_diff": self.pipeline.use_square_diff,
                "use_sorting": self.pipeline.use_sorting,
                "delay_start": self.pipeline.delay_start,
                "n_workers": self.pipeline.n_workers,
                "pcie_gen": self.pipeline.pcie_gen,
            }

        if self.compute:
            config["compute"] = {
                "cores": self.compute.cores,
                "core_frequency": self.compute.core_frequency,
                "flops_per_cycle": self.compute.flops_per_cycle,
                "memory_channels": self.compute.memory_channels,
                "memory_width": self.compute.memory_width,
                "memory_frequency": self.compute.memory_frequency,
                "network_speed": self.compute.network_speed,
                "time_in_driver": self.compute.time_in_driver,
            }

        with open(file_path, "w") as f:
            yaml.safe_dump(config, f, default_flow_style=False)
            
"""
Hardware module for DaoLITE compute resources.

This module provides predefined hardware configurations for various
CPUs and GPUs, which can be used in latency estimation.
"""

import os
import yaml
from daolite.compute.base_resources import (
    ComputeResources,
    create_compute_resources_from_yaml,
    create_compute_resources,
    create_gpu_resource,
)

# Directory containing hardware YAML files
HARDWARE_DIR = os.path.join(os.path.dirname(__file__))


# CPU resource factories
def amd_epyc_7763() -> ComputeResources:
    """Create AMD EPYC 7763 (Milan) compute resource."""
    return _load_hardware("amd_epyc_7763.yaml")


def amd_epyc_9654() -> ComputeResources:
    """Create AMD EPYC 9654 (Genoa) compute resource."""
    return _load_hardware("amd_epyc_9654.yaml")


def intel_xeon_8480() -> ComputeResources:
    """Create Intel Xeon Platinum 8480+ (Sapphire Rapids) compute resource."""
    return _load_hardware("intel_xeon_8480.yaml")


def intel_xeon_8462() -> ComputeResources:
    """Create Intel Xeon 8462Y+ (Emerald Rapids) compute resource."""
    return _load_hardware("intel_xeon_8462.yaml")


def amd_ryzen_7950x() -> ComputeResources:
    """Create AMD Ryzen 9 7950X compute resource."""
    return _load_hardware("amd_ryzen_7950x.yaml")


# GPU resource factories
def nvidia_a100_80gb() -> ComputeResources:
    """Create NVIDIA A100 80GB compute resource."""
    return _load_hardware("nvidia_a100_80gb.yaml")


def nvidia_a100_40gb() -> ComputeResources:
    """Create NVIDIA A100 40GB compute resource."""
    return _load_hardware("nvidia_a100_40gb.yaml")


def nvidia_h100_80gb() -> ComputeResources:
    """Create NVIDIA H100 80GB compute resource."""
    return _load_hardware("nvidia_h100_80gb.yaml")


def nvidia_rtx_6000_ada() -> ComputeResources:
    """Create NVIDIA RTX 6000 Ada compute resource."""
    return _load_hardware("nvidia_rtx_6000_ada.yaml")


def nvidia_rtx_4090() -> ComputeResources:
    """Create NVIDIA RTX 4090 compute resource."""
    return _load_hardware("nvidia_rtx_4090.yaml")


def nvidia_v100_32gb() -> ComputeResources:
    """Create NVIDIA V100 32GB compute resource."""
    return _load_hardware("nvidia_v100_32gb.yaml")


def amd_mi250x() -> ComputeResources:
    """Create AMD Instinct MI250X compute resource."""
    return _load_hardware("amd_mi250x.yaml")


def amd_mi300x() -> ComputeResources:
    """Create AMD Instinct MI300X compute resource."""
    return _load_hardware("amd_mi300x.yaml")


def _load_hardware(filename: str) -> ComputeResources:
    """
    Load hardware configuration from YAML file.

    Args:
        filename: Name of YAML file in hardware directory

    Returns:
        ComputeResources: Configured compute resource
    """
    filepath = os.path.join(HARDWARE_DIR, filename)

    try:
        # Use the existing function to load the configuration
        resource = create_compute_resources_from_yaml(filepath)

        # Set name attribute for better display if not set
        if not hasattr(resource, "name") or not resource.name:
            with open(filepath, "r") as f:
                data = yaml.safe_load(f)
                resource.name = data.get("name", os.path.splitext(filename)[0])

        return resource

    except FileNotFoundError:
        print(
            f"Warning: Hardware config file {filename} not found. Using default values."
        )
        resource = create_compute_resources(
            cores=16,
            core_frequency=2.6e9,
            flops_per_cycle=32,
            memory_channels=4,
            memory_width=64,
            memory_frequency=3200e6,
            network_speed=100e9,
            time_in_driver=5,
        )
        resource.name = os.path.splitext(filename)[0]
        return resource
    except Exception as e:
        print(f"Error loading hardware config from {filename}: {e}")
        resource = create_compute_resources(
            cores=16,
            core_frequency=2.6e9,
            flops_per_cycle=32,
            memory_channels=4,
            memory_width=64,
            memory_frequency=3200e6,
            network_speed=100e9,
            time_in_driver=5,
        )
        resource.name = os.path.splitext(filename)[0]
        return resource

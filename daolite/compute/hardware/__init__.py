"""
Hardware module for daolite compute resources.

This module provides predefined hardware configurations for various
CPUs and GPUs, which can be used in latency estimation.
"""

import os

import yaml

from daolite.compute.base_resources import (
    ComputeResources,
    create_compute_resources,
    create_compute_resources_from_yaml,
)

# Directory containing hardware YAML files
HARDWARE_DIR = os.path.join(os.path.dirname(__file__))


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
            with open(filepath) as f:
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


# --- Auto-discover YAML hardware files and create factory functions ---


def _make_factory(yaml_filename):
    def factory():
        return _load_hardware(yaml_filename)

    factory.__name__ = os.path.splitext(yaml_filename)[0]
    factory.__doc__ = f"Create compute resource from {yaml_filename}"
    return factory


for fname in os.listdir(HARDWARE_DIR):
    if fname.endswith(".yaml") and not fname.startswith("_"):
        func_name = os.path.splitext(fname)[0]
        # Only add if not already defined (manual overrides allowed)
        if func_name not in globals():
            globals()[func_name] = _make_factory(fname)

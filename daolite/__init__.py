"""
daolite - Durham Adaptive Optics Latency Inspection Tool Environment

A Python package for estimating latency in Adaptive Optics Real-time
Control Systems, with a focus on Durham Adaptive Optics (DAO) RTC systems.
"""

# Import core modules
from daolite.common import ComponentType
from daolite.component import Component
from daolite.compute import (
    ComputeResources,
    create_compute_resources,
    create_compute_resources_from_yaml,
    create_gpu_resource,
)
from daolite.config import Config, SystemConfig
from daolite.pipeline import Pipeline, PipelineComponent

# Version information
__version__ = "0.1.0"
__author__ = "David Barr"

# Export public API
__all__ = [
    # Core classes
    "Component",
    "Config",
    "SystemConfig",
    "ComputeResources",
    "create_compute_resources",
    "create_gpu_resource",
    "create_compute_resources_from_yaml",
    "ComponentType",
    # New pipeline system
    "Pipeline",
    "PipelineComponent",
    # CPU resources
    "amd_epyc_7763",
    "amd_epyc_9654",
    "intel_xeon_8480",
    "intel_xeon_8462",
    "amd_epyc_7742",
    "intel_xeon_8380",
    "amd_ryzen_7950x",
    "intel_core_i9_14900k",
    # GPU resources
    "nvidia_a100_80gb",
    "nvidia_a100_40gb",
    "nvidia_h100_80gb",
    "nvidia_rtx_6000_ada",
    "nvidia_rtx_4090",
    "nvidia_v100_32gb",
    "amd_mi250x",
    "amd_mi300x",
]

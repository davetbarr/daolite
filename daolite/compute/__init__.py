"""
Compute resources module for daolite.

This module provides classes and functions for defining and managing
compute resources in adaptive optics pipelines.
"""

from daolite.compute.base_resources import (
    ComputeResources,
    create_compute_resources,
    create_compute_resources_from_system,
    create_compute_resources_from_yaml,
    create_gpu_resource,
)

__all__ = [
    "ComputeResources",
    "create_compute_resources",
    "create_compute_resources_from_yaml",
    "create_compute_resources_from_system",
    "create_gpu_resource",
]

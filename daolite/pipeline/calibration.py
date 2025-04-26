"""
Pixel calibration module for adaptive optics.

This module provides functions for estimating computational latency
of pixel calibration operations in adaptive optics systems.
"""

import numpy as np
from typing import Optional
from daolite.compute import ComputeResources


def _calibration_flops(n_pixels: int) -> int:
    """
    Calculate number of floating point operations for pixel calibration.

    Args:
        n_pixels: Number of pixels to calibrate

    Returns:
        int: Number of floating point operations
    """
    # Operations: dark subtraction, flat field division, bad pixel handling
    return 3 * n_pixels


def _calibration_mem(n_pixels: int) -> int:
    """
    Calculate memory operations for pixel calibration.

    Args:
        n_pixels: Number of pixels to calibrate

    Returns:
        int: Number of memory operations in bytes
    """
    # Read pixel, read dark, read flat, write calibrated pixel
    return 4 * n_pixels


def PixelCalibration(
    n_pixels: int,
    compute_resources: ComputeResources,
    start_times: np.ndarray,
    group: Optional[int] = None,
    scale: float = 1.0,
    debug: bool = False,
) -> np.ndarray:
    """
    Calculate timing for pixel calibration operations.

    Args:
        n_pixels: Total number of pixels to calibrate
        compute_resources: ComputeResources instance
        start_times: Array of shape (rows, 2) with start/end times from camera
        group: Number of groups to process (default: use start_times length)
        scale: Computational scaling factor (default: 1.0)
        debug: Enable debug output

    Returns:
        np.ndarray: Array of shape (rows, 2) with calibration start/end times
    """
    if group is None:
        group = len(start_times)

    # Calculate pixels per group
    pixels_per_group = n_pixels // group + 1

    # Calculate FLOPS and memory operations per group
    flops_per_group = _calibration_flops(pixels_per_group)
    mem_ops_per_group = _calibration_mem(pixels_per_group)

    # Calculate computation time per group
    computation_time = (
        compute_resources.total_time(mem_ops_per_group, flops_per_group) / scale
    )  # Apply scaling factor

    # Create timing array
    timings = np.zeros([len(start_times), 2])

    # First calibration starts after first camera data is ready
    timings[0, 0] = start_times[0, 1]
    timings[0, 1] = timings[0, 0] + computation_time

    # Subsequent calibrations follow their respective camera data
    for i in range(1, len(start_times)):
        timings[i, 0] = max(timings[i - 1, 1], start_times[i, 1])
        timings[i, 1] = timings[i, 0] + computation_time

    if debug:
        print("\n*************Pixel Calibration************")
        print(f"Total pixels: {n_pixels}")
        print(f"Pixels per group: {pixels_per_group}")
        print(f"FLOPS per group: {flops_per_group}")
        print(f"Memory operations per group: {mem_ops_per_group}")
        print(f"Computation time per group: {computation_time:.2f} μs")
        print(f"Total calibration time: {timings[-1, 1] - timings[0, 0]:.2f} μs")

    return timings

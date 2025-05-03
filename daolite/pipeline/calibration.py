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
    # Operations: dark subtraction, flat field division
    return 2 * n_pixels


def _calibration_mem(n_pixels: int, bit_depth: int) -> int:
    """
    Calculate memory operations for pixel calibration.

    Args:
        n_pixels: Number of pixels to calibrate

    Returns:
        int: Number of memory operations in bits
    """
    # Read pixel, read dark, read flat, write calibrated pixel
    return  bit_depth*n_pixels + 3*n_pixels*32


def PixelCalibration(
    n_pixels: int,
    compute_resources: ComputeResources,
    start_times: np.ndarray,
    n_workers: int = 1,
    bitdepth: int = 16,
    group: Optional[int] = None,
    scale: float = 1.0,
    debug: bool = False,
) -> np.ndarray:
    """
    Calculate timing for pixel calibration operations.

    Args:
        n_pixels: Total number of pixels to calibrate
        compute_resources: ComputeResources instance
        start_times: Array of shape (rows, 2) with start/end times from camera,
                     or a scalar value representing a single timing
        n_workers: Number of workers (default: 1)
        bitdepth: Bit depth of the pixel data (default: 16)
        group: Number of groups to process (default: use start_times length)
        scale: Computational scaling factor (default: 1.0)
        debug: Enable debug output

    Returns:
        np.ndarray: Array of shape (rows, 2) with calibration start/end times,
                    or a scalar value representing calibration time
    """
    # Check if start_times is a scalar value (float/int)
    is_scalar = np.isscalar(start_times)
    
    # If start_times is a scalar and group is None, set group to 1
    if is_scalar and group is None:
        group = 1
    # If start_times is an array and group is None, use its length
    elif not is_scalar and group is None:
        group = len(start_times)

    # Calculate pixels per group
    pixels_per_group = n_pixels // group + 1

    # Calculate FLOPS and memory operations per group
    flops_per_group = _calibration_flops(pixels_per_group)
    mem_ops_per_group = _calibration_mem(pixels_per_group, bitdepth)

    # Calculate computation time per group
    computation_time = (
        compute_resources.total_time(mem_ops_per_group, flops_per_group) / scale
    )  # Apply scaling factor

    if debug:
        print("\n*************Pixel Calibration************")
        print(f"Total pixels: {n_pixels}")
        print(f"Pixels per group: {pixels_per_group}")
        print(f"FLOPS per group: {flops_per_group}")
        print(f"Memory operations per group: {mem_ops_per_group}")
        print(f"Computation time per group: {computation_time:.2f} μs")
        
    # Handle scalar input - just return the computation time
    if is_scalar:
        if debug:
            print(f"Total calibration time: {computation_time:.2f} μs")
        return computation_time
        
    # Create timing array for non-scalar input
    timings = np.zeros([len(start_times), 2])

    # First calibration starts after first camera data is ready
    timings[0, 0] = start_times[0, 1]
    timings[0, 1] = timings[0, 0] + computation_time

    # Subsequent calibrations follow their respective camera data
    for i in range(1, len(start_times)):
        timings[i, 0] = max(timings[i - 1, 1], start_times[i, 1])
        timings[i, 1] = timings[i, 0] + computation_time

    if debug:
        print(f"Total calibration time: {timings[-1, 1] - timings[0, 0]:.2f} μs")

    return timings

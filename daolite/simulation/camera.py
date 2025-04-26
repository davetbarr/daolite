"""
Camera simulation module for modeling camera readout and data transfer timing.

This module provides timing estimation for camera readout and data transfer
operations in adaptive optics systems, with support for different camera
interfaces and readout modes.
"""

import numpy as np
from daolite.compute import ComputeResources


def PCOCamLink(
    compute_resources: ComputeResources,
    n_pixels: int,
    group: int = 50,
    readout: float = 500,
    debug: bool = False,
) -> np.ndarray:
    """
    Calculate timing for PCO camera with CameraLink interface.

    Args:
        compute_resources: ComputeResources instance
        n_pixels: Total number of pixels to read
        group: Number of readout groups (default: 50)
        readout: Camera readout time in microseconds (default: 500)
        debug: Enable debug output

    Returns:
        np.ndarray: Array of shape (group, 2) with readout start/end times
    """
    # Calculate pixels per group
    pixels_per_group = n_pixels // group + 1

    # Calculate time per group based on network speed
    bits_per_pixel = 16  # Assuming 16-bit pixels
    bits_per_group = pixels_per_group * bits_per_pixel
    transfer_time = compute_resources.network_time(bits_per_group)

    # Create timing array
    timings = np.zeros([group, 2])

    # First group starts after readout time
    timings[0, 0] = readout
    timings[0, 1] = timings[0, 0] + transfer_time

    # Subsequent groups follow immediately
    for i in range(1, group):
        timings[i, 0] = timings[i - 1, 1]
        timings[i, 1] = timings[i, 0] + transfer_time

    if debug:
        print("\n*************PCO CameraLink************")
        print(f"Total pixels: {n_pixels}")
        print(f"Pixels per group: {pixels_per_group}")
        print(f"Bits per group: {bits_per_group}")
        print(f"Transfer time per group: {transfer_time:.2f} μs")
        print(f"Total transfer time: {timings[-1, 1] - timings[0, 0]:.2f} μs")

    return timings


def GigeVisionCamera(
    compute_resources: ComputeResources,
    n_pixels: int,
    group: int = 50,
    readout: float = 600,
    debug: bool = False,
) -> np.ndarray:
    """
    Simulate a GigE Vision camera timing (placeholder logic).
    """
    # Placeholder: similar to PCOCamLink but with different readout
    return PCOCamLink(compute_resources, n_pixels, group, readout, debug)


def RollingShutterCamera(
    compute_resources: ComputeResources,
    n_pixels: int,
    group: int = 50,
    readout: float = 700,
    debug: bool = False,
) -> np.ndarray:
    """
    Simulate a rolling shutter camera timing (placeholder logic).
    """
    # Placeholder: similar to PCOCamLink but with different readout
    return PCOCamLink(compute_resources, n_pixels, group, readout, debug)

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
    Calculate timing for when pixels become available from a PCO camera with CameraLink interface.
    
    This function calculates only when pixels are available from the camera, 
    NOT including network transfer time which should be calculated separately.

    Args:
        compute_resources: ComputeResources instance
        n_pixels: Total number of pixels to read
        group: Number of readout groups (default: 50)
        readout: Camera readout time in microseconds (default: 500)
        debug: Enable debug output

    Returns:
        np.ndarray: Array of shape (group, 2) with pixel availability start/end times
    """
    # Calculate pixels per group
    pixels_per_group = n_pixels // group + 1
    
    # Calculate row spacing (time between groups becoming available)
    row_spacing = readout / group if group > 1 else readout / n_pixels
    
    # Create timing array
    timings = np.zeros([group, 2])
    
    # First group available after initial readout delay
    timings[0, 0] = row_spacing
    timings[0, 1] = timings[0, 0]  # End time equals start time (instantly available)
    
    # Subsequent groups become available at regular intervals
    for i in range(1, group):
        timings[i, 0] = timings[i-1, 0] + row_spacing
        timings[i, 1] = timings[i, 0]  # End time equals start time (instantly available)
    
    if debug:
        print("\n*************PCO CameraLink************")
        print(f"Total pixels: {n_pixels}")
        print(f"Pixels per group: {pixels_per_group}")
        print(f"Row spacing (time between groups): {row_spacing:.2f} μs")
        print(f"Total readout time: {timings[-1, 0] - timings[0, 0] + row_spacing:.2f} μs")
    
    return timings


def GigeVisionCamera(
    compute_resources: ComputeResources,
    n_pixels: int,
    group: int = 50,
    readout: float = 600,
    debug: bool = False,
) -> np.ndarray:
    """
    Calculate timing for when pixels become available from a GigE Vision camera.
    
    This function calculates only when pixels are available from the camera,
    NOT including network transfer time which should be calculated separately.

    Args:
        compute_resources: ComputeResources instance
        n_pixels: Total number of pixels to read
        group: Number of readout groups (default: 50)
        readout: Camera readout time in microseconds (default: 600)
        debug: Enable debug output

    Returns:
        np.ndarray: Array of shape (group, 2) with pixel availability start/end times
    """
    # GigE Vision cameras typically have different readout characteristics
    # but for simplicity, we'll use a similar model with adjusted timing
    
    # Calculate pixels per group
    pixels_per_group = n_pixels // group + 1
    
    # Calculate row spacing (time between groups becoming available)
    # GigE Vision typically has slightly different timing characteristics
    row_spacing = (readout / group) * 1.1 if group > 1 else (readout / n_pixels) * 1.1
    
    # Create timing array
    timings = np.zeros([group, 2])
    
    # First group available after initial readout delay
    timings[0, 0] = row_spacing
    timings[0, 1] = timings[0, 0]  # End time equals start time (instantly available)
    
    # Subsequent groups become available at regular intervals
    for i in range(1, group):
        timings[i, 0] = timings[i-1, 0] + row_spacing
        timings[i, 1] = timings[i, 0]  # End time equals start time (instantly available)
    
    if debug:
        print("\n*************GigE Vision Camera************")
        print(f"Total pixels: {n_pixels}")
        print(f"Pixels per group: {pixels_per_group}")
        print(f"Row spacing (time between groups): {row_spacing:.2f} μs")
        print(f"Total readout time: {timings[-1, 0] - timings[0, 0] + row_spacing:.2f} μs")
    
    return timings


def RollingShutterCamera(
    compute_resources: ComputeResources,
    n_pixels: int,
    group: int = 50,
    readout: float = 700,
    exposure_offset: float = 100,
    debug: bool = False,
) -> np.ndarray:
    """
    Calculate timing for when pixels become available from a rolling shutter camera.
    
    This function calculates only when pixels are available from the camera,
    NOT including network transfer time which should be calculated separately.
    Rolling shutter cameras expose different rows at different times, which 
    affects when pixels become available.

    Args:
        compute_resources: ComputeResources instance
        n_pixels: Total number of pixels to read
        group: Number of readout groups (default: 50)
        readout: Camera readout time in microseconds (default: 700)
        exposure_offset: Time offset between row exposures in microseconds (default: 100)
        debug: Enable debug output

    Returns:
        np.ndarray: Array of shape (group, 2) with pixel availability start/end times
    """
    # Calculate pixels per group
    pixels_per_group = n_pixels // group + 1
    
    # Calculate row spacing (time between groups becoming available)
    row_spacing = readout / group if group > 1 else readout / n_pixels
    
    # Create timing array
    timings = np.zeros([group, 2])
    
    # First group available after initial readout delay
    timings[0, 0] = row_spacing
    timings[0, 1] = timings[0, 0]  # End time equals start time (instantly available)
    
    # For rolling shutter, each subsequent group has an additional exposure offset
    for i in range(1, group):
        # Each group has staggered exposure start times
        timings[i, 0] = timings[i-1, 0] + row_spacing + (exposure_offset / group)
        timings[i, 1] = timings[i, 0]  # End time equals start time (instantly available)
    
    if debug:
        print("\n*************Rolling Shutter Camera************")
        print(f"Total pixels: {n_pixels}")
        print(f"Pixels per group: {pixels_per_group}")
        print(f"Row spacing (time between groups): {row_spacing:.2f} μs")
        print(f"Exposure offset per group: {exposure_offset / group:.2f} μs")
        print(f"Total readout time: {timings[-1, 0] - timings[0, 0] + row_spacing:.2f} μs")
    
    return timings

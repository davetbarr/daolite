"""
Pixel calibration module for adaptive optics.

This module provides functions for estimating computational latency
of pixel calibration operations in adaptive optics systems.
"""

import numpy as np

from daolite.compute import ComputeResources


def Descramble(
    compute_resources: ComputeResources,
    start_times: np.ndarray,
    pixel_agenda: np.ndarray,
    bitDepth: int = 16,
    nWorkers: int = 1,
    flop_scale: float = 1.0,
    mem_scale: float = 1.0,
    debug: bool = False,
) -> np.ndarray:
    """
    Calculate timing for pixel calibration operations.

    Args:
        compute_resources (ComputeResources): Compute resources for the operation
        start_times (np.ndarray): Array of start times for each pixel calibration
        pixel_agenda (np.ndarray): Pixel agenda for calibration
        bitDepth (int): Bit depth of the data
        nWorkers (int): Number of workers for parallel processing
        flop_scale (float): Scaling factor for FLOPS
        mem_scale (float): Scaling factor for memory operations
        debug (bool): If True, print debug information
    Returns:
        np.ndarray: Array of shape (rows, 2) with calibration start/end times,
                    or a scalar value representing calibration time
    """

    # Create timing array for non-scalar input
    timings = np.zeros([len(start_times), 2])
    mem_ops_per_group = pixel_agenda[0] * 8 + 2 * pixel_agenda[0] * 16
    flops_per_group = 9 * pixel_agenda[0]  # dark subtraction and flat field division
    memory_time = compute_resources.load_time(mem_ops_per_group) / mem_scale
    compute_time = compute_resources.calc_time(flops_per_group) / flop_scale

    # First calibration starts after first camera data is ready
    timings[0, 0] = start_times[0, 1]
    timings[0, 1] = timings[0, 0] + memory_time + compute_time

    # Subsequent calibrations follow their respective camera data
    for i in range(1, len(start_times)):
        mem_ops_per_group = pixel_agenda[i] * 8 + 2 * pixel_agenda[i] * 16
        flops_per_group = (
            9 * pixel_agenda[i]
        )  # dark subtraction and flat field division
        memory_time = compute_resources.load_time(mem_ops_per_group) / mem_scale
        compute_time = compute_resources.calc_time(flops_per_group) / flop_scale

        timings[i, 0] = max(timings[i - 1, 1], start_times[i, 1])
        timings[i, 1] = timings[i, 0] + memory_time + compute_time

    if debug:
        print(f"Total calibration time: {timings[-1, 1] - timings[0, 0]:.2f} μs")

    return timings

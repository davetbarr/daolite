"""
Pixel calibration module for adaptive optics.

This module provides functions for estimating computational latency
of pixel calibration operations in adaptive optics systems.
"""

import numpy as np
from daolite.compute import ComputeResources
from daolite.utils.algorithm_ops import _calibration_flops, _calibration_mem


def PixelCalibration(
    compute_resources: ComputeResources,
    start_times: np.ndarray,
    pixel_agenda: np.ndarray,
    bit_depth: int = 16,
    n_workers: int = 1,
    flop_scale: float = 1.0,
    mem_scale: float = 1.0,
    debug: bool = False,
) -> np.ndarray:
    """
    Calculate timing for pixel calibration operations using agenda-based API.

    Args:
        compute_resources (ComputeResources): Compute resources for the operation
        start_times (np.ndarray): Array of start times for each pixel calibration
        pixel_agenda (np.ndarray): Agenda specifying number of pixels per iteration
        bit_depth (int): Bit depth of the pixel data (default: 16)
        n_workers (int): Number of workers for parallel processing
        flop_scale (float): Scaling factor for FLOPS
        mem_scale (float): Scaling factor for memory operations
        debug (bool): Enable debug output
        
    Returns:
        np.ndarray: Array of shape (rows, 2) with calibration start/end times
    """
 
    # Create timing array
    timings = np.zeros([len(start_times), 2])
    
    # Process first calibration
    mem_ops_per_group = _calibration_mem(pixel_agenda[0], bit_depth)
    flops_per_group = _calibration_flops(pixel_agenda[0])
    memory_time = compute_resources.load_time(mem_ops_per_group) / mem_scale
    compute_time = compute_resources.calc_time(flops_per_group) / flop_scale

    # First calibration starts after first camera data is ready
    timings[0, 0] = start_times[0, 1]
    timings[0, 1] = timings[0, 0] + memory_time + compute_time
    
    if debug:
        total_load_time = memory_time
        total_compute_time = compute_time
    
    # Subsequent calibrations follow their respective camera data
    for i in range(1, len(start_times)):
        mem_ops_per_group = _calibration_mem(pixel_agenda[i], bit_depth)
        flops_per_group = _calibration_flops(pixel_agenda[i])
        memory_time = compute_resources.load_time(mem_ops_per_group) / mem_scale
        compute_time = compute_resources.calc_time(flops_per_group) / flop_scale
        
        timings[i, 0] = max(timings[i - 1, 1], start_times[i, 1])
        timings[i, 1] = timings[i, 0] + memory_time + compute_time
        
        if debug:
            total_load_time += memory_time
            total_compute_time += compute_time
            
    if debug:
        print("*************PixelCalibration************")
        print(f"Pixel agenda: {pixel_agenda}")
        print(f"Bit depth: {bit_depth}")
        print(f"Total calibration time: {timings[-1, 1] - timings[0, 0]:.2f} μs")
        print(f"  Total load time: {total_load_time:.2f} μs")
        print(f"  Total compute time: {total_compute_time:.2f} μs")
        print(f"FLOP scaling factor: {flop_scale}")
        print(f"Memory scaling factor: {mem_scale}")

    return timings

"""
Pyramid wavefront sensor centroider module for timing estimation.

This module provides timing estimation for pyramid wavefront sensor (PWFS) centroiding,
which differs from Shack-Hartmann sensors. The pyramid sensor splits incoming light into
four quadrants and measures intensity or slope differences across these quadrants.

Supports three operating modes:
- 'intensity': Direct intensity-based centroiding
- 'slopes': Slope-based centroiding (standard PWFS operation)
- 'ESC': Extended source correlation mode
"""

import numpy as np
from typing import Optional
from daolite.compute import ComputeResources


def PyramidCentroider(
    compute_resources: ComputeResources,
    start_times: np.ndarray,
    centroid_agenda: np.ndarray,
    mode: str = 'slopes',
    n_workers: int = 1,
    delay_start: int = 0,
    flop_scale: float = 1.0,
    mem_scale: float = 1.0,
    debug: bool = False,
) -> np.ndarray:
    """
    Pyramid wavefront sensor centroiding pipeline with timing estimation.

    Args:
        compute_resources (ComputeResources): Compute resources for the operation
        start_times (np.ndarray): Array of start times for each centroid operation
        centroid_agenda (np.ndarray): Agenda specifying number of subapertures per iteration
        mode (str): Operating mode - 'intensity', 'slopes', or 'ESC' (default: 'slopes')
        n_workers (int): Number of workers for parallel processing
        delay_start (int): Delay start index for processing
        flop_scale (float): Scaling factor for FLOPS
        mem_scale (float): Scaling factor for memory operations
        debug (bool): Enable debug output
        
    Returns:
        np.ndarray: Array of shape (rows, 2) with processing start/end times
        
    Raises:
        ValueError: If mode is not one of 'intensity', 'slopes', or 'ESC'
    """
    if mode not in ['intensity', 'slopes', 'ESC']:
        raise ValueError(f"Mode must be 'intensity', 'slopes', or 'ESC', got '{mode}'")
    
    iterations = start_times.shape[0]
    n_subs = centroid_agenda[0]
    timings = np.zeros([iterations, 2])

    # Process first group
    if n_subs == 0:
        total_time = 0
    else:
        total_time = _process_pyramid_group(
            n_subs, compute_resources, mode,
            flop_scale, mem_scale, debug
        )

    timings[0, 0] = start_times[delay_start, 1]
    timings[0, 1] = timings[0, 0] + total_time

    # Process remaining groups
    for i in range(1, iterations):
        n_subs = centroid_agenda[i]
        
        if n_subs == 0:
            total_time = 0
        else:
            total_time = _process_pyramid_group(
                n_subs,
                compute_resources,
                mode,
                flop_scale,
                mem_scale,
                False,  # Debug only first iteration
            )

        start = max(timings[i - 1, 1], start_times[i, 1])
        timings[i, 0] = start
        timings[i, 1] = timings[i, 0] + total_time
        
    if debug:
        print("*************PyramidCentroider************")
        print(f"Mode: {mode}")
        print(f"Timings: {timings}")
        print(f"Start times: {start_times}")
        print(f"Centroid agenda: {centroid_agenda}")

    return timings


def _process_pyramid_group(
    n_subs: int,
    compute_resources: ComputeResources,
    mode: str,
    flop_scale: float,
    mem_scale: float,
    debug: bool
) -> float:
    """
    Helper to process a group of pyramid subapertures with scaling factors.
    
    Calculates FLOPS and memory operations based on the pyramid sensor mode.
    
    Args:
        n_subs: Number of subapertures to process
        compute_resources: ComputeResources instance
        mode: Operating mode ('intensity', 'slopes', or 'ESC')
        flop_scale: Computational scaling factor for FLOPS
        mem_scale: Memory scaling factor for bandwidth
        debug: Enable debug output
        
    Returns:
        float: Total processing time with scaling applied
    """
    # Calculate operations based on mode
    if mode == 'intensity':
        # Intensity mode: normalize pixels + copy operation
        # Normalization: sum all pixels (2*n_subs operations) + divide by total (4 operations)
        norm_flops = 2 * n_subs + 4
        norm_mem = n_subs * 32
        
        # Copy operation
        copy_flops = n_subs
        copy_mem = n_subs * 32
        
        total_flops = norm_flops + copy_flops
        total_mem = norm_mem + copy_mem
        
    elif mode == 'slopes':
        # Slopes mode: normalize 4 quadrants + compute slopes + reference subtraction
        # Normalization: 2 operations per quadrant * 4 quadrants per sub + 4
        norm_flops = 2 * n_subs * 4 + 4
        norm_mem = n_subs * 32 * 4
        
        # Slope computation: 8 operations per subaperture (differences between quadrants)
        slope_flops = n_subs * 8
        slope_mem = n_subs * 32 * 4
        
        # Reference slope subtraction
        ref_slope_subtraction_flops = n_subs
        ref_slope_subtraction_mem = n_subs * 32
        
        total_flops = norm_flops + slope_flops + ref_slope_subtraction_flops
        total_mem = norm_mem + slope_mem + ref_slope_subtraction_mem

    elif mode == 'ESC':
        # Extended Source Correlation mode: similar to slopes but with more operations
        # Normalization across 4 quadrants
        norm_flops = 2 * n_subs * 4 + 4
        norm_mem = n_subs * 32 * 4
        
        # Extended slope computation: 16 operations per subaperture
        slope_flops = n_subs * 16
        slope_mem = n_subs * 32 * 4
        
        # Reference slope subtraction
        ref_slope_subtraction_flops = n_subs
        ref_slope_subtraction_mem = n_subs * 32
        
        total_flops = norm_flops + slope_flops + ref_slope_subtraction_flops
        total_mem = norm_mem + slope_mem + ref_slope_subtraction_mem
    
    # Apply scaling and compute times
    mem_time = compute_resources.load_time(total_mem) / mem_scale
    flops_time = compute_resources.calc_time(total_flops) / flop_scale
    total_time = flops_time + mem_time

    if debug:
        print(f"*************PyramidCentroider ({mode} mode)************")
        print(f"Number of subapertures: {n_subs}")
        print(f"Total FLOPS: {total_flops}")
        print(f"Total memory: {total_mem} bits")
        print(f"FLOPS time: {flops_time:.2f} μs")
        print(f"Memory time: {mem_time:.2f} μs")
        print(f"Total time: {total_time:.2f} μs")
        print(f"FLOP scaling factor: {flop_scale}")
        print(f"Memory scaling factor: {mem_scale}")

    return total_time

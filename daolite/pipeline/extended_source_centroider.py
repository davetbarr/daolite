"""
Extended source centroider module for wavefront sensing calculations and timing estimation.

This module provides timing estimation for extended source centroiding operations,
which require cross-correlation or square difference algorithms to determine centroids
(as opposed to point sources which compute centroids directly from pixel intensities).
"""

import numpy as np
from daolite.compute import ComputeResources
from daolite.utils.algorithm_ops import (
    _fft_flops,
    _fft_mem,
    _conjugate_flops,
    _conjugate_mem,
    _mmm_flops,
    _mmm_mem,
    _merge_sort_flops,
    _merge_sort_mem,
    _square_diff_flops,
    _square_diff_mem,
)


def CrossCorrelate(
    n_valid_subaps: int,
    n_pix_per_subap: int,
    compute_resources: ComputeResources,
    debug: bool = False,
) -> float:
    """
    Calculate timing for cross-correlation based centroiding.

    Args:
        n_valid_subaps: Number of valid subapertures
        n_pix_per_subap: Number of pixels per subaperture
        compute_resources: ComputeResources instance
        debug: Enable debug output

    Returns:
        float: Total processing time in microseconds
    """
    mem_load_per_subap = sum(
        [
            _fft_mem(n_pix_per_subap, n_pix_per_subap) * 32,
            _fft_mem(n_pix_per_subap, n_pix_per_subap) * 32,
            _conjugate_mem(n_pix_per_subap, n_pix_per_subap) * 32,
            _mmm_mem(n_pix_per_subap, n_pix_per_subap) * 32,
            _fft_mem(n_pix_per_subap, n_pix_per_subap) * 32,
        ]
    )

    total_mem_load = mem_load_per_subap * n_valid_subaps
    load_time = compute_resources.load_time(mem_load_per_subap)

    flops_per_subap = sum(
        [
            _fft_flops(n_pix_per_subap, n_pix_per_subap),
            _fft_flops(n_pix_per_subap, n_pix_per_subap),
            _conjugate_flops(n_pix_per_subap, n_pix_per_subap),
            _mmm_flops(n_pix_per_subap, n_pix_per_subap),
            _fft_flops(n_pix_per_subap, n_pix_per_subap),
        ]
    )

    total_flops = flops_per_subap * n_valid_subaps
    calc_time = compute_resources.calc_time(total_flops)
    total_time = load_time + calc_time

    if debug:
        print("*************CrossCorrelate************")
        print(f"Memory load per subap: {mem_load_per_subap}")
        print(f"Total memory load: {total_mem_load}")
        print(f"Load time: {load_time}")
        print(f"FLOPS per subap: {flops_per_subap}")
        print(f"Total FLOPS: {total_flops}")
        print(f"Calculation time: {calc_time}")
        print(f"Total time: {total_time}")

    return total_time


def Centroid(
    n_valid_subaps: int,
    n_pix_per_subap: int,
    compute_resources: ComputeResources,
    sort: bool = False,
    debug: bool = False,
) -> float:
    """
    Calculate timing for centroid computation.

    Args:
        n_valid_subaps: Number of valid subapertures
        n_pix_per_subap: Number of pixels per subaperture
        compute_resources: ComputeResources instance
        sort: Whether to sort the results
        debug: Enable debug output

    Returns:
        float: Total processing time in microseconds
    """
    sort_mem = _merge_sort_mem(n_pix_per_subap**2) * 32 if sort else 0
    sort_flops = _merge_sort_flops(n_pix_per_subap**2) if sort else 0

    mem_per_subap = (n_pix_per_subap * n_pix_per_subap * 32) + sort_mem
    total_mem = mem_per_subap * n_valid_subaps
    load_time = compute_resources.load_time(total_mem)

    flops_per_subap = (5 * n_pix_per_subap * n_pix_per_subap - 1) + sort_flops
    total_flops = flops_per_subap * n_valid_subaps
    calc_time = compute_resources.calc_time(total_flops)
    total_time = load_time + calc_time

    if debug:
        print("*************Centroid************")
        print(f"Memory per subap: {mem_per_subap}")
        print(f"Total memory: {total_mem}")
        print(f"Load time: {load_time}")
        print(f"FLOPS per subap: {flops_per_subap}")
        print(f"Total FLOPS: {total_flops}")
        print(f"Calculation time: {calc_time}")
        print(f"Total time: {total_time}")

    return total_time


def SquareDiff(
    n_valid_subaps: int,
    n_pix_per_subap: int,
    compute_resources: ComputeResources,
    debug: bool = False,
) -> float:
    """
    Calculate timing for square difference based centroiding.

    Args:
        n_valid_subaps: Number of valid subapertures
        n_pix_per_subap: Number of pixels per subaperture
        compute_resources: ComputeResources instance
        debug: Enable debug output

    Returns:
        float: Total processing time in microseconds
    """
    mem_load = (
        _square_diff_mem(n_pix_per_subap, n_pix_per_subap * 2) * 32 * n_valid_subaps
    )
    load_time = compute_resources.load_time(mem_load)

    flops = _square_diff_flops(n_pix_per_subap, n_pix_per_subap * 2) * n_valid_subaps
    calc_time = compute_resources.calc_time(flops)
    total_time = load_time + calc_time

    if debug:
        print("*************SquareDiff************")
        print(f"Memory load: {mem_load}")
        print(f"Load time: {load_time}")
        print(f"FLOPS: {flops}")
        print(f"Calculation time: {calc_time}")
        print(f"Total time: {total_time}")

    return total_time


def ReferenceSlopes(
    n_valid_subaps: int,
    n_pix_per_subap: int,
    compute_resources: ComputeResources,
    debug: bool = False,
) -> float:
    """
    Calculate timing for reference slopes computation.

    Args:
        n_valid_subaps: Number of valid subapertures
        n_pix_per_subap: Number of pixels per subaperture
        compute_resources: ComputeResources instance
        debug: Enable debug output

    Returns:
        float: Total processing time in microseconds
    """
    mem_load = 2 * n_valid_subaps * 32
    load_time = compute_resources.load_time(mem_load)

    flops = 2 * n_valid_subaps
    calc_time = compute_resources.calc_time(flops)
    total_time = load_time + calc_time

    if debug:
        print("*************ReferenceSlopes************")
        print(f"Memory load: {mem_load}")
        print(f"Load time: {load_time}")
        print(f"FLOPS: {flops}")
        print(f"Calculation time: {calc_time}")
        print(f"Total time: {total_time}")

    return total_time


def Error(
    n_valid_subaps: int,
    n_pix_per_subap: int,
    compute_resources: ComputeResources,
    debug: bool = False,
) -> float:
    """
    Calculate timing for error computation between measured and reference slopes.

    Args:
        n_valid_subaps: Number of valid subapertures
        n_pix_per_subap: Number of pixels per subaperture
        compute_resources: ComputeResources instance
        debug: Enable debug output

    Returns:
        float: Total processing time in microseconds
    """
    mem_load = 2 * n_valid_subaps * 32
    load_time = compute_resources.load_time(mem_load)

    flops = 8 * n_valid_subaps  # Includes subtraction and error computation
    calc_time = compute_resources.calc_time(flops)
    total_time = load_time + calc_time

    if debug:
        print("*************Error************")
        print(f"Memory load: {mem_load}")
        print(f"Load time: {load_time}")
        print(f"FLOPS: {flops}")
        print(f"Calculation time: {calc_time}")
        print(f"Total time: {total_time}")

    return total_time


def ExtendedSourceCentroider(
    compute_resources: ComputeResources,
    start_times: np.ndarray,
    centroid_agenda: np.ndarray,
    n_pix_per_subap: int,
    square_diff: bool = False,
    n_workers: int = 1,
    delay_start: int = 0,
    sort: bool = False,
    flop_scale: float = 1.0,
    mem_scale: float = 1.0,
    debug: bool = False,
) -> np.ndarray:
    """
    Extended source centroiding pipeline with cross-correlation or square difference.
    
    For extended sources, centroids cannot be computed directly from pixel intensities.
    This function uses either cross-correlation (FFT-based) or square difference algorithms
    to determine centroid positions.

    Args:
        compute_resources (ComputeResources): Compute resources for the operation
        start_times (np.ndarray): Array of start times for each centroid operation
        centroid_agenda (np.ndarray): Agenda specifying number of subapertures per iteration
        n_pix_per_subap (int): Number of pixels per subaperture
        square_diff (bool): Whether to use square difference algorithm (default: False, uses cross-correlation)
        n_workers (int): Number of workers for parallel processing
        delay_start (int): Delay start index for processing
        sort (bool): Whether to sort the results
        flop_scale (float): Scaling factor for FLOPS
        mem_scale (float): Scaling factor for memory operations
        debug (bool): Enable debug output
        
    Returns:
        np.ndarray: Array of shape (rows, 2) with processing start/end times
    """
    
    if np.sum(centroid_agenda) == 1:
        total_time = (
            Centroid(1, n_pix_per_subap, compute_resources, sort, debug)
            / n_workers
        )
        return np.array([[start_times[-1, 1], start_times[-1, 1] + total_time]])

    iterations = start_times.shape[0]
    n_subs = centroid_agenda[0]
    timings = np.zeros([iterations, 2])

    # Process first group
    if n_subs == 0:
        total_time = 0
    else:
        total_time = _process_extended_source_group(
            n_subs, n_pix_per_subap, compute_resources, square_diff, sort, 
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
            total_time = _process_extended_source_group(
                n_subs,
                n_pix_per_subap,
                compute_resources,
                square_diff,
                sort,
                flop_scale,
                mem_scale,
                False,
            )

        start = max(timings[i - 1, 1], start_times[i, 1])
        timings[i, 0] = start
        timings[i, 1] = timings[i, 0] + total_time
        
    if debug:
        print("*************ExtendedSourceCentroider************")
        print(f"Timings: {timings}")
        print(f"Start times: {start_times}")
        print(f"Centroid agenda: {centroid_agenda}")

    return timings


def _process_extended_source_group(
    n_subs: int,
    n_pix_per_subap: int,
    compute_resources: ComputeResources,
    square_diff: bool,
    sort: bool,
    flop_scale: float,
    mem_scale: float,
    debug: bool,
) -> float:
    """
    Helper to process a group of subapertures for extended sources with separate scaling factors.
    
    Args:
        n_subs: Number of subapertures to process
        n_pix_per_subap: Number of pixels per subaperture
        compute_resources: ComputeResources instance
        square_diff: Whether to use square difference algorithm
        sort: Whether to sort centroids
        flop_scale: Computational scaling factor for FLOPS
        mem_scale: Memory scaling factor for bandwidth
        debug: Enable debug output
        
    Returns:
        float: Total processing time with scaling applied
    """
    # Create a modified ComputeResources instance to apply scaling
    modified_resources = ComputeResources(
        hardware=compute_resources.hardware,
        memory_bandwidth=compute_resources.memory_bandwidth * mem_scale,
        flops=compute_resources.flops * flop_scale,
        network_speed=compute_resources.network_speed,
        time_in_driver=compute_resources.time_in_driver,
        core_fudge=compute_resources.core_fudge,
        mem_fudge=compute_resources.mem_fudge,
        network_fudge=compute_resources.network_fudge,
        adjust=compute_resources.adjust,
        cores=compute_resources.cores,
        core_frequency=compute_resources.core_frequency,
        flops_per_cycle=compute_resources.flops_per_cycle,
        memory_frequency=compute_resources.memory_frequency,
        memory_width=compute_resources.memory_width,
        memory_channels=compute_resources.memory_channels,
    )
    
    # Run operations with the modified resource
    if square_diff:
        corr_time = SquareDiff(n_subs, n_pix_per_subap, modified_resources, debug)
        cent_time = 0
    else:
        corr_time = CrossCorrelate(n_subs, n_pix_per_subap, modified_resources, debug)
        cent_time = Centroid(n_subs, n_pix_per_subap, modified_resources, sort, debug)

    ref_time = ReferenceSlopes(n_subs, n_pix_per_subap, modified_resources, debug)
    err_time = Error(n_subs, n_pix_per_subap, modified_resources, debug)

    if debug:
        print(f"FLOP scaling factor: {flop_scale}")
        print(f"Memory scaling factor: {mem_scale}")
        
    return corr_time + cent_time + ref_time + err_time

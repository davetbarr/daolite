"""
Reconstruction module for wavefront reconstruction timing estimation.

This module provides functions to estimate the computational time required for
wavefront reconstruction operations in an adaptive optics system using an
agenda-based API for consistent pipeline integration.
"""

import numpy as np

from daolite.compute import ComputeResources
from daolite.utils.algorithm_ops import _mvm_flops, _mvm_mem


def Reconstruction(
    compute_resources: ComputeResources,
    start_times: np.ndarray,
    centroid_agenda: np.ndarray,
    n_acts: int,
    flop_scale: float = 1.0,
    mem_scale: float = 1.0,
    n_workers: int = 1,
    debug: bool = False,
) -> np.ndarray:
    """
    Calculate timing for wavefront reconstruction operations using agenda-based API.

    For full-frame reconstruction (equivalent to old FullFrameReconstruction),
    simply pass a centroid_agenda with a single element containing all slopes.

    Args:
        compute_resources (ComputeResources): Compute resources for the operation
        start_times (np.ndarray): Array of shape (rows, 2) with start/end times
        centroid_agenda (np.ndarray): Agenda specifying number of slopes per iteration
        n_acts (int): Number of actuators
        flop_scale (float): Scaling factor for FLOPS (default: 1.0)
        mem_scale (float): Scaling factor for memory operations (default: 1.0)
        n_workers (int): Number of workers for parallel processing (default: 1)
        debug (bool): Enable debug output (default: False)

    Returns:
        np.ndarray: Array of shape (rows, 2) with processing start/end times

    Raises:
        ValueError: If input validation fails
    """
    # Validate inputs
    if centroid_agenda is None:
        raise ValueError("centroid_agenda cannot be None")
    if start_times is None:
        raise ValueError("start_times cannot be None")
    if start_times.shape[1] != 2:
        raise ValueError("start_times must have shape (rows, 2)")
    if start_times.shape[0] != centroid_agenda.shape[0]:
        raise ValueError(
            "start_times and centroid_agenda must have the same number of rows"
        )
    if n_acts <= 0:
        raise ValueError("n_acts must be greater than 0")

    timings = np.zeros([start_times.shape[0], 2])

    # Process first group
    total_time = _process_reconstruction_group(
        centroid_agenda[0], n_acts, compute_resources, flop_scale, mem_scale, debug
    )

    timings[0, 0] = start_times[0, 1]
    timings[0, 1] = timings[0, 0] + total_time

    if debug:
        summed_times = total_time

    # Process remaining groups
    for i in range(1, start_times.shape[0]):
        total_time = _process_reconstruction_group(
            centroid_agenda[i],
            n_acts,
            compute_resources,
            flop_scale,
            mem_scale,
            False,  # Debug only first iteration
        )

        start = max(timings[i - 1, 1], start_times[i, 1])
        timings[i, 0] = start
        timings[i, 1] = timings[i, 0] + total_time

        if debug:
            summed_times += total_time

    if debug:
        print("*************Reconstruction************")
        print(f"Centroid agenda: {centroid_agenda}")
        print(f"Number of groups: {start_times.shape[0]}")
        print(f"Total slopes: {2 * np.sum(centroid_agenda)}")
        print(f"Number of actuators: {n_acts}")
        print(f"Total reconstruction time: {summed_times:.2f} μs")
        print(f"FLOP scaling factor: {flop_scale}")
        print(f"Memory scaling factor: {mem_scale}")

    return timings


def _process_reconstruction_group(
    n_slopes: int,
    n_acts: int,
    compute_resources: ComputeResources,
    flop_scale: float = 1.0,
    mem_scale: float = 1.0,
    debug: bool = False,
) -> float:
    """
    Helper to process a reconstruction group with separate scaling factors.

    Args:
        n_slopes: Number of slopes to process
        n_acts: Number of actuators
        compute_resources: ComputeResources instance
        flop_scale: Computational scaling factor for FLOPS
        mem_scale: Memory scaling factor for bandwidth
        debug: Enable debug output

    Returns:
        float: Total processing time with scaling applied
    """
    # Each slope has X and Y components, so total slope values = 2 * n_slopes
    total_slope_values = 2 * n_slopes

    # Memory for slopes + actuators + reconstruction matrix
    # Matrix is (n_acts x total_slope_values), vector is total_slope_values, output is n_acts
    memory_to_load = _mvm_mem(n_acts, total_slope_values)
    load_time = compute_resources.load_time(memory_to_load) / mem_scale

    # Matrix-vector multiplication operations: (n_acts x total_slope_values) * (total_slope_values x 1)
    num_operations = _mvm_flops(n_acts, total_slope_values)
    calc_time = compute_resources.calc_time(num_operations) / flop_scale

    if debug:
        print("*************Reconstruction Group************")
        print(f"Number of slopes (subapertures): {n_slopes}")
        print(f"Total slope values (X+Y): {total_slope_values}")
        print(f"Number of actuators: {n_acts}")
        print(f"Matrix shape: ({n_acts} x {total_slope_values})")
        print(f"Memory to load: {memory_to_load} bits")
        print(f"Number of operations: {num_operations}")
        print(f"Load time: {load_time:.2f} μs")
        print(f"Calculation time: {calc_time:.2f} μs")
        print(f"Total time: {load_time + calc_time:.2f} μs")
        print(f"FLOP scaling factor: {flop_scale}")
        print(f"Memory scaling factor: {mem_scale}")

    return load_time + calc_time

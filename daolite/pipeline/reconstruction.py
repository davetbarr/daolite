"""
Reconstruction module for wavefront reconstruction timing estimation.

This module provides functions to estimate the computational time required for
wavefront reconstruction operations in an adaptive optics system.
"""

import numpy as np
from typing import Optional
from daolite.compute import ComputeResources


def FullFrameReconstruction(
    n_slopes: int,
    n_acts: int,
    compute_resources: ComputeResources,
    scale: float = 1.0,
    debug: bool = False,
) -> float:
    """
    Calculate timing for full-frame wavefront reconstruction.

    Args:
        n_slopes: Number of slope measurements
        n_acts: Number of actuators
        compute_resources: ComputeResources instance for hardware capabilities
        scale: Scaling factor for computation time (default: 1.0)
        debug: Enable debug output (default: False)

    Returns:
        float: Total processing time in microseconds
    """
    # Memory for slopes + actuators + reconstruction matrix
    memory_to_load = (n_slopes + n_acts + n_slopes * n_acts) * 32
    load_time = compute_resources.load_time(memory_to_load) / scale

    # Matrix-vector multiplication operations
    num_operations = 2 * n_slopes * n_acts
    calc_time = compute_resources.calc_time(num_operations) / scale

    total_time = load_time + calc_time

    if debug:
        print("*************FullFrameReconstruction************")
        print(f"Memory to load:   {memory_to_load}")
        print(f"Number of ops:    {num_operations}")
        print(f"Load time:        {load_time}")
        print(f"Calculation time: {calc_time}")
        print(f"Total time:       {total_time}")

    return total_time


def Reconstruction(
    n_slopes: int,
    n_acts: int,
    compute_resources: ComputeResources,
    start_times: np.ndarray,
    group: int = 50,
    scale: float = 1.0,
    n_workers: int = 1,
    agenda: Optional[np.ndarray] = None,
    debug: bool = False,
) -> np.ndarray:
    """
    Calculate timing for grouped wavefront reconstruction operations.

    Args:
        n_slopes: Total number of slope measurements
        n_acts: Number of actuators
        compute_resources: ComputeResources instance
        start_times: Array of shape (rows, 2) with start/end times
        group: Number of slopes per group (default: 50)
        scale: Scaling factor for computation time (default: 1.0)
        n_workers: Number of parallel workers (default: 1)
        agenda: Optional array or filename specifying slopes per iteration
        debug: Enable debug output (default: False)

    Returns:
        np.ndarray: Array of shape (rows, 2) with processing start/end times
    """
    # Support agenda as filename or array
    if agenda is not None and isinstance(agenda, str):
        try:
            agenda = np.load(agenda)
        except Exception:
            agenda = np.genfromtxt(agenda)

    n_slopes_per_group = _calculate_n_slopes(n_slopes, group, n_workers, agenda)
    timings = np.zeros([start_times.shape[0], 2])

    # Process first group
    if n_slopes_per_group == 0:
        total_time = 0
    else:
        total_time = _process_group(
            n_slopes_per_group, n_acts, compute_resources, scale
        )

    timings[0, 0] = start_times[0, 1]
    timings[0, 1] = timings[0, 0] + total_time

    # Process remaining groups
    for i in range(1, start_times.shape[0]):
        if agenda is not None:
            n_slopes_per_group = _calculate_n_slopes(
                n_slopes, group, n_workers, agenda[i : i + 1]
            )

        if n_slopes_per_group == 0:
            total_time = 0
        else:
            total_time = _process_group(
                n_slopes_per_group, n_acts, compute_resources, scale
            )

        start = max(timings[i - 1, 1], start_times[i, 1])
        timings[i, 0] = start
        timings[i, 1] = timings[i, 0] + total_time

    if debug:
        print("*************Reconstruction************")
        print(f"Memory per group: {4 * n_slopes_per_group * n_acts * 32}")
        print(f"Operations per group: {2 * n_slopes_per_group * n_acts}")

    return timings


def _calculate_n_slopes(
    n_slopes: int, group: int, n_workers: int, agenda: Optional[np.ndarray] = None
) -> int:
    """Helper to calculate number of slopes to process per group."""
    if agenda is not None:
        if agenda[0] == 0:
            return 0
        return (agenda[0] + n_workers - 1) // n_workers

    return (n_slopes + (group * n_workers) - 1) // (group * n_workers)


def _process_group(
    n_slopes: int, n_acts: int, compute_resources: ComputeResources, scale: float
) -> float:
    """Helper to process a group of slopes."""
    memory_to_load = 4 * n_slopes * n_acts * 32  # Double buffer for input/output
    load_time = compute_resources.load_time(memory_to_load)

    num_operations = 2 * n_slopes * n_acts  # Matrix-vector multiplication
    calc_time = compute_resources.calc_time(num_operations)

    return (load_time + calc_time) / scale

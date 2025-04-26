"""
Centroider module for wavefront sensing calculations and timing estimation.
"""

import numpy as np
from typing import Optional
from daolite.compute import ComputeResources


# FFT operation utilities
def _fft_flops(m: int, n: int) -> int:
    """Calculate number of FLOPS for FFT operation."""
    return 5 * m * n * np.log2(m)


def _fft_mem(m: int, n: int) -> int:
    """Calculate memory requirement for FFT operation."""
    return 2 * m * n


def _conjugate_flops(m: int, n: int) -> int:
    """Calculate FLOPS for complex conjugate operation."""
    return m * n


def _conjugate_mem(m: int, n: int) -> int:
    """Calculate memory for complex conjugate operation."""
    return m * n


def _mvm_flops(m: int, n: int) -> int:
    """Calculate FLOPS for matrix-vector multiplication."""
    return 2 * m * n


def _mvm_mem(m: int, n: int) -> int:
    """Calculate memory for matrix-vector multiplication."""
    return 2 * m * n


def _mmm_flops(m: int, n: int) -> int:
    """Calculate FLOPS for matrix-matrix multiplication."""
    return m * n


def _mmm_mem(m: int, n: int) -> int:
    """Calculate memory for matrix-matrix multiplication."""
    return 2 * m * n


def _merge_sort_flops(n: int) -> int:
    """Calculate FLOPS for merge sort operation."""
    return 2 * n * np.log2(n)


def _merge_sort_mem(n: int) -> int:
    """Calculate memory for merge sort operation."""
    return 2 * n


def _square_diff_flops(m: int, n: int) -> int:
    """Calculate FLOPS for square difference operation."""
    a = (2 * n**2) - 1
    b = m - n + 1
    return (a * (b**2)) + ((n**2) * (m - n + 1) ** 2)


def _square_diff_mem(m: int, n: int) -> int:
    """Calculate memory for square difference operation."""
    return m**2 + n**2


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


def Centroider(
    n_valid_subaps: int,
    n_pix_per_subap: int,
    compute_resources: ComputeResources,
    start_times: np.ndarray,
    group: int = 50,
    scale: float = 1.0,
    square_diff: bool = False,
    n_workers: int = 1,
    delay_start: int = 0,
    sort: bool = False,
    agenda: Optional[np.ndarray] = None,
    debug: bool = False,
) -> np.ndarray:
    """
    Main centroiding pipeline that handles timing for the complete centroiding process.

    Args:
        n_valid_subaps: Number of valid subapertures
        n_pix_per_subap: Number of pixels per subaperture
        compute_resources: ComputeResources instance
        start_times: Array of shape (rows, 2) with start/end times
        group: Number of subapertures per group
        scale: Scaling factor for computation time
        square_diff: Use square difference instead of cross-correlation
        n_workers: Number of parallel workers
        delay_start: Delay start time by N groups
        sort: Whether to sort centroids
        agenda: Optional array specifying number of subaps per iteration
        debug: Enable debug output

    Returns:
        np.ndarray: Array of shape (rows, 2) with processing start/end times
    """
    if n_valid_subaps == 1:
        total_time = (
            Centroid(n_valid_subaps, n_pix_per_subap, compute_resources, sort, debug)
            / n_workers
        )
        return np.array([[start_times[-1, 1], start_times[-1, 1] + total_time]])

    iterations = start_times.shape[0]
    n_subs = _calculate_n_subs(n_valid_subaps, group, n_workers, agenda)
    timings = np.zeros([iterations, 2])

    # Process first group
    if n_subs == 0:
        total_time = 0
    else:
        total_time = _process_group(
            n_subs, n_pix_per_subap, compute_resources, square_diff, sort, scale, debug
        )

    timings[0, 0] = start_times[delay_start, 1]
    timings[0, 1] = timings[0, 0] + total_time

    # Process remaining groups
    for i in range(1, iterations):
        if agenda is not None:
            n_subs = _calculate_n_subs(
                n_valid_subaps, group, n_workers, agenda[i : i + 1]
            )

        if n_subs == 0:
            total_time = 0
        else:
            total_time = _process_group(
                n_subs,
                n_pix_per_subap,
                compute_resources,
                square_diff,
                sort,
                scale,
                debug,
            )

        start = max(timings[i - 1, 1], start_times[i, 1])
        timings[i, 0] = start
        timings[i, 1] = timings[i, 0] + total_time

    return timings


def _calculate_n_subs(
    n_valid_subaps: int, group: int, n_workers: int, agenda: Optional[np.ndarray] = None
) -> int:
    """Helper to calculate number of subapertures to process."""
    if agenda is not None:
        if agenda[0] == 0:
            return 0
        return (agenda[0] + n_workers - 1) // n_workers

    return (n_valid_subaps + (group * n_workers) - 1) // (group * n_workers)


def _process_group(
    n_subs: int,
    n_pix_per_subap: int,
    compute_resources: ComputeResources,
    square_diff: bool,
    sort: bool,
    scale: float,
    debug: bool,
) -> float:
    """Helper to process a group of subapertures."""
    if square_diff:
        corr_time = SquareDiff(n_subs, n_pix_per_subap, compute_resources, debug)
        cent_time = 0
    else:
        corr_time = CrossCorrelate(n_subs, n_pix_per_subap, compute_resources, debug)
        cent_time = Centroid(n_subs, n_pix_per_subap, compute_resources, sort, debug)

    ref_time = ReferenceSlopes(n_subs, n_pix_per_subap, compute_resources, debug)
    err_time = Error(n_subs, n_pix_per_subap, compute_resources, debug)

    return (corr_time + cent_time + ref_time + err_time) / scale


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

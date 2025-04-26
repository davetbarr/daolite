"""
Control module for DM (Deformable Mirror) control timing estimation.

This module provides functions to estimate computational time for various
control operations in an adaptive optics system, including integration,
offset calculation, saturation handling, and DM power estimation.
"""

from daolite.compute import ComputeResources


# Operation complexity functions
def _integration_flops(m: int) -> int:
    """Calculate FLOPS for integration operation."""
    return 2 * m


def _integration_mem(m: int) -> int:
    """Calculate memory for integration operation."""
    return 2 * m


def _pid_flops(m: int) -> int:
    """Calculate FLOPS for PID control."""
    return 6 * m


def _pid_mem(m: int) -> int:
    """Calculate memory for PID control."""
    return 2 * m


def _offset_flops(m: int) -> int:
    """Calculate FLOPS for offset computation."""
    return m


def _offset_mem(m: int) -> int:
    """Calculate memory for offset computation."""
    return 2 * m


def _saturation_flops(m: int) -> int:
    """Calculate FLOPS for saturation handling."""
    return 2 * m


def _saturation_mem(m: int) -> int:
    """Calculate memory for saturation handling."""
    return 2 * m


def _dm_power_flops(m: int) -> int:
    """Calculate FLOPS for DM power estimation."""
    return 2 * m


def _dm_power_mem(m: int) -> int:
    """Calculate memory for DM power estimation."""
    return 2 * m


def Integrator(
    n_acts: int, compute_resources: ComputeResources, debug: bool = False
) -> float:
    """
    Calculate timing for integrator operation.

    Args:
        n_acts: Number of actuators
        compute_resources: ComputeResources instance
        debug: Enable debug output

    Returns:
        float: Total processing time in microseconds
    """
    mem_load = _integration_mem(n_acts) * 32
    load_time = compute_resources.load_time(mem_load)

    flops = _integration_flops(n_acts)
    calc_time = compute_resources.calc_time(flops)
    total_time = load_time + calc_time

    if debug:
        print("*************Integrator************")
        print(f"Memory load: {mem_load}")
        print(f"Load time: {load_time}")
        print(f"FLOPS: {flops}")
        print(f"Calculation time: {calc_time}")
        print(f"Total time: {total_time}")

    return total_time


def Offset(
    n_acts: int, compute_resources: ComputeResources, debug: bool = False
) -> float:
    """
    Calculate timing for offset computation.

    Args:
        n_acts: Number of actuators
        compute_resources: ComputeResources instance
        debug: Enable debug output

    Returns:
        float: Total processing time in microseconds
    """
    mem_load = _offset_mem(n_acts) * 32
    load_time = compute_resources.load_time(mem_load)

    flops = _offset_flops(n_acts)
    calc_time = compute_resources.calc_time(flops)
    total_time = load_time + calc_time

    if debug:
        print("*************Offset************")
        print(f"Memory load: {mem_load}")
        print(f"Load time: {load_time}")
        print(f"FLOPS: {flops}")
        print(f"Calculation time: {calc_time}")
        print(f"Total time: {total_time}")

    return total_time


def Saturation(
    n_acts: int, compute_resources: ComputeResources, debug: bool = False
) -> float:
    """
    Calculate timing for saturation handling.

    Args:
        n_acts: Number of actuators
        compute_resources: ComputeResources instance
        debug: Enable debug output

    Returns:
        float: Total processing time in microseconds
    """
    mem_load = _saturation_mem(n_acts) * 32
    load_time = compute_resources.load_time(mem_load)

    flops = _saturation_flops(n_acts)
    calc_time = compute_resources.calc_time(flops)
    total_time = load_time + calc_time

    if debug:
        print("*************Saturation************")
        print(f"Memory load: {mem_load}")
        print(f"Load time: {load_time}")
        print(f"FLOPS: {flops}")
        print(f"Calculation time: {calc_time}")
        print(f"Total time: {total_time}")

    return total_time


def DMPower(
    n_acts: int, compute_resources: ComputeResources, debug: bool = False
) -> float:
    """
    Calculate timing for DM power estimation.

    Args:
        n_acts: Number of actuators
        compute_resources: ComputeResources instance
        debug: Enable debug output

    Returns:
        float: Total processing time in microseconds
    """
    mem_load = _dm_power_mem(n_acts) * 32
    load_time = compute_resources.load_time(mem_load)

    flops = _dm_power_flops(n_acts)
    calc_time = compute_resources.calc_time(flops)
    total_time = load_time + calc_time

    if debug:
        print("*************DMPower************")
        print(f"Memory load: {mem_load}")
        print(f"Load time: {load_time}")
        print(f"FLOPS: {flops}")
        print(f"Calculation time: {calc_time}")
        print(f"Total time: {total_time}")

    return total_time


def FullFrameControl(
    n_acts: int,
    compute_resources: ComputeResources,
    scale: float = 1.0,
    combine: float = 1.0,
    overhead: float = 8.0,
    debug: bool = False,
) -> float:
    """
    Calculate timing for complete DM control pipeline.

    Args:
        n_acts: Number of actuators
        compute_resources: ComputeResources instance
        scale: Scaling factor for computation time (default: 1.0)
        combine: Combine factor for integration time (default: 1.0)
        overhead: Overhead time for control operations (default: 8.0)
        debug: Enable debug output (default: False)

    Returns:
        float: Total processing time in microseconds
    """
    int_time = Integrator(n_acts, compute_resources, debug) * combine * 2
    off_time = Offset(n_acts, compute_resources, debug)
    sat_time = Saturation(n_acts, compute_resources, debug)
    dmp_time = DMPower(n_acts, compute_resources, debug)

    # Add 8μs overhead time for control operations
    total_time = (int_time + off_time + sat_time + dmp_time) / scale + overhead

    if debug:
        print("*************FullFrameControl************")
        print(f"Integration time: {int_time}")
        print(f"Offset time: {off_time}")
        print(f"Saturation time: {sat_time}")
        print(f"DM Power time: {dmp_time}")
        print(f"Total time: {total_time}")

    return total_time

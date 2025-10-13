"""
Control module for DM (Deformable Mirror) control timing estimation.

This module provides functions to estimate computational time for various
control operations in an adaptive optics system, including integration,
offset calculation, saturation handling, and DM power estimation.
"""

from daolite.compute import ComputeResources
from daolite.utils.algorithm_ops import (
    _dm_power_flops,
    _dm_power_mem,
    _integration_flops,
    _integration_mem,
    _offset_flops,
    _offset_mem,
    _saturation_flops,
    _saturation_mem,
)


def Integrator(
    n_acts: int,
    compute_resources: ComputeResources,
    flop_scale: float = 1.0,
    mem_scale: float = 1.0,
    debug: bool = False,
) -> float:
    """
    Calculate timing for integrator operation.

    Args:
        n_acts: Number of actuators
        compute_resources: ComputeResources instance
        flop_scale: Computational scaling factor for FLOPS (default: 1.0)
        mem_scale: Memory bandwidth scaling factor (default: 1.0)
        debug: Enable debug output

    Returns:
        float: Total processing time in microseconds
    """
    mem_load = _integration_mem(n_acts) * 32
    load_time = compute_resources.load_time(mem_load) / mem_scale

    flops = _integration_flops(n_acts)
    calc_time = compute_resources.calc_time(flops) / flop_scale
    total_time = load_time + calc_time

    if debug:
        print("*************Integrator************")
        print(f"Memory load: {mem_load}")
        print(f"Load time: {load_time}")
        print(f"FLOPS: {flops}")
        print(f"Calculation time: {calc_time}")
        print(f"Total time: {total_time}")
        print(f"FLOP scaling factor: {flop_scale}")
        print(f"Memory scaling factor: {mem_scale}")

    return total_time


def Offset(
    n_acts: int,
    compute_resources: ComputeResources,
    flop_scale: float = 1.0,
    mem_scale: float = 1.0,
    debug: bool = False,
) -> float:
    """
    Calculate timing for offset computation.

    Args:
        n_acts: Number of actuators
        compute_resources: ComputeResources instance
        flop_scale: Computational scaling factor for FLOPS (default: 1.0)
        mem_scale: Memory bandwidth scaling factor (default: 1.0)
        debug: Enable debug output

    Returns:
        float: Total processing time in microseconds
    """
    mem_load = _offset_mem(n_acts) * 32
    load_time = compute_resources.load_time(mem_load) / mem_scale

    flops = _offset_flops(n_acts)
    calc_time = compute_resources.calc_time(flops) / flop_scale
    total_time = load_time + calc_time

    if debug:
        print("*************Offset************")
        print(f"Memory load: {mem_load}")
        print(f"Load time: {load_time}")
        print(f"FLOPS: {flops}")
        print(f"Calculation time: {calc_time}")
        print(f"Total time: {total_time}")
        print(f"FLOP scaling factor: {flop_scale}")
        print(f"Memory scaling factor: {mem_scale}")

    return total_time


def Saturation(
    n_acts: int,
    compute_resources: ComputeResources,
    flop_scale: float = 1.0,
    mem_scale: float = 1.0,
    debug: bool = False,
) -> float:
    """
    Calculate timing for saturation handling.

    Args:
        n_acts: Number of actuators
        compute_resources: ComputeResources instance
        flop_scale: Computational scaling factor for FLOPS (default: 1.0)
        mem_scale: Memory bandwidth scaling factor (default: 1.0)
        debug: Enable debug output

    Returns:
        float: Total processing time in microseconds
    """
    mem_load = _saturation_mem(n_acts) * 32
    load_time = compute_resources.load_time(mem_load) / mem_scale

    flops = _saturation_flops(n_acts)
    calc_time = compute_resources.calc_time(flops) / flop_scale
    total_time = load_time + calc_time

    if debug:
        print("*************Saturation************")
        print(f"Memory load: {mem_load}")
        print(f"Load time: {load_time}")
        print(f"FLOPS: {flops}")
        print(f"Calculation time: {calc_time}")
        print(f"Total time: {total_time}")
        print(f"FLOP scaling factor: {flop_scale}")
        print(f"Memory scaling factor: {mem_scale}")

    return total_time


def DMPower(
    n_acts: int,
    compute_resources: ComputeResources,
    flop_scale: float = 1.0,
    mem_scale: float = 1.0,
    debug: bool = False,
) -> float:
    """
    Calculate timing for DM power estimation.

    Args:
        n_acts: Number of actuators
        compute_resources: ComputeResources instance
        flop_scale: Computational scaling factor for FLOPS (default: 1.0)
        mem_scale: Memory bandwidth scaling factor (default: 1.0)
        debug: Enable debug output

    Returns:
        float: Total processing time in microseconds
    """
    mem_load = _dm_power_mem(n_acts) * 32
    load_time = compute_resources.load_time(mem_load) / mem_scale

    flops = _dm_power_flops(n_acts)
    calc_time = compute_resources.calc_time(flops) / flop_scale
    total_time = load_time + calc_time

    if debug:
        print("*************DMPower************")
        print(f"Memory load: {mem_load}")
        print(f"Load time: {load_time}")
        print(f"FLOPS: {flops}")
        print(f"Calculation time: {calc_time}")
        print(f"Total time: {total_time}")
        print(f"FLOP scaling factor: {flop_scale}")
        print(f"Memory scaling factor: {mem_scale}")

    return total_time


def FullFrameControl(
    n_acts: int,
    compute_resources: ComputeResources,
    flop_scale: float = 1.0,
    mem_scale: float = 1.0,
    combine: float = 1.0,
    overhead: float = 8.0,
    debug: bool = False,
    **kwargs,  # To catch legacy 'scale' parameter
) -> float:
    """
    Calculate timing for complete DM control pipeline.

    Args:
        n_acts: Number of actuators
        compute_resources: ComputeResources instance
        flop_scale: Computational scaling factor for FLOPS (default: 1.0)
        mem_scale: Memory bandwidth scaling factor (default: 1.0)
        combine: Combine factor for integration time (default: 1.0)
        overhead: Overhead time for control operations (default: 8.0)
        debug: Enable debug output (default: False)
        **kwargs: Catches legacy parameters (e.g., 'scale')

    Returns:
        float: Total processing time in microseconds
    """
    # For backward compatibility - check for legacy scale parameter
    if "scale" in kwargs and kwargs["scale"] != 1.0:
        if flop_scale == 1.0 and mem_scale == 1.0:
            flop_scale = kwargs["scale"]
            mem_scale = kwargs["scale"]
            if debug:
                print(
                    f"Warning: Using legacy 'scale' parameter ({kwargs['scale']}). Consider using flop_scale and mem_scale instead."
                )

    int_time = (
        Integrator(n_acts, compute_resources, flop_scale, mem_scale, debug)
        * combine
        * 2
    )
    off_time = Offset(n_acts, compute_resources, flop_scale, mem_scale, debug)
    sat_time = Saturation(n_acts, compute_resources, flop_scale, mem_scale, debug)
    dmp_time = DMPower(n_acts, compute_resources, flop_scale, mem_scale, debug)

    # Add overhead time for control operations
    total_time = int_time + off_time + sat_time + dmp_time + overhead

    if debug:
        print("*************FullFrameControl************")
        print(f"Integration time: {int_time}")
        print(f"Offset time: {off_time}")
        print(f"Saturation time: {sat_time}")
        print(f"DM Power time: {dmp_time}")
        print(f"Total time: {total_time}")
        print(f"FLOP scaling factor: {flop_scale}")
        print(f"Memory scaling factor: {mem_scale}")

    return total_time

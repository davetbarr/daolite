"""
Deformable Mirror simulation module for modeling terminal points in a pipeline.

This module provides timing estimation for deformable mirror components that accept data from 
the pipeline and represent terminal endpoint devices that receive network communications.
The DM model handles both network transfers and PCIe transfers when needed.
"""

import numpy as np
from daolite.compute import ComputeResources
from daolite.utils.network import network_transfer, pcie_transfer


def StandardDM(
    compute_resources: ComputeResources,
    start_times: np.ndarray,
    n_actuators: int = 5000,
    bits_per_actuator: int = 16,
    debug: bool = False,
) -> np.ndarray:
    """
    Calculate timing for a standard deformable mirror endpoint, including network transfers.
    
    This function represents a network endpoint that receives commands for a DM.
    It calculates network transfer times from the source component to the DM.
    If the source component is on a GPU, it also calculates PCIe transfer time.

    Args:
        compute_resources: ComputeResources instance of the source component
        start_times: Array of shape (rows, 2) with start/end times from previous component
        n_actuators: Number of DM actuators (default: 5000)
        bits_per_actuator: Bits per actuator value (default: 16)
        debug: Enable debug output

    Returns:
        np.ndarray: Array of shape (rows, 2) with data reception times
    """
    # Calculate total data size
    n_bits = n_actuators * bits_per_actuator
    
    # Check if start_times is a scalar value (float/int)
    is_scalar = np.isscalar(start_times)
    
    # Calculate number of groups
    if is_scalar:
        # For scalar inputs, set group to 1
        group = 1
    else:
        # For array inputs, use the length
        group = len(start_times)
        
    # First, check if we need PCIe transfer (source on GPU)
    if hasattr(compute_resources, 'is_gpu') and compute_resources.is_gpu:
        if debug:
            print("\n*************DM PCIe Transfer************")
            print(f"Source component is on GPU, performing PCIe transfer")
            print(f"Total actuators: {n_actuators}")
            print(f"Bits per actuator: {bits_per_actuator}")
            print(f"Total bits: {n_bits}")
        
        # Calculate PCIe transfer timings
        pcie_timings = pcie_transfer(
            n_bits=n_bits,
            compute_resources=compute_resources,
            start_times=start_times,
            group=group,
            debug=debug
        )
        
        # Use PCIe timings as the start for network transfer
        transfer_start_times = pcie_timings
    else:
        # No PCIe transfer needed
        transfer_start_times = start_times
    
    # Calculate network transfer to DM
    # The DM inherits network speed from the computer it's attached to
    transfer_timings = network_transfer(
        n_bits=n_bits,
        compute_resources=compute_resources,
        start_times=transfer_start_times,
        group=group,
        debug=debug
    )
    
    if debug:
        print("\n*************DM Endpoint************")
        print(f"Groups: {group}")
        print(f"Total actuators: {n_actuators}")
        print(f"Bits per actuator: {bits_per_actuator}")
        print(f"Total bits: {n_bits}")
        
        if is_scalar:
            print(f"Received at: {transfer_timings:.2f} μs")
        else:
            print(f"First group received at: {transfer_timings[0, 0]:.2f} μs")
            print(f"Last group received at: {transfer_timings[-1, 1]:.2f} μs")
    
    return transfer_timings


def DMController(
    compute_resources: ComputeResources,
    start_times: np.ndarray,
    n_actuators: int = 5000,
    bits_per_actuator: int = 16,
    debug: bool = False,
) -> np.ndarray:
    """
    Network endpoint for DM controller, including network transfers.
    
    This function is a specialized version of StandardDM for controller-type DMs.

    Args:
        compute_resources: ComputeResources instance
        start_times: Array of shape (rows, 2) with start/end times from previous component
        n_actuators: Number of DM actuators (default: 5000)
        bits_per_actuator: Bits per actuator value (default: 16)
        debug: Enable debug output

    Returns:
        np.ndarray: Array of shape (rows, 2) with data reception times
    """
    # Use the StandardDM implementation with DMController specifics
    return StandardDM(
        compute_resources, 
        start_times, 
        n_actuators=n_actuators,
        bits_per_actuator=bits_per_actuator,
        debug=debug
    )


def WavefrontCorrector(
    compute_resources: ComputeResources,
    start_times: np.ndarray,
    n_actuators: int = 5000,
    bits_per_actuator: int = 16,
    debug: bool = False,
) -> np.ndarray:
    """
    Network endpoint for wavefront corrector, including network transfers.
    
    This is a specialized version of StandardDM for wavefront corrector DMs.

    Args:
        compute_resources: ComputeResources instance
        start_times: Array of shape (rows, 2) with start/end times from previous component
        n_actuators: Number of DM actuators (default: 5000) 
        bits_per_actuator: Bits per actuator value (default: 16)
        debug: Enable debug output

    Returns:
        np.ndarray: Array of shape (rows, 2) with data reception times
    """
    # Use the StandardDM implementation with WavefrontCorrector specifics
    return StandardDM(
        compute_resources, 
        start_times, 
        n_actuators=n_actuators,
        bits_per_actuator=bits_per_actuator,
        debug=debug
    )
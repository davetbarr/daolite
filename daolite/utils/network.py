"""
Network timing module for estimating data transfer times.

This module provides utilities for calculating network and PCIe transfer times
in adaptive optics systems, including bandwidth calculations, switch delays,
and driver overhead estimation.
"""

import numpy as np
from daolite.compute import ComputeResources


def TimeOnNetwork(
    n_bits: int, compute_resources: ComputeResources, debug: bool = False
) -> float:
    """
    Calculate time spent on network transfer.

    Args:
        n_bits: Number of bits to transfer
        compute_resources: ComputeResources instance
        debug: Enable debug output

    Returns:
        float: Network transfer time in microseconds
    """
    time = compute_resources.network_time(n_bits)
    if debug:
        print(f"Time on Network: {time}")
    return time


def network_transfer(
    n_bits: int, compute_resources: ComputeResources, debug: bool = False,
    use_dest_network: bool = False, dest_network_speed: float = None,
    dest_time_in_driver: float = None, start_times=None, group=None, **kwargs
) -> np.ndarray:
    """
    Calculate time spent on network transfer.

    Args:
        n_bits: Number of bits to transfer
        compute_resources: ComputeResources instance 
        debug: Enable debug output
        use_dest_network: If True, use destination network speed (for camera connections)
        dest_network_speed: Network speed of destination compute (for camera connections)
        dest_time_in_driver: Time in driver of destination compute (for camera connections)
        start_times: Array of start/end times from source component (for timing propagation)
        group: Number of groups to process (used with start_times)
        **kwargs: Additional parameters

    Returns:
        float or np.ndarray: Network transfer time in microseconds or array of transfer timings
    """
    # Check if we're dealing with a camera or other component that passes timing data
    if start_times is not None and isinstance(start_times, np.ndarray) and len(start_times.shape) == 2:
        # We're propagating timing data through the network
        if group is None:
            group = len(start_times)
        
        # Calculate bits per group
        bits_per_group = n_bits // group
        
        # Determine which network speed to use
        if use_dest_network and dest_network_speed is not None:
            network_speed = dest_network_speed
            driver_overhead = dest_time_in_driver if dest_time_in_driver is not None else 5.0
        else:
            network_speed = compute_resources.network_speed
            driver_overhead = compute_resources.time_in_driver
            
        # Calculate transfer time per group
        transfer_time = (bits_per_group / network_speed) * 1e6  # Convert to microseconds
        total_time_per_group = transfer_time + (driver_overhead * 2)  # Driver overhead at both ends
        
        # Create timing array for network transfers
        network_timings = np.zeros_like(start_times)
        
        # First group starts transfer as soon as source data is available
        network_timings[0, 0] = start_times[0, 1]  # Start when source data is ready
        network_timings[0, 1] = network_timings[0, 0] + total_time_per_group
        
        # Subsequent groups start when previous transfer ends AND source data is available
        for i in range(1, len(start_times)):
            # Start when both previous transfer is complete AND source data is available
            network_timings[i, 0] = max(network_timings[i-1, 1], start_times[i, 1])
            network_timings[i, 1] = network_timings[i, 0] + total_time_per_group
        
        if debug:
            print(f"Camera network transfer for {n_bits/8:.2f} bytes: {total_time_per_group:.2f} µs per group")
            print(f"  - Pure transfer: {transfer_time:.2f} µs at {network_speed/1e9:.1f} Gbps")
            print(f"  - Driver overhead: {(total_time_per_group-transfer_time):.2f} µs")
            print(f"  - Total time across all groups: {network_timings[-1, 1] - network_timings[0, 0]:.2f} µs")
        
        return network_timings
    
    # SPECIAL CASE: For camera components without timing data, we use the destination compute's network speed
    elif use_dest_network and dest_network_speed is not None:
        # Calculate transfer time based on bits and network speed
        transfer_time = (n_bits / dest_network_speed) * 1e6  # Convert to microseconds
        
        # Add driver overhead if specified
        if dest_time_in_driver is not None:
            total_time = transfer_time + (dest_time_in_driver * 2)  # Driver overhead at both ends
        else:
            total_time = transfer_time + 10.0  # Default 10µs overhead
            
        if debug:
            print(f"Camera network transfer for {n_bits/8:.2f} bytes: {total_time:.2f} µs")
            print(f"  - Pure transfer: {transfer_time:.2f} µs at {dest_network_speed/1e9:.1f} Gbps")
            print(f"  - Driver overhead: {(total_time-transfer_time):.2f} µs")
        return total_time
    
    # Standard case: use the compute_resources of the source component
    time = compute_resources.network_time(n_bits)
    if debug:
        print(f"Network transfer for {n_bits/8:.2f} bytes: {time:.2f} µs")
    return time


def pcie_transfer(
    n_bits: int, compute_resources: ComputeResources, debug: bool = False
) -> float:
    """
    Calculate time spent on PCIe transfer between CPU and GPU.

    Args:
        n_bits: Number of bits to transfer
        compute_resources: ComputeResources instance
        debug: Enable debug output

    Returns:
        float: PCIe transfer time in microseconds
    """
    # For PCIe transfers, we assume:
    # 1. A basic driver overhead for initiating the transfer
    # 2. The actual transfer time based on PCIe bandwidth
    # 3. An additional overhead for completion
    
    # Default to PCIe Gen4 x16 if compute_resources doesn't specify
    pcie_gen = getattr(compute_resources, 'pcie_gen', 4)
    
    # Calculate the transfer time using the pcie_bus function
    transfer_time = pcie_bus(n_bits, gen=pcie_gen, debug=False) * 1e6  # Convert to µs
    
    # Add driver overhead
    driver_overhead = getattr(compute_resources, 'time_in_driver', 5.0)  # µs
    total_time = transfer_time + driver_overhead * 2  # Overhead at both ends
    
    if debug:
        print(f"PCIe transfer for {n_bits/8:.2f} bytes: {total_time:.2f} µs")
        print(f"  - Pure transfer: {transfer_time:.2f} µs")
        print(f"  - Driver overhead: {driver_overhead * 2:.2f} µs")
    
    return total_time


def calculate_memory_bandwidth(
    memory_speed_mts: float = 4800, bus_width_bits: int = 64
) -> float:
    """
    Calculate memory bandwidth in GB/s.

    Args:
        memory_speed_mts: Memory speed in megatransfers per second
        bus_width_bits: Memory bus width in bits

    Returns:
        float: Memory bandwidth in gigabytes per second
    """
    memory_speed_tps = memory_speed_mts * 10**6  # Convert to transfers/sec
    bandwidth_bps = memory_speed_tps * bus_width_bits  # bits per second
    return bandwidth_bps / (8 * 10**9)  # Convert to GB/s


def calculate_switch_time(frame_size_bytes: int, speed_gbe: float) -> float:
    """
    Calculate network switch traversal time.

    Args:
        frame_size_bytes: Size of network frame in bytes
        speed_gbe: Network speed in gigabits per second

    Returns:
        float: Switch traversal time in microseconds
    """
    frame_size_bits = frame_size_bytes * 8
    speed_bps = speed_gbe * 10**9
    return (frame_size_bits / speed_bps) * 10**6


def calculate_driver_delay(n_bits: int, debug: bool = False) -> float:
    """
    Calculate network driver processing delay.

    Args:
        n_bits: Number of bits to process
        debug: Enable debug output

    Returns:
        float: Driver processing time in microseconds
    """
    bandwidth = calculate_memory_bandwidth()
    load_time = (n_bits / bandwidth) * 0.8

    flops = n_bits
    calc_time = (flops / (16 * 2.6e9)) * 0.8  # Assuming 16 cores at 2.6GHz
    total_time = load_time + calc_time

    if debug:
        print("*************Driver Delay************")
        print(f"Memory load: {n_bits}")
        print(f"Bandwidth: {bandwidth}")
        print(f"Load time: {load_time}")
        print(f"FLOPS: {flops}")
        print(f"Calculation time: {calc_time}")
        print(f"Total time: {total_time}")

    return total_time


def estimate_transfer_time_us(
    data_size: int,
    bandwidth: float,
    cable_length: float,
    driver_overhead: float = 5,
    num_switch_hops: int = 0,
    debug: bool = False,
) -> float:
    """
    Estimate total network transfer time including propagation and processing delays.

    Args:
        data_size: Size of data packet in bytes
        bandwidth: Network bandwidth in bytes per second
        cable_length: Cable length in meters between hops
        driver_overhead: Driver processing overhead in microseconds (default: 5)
        num_switch_hops: Number of network switches in path (default: 0)
        debug: Enable debug output

    Returns:
        float: Estimated total transfer time in microseconds
    """
    speed_of_light = 3e8  # meters per second
    time_in_switch = calculate_switch_time(data_size, bandwidth)
    driver_overhead2 = calculate_driver_delay(data_size, debug)

    # Propagation delays
    prop_delay_per_hop = (cable_length / speed_of_light) * 1e6 + time_in_switch
    total_prop_delay = prop_delay_per_hop * (1 + num_switch_hops)

    # Data transmission time
    transmission_time = (data_size * 8 / bandwidth) * 1e6

    # Total transfer time
    total_time = total_prop_delay + transmission_time + (driver_overhead * 2)

    if debug:
        print("\n*************Network Transfer************")
        print(f"Data size: {data_size} bytes")
        print(f"Bandwidth: {bandwidth:.2e} bps")
        print(f"Cable length: {cable_length} meters")
        print(f"Driver overhead: {driver_overhead} μs")
        print(f"Additional driver delay: {driver_overhead2} μs")
        print(f"Switch hops: {num_switch_hops}")
        print(f"Time in switch: {time_in_switch:.2f} μs")
        print(f"Propagation delay per hop: {prop_delay_per_hop:.2f} μs")
        print(f"Total propagation delay: {total_prop_delay:.2f} μs")
        print(f"Transmission time: {transmission_time:.2f} μs")
        print(f"Total transfer time: {total_time:.2f} μs")

    return total_time


def pcie_bus(n_bits: int, gen: int = 5, debug: bool = False) -> float:
    """
    Calculate PCIe bus transfer time.

    Args:
        n_bits: Number of bits to transfer
        gen: PCIe generation (1-5, default: 5)
        debug: Enable debug output

    Returns:
        float: Transfer time in seconds
    """
    # PCIe bandwidth calculation (16 lanes)
    bandwidths = {
        5: 16 * 8 * 64 * 10**9,  # Gen 5: 64 GT/s
        4: 16 * 8 * 32 * 10**9,  # Gen 4: 32 GT/s
        3: 16 * 8 * 8 * 10**9,  # Gen 3: 8 GT/s
        2: 16 * 8 * 5 * 10**9,  # Gen 2: 5 GT/s
        1: 16 * 8 * 2 * 10**9,  # Gen 1: 2 GT/s
    }

    if gen not in bandwidths:
        raise ValueError(f"Unknown PCIe generation: {gen}")

    bandwidth = bandwidths[gen]
    transfer_time = n_bits / bandwidth

    if debug:
        print(f"PCIe Gen {gen} x16 bandwidth: {bandwidth:.2e} B/s")
        print(f"Transfer time: {transfer_time:.2e} seconds")

    return transfer_time


def PCIE(
    n_bits: int,
    compute_resources: ComputeResources,
    start_times: np.ndarray,
    scale: float = 1.0,
    gen: int = 5,
    debug: bool = False,
) -> np.ndarray:
    """
    Calculate PCIe transfer timing for grouped data transfers.

    Args:
        n_bits: Total number of bits to transfer
        compute_resources: ComputeResources instance
        start_times: Array of shape (rows, 2) with start/end times
        scale: Scaling factor for computation time (default: 1.0)
        gen: PCIe generation (default: 5)
        debug: Enable debug output

    Returns:
        np.ndarray: Array of shape (rows, 2) with transfer start/end times
    """
    group = len(start_times)
    chunk_size = n_bits // group + 1

    load_time = compute_resources.load_time(chunk_size) / 0.125
    transfer_time = pcie_bus(chunk_size, gen, debug)
    total_time = load_time + transfer_time

    timings = np.zeros([start_times.shape[0], 2])
    timings[0, 0] = start_times[0, 1]
    timings[0, 1] = timings[0, 0] + total_time

    for i in range(1, start_times.shape[0]):
        start = max(timings[i - 1, 1], start_times[i, 1])
        timings[i, 0] = start
        timings[i, 1] = timings[i, 0] + total_time

    return timings


def CameraDataTransfer(
    compute_resources: ComputeResources,
    pixel_availability_timings: np.ndarray,
    n_pixels: int,
    bits_per_pixel: int = 16,
    debug: bool = False,
) -> np.ndarray:
    """
    Calculate network transfer timing for camera data based on pixel availability.

    This function takes the pixel availability timing from the camera and calculates
    when those pixels will be transferred over the network.

    Args:
        compute_resources: ComputeResources instance
        pixel_availability_timings: Array from camera with pixel availability times
        n_pixels: Total number of pixels to transfer
        bits_per_pixel: Number of bits per pixel (default: 16 for 16-bit pixels)
        debug: Enable debug output

    Returns:
        np.ndarray: Array of shape (groups, 2) with network transfer start/end times
    """
    group = len(pixel_availability_timings)
    pixels_per_group = n_pixels // group + 1
    bits_per_group = pixels_per_group * bits_per_pixel
    
    # Calculate network transfer time for each group
    transfer_time = compute_resources.network_time(bits_per_group)
    
    # Create timing array for network transfers
    network_timings = np.zeros_like(pixel_availability_timings)
    
    # First group starts transfer as soon as pixels are available
    network_timings[0, 0] = pixel_availability_timings[0, 1]
    network_timings[0, 1] = network_timings[0, 0] + transfer_time
    
    # Subsequent groups start transfer when previous transfer ends AND pixels are available
    for i in range(1, group):
        # Start when both previous transfer is complete AND pixels are available
        network_timings[i, 0] = max(network_timings[i-1, 1], pixel_availability_timings[i, 1])
        network_timings[i, 1] = network_timings[i, 0] + transfer_time
    
    if debug:
        print("\n*************Camera Data Network Transfer************")
        print(f"Total pixels: {n_pixels}")
        print(f"Pixels per group: {pixels_per_group}")
        print(f"Bits per group: {bits_per_group}")
        print(f"Transfer time per group: {transfer_time:.2f} μs")
        print(f"Total transfer time: {network_timings[-1, 1] - network_timings[0, 0]:.2f} μs")
        print(f"First group available: {pixel_availability_timings[0, 1]:.2f} μs")
        print(f"First group transfer start: {network_timings[0, 0]:.2f} μs")
        print(f"Last group available: {pixel_availability_timings[-1, 1]:.2f} μs")
        print(f"Last group transfer end: {network_timings[-1, 1]:.2f} μs")
    
    return network_timings

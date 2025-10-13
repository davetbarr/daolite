.. _hardware_compute_resources:

Compute Resources
=================

Overview
--------

The Compute Resources module in daolite provides detailed models of various computing hardware to accurately estimate the performance of AO pipeline components. This module allows users to:

1. Define custom hardware specifications
2. Use pre-defined hardware profiles
3. Compare performance across different systems
4. Model heterogeneous computing (CPU + GPU)

Hardware Model Components
-------------------------

CPU Resources
~~~~~~~~~~~~~

CPU resources are modeled with the following parameters:

- **Number of cores**: Physical CPU cores available
- **Core frequency**: Clock speed of CPU cores in Hz
- **FLOPS per cycle**: Floating point operations per clock cycle (vectorization capability)
- **Memory channels**: Number of memory channels
- **Memory width**: Width of each memory channel in bits
- **Memory frequency**: Memory clock frequency in Hz
- **Network speed**: Network interface speed in bits/second
- **Driver time**: Overhead for kernel/driver interactions

.. code-block:: python

    # Example: Creating custom CPU resources
    from daolite.compute import ComputeResources
    
    # Define an AMD EPYC server
    cpu = ComputeResources(
        hardware="CPU",
        cores=64,
        core_frequency=2.45e9,  # 2.45 GHz
        flops_per_cycle=32,    # AVX-512 support
        memory_channels=8,
        memory_width=64,       # 64 bits per channel
        memory_frequency=3200e6,  # 3200 MHz
        network_speed=100e9,   # 100 Gbps
        time_in_driver=5       # 5 μs driver overhead
    )

GPU Resources
~~~~~~~~~~~~~

GPU resources are modeled with a simplified approach focusing on the key performance parameters:

- **Hardware type**: Indicator that this is a GPU resource
- **Memory bandwidth**: Peak memory bandwidth in bytes/second
- **FLOPS**: Peak floating point operations per second
- **Network speed**: PCIe or network interface speed
- **Driver time**: GPU driver and kernel launch overhead

.. code-block:: python

    # Example: Creating custom GPU resources
    from daolite.compute import ComputeResources
    
    # Define an NVIDIA A100 GPU
    gpu = ComputeResources(
        hardware="GPU",
        memory_bandwidth=1.6e12,     # 1.6 TB/s (HBM2e)
        flops=1.9e13,                # 19.5 TFLOPS (FP32)
        network_speed=25e9,          # PCIe 4.0 x16
        time_in_driver=20            # 20 μs driver overhead
    )

Pre-defined Hardware Library
----------------------------

daolite includes a comprehensive library of pre-defined hardware profiles for common CPUs and GPUs:

CPU Profiles
~~~~~~~~~~~~

.. code-block:: python

    from daolite.compute import hardware
    
    # AMD CPUs
    cpu1 = hardware.amd_epyc_7763()    # AMD EPYC 7763 (Milan)
    cpu2 = hardware.amd_epyc_9654()    # AMD EPYC 9654 (Genoa)
    cpu3 = hardware.amd_ryzen_7950x()  # AMD Ryzen 9 7950X
    
    # Intel CPUs
    cpu4 = hardware.intel_xeon_8480()  # Intel Xeon Platinum 8480+
    cpu5 = hardware.intel_xeon_8462()  # Intel Xeon 8462Y+
    
    # Use a pre-defined CPU in a pipeline
    pipeline.add_component(PipelineComponent(
        name="Centroider",
        compute=hardware.amd_epyc_7763(),  # Easy to use!
        ...
    ))

GPU Profiles
~~~~~~~~~~~~

.. code-block:: python

    from daolite.compute import hardware
    
    # NVIDIA GPUs
    gpu1 = hardware.nvidia_a100_80gb()  # NVIDIA A100 80GB
    gpu2 = hardware.nvidia_h100_80gb()  # NVIDIA H100 80GB
    gpu3 = hardware.nvidia_rtx_4090()   # NVIDIA RTX 4090
    
    # AMD GPUs
    gpu4 = hardware.amd_mi300x()        # AMD Instinct MI300X
    
    # Use a pre-defined GPU in a pipeline
    pipeline.add_component(PipelineComponent(
        name="Reconstructor",
        compute=hardware.nvidia_rtx_4090(),
        ...
    ))

Memory Model
------------

The memory model in daolite calculates effective bandwidth based on:

1. **Theoretical peak bandwidth**: Base calculation from hardware specs
   
   For CPUs: ``memory_channels * memory_width * memory_frequency / 8``
   
   For GPUs: Directly specified memory bandwidth

2. **Access pattern efficiency**: Real-world memory access patterns rarely achieve theoretical peak
   
   - Sequential access: ~80-95% efficiency
   - Strided access: ~40-60% efficiency
   - Random access: ~10-30% efficiency

3. **Cache effects**: Optional modeling of cache benefits

Computation Model
-----------------

The computation model estimates processing time based on:

1. **Theoretical peak FLOPS**: Maximum floating point operations per second
   
   For CPUs: ``cores * core_frequency * flops_per_cycle``
   
   For GPUs: Directly specified FLOPS

2. **Algorithm efficiency**: Real-world efficiency compared to theoretical peak
   
   - Memory-bound algorithms: Typically limited by memory bandwidth
   - Compute-bound algorithms: Limited by computational throughput
   - Each algorithm has a scaling factor to account for implementation efficiency

Multiple Resource Types
-----------------------

daolite supports defining multiple resource types for different components:

.. code-block:: python

    # Define CPU for camera readout and DM control
    cpu_resource = amd_epyc_7763()
    
    # Define GPU for centroiding and reconstruction
    gpu_resource = nvidia_rtx_4090()
    
    # Use in pipeline components
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.CAMERA,
        name="Camera",
        compute=cpu_resource,  # CPU for camera
        # ...other parameters...
    ))
    
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.CENTROIDER,
        name="Centroider",
        compute=gpu_resource,  # GPU for centroiding
        # ...other parameters...
    ))

Adding Custom Hardware Profiles
-------------------------------

Users can extend the hardware library with custom profiles:

.. code-block:: python

    from daolite.compute import ComputeResources
    from daolite.compute.resources import register_hardware_profile
    
    # Create a custom hardware profile factory function
    def my_custom_server():
        return ComputeResources(
            hardware="CPU",
            cores=128,
            core_frequency=3.2e9,
            flops_per_cycle=64,
            memory_channels=16,
            memory_width=64,
            memory_frequency=3600e6,
            network_speed=200e9,
            time_in_driver=2
        )
    
    # Register the profile
    register_hardware_profile("my_custom_server", my_custom_server)
    
    # Later use it from the library
    from daolite import my_custom_server
    
    resource = my_custom_server()

Implementation Details
----------------------

The Compute Resources module uses a factory pattern to create resources with consistent configurations:

- ``ComputeResources``: Class for both CPU and GPU resources
- Pre-defined hardware profiles are factory functions

This design allows for easy extension and customization while maintaining type safety and consistent interfaces.

API Reference
-------------

For complete API details, see the :ref:`api_compute_resources` section.

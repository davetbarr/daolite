.. _latency_model:

Latency Model
=============

Overview
--------

daolite models the computational latency of Adaptive Optics (AO) real-time control systems by breaking down the process into distinct components and estimating the processing time for each. The model takes into account hardware specifications, data transfers, and algorithm complexity.

Core Concepts
-------------

The latency modeling in daolite is based on several key concepts:

Pipeline Components
~~~~~~~~~~~~~~~~~~~

An AO pipeline typically consists of:

1. **Camera Readout**: Time taken for the detector to read out pixel values
2. **Pixel Transfer**: Time required to transfer pixel data from camera to processing hardware
3. **Pixel Calibration**: Processing to remove bias, flat field, etc.
4. **Centroiding**: Calculation of wavefront slopes from subaperture images
5. **Wavefront Reconstruction**: Converting slopes to phase or actuator commands
6. **Network Transfer**: Time to transfer commands across networks
7. **DM Control**: Time for the deformable mirror controller to process commands

Packetization
~~~~~~~~~~~~~

daolite supports modeling of "packetized" processing, where data is processed in chunks as it becomes available:

- Camera readout is often performed in rows or regions
- Each packet can begin processing as soon as it's available
- Processing of packets can overlap, creating a pipelined effect
- This approach can significantly reduce overall latency

Compute Resources
~~~~~~~~~~~~~~~~~

The performance of each component depends on the available compute resources:

- **CPU-based processing**: Modeled using cores, frequency, FLOPS, and memory bandwidth
- **GPU-based processing**: Modeled using compute units, memory bandwidth, and driver overhead
- **Mixed hardware**: Different pipeline stages can run on different hardware

Hardware/Software Co-Design
~~~~~~~~~~~~~~~~~~~~~~~~~~~

daolite enables users to explore different hardware and software configurations:

- Test different algorithms (e.g., square difference vs. cross-correlation for centroiding)
- Evaluate hardware options (CPU vs. GPU, memory bandwidth effects)
- Optimize pipeline configurations (e.g., packet size, number of workers)

Latency Determination Methodology
---------------------------------

daolite uses a detailed latency determination model based on both computational throughput (FLOPS) and memory bandwidth limitations. This section explains the core methodology and the theoretical foundations behind the latency calculations.

Basic Principles
~~~~~~~~~~~~~~~~

The fundamental principle behind daolite's latency model is that processing time is limited by either:

1. **Computational throughput** - How quickly can the processor execute the required arithmetic operations
2. **Memory bandwidth** - How quickly can data be moved between memory and the processor

For any given operation, the overall latency is determined by the more restrictive of these two factors:

.. code-block:: python

    latency = max(compute_time, memory_time)

Calculating Computational Throughput Time
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The computational time is calculated based on:

.. code-block:: python

    compute_time = (operations_required) / (available_computational_throughput)

Where:

- **Operations required**: Total floating-point operations needed for the calculation
- **Available computational throughput**: Maximum FLOPS (Floating Point Operations Per Second) the hardware can deliver

Determining Available FLOPS
^^^^^^^^^^^^^^^^^^^^^^^^^^^

For a CPU, the theoretical peak FLOPS is calculated as:

.. code-block:: python

    CPU_theoretical_FLOPS = cores * core_frequency * FLOPS_per_cycle

Where:

- **Cores**: Number of physical CPU cores
- **Core frequency**: Clock speed in Hz (cycles per second)
- **FLOPS per cycle**: Operations possible per clock cycle (depends on vector instructions)

  - For example:
    - SSE: 4 FLOPS per cycle for single precision
    - AVX2: 8 FLOPS per cycle for single precision
    - AVX-512: 16 FLOPS per cycle for single precision

For a GPU, the theoretical peak FLOPS is calculated as:

.. code-block:: python

    GPU_theoretical_FLOPS = compute_units * clock_frequency * operations_per_compute_unit

Where:

- **Compute units**: Number of compute units (CUDA cores, Stream Processors, etc.)
- **Clock frequency**: GPU core clock speed
- **Operations per compute unit**: Typically 2 for fused multiply-add operations

Realistic FLOPS Adjustment
^^^^^^^^^^^^^^^^^^^^^^^^^^

In practice, achieving theoretical peak FLOPS is rarely possible due to various factors:

- Instruction mix (not all instructions are FMA operations)
- Code branching
- Instruction dependencies
- Hardware utilization inefficiencies

Therefore, daolite applies an algorithm-specific scaling factor:

.. code-block:: python

    effective_FLOPS = theoretical_FLOPS * efficiency_factor

The efficiency factor typically ranges from 0.1 to 0.8 depending on the algorithm and implementation.

Calculating Memory Bandwidth Time
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Memory bandwidth time is calculated based on:

.. code-block:: python

    memory_time = (data_accessed) / (effective_memory_bandwidth)

Where:

- **Data accessed**: Total bytes that must be read from and written to memory
- **Effective memory bandwidth**: Actual achievable memory bandwidth

Determining Theoretical Memory Bandwidth
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For a CPU, the theoretical peak memory bandwidth is calculated as:

.. code-block:: python

    CPU_theoretical_bandwidth = memory_channels * memory_width * memory_frequency / 8

Where:

- **Memory channels**: Number of memory channels
- **Memory width**: Width of each channel in bits
- **Memory frequency**: Effective memory frequency in Hz
- **Division by 8**: Conversion from bits to bytes

For example, a system with 4 channels of DDR4-3200 memory with 64-bit wide channels has a theoretical bandwidth of:

.. code-block:: python

    4 * 64 * 3,200,000,000 / 8 = 102.4 GB/s

For a GPU, the theoretical peak memory bandwidth depends on the memory technology:

.. code-block:: python

    GPU_theoretical_bandwidth = memory_bus_width * memory_frequency * transfers_per_clock / 8

Where:

- **Memory bus width**: Width of the memory bus in bits
- **Memory frequency**: Memory clock frequency
- **Transfers per clock**: For GDDR6, typically 2 transfers per clock (double data rate)

Realistic Memory Bandwidth Adjustment
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Similar to computational efficiency, memory bandwidth is affected by access patterns:

.. code-block:: python

    effective_bandwidth = theoretical_bandwidth * pattern_efficiency

Typical efficiency factors:

- Sequential access: 80-95%
- Strided access: 40-60%
- Random access: 10-30%

Combined Latency Model
~~~~~~~~~~~~~~~~~~~~~~

For each pipeline component, daolite calculates:

1. The computational time based on required FLOPS and available throughput
2. The memory time based on data access and available bandwidth
3. Takes the maximum of the two as the limiting factor

This produces a realistic estimation of processing time for each component.

Example: Centroiding Calculation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For a centroiding operation with 80×80 subapertures, each 16×16 pixels:

1. **Data requirements**:
   - 80*80*16*16 = 1,638,400 pixels
   - 4 bytes per pixel = 6,553,600 bytes total

2. **Computational requirements**:
   - Basic operations per pixel (subtract background, multiply by weights): ~5 ops per pixel
   - Total: 5 * 1,638,400 = 8,192,000 operations

3. **For a system with**:
   - Theoretical FLOPS: 10 TFLOPS
   - Memory bandwidth: 100 GB/s
   - Centroiding algorithm efficiency: 0.4
   - Memory access pattern efficiency: 0.7

4. **Calculation**:
   - Compute time: 8,192,000 / (10 * 10^12 * 0.4) = 2.048 μs
   - Memory time: 6,553,600 / (100 * 10^9 * 0.7) = 93.62 μs
   - Resulting latency: max(2.048, 93.62) = 93.62 μs

In this example, the operation is clearly memory-bound, as is common for many image processing operations.

Resource Partitioning in Packetized Systems
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In real-world AO systems using a packetized approach, different components of the pipeline operate simultaneously on different packets of data. For example, while one part of the system is performing calibration on packet N, another part might be computing centroids for packet N-1, and a third part might be handling reconstruction for packet N-2.

This parallelism requires careful modeling of how compute resources are partitioned across these simultaneous operations. daolite accounts for this with specialized scaling factors that represent resource allocation in pipelined systems:

.. code-block:: python

    effective_resource = total_resource * resource_partition_factor

Scaling Factor for Resource Partitioning
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The resource partition factor accounts for how computational resources are divided among simultaneously executing pipeline components:

.. code-block:: python

    compute_time = operations_required / (available_throughput * resource_partition_factor)
    memory_time = data_accessed / (memory_bandwidth * resource_partition_factor)

Where:

- **Resource partition factor**: Represents the fraction of the total resource allocated to a particular component
- This factor typically ranges from 0.2 to 0.5 for components running in parallel

Example: Partitioned Resources in a Packetized Pipeline
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Consider a GPU with 10 TFLOPS theoretical peak processing 3 pipeline stages in parallel:

1. **Resources without partitioning**:
   - Each component would use the full 10 TFLOPS if run sequentially
   - Total latency would be the sum of individual component latencies

2. **Resources with partitioning**:
   - Calibration: allocated 30% of resources = 3 TFLOPS effective
   - Centroiding: allocated 40% of resources = 4 TFLOPS effective
   - Reconstruction: allocated 30% of resources = 3 TFLOPS effective
   - All components run in parallel on different data packets

3. **Impact on pipeline throughput**:
   - While individual component latency increases due to reduced resources
   - Overall pipeline throughput increases as components run in parallel
   - Pipeline latency is determined by the longest component latency, not the sum

Implementing Resource Partitioning in daolite
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

When using daolite to model packetized processing, you should adjust the scaling factors to reflect resource partitioning:

.. code-block:: python

    # For a system with 3 parallel components on a GPU
    # Assuming compute resources are divided approximately evenly

    # Calibration component
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.CALIBRATION,
        name="Calibration",
        compute=gpu_resource,
        function=PixelCalibration,
        params={
            "n_pixels": nPixels,
            "scale": 0.3,  # Resource partition factor for calibration
            # ...other parameters...
        }
    ))

    # Centroiding component (runs in parallel with calibration on different packets)
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.CENTROIDER,
        name="Centroider",
        compute=gpu_resource,
        function=Centroider,
        params={
            "n_valid_subaps": nValidSubAps,
            "scale": 0.4,  # Resource partition factor for centroiding
            # ...other parameters...
        }
    ))

    # Reconstruction component (runs in parallel with other components on different packets)
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.RECONSTRUCTION,
        name="Reconstruction",
        compute=gpu_resource,
        function=Reconstruction,
        params={
            "n_slopes": nValidSubAps * 2,
            "scale": 0.3,  # Resource partition factor for reconstruction
            # ...other parameters...
        }
    ))

Determining Appropriate Partition Factors
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The appropriate partition factors depend on:

1. **Hardware architecture**: How well the hardware supports parallel execution
   - GPUs typically allow fine-grained resource partitioning
   - CPUs may use separate cores for different components

2. **Algorithm characteristics**: Some algorithms require more resources than others
   - Compute-intensive operations (like matrix multiplications) might need larger fractions
   - Memory-bound operations might need smaller fractions

3. **System implementation**: How the software divides the resources
   - CUDA stream priorities in GPU implementations
   - Thread priorities and affinities in CPU implementations
   - Explicit resource allocation by the real-time scheduler

When modeling a specific system, these partition factors should be calibrated based on the actual system behavior or detailed knowledge of the implementation.

Benefits of Accurate Resource Partitioning
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Properly modeling resource partitioning in packetized systems allows daolite to:

1. **Accurately predict pipeline throughput**: By accounting for parallel execution
2. **Identify bottlenecks**: Components with insufficient resources will limit throughput
3. **Optimize resource allocation**: Test different partitioning strategies
4. **Explore hardware options**: Determine if adding more compute resources would help

Note that while partitioning resources reduces the performance of individual components, the overall system throughput typically improves due to the pipelined parallelism.

Advantages and Disadvantages
----------------------------

Advantages of daolite's Latency Model
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. **Physically-based modeling**: The model is based on actual hardware constraints rather than empirical timing measurements that might vary between systems.

2. **Separates memory and compute bottlenecks**: By modeling both memory and compute limitations separately, it identifies the true bottleneck in a system, enabling targeted optimization.

3. **Hardware-independent predictions**: Can predict performance on new or hypothetical hardware configurations without requiring actual hardware.

4. **Scaling insights**: Provides clear insights into how performance will scale with more cores, faster memory, or different algorithms.

5. **Adaptable to different implementations**: Through efficiency factors, the model can represent different algorithm implementations on the same hardware.

6. **System-level analysis**: By combining component latencies, it provides insights into full pipeline behavior including pipelining opportunities.

Disadvantages and Limitations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. **Simplification of complex hardware**: Modern processors have complex behaviors (branch prediction, out-of-order execution, cache hierarchies) that are simplified in the model.

2. **Efficiency factor calibration**: Determining the correct efficiency factors requires either expert knowledge or empirical measurements.

3. **Overlapping compute and memory operations**: Modern hardware can often overlap compute and memory operations, which is difficult to model precisely.

4. **Ignores some system effects**: The model may not fully capture effects of operating system scheduling, thermal throttling, or dynamic frequency scaling.

5. **Implementation-specific optimizations**: Hand-optimized code with specific hardware instructions may perform differently than the model predicts.

6. **Synchronization overhead**: In multi-threaded or distributed systems, the cost of synchronization is difficult to model accurately.

7. **Architectural differences**: Some architectures (like GPUs vs CPUs) have fundamentally different performance characteristics that may need specialized modeling.

When to Trust the Model
~~~~~~~~~~~~~~~~~~~~~~~

The daolite latency model is most accurate when:

1. The operations are regular and predictable (like most numerical computations in AO pipelines)
2. The system is not I/O bound or limited by external factors
3. The efficiency factors have been properly calibrated for the specific algorithms and hardware
4. The comparison is between similar types of hardware architectures

The model provides relative performance estimates that are typically within 10-30% of real-world performance, which is sufficient for most system design and comparison tasks in AO system development.

Timing Model
------------

The latency estimation follows these principles:

1. **Memory-bound vs. Compute-bound**:
   - For each operation, determine if it's limited by memory bandwidth or computational throughput
   - Use the more limiting factor to estimate processing time

2. **Bandwidth Calculation**:
   - Memory bandwidth: Amount of data * Access pattern efficiency / Hardware bandwidth
   - Network bandwidth: Data size / Transfer rate + Driver overhead

3. **Computation Time**:
   - FLOPS required / Available FLOPS
   - Scaled by algorithmic efficiency factors

4. **Dependency Handling**:
   - Track dependencies between components
   - Component timing starts when its dependencies complete
   - Support for partial dependencies (e.g., start processing when first packet is ready)

5. **Scheduling**:
   - Optional: model task scheduling overhead
   - Optional: include thread synchronization costs

Example: Centroiding Latency
----------------------------

As an example, here's how centroiding latency is modeled:

.. code-block:: python

    # Determine if memory or compute bound
    memory_time = (pixels_per_subap * 4) / compute_resource.memory_bandwidth
    compute_time = (pixels_per_subap * ops_per_pixel) / compute_resource.flops
    
    # Scale by implementation efficiency
    compute_time *= scale_factor
    
    # Use the limiting factor (max of the two)
    processing_time = max(memory_time, compute_time)
    
    # Multiply by number of subapertures to process
    # (or divide by number of parallel workers)
    total_time = processing_time * n_subaps / n_workers


Advanced Features
-----------------

- **Multiple Lines of Sight**: Model processing for Solar Adaptive optics
- **Different Centroiding Methods**: Compare correlation, CoG, and other methods
- **Sorting Effects**: Evaluate impact of prioritizing certain slopes
- **Control Algorithms**: Model different control approaches (integrator, Kalman filter)
- **Wavefront Reconstruction**: Compare MVM, CuReD, and other methods

Usage Examples
--------------

See the :ref:`examples` section for complete examples of how to use the latency model.
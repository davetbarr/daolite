.. _reconstruction:

Wavefront Reconstruction
========================

Overview
--------

The wavefront reconstruction component in daolite (**D**\ urham **A**\ daptive **O**\ ptics **L**\ atency **I**\ nspection and **T**\ iming **E**\ stimator) is responsible for converting wavefront slope measurements into commands for deformable mirrors. This is a critical computational step in adaptive optics systems, translating Shack-Hartmann wavefront sensor measurements into the shape required for the deformable mirror to correct wavefront aberrations.

Key Reconstruction Features
---------------------------

* **Single Algorithm**: Implementation of the Minimum Variance Reconstruction (MVR) technique
* **Performance Modeling**: Accurate timing estimates based on algorithm complexity and hardware capabilities
* **GPU Acceleration**: Models for GPU-accelerated reconstruction operations
* **Tomographic Reconstruction**: Planned support for multi-conjugate and multi-object AO configurations

Using Reconstruction Components
-------------------------------

Adding a reconstructor to your AO pipeline:

.. code-block:: python

    from daolite import Pipeline, PipelineComponent, ComponentType
    from daolite.pipeline.reconstruction import mvr_reconstruction
    from daolite import nvidia_a100_80gb
    
    # Create a pipeline
    pipeline = Pipeline()
    
    # Define a GPU resource for reconstruction
    gpu = nvidia_a100_80gb()
    
    # Add reconstructor component
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.RECONSTRUCTOR,
        name="MVR Reconstructor",
        compute=gpu,
        function=mvr_reconstruction,
        params={
            "n_slopes": 40*40*2,  # 40×40 subapertures, x and y slopes
            "n_actuators": 41*41,  # 41×41 actuator grid
        },
        dependencies=["CoG Centroider"]
    ))

Reconstruction Algorithms
-------------------------

daolite provides timing models for the Minimum Variance Reconstruction (MVR) method.

Minimum Variance Reconstruction (MVR)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Reconstruction that incorporates atmospheric statistics:

.. code-block:: python

    from daolite.pipeline.reconstruction import mvr_reconstruction
    
    # Add MVR reconstructor to pipeline
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.RECONSTRUCTOR,
        name="MVR Reconstructor",
        compute=gpu,
        function=mvr_reconstruction,
        params={
            "n_slopes": 60*60*2,  # 60×60 subapertures
            "n_actuators": 61*61,  # 61×61 actuator grid
            "noise_variance": 0.1,  # Noise variance
            "turbulence_strength": 1.0  # Cn² parameter
        }
    ))

Planned Algorithms
~~~~~~~~~~~~~~~~~~

The following reconstruction methods are planned for future implementation:

* **Tomographic Reconstruction**: Multi-guide star reconstruction for wide-field correction
* **Conjugate Gradient (CG)**: Iterative method that avoids explicit control matrix computation
* **Fourier Domain Preconditioned CG (FDPCG)**: Specialized iterative method with faster convergence

Practical Examples
------------------

Example 1: High-Order SCAO System
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Reconstructor configuration for a high-order SCAO system:

.. code-block:: python

    # High-order SCAO MVR reconstructor
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.RECONSTRUCTOR,
        name="SCAO Reconstructor",
        compute=gpu,
        function=mvr_reconstruction,
        params={
            "n_slopes": 74*74*2,  # 74×74 subapertures
            "n_actuators": 75*75,  # 75×75 actuator grid
            "noise_variance": 0.1,  # Noise variance
            "turbulence_strength": 1.0,  # Cn² parameter
            "precision": "single",  # Use single precision for speed
            "memory_layout": "optimal",  # Optimize memory layout for GPU
            "matrix_layout": "column_major"  # Use column-major layout for CUDA
        },
        dependencies=["Solar Centroider"]
    ))

Performance Considerations
--------------------------

Several factors affect reconstruction performance:

Matrix Size
~~~~~~~~~~~

The control matrix size scales with:
* Number of slopes: O(n² subapertures) since each subaperture produces 2 slopes (x and y)
* Number of actuators: O(n² actuators) for a square DM

For MVR methods, the computational complexity is O(slopes × actuators), which can become prohibitive for very large AO systems.

Algorithm Computational Complexity
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The MVR algorithm has the following computational requirements:

* **MVR**: O(slopes × actuators) - Direct computation

GPU Acceleration Factors
~~~~~~~~~~~~~~~~~~~~~~~~

When using GPU acceleration, consider:

* **Memory Bandwidth**: MVR operations are often memory-bound rather than compute-bound
* **Precision**: Single precision (fp32) vs. double precision (fp64) has significant impact on GPU performance
* **Kernel Occupancy**: Ensuring GPU cores are well-utilized through appropriate blocking and thread assignment
* **Memory Transfers**: Minimizing CPU-GPU transfers, especially for iterative methods

Memory Requirements
~~~~~~~~~~~~~~~~~~~

Memory usage depends on the reconstructor type:

* **Dense MVR**: O(slopes × actuators) - Requires storing entire control matrix

Example: Memory Requirements by System Size
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    import matplotlib.pyplot as plt
    import numpy as np
    
    # Compare memory requirements
    def plot_memory_requirements():
        # System sizes to compare
        system_sizes = np.arange(20, 201, 20)  # 20 to 200 in steps of 20
        
        # Calculate memory requirements
        dense_memory = []
        
        for size in system_sizes:
            n_slopes = size * size * 2
            n_actuators = (size + 1) * (size + 1)
            
            # Dense MVR (4 bytes per float32)
            mem_dense = n_slopes * n_actuators * 4 / (1024**2)  # MB
            dense_memory.append(mem_dense)
        
        # Plot results
        plt.figure(figsize=(10, 6))
        plt.plot(system_sizes, dense_memory, 'o-', label='Dense MVR')
        plt.xlabel('System Size (subapertures across diameter)')
        plt.ylabel('Memory Requirement (MB)')
        plt.title('Reconstruction Algorithm Memory Requirements')
        plt.legend()
        plt.grid(True)
        plt.yscale('log')
        plt.savefig('reconstruction_memory.png')
        plt.show()
    
    # Plot memory requirements
    plot_memory_requirements()

Troubleshooting
---------------

Common issues and solutions:

* **High Latency**:
  - For large systems, reduce precision from double to single when possible
  - Optimize memory layout for coalesced access on GPUs
  - Use asynchronous operations and streams for concurrent execution
  
* **Memory Limitations**:
  - For very large systems, consider mixed-precision approaches (e.g., fp16 for computation, fp32 for accumulation)
  
* **Numerical Stability**:
  - Monitor convergence and adjust regularization parameters
  - Ensure control matrix is well-conditioned

* **Multi-GPU Scaling**:
  - For extremely large systems, distribute computation across multiple GPUs

Related Topics
--------------

* :ref:`centroider` - Wavefront sensing that provides inputs to reconstruction
* :ref:`control` - Control algorithms that use reconstruction outputs
* :ref:`network` - Data transfer between system components

API Reference
-------------

For complete API details, see the :ref:`api_reconstruction` section.
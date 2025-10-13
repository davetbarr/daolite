.. _centroider:

Wavefront Sensing
=================

Overview
--------

The wavefront sensing (centroiding) component in daolite (**D**\ urham **A**\ daptive **O**\ ptics **L**\ atency **I**\ nspection and **T**\ iming **E**\ stimator) handles the calculation of wavefront slopes from Shack-Hartmann sensor images. These slopes represent the local tilts of the wavefront across the pupil and are crucial inputs for wavefront reconstruction in adaptive optics systems.

Key Centroiding Features
------------------------

* **Cross-Correlation Algorithm**: Optimized for extended sources like in solar AO
* **Performance Modeling**: Accurate timing estimates based on algorithm complexity and hardware
* **Flexibility**: Support for different subaperture configurations and detector parameters
* **GPU Acceleration**: Models for GPU-accelerated centroiding operations

Using Centroiding Components
----------------------------

Adding a centroider to your AO pipeline:

.. code-block:: python

    from daolite import Pipeline, PipelineComponent, ComponentType
    from daolite.pipeline.centroider import Centroider
    from daolite.compute import hardware
    import numpy as np
    
    # Create a pipeline
    pipeline = Pipeline()
    
    # Define a GPU resource for centroiding
    gpu = hardware.nvidia_rtx_4090()
    
    # Define centroid agenda (how many subapertures per iteration)
    n_valid_subaps = 6400
    n_groups = 50
    centroid_agenda = np.ones(n_groups, dtype=int) * (n_valid_subaps // n_groups)
    
    # Add centroider component
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.CENTROIDER,
        name="Centroider",
        compute=gpu,
        function=Centroider,
        params={
            "centroid_agenda": centroid_agenda,
            "n_pix_per_subap": 16*16,  # 16×16 pixels per subaperture
            "n_workers": 1,
            "sort": False
        },
        dependencies=["Pixel Calibration"]  # Depends on output from calibration
    ))

Centroiding Functions
----------------------

daolite provides several centroiding functions for different wavefront sensor types:

Point Source Centroiding (Shack-Hartmann)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``Centroider`` function is used for standard Shack-Hartmann wavefront sensors with point sources:

.. code-block:: python

    from daolite.pipeline.centroider import Centroider
    
    # Add Shack-Hartmann centroider to pipeline
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.CENTROIDER,
        name="SH Centroider",
        compute=gpu,
        function=Centroider,
        params={
            "centroid_agenda": centroid_agenda,  # Processing agenda
            "n_pix_per_subap": 16*16,            # Pixels per subaperture
            "n_workers": 1,                       # Parallel workers
            "sort": False,                        # Sorting (for brightest pixel)
            "flop_scale": 1.0,                    # FLOP scaling factor
            "mem_scale": 1.0                      # Memory scaling factor
        }
    ))

Extended Source Centroiding
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For extended sources (solar AO), use the extended source centroider module:

.. code-block:: python

    from daolite.pipeline.extended_source_centroider import ExtendedSourceCentroider
    
    # Add extended source centroider
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.CENTROIDER,
        name="Extended Source Centroider",
        compute=gpu,
        function=ExtendedSourceCentroider,
        params={
            "centroid_agenda": centroid_agenda,
            "n_pix_per_subap": 20*20,
            "n_combine": 4  # Number of images to combine
        }
    ))

Practical Examples
------------------

Example 1: High-Order Adaptive Optics System
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Centroider configuration for a high-order AO system with many subapertures:

.. code-block:: python

    import numpy as np
    
    # High-order AO centroider for 85×85 subapertures
    n_valid_subaps = 85 * 85
    n_groups = 100  # Process in 100 groups
    centroid_agenda = np.ones(n_groups, dtype=int) * (n_valid_subaps // n_groups)
    
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.CENTROIDER,
        name="High-Order Centroider",
        compute=gpu,
        function=Centroider,
        params={
            "centroid_agenda": centroid_agenda,
            "n_pix_per_subap": 16*16,  # 16×16 pixels per subaperture
            "n_workers": 1,
            "sort": False
        },
        dependencies=["Pixel Calibration"]
    ))

Performance Considerations
--------------------------

Several factors affect centroiding performance:

Algorithm Complexity
~~~~~~~~~~~~~~~~~~~~

The cross-correlation algorithm has computational complexity:

* **Correlation**: O(n log n) with FFT or O(n²) without FFT

Subaperture Count
~~~~~~~~~~~~~~~~~

More subapertures increase compute load linearly for most algorithms, but may have additional overhead for data transfers.

Pixels Per Subaperture
~~~~~~~~~~~~~~~~~~~~~~

Increasing pixel count per subaperture affects performance:

* **Correlation methods**: Quadratic scaling in naive implementation, n log n with FFT

GPU Acceleration Factors
~~~~~~~~~~~~~~~~~~~~~~~~

When using GPU acceleration, consider:

* **Data Transfer**: Time to move pixel data to GPU memory
* **Kernel Launch Overhead**: Fixed overhead per GPU kernel launch
* **Parallelism**: GPUs benefit from high subaperture counts that can utilize all cores
* **Memory Pattern**: Coalesced memory access patterns are crucial for performance

Example: Performance Analysis
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    import matplotlib.pyplot as plt
    import numpy as np
    from daolite import Pipeline, PipelineComponent, ComponentType
    from daolite.compute import hardware
    from daolite.pipeline.centroider import Centroider
    
    # Compare performance across different subaperture counts
    def compare_centroider_performance():
        # Create GPU resource
        gpu = hardware.nvidia_rtx_4090()
        
        # Subaperture counts to test
        subap_counts = [20*20, 40*40, 60*60, 80*80, 100*100]
        pixels_per_subap = 16*16
        
        # Store results
        centroid_times = []
        
        # Test each subaperture count
        for n_subaps in subap_counts:
            # Define centroid agenda
            n_groups = 50
            centroid_agenda = np.ones(n_groups, dtype=int) * (n_subaps // n_groups)
            
            # Test Centroider
            pipeline = Pipeline()
            pipeline.add_component(PipelineComponent(
                component_type=ComponentType.CENTROIDER,
                name="Centroider",
                compute=gpu,
                function=Centroider,
                params={
                    "centroid_agenda": centroid_agenda,
                    "n_pix_per_subap": pixels_per_subap,
                    "n_workers": 1,
                    "sort": False
                }
            ))
            results = pipeline.run()
            centroid_times.append(results["Centroider"].duration)
        
        # Plot results
        plt.figure(figsize=(10, 6))
        plt.plot(subap_counts, centroid_times, 's-', label='Centroider')
        plt.xlabel('Number of Subapertures')
        plt.ylabel('Execution Time (microseconds)')
        plt.title('Centroiding Performance vs. Subaperture Count')
        plt.legend()
        plt.grid(True)
        plt.savefig('centroider_performance.png')
        plt.show()
    
    # Run the comparison
    compare_centroider_performance()

Troubleshooting
---------------

Common issues and solutions:

* **High Latency**: 
  - Reduce pixels per subaperture
  - Use FFT-based correlation instead of direct computation
  - Ensure input data is optimally arranged in memory
  
* **GPU Memory Limitations**:
  - Process subapertures in batches
  - Reduce template or search region size
  - Use a more memory-efficient algorithm

* **Poor Accuracy**:
  - For extended sources, correlation methods typically outperform simpler methods
  - Adjust thresholds or weighting parameters

API Reference
-------------

For complete API details, see the :ref:`api_centroider` section.
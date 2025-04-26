.. _centroider:

Wavefront Sensing
=================

Overview
--------

The wavefront sensing (centroiding) component in DaoLITE (**D**\ urham **A**\ daptive **O**\ ptics **L**\ atency **I**\ nspection and **T**\ iming **E**\ stimator) handles the calculation of wavefront slopes from Shack-Hartmann sensor images. These slopes represent the local tilts of the wavefront across the pupil and are crucial inputs for wavefront reconstruction in adaptive optics systems.

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
    from daolite.pipeline.centroider import cross_correlation_centroider
    from daolite.compute import hardware
    
    # Create a pipeline
    pipeline = Pipeline()
    
    # Define a GPU resource for centroiding
    gpu = hardware.nvidia_rtx_4090()
    
    # Add centroider component
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.CENTROIDER,
        name="Correlation Centroider",
        compute=gpu,
        function=cross_correlation_centroider,
        params={
            "n_subaps": 80*80,  # 80×80 solar wavefront sensor
            "pixels_per_subap": 16*16,
            "template_size": 8*8,  # 8×8 reference template
            "search_extent": 4,  # Search +/- 4 pixels
            "use_fft": True  # Use FFT for fast correlation
        },
        dependencies=["Pixel Calibration"]  # Depends on output from calibration
    ))

Centroiding Algorithms
----------------------

DaoLITE provides timing models for the cross-correlation centroiding method, which is optimized for extended sources like in solar AO.

Cross-Correlation
~~~~~~~~~~~~~~~~~

Ideal for extended sources like in solar AO:

.. code-block:: python

    from daolite.pipeline.centroider import cross_correlation_centroider
    
    # Add correlation centroider to pipeline
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.CENTROIDER,
        name="Correlation Centroider",
        compute=gpu,
        function=cross_correlation_centroider,
        params={
            "n_subaps": 80*80,  # 80×80 solar wavefront sensor
            "pixels_per_subap": 16*16,
            "template_size": 8*8,  # 8×8 reference template
            "search_extent": 4,  # Search +/- 4 pixels
            "use_fft": True  # Use FFT for fast correlation
        }
    ))

Practical Examples
------------------

Example 1: High-Resolution Solar AO
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Centroider configuration for a high-resolution solar wavefront sensor:

.. code-block:: python

    # Solar AO correlation centroider
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.CENTROIDER,
        name="Solar Centroider",
        compute=gpu,
        function=cross_correlation_centroider,
        params={
            "n_subaps": 85*85,  # 85×85 subapertures
            "pixels_per_subap": 20*20,  # 20×20 pixels
            "template_size": 10*10,  # 10×10 reference
            "search_extent": 5,  # Search range
            "use_fft": True,  # Use FFT for speed
            "subpixel_method": "parabolic"  # Subpixel accuracy method
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

Example: Comparing Algorithm Performance
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    import matplotlib.pyplot as plt
    import numpy as np
    from daolite import Pipeline, PipelineComponent, ComponentType
    from daolite.compute import hardware
    from daolite.pipeline.centroider import cross_correlation_centroider
    
    # Compare performance of cross-correlation centroiding algorithm
    def compare_centroider_performance():
        # Create GPU resource
        gpu = hardware.nvidia_rtx_4090()
        
        # Subaperture counts to test
        subap_counts = [20*20, 40*40, 60*60, 80*80, 100*100]
        pixels_per_subap = 16*16
        
        # Store results
        cc_times = []
        
        # Test each subaperture count
        for n_subaps in subap_counts:
            # Test Cross-Correlation
            pipeline = Pipeline()
            pipeline.add_component(PipelineComponent(
                component_type=ComponentType.CENTROIDER,
                name="CC Centroider",
                compute=gpu,
                function=cross_correlation_centroider,
                params={
                    "n_subaps": n_subaps,
                    "pixels_per_subap": pixels_per_subap,
                    "template_size": 8*8,
                    "search_extent": 4,
                    "use_fft": True
                }
            ))
            results = pipeline.run()
            cc_times.append(results["CC Centroider"].duration)
        
        # Plot results
        plt.figure(figsize=(10, 6))
        plt.plot(subap_counts, cc_times, 's-', label='Cross-Correlation')
        plt.xlabel('Number of Subapertures')
        plt.ylabel('Execution Time (microseconds)')
        plt.title('Centroiding Algorithm Performance Comparison')
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
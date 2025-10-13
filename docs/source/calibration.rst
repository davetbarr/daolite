.. _calibration:

Pixel Calibration
=================

Overview
--------

The pixel calibration component in daolite (**D**\ urham **A**\ daptive **O**\ ptics **L**\ atency **I**\ nspection and **T**\ iming **E**\ stimator) handles the preprocessing of raw camera data before wavefront sensing. This preprocessing is essential for accurate wavefront measurements and includes dark frame subtraction, flat fielding, bad pixel correction, and other operations to prepare the raw pixel data for centroiding.

Key Calibration Operations
--------------------------

* **Dark Subtraction**: Removal of dark current and bias
* **Flat Fielding**: Correction for pixel sensitivity variations
* **Bad Pixel Correction**: Handling of defective pixels
* **Background Estimation**: Subtraction of background flux
* **Thresholding**: Application of intensity thresholds
* **Normalization**: Scaling of pixel intensities

Using Calibration Components
----------------------------

daolite makes it easy to add pixel calibration stages to your AO pipeline:

.. code-block:: python

    from daolite import Pipeline, PipelineComponent, ComponentType
    from daolite.pipeline.calibration import PixelCalibration
    from daolite.compute import hardware
    import numpy as np
    
    pipeline = Pipeline()
    
    # Define a CPU resource
    cpu = hardware.amd_epyc_7763()
    
    # Define pixel agenda (how many pixels per iteration)
    n_pixels = 1024 * 1024
    n_groups = 10
    pixel_agenda = np.ones(n_groups, dtype=int) * (n_pixels // n_groups)
    
    # Add pixel calibration component
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.CALIBRATION,
        name="Pixel Calibration",
        compute=cpu,
        function=PixelCalibration,
        params={
            "pixel_agenda": pixel_agenda,
            "bit_depth": 16,  # 16-bit camera data
            "n_workers": 1
        },
        dependencies=["Camera"]
    ))

Calibration Configuration
-------------------------

The pixel calibration component accepts the following parameters:

.. code-block:: python

    params={
        # Required parameters
        "pixel_agenda": pixel_agenda,  # Processing agenda (np.ndarray)
        
        # Optional parameters
        "bit_depth": 16,       # Bit depth of pixel data (default: 16)
        "n_workers": 1,        # Number of parallel workers (default: 1)
        "flop_scale": 1.0,     # FLOP scaling factor (default: 1.0)
        "mem_scale": 1.0,      # Memory scaling factor (default: 1.0)
        "debug": False         # Enable debug output (default: False)
    }

Understanding Pixel Calibration
--------------------------------

The ``PixelCalibration`` function models the computational latency of preprocessing raw camera data before wavefront sensing. This includes operations like dark frame subtraction, flat fielding, and other pixel-level corrections.

The function uses an **agenda-based API** where you specify how many pixels to process in each iteration through the ``pixel_agenda`` parameter. This allows modeling of pipelined or batched processing patterns.

Key Factors Affecting Performance
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The computational cost of pixel calibration depends on:

* **Number of Pixels**: Scales linearly with pixel count
* **Bit Depth**: Higher bit depths require more memory bandwidth
* **Memory Bandwidth**: Calibration operations are typically memory-bound
* **Computational Resource**: CPU vs GPU implementation affects throughput

Practical Example
-----------------

Complete Example: Full Pipeline with Calibration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from daolite import Pipeline, PipelineComponent, ComponentType
    from daolite.pipeline.camera import PCOCamLink
    from daolite.pipeline.calibration import PixelCalibration
    from daolite.compute import hardware
    import numpy as np
    
    # Create pipeline
    pipeline = Pipeline()
    
    # Define compute resources
    cpu = hardware.amd_epyc_7763()
    
    # Camera parameters
    n_pixels = 1024 * 1024
    camera_groups = 10
    
    # Pixel calibration agenda
    pixel_agenda = np.ones(camera_groups, dtype=int) * (n_pixels // camera_groups)
    
    # Add camera
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.CAMERA,
        name="Camera",
        compute=cpu,
        function=PCOCamLink,
        params={
            "n_pixels": n_pixels,
            "group": camera_groups,
            "readout": "rolling"
        }
    ))
    
    # Add pixel calibration
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.CALIBRATION,
        name="Pixel Calibration",
        compute=cpu,
        function=PixelCalibration,
        params={
            "pixel_agenda": pixel_agenda,
            "bit_depth": 16,
            "n_workers": 1
        },
        dependencies=["Camera"]
    ))
    
    # Run pipeline
    results = pipeline.run()
    print(f"Calibration time: {results['Pixel Calibration'].duration:.2f} µs")
        GPU Acceleration
~~~~~~~~~~~~~~~~

You can model GPU-accelerated pixel calibration by using a GPU compute resource:

.. code-block:: python

    from daolite.compute import hardware
    
    # Use GPU instead of CPU
    gpu = hardware.nvidia_rtx_4090()
    
    # Add GPU-accelerated calibration
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.CALIBRATION,
        name="GPU Calibration",
        compute=gpu,  # Use GPU resource
        function=PixelCalibration,
        params={
            "pixel_agenda": pixel_agenda,
            "bit_depth": 16,
            "n_workers": 1
        },
        dependencies=["Camera"]
    ))

Tuning Performance
~~~~~~~~~~~~~~~~~~

You can tune the performance model using the ``flop_scale`` and ``mem_scale`` parameters:

.. code-block:: python

    # Scale computational intensity
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.CALIBRATION,
        name="Tuned Calibration",
        compute=cpu,
        function=PixelCalibration,
        params={
            "pixel_agenda": pixel_agenda,
            "bit_depth": 16,
            "flop_scale": 1.2,  # Increase FLOPs by 20%
            "mem_scale": 0.8,   # Reduce memory ops by 20%
            "n_workers": 4      # Use 4 parallel workers
        },
        dependencies=["Camera"]
    ))

API Reference
-------------

For complete API details, see the :ref:`api_calibration` section.

Chunked Processing
~~~~~~~~~~~~~~~~~~

For very large pixel arrays, chunked processing can be more efficient:

.. code-block:: python

    # Configure chunked processing
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.CALIBRATION,
        name="Chunked Calibration",
        compute=cpu,
        function=PixelCalibration,
        params={
            "n_pixels": 4096*4096,  # 16 megapixel array
            "operations": ["dark_subtract", "flat_field"],
            "use_chunking": True,
            "chunk_size": 1024*1024  # Process in 1 megapixel chunks
        },
        dependencies=["Camera"]
    ))

Customizing Calibration Models
------------------------------

daolite allows you to create custom calibration operations with your own timing models:

.. code-block:: python

    def custom_calibration(compute, n_pixels, extra_param=1.0, debug=False):
        """
        Custom calibration function with timing model.
        
        Args:
            compute: Compute resource
            n_pixels: Number of pixels to process
            extra_param: Custom scaling parameter
            debug: Enable debug output
            
        Returns:
            Numpy array with timing information
        """
        # Model timing based on compute resource
        if compute.hardware == "GPU":
            # GPU timing model
            bytes_per_pixel = 4  # Float32
            total_bytes = n_pixels * bytes_per_pixel * 2  # Read + write
            mem_time = total_bytes / compute.memory_bandwidth
            
            # GPU kernels typically need some launch overhead
            kernel_overhead = 5.0  # microseconds
            compute_time = n_pixels * 0.5 / compute.flops + kernel_overhead
        else:
            # CPU timing model
            bytes_per_pixel = 4  # Float32
            total_bytes = n_pixels * bytes_per_pixel * 2  # Read + write
            
            mem_bandwidth = (compute.memory_channels * 
                           compute.memory_width * 
                           compute.memory_frequency / 8)  # Bytes/sec
            mem_time = total_bytes / mem_bandwidth
            
            # CPU model with core utilization
            ops_per_pixel = 10  # Example number of operations per pixel
            total_ops = n_pixels * ops_per_pixel
            compute_time = total_ops / (compute.cores * 
                                      compute.core_frequency * 
                                      compute.flops_per_cycle)
        
        # Scale by custom parameter
        compute_time *= extra_param
        
        # Memory or compute bound?
        processing_time = max(mem_time, compute_time)
        
        if debug:
            print(f"Memory time: {mem_time} µs")
            print(f"Compute time: {compute_time} µs")
            print(f"Total processing time: {processing_time} µs")
        
        # Create timing array
        timing = np.zeros([1, 2])
        timing[0, 1] = processing_time
        
        return timing
    
    # Use custom calibration in a pipeline
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.CALIBRATION,
        name="Custom Calibration",
        compute=cpu,
        function=custom_calibration,
        params={
            "n_pixels": 1024*1024,
            "extra_param": 1.2,
            "debug": True
        },
        dependencies=["Camera"]
    ))

Real-World Applications
-----------------------

Example: High-speed AO System
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Calibration configuration for a high-speed adaptive optics system:

.. code-block:: python

    # High-speed system with optimized calibration
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.CALIBRATION,
        name="Fast Calibration",
        compute=gpu,  # Use GPU for speed
        function=PixelCalibration,
        params={
            "n_pixels": 128*128,  # Small format sensor
            "operations": ["dark_subtract"],  # Minimal processing
            "use_gpu_kernels": True,
            "use_async": True  # Use asynchronous processing
        },
        dependencies=["Camera"]
    ))

Example: High-precision System
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Calibration configuration for a high-precision AO system:

.. code-block:: python

    # High-precision system with comprehensive calibration
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.CALIBRATION,
        name="Precision Calibration",
        compute=cpu,
        function=PixelCalibration,
        params={
            "n_pixels": 2048*2048,
            "operations": ["dark_subtract", "flat_field", "bad_pixel", 
                          "background", "threshold", "normalize"],
            "window_size": 5,  # Larger window for better correction
            "bad_pixel_fraction": 0.02,
            "threshold": 50
        },
        dependencies=["Camera"]
    ))

API Reference
-------------

For complete API details, see the :ref:`api_calibration` section.
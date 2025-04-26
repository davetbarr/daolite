.. _calibration:

Pixel Calibration
=================

Overview
--------

The pixel calibration component in DaoLITE (**D**\ urham **A**\ daptive **O**\ ptics **L**\ atency **I**\ nspection and **T**\ iming **E**\ stimator) handles the preprocessing of raw camera data before wavefront sensing. This preprocessing is essential for accurate wavefront measurements and includes dark frame subtraction, flat fielding, bad pixel correction, and other operations to prepare the raw pixel data for centroiding.

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

DaoLITE makes it easy to add pixel calibration stages to your AO pipeline:

.. code-block:: python

    from daolite import Pipeline, PipelineComponent, ComponentType
    from daolite.pipeline.calibration import PixelCalibration
    from daolite import amd_epyc_7763
    
    pipeline = Pipeline()
    
    # Define a CPU resource
    cpu = amd_epyc_7763()
    
    # Add camera component first
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.CAMERA,
        name="Camera",
        compute=cpu,
        function=simulate_camera_readout,
        params={"n_pixels": 1024*1024}
    ))
    
    # Add pixel calibration component
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.CALIBRATION,
        name="Pixel Calibration",
        compute=cpu,
        function=PixelCalibration,
        params={
            "n_pixels": 1024*1024,
            "operations": ["dark_subtract", "flat_field", "threshold"],
            "threshold": 100
        },
        dependencies=["Camera"]
    ))

Calibration Configuration
-------------------------

The pixel calibration component accepts a variety of parameters to customize its behavior:

.. code-block:: python

    params={
        # Required parameters
        "n_pixels": 1024*1024,  # Total number of pixels
        
        # Optional parameters
        "operations": ["dark_subtract", "flat_field", "bad_pixel", "normalize"],
        "threshold": 100,  # Intensity threshold value
        "iterations": 1,  # Number of iterations for certain operations
        "window_size": 3,  # Window size for filtering operations (e.g., bad pixel)
        "use_chunking": True,  # Process data in chunks for better memory usage
        "chunk_size": 4096,  # Size of chunks when chunking is enabled
    }

Available Calibration Operations
--------------------------------

DaoLITE provides timing models for the following calibration operations:

Dark Subtraction
~~~~~~~~~~~~~~~~

Removes dark current and bias from raw pixel data:

.. code-block:: python

    from daolite.pipeline.calibration import dark_subtraction
    
    # Use as a standalone function
    timing = dark_subtraction(
        compute=cpu,
        n_pixels=1024*1024,
        debug=True
    )
    
    # Or in a pipeline component
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.CALIBRATION,
        name="Dark Subtraction",
        compute=cpu,
        function=dark_subtraction,
        params={"n_pixels": 1024*1024},
        dependencies=["Camera"]
    ))

Flat Fielding
~~~~~~~~~~~~~

Corrects for pixel sensitivity variations:

.. code-block:: python

    from daolite.pipeline.calibration import flat_field_correction
    
    # Add as a pipeline component
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.CALIBRATION,
        name="Flat Fielding",
        compute=cpu,
        function=flat_field_correction,
        params={"n_pixels": 1024*1024},
        dependencies=["Dark Subtraction"]
    ))

Bad Pixel Correction
~~~~~~~~~~~~~~~~~~~~

Handles defective pixels:

.. code-block:: python

    from daolite.pipeline.calibration import bad_pixel_correction
    
    # Add as a pipeline component
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.CALIBRATION,
        name="Bad Pixel Correction",
        compute=cpu,
        function=bad_pixel_correction,
        params={
            "n_pixels": 1024*1024,
            "window_size": 3,  # Use a 3x3 window for correction
            "bad_pixel_fraction": 0.01  # 1% of pixels are defective
        },
        dependencies=["Flat Fielding"]
    ))

Combined Calibration
~~~~~~~~~~~~~~~~~~~~

For convenience, DaoLITE provides a combined calibration function that performs multiple operations in sequence:

.. code-block:: python

    from daolite.pipeline.calibration import PixelCalibration
    
    # Add combined calibration to the pipeline
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.CALIBRATION,
        name="Pixel Calibration",
        compute=cpu,
        function=PixelCalibration,
        params={
            "n_pixels": 1024*1024,
            "operations": ["dark_subtract", "flat_field", "bad_pixel", "normalize"],
            "window_size": 3,
            "threshold": 100
        },
        dependencies=["Camera"]
    ))

Performance Considerations
--------------------------

The computational cost of pixel calibration operations depends on several factors:

* **Number of Pixels**: Scales linearly with pixel count
* **Operations Used**: More operations increase processing time
* **Window-based Operations**: Operations like bad pixel correction scale with window size
* **Memory Bandwidth**: Many calibration operations are memory-bound
* **Computational Resource**: CPU vs GPU implementation

GPU Acceleration
~~~~~~~~~~~~~~~~

DaoLITE models GPU-accelerated pixel calibration for higher performance:

.. code-block:: python

    from daolite import nvidia_rtx_4090
    
    # Define a GPU resource
    gpu = nvidia_rtx_4090()
    
    # Use GPU-accelerated calibration
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.CALIBRATION,
        name="GPU Calibration",
        compute=gpu,  # Use GPU resource
        function=PixelCalibration,
        params={
            "n_pixels": 1024*1024,
            "operations": ["dark_subtract", "flat_field", "normalize"],
            "use_gpu_kernels": True  # Enable GPU-specific optimizations
        },
        dependencies=["Camera"]
    ))

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

DaoLITE allows you to create custom calibration operations with your own timing models:

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
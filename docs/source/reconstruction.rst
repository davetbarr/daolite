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
    from daolite.pipeline.reconstruction import Reconstruction
    from daolite.compute import hardware
    import numpy as np
    
    # Create a pipeline
    pipeline = Pipeline()
    
    # Define a GPU resource for reconstruction
    gpu = hardware.nvidia_a100_80gb()
    
    # Define centroid agenda (matching centroider output)
    n_valid_subaps = 6400
    n_groups = 50
    centroid_agenda = np.ones(n_groups, dtype=int) * (n_valid_subaps // n_groups)
    
    # Add reconstructor component
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.RECONSTRUCTOR,
        name="Reconstructor",
        compute=gpu,
        function=Reconstruction,
        params={
            "centroid_agenda": centroid_agenda,
            "n_acts": 81*81,  # 81×81 actuator grid
            "n_workers": 1
        },
        dependencies=["Centroider"]
    ))

Reconstruction Configuration
----------------------------

The reconstruction component accepts the following parameters:

.. code-block:: python

    params={
        # Required parameters
        "centroid_agenda": centroid_agenda,  # Processing agenda (np.ndarray)
        "n_acts": 81*81,                     # Number of actuators
        
        # Optional parameters
        "flop_scale": 1.0,    # FLOP scaling factor (default: 1.0)
        "mem_scale": 1.0,     # Memory scaling factor (default: 1.0)
        "n_workers": 1,       # Number of parallel workers (default: 1)
        "debug": False        # Enable debug output (default: False)
    }

Understanding Reconstruction
----------------------------

The ``Reconstruction`` function models the computational latency of matrix-vector multiplication (MVM) operations that convert wavefront slopes into actuator commands. This corresponds to the operation:

.. math::

    \\mathbf{a} = \\mathbf{R} \\cdot \\mathbf{s}

where:

* :math:`\\mathbf{s}` is the slope vector (from centroiding)
* :math:`\\mathbf{R}` is the reconstruction matrix (e.g., pseudo-inverse of interaction matrix)
* :math:`\\mathbf{a}` is the actuator command vector

The function uses an **agenda-based API** where you specify how many slopes to process in each iteration through the ``centroid_agenda`` parameter.

Practical Examples
------------------

Example: Complete AO Pipeline with Reconstruction
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from daolite import Pipeline, PipelineComponent, ComponentType
    from daolite.pipeline.camera import PCOCamLink
    from daolite.pipeline.calibration import PixelCalibration
    from daolite.pipeline.centroider import Centroider
    from daolite.pipeline.reconstruction import Reconstruction
    from daolite.compute import hardware
    import numpy as np
    
    # Create pipeline
    pipeline = Pipeline()
    
    # Define compute resources
    cpu = hardware.amd_epyc_7763()
    gpu = hardware.nvidia_a100_80gb()
    
    # System parameters
    n_subaps = 74 * 74
    n_acts = 75 * 75
    n_pixels = 1024 * 1024
    
    # Define agendas
    n_groups = 50
    centroid_agenda = np.ones(n_groups, dtype=int) * (n_subaps // n_groups)
    pixel_agenda = np.ones(n_groups, dtype=int) * (n_pixels // n_groups)
    
    # Add camera
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.CAMERA,
        name="Camera",
        compute=cpu,
        function=PCOCamLink,
        params={"n_pixels": n_pixels, "group": n_groups, "readout": "rolling"}
    ))
    
    # Add calibration
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.CALIBRATION,
        name="Pixel Calibration",
        compute=cpu,
        function=PixelCalibration,
        params={"pixel_agenda": pixel_agenda, "bit_depth": 16},
        dependencies=["Camera"]
    ))
    
    # Add centroider
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.CENTROIDER,
        name="Centroider",
        compute=gpu,
        function=Centroider,
        params={"centroid_agenda": centroid_agenda, "n_pix_per_subap": 16*16},
        dependencies=["Pixel Calibration"]
    ))
    
    # Add reconstructor
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.RECONSTRUCTOR,
        name="Reconstructor",
        compute=gpu,
        function=Reconstruction,
        params={
            "centroid_agenda": centroid_agenda,
            "n_acts": n_acts
        },
        dependencies=["Centroider"]
    ))
    
    # Run and analyze
    results = pipeline.run()
    print(f"Reconstruction time: {results['Reconstructor'].duration:.2f} µs")

Performance Considerations
--------------------------

Several factors affect reconstruction performance:

Matrix Size
~~~~~~~~~~~

The reconstruction matrix size scales with:

* Number of slopes: Each subaperture produces 2 slopes (x and y), so :math:`n_{slopes} = 2 \\times n_{subaps}`
* Number of actuators: Typically :math:`n_{acts} = (n_{subaps}^{1/2} + 1)^2` for a square DM

The computational complexity is :math:`O(n_{slopes} \\times n_{acts})` for matrix-vector multiplication.

GPU Acceleration
~~~~~~~~~~~~~~~~

When using GPU acceleration, consider:

* **Memory Bandwidth**: Reconstruction operations are often memory-bound
* **Data Transfers**: GPU memory transfers should be minimized
* **Parallelism**: GPUs excel with large matrix operations that utilize all cores

Tuning Performance
~~~~~~~~~~~~~~~~~~

You can tune the performance model using the ``flop_scale`` and ``mem_scale`` parameters:

.. code-block:: python

    # Scale computational model
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.RECONSTRUCTOR,
        name="Tuned Reconstructor",
        compute=gpu,
        function=Reconstruction,
        params={
            "centroid_agenda": centroid_agenda,
            "n_acts": n_acts,
            "flop_scale": 1.2,  # Increase FLOPs by 20%
            "mem_scale": 0.8,   # Reduce memory ops by 20%
            "n_workers": 4      # Use 4 parallel workers
        },
        dependencies=["Centroider"]
    ))

Troubleshooting
---------------

Common performance considerations:

* **High Latency**: Use GPU acceleration for large systems, consider reducing precision
* **Memory Limitations**: For very large systems, GPU memory may be a constraint
* **Scaling**: Computational complexity is :math:`O(n_{slopes} \\times n_{acts})`

Related Topics
--------------

* :ref:`centroider` - Wavefront sensing that provides inputs to reconstruction
* :ref:`control` - Control algorithms that use reconstruction outputs

API Reference
-------------

For complete API details, see the :ref:`api_reconstruction` section.
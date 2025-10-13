.. _control:

Control System
==============

.. _control_overview:

Overview
--------

The control system in daolite (**D**\ urham **A**\ daptive **O**\ ptics **L**\ atency **I**\ nspection and **T**\ iming **E**\ stimator) governs how the adaptive optics system responds to measured wavefront errors. This component is responsible for converting reconstructed wavefront shapes into appropriate commands for deformable mirrors (DMs), applying control laws to ensure stability and optimal performance.

.. _control_features:

Key Control Features
--------------------

* **Multiple Control Laws**: Implementation of various control strategies from simple integrators to advanced predictive controllers
* **Performance Modeling**: Accurate timing estimates for control algorithms based on system complexity and hardware
* **Modal Control**: Support for modal gain optimization and modal filtering
* **Predictive Control**: Advanced techniques for reducing temporal error through prediction
* **Real-Time Implementation Models**: Realistic modeling of controller implementation on various hardware platforms

.. _using_control:

Using Control Components
------------------------

Adding control operations to your AO pipeline:

.. code-block:: python

    from daolite import Pipeline, PipelineComponent, ComponentType
    from daolite.pipeline.control import FullFrameControl
    from daolite.compute import hardware
    
    # Create a pipeline
    pipeline = Pipeline()
    
    # Define a CPU resource for control
    cpu = hardware.intel_xeon_gold_6342()
    
    # Add controller component
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.CONTROL,
        name="DM Controller",
        compute=cpu,
        function=FullFrameControl,
        params={
            "n_acts": 81*81,  # 81×81 actuator grid
            "operations": ["integration", "offset", "saturation", "dm_power"],
            "flop_scale": 1.0,
            "mem_scale": 1.0
        },
        dependencies=["Reconstructor"]
    ))

Control Operations
------------------

daolite provides timing models for several control operations:

Integration
~~~~~~~~~~~

Models the timing for integrator control operations:

.. code-block:: python

    from daolite.pipeline.control import Integrator
    
    # Add integrator to pipeline
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.CONTROL,
        name="Integrator",
        compute=cpu,
        function=Integrator,
        params={
            "n_acts": 81*81,
            "flop_scale": 1.0,
            "mem_scale": 1.0
        },
        dependencies=["Reconstructor"]
    ))

Full-Frame Control
~~~~~~~~~~~~~~~~~~

For convenience, daolite provides a combined control function that performs multiple operations:

.. code-block:: python

    from daolite.pipeline.control import FullFrameControl
    
    # Add full-frame control
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.CONTROL,
        name="Full Control",
        compute=cpu,
        function=FullFrameControl,
        params={
            "n_acts": 81*81,
            "operations": ["integration", "offset", "saturation", "dm_power"],
            "flop_scale": 1.0,
            "mem_scale": 1.0,
            "debug": False
        },
        dependencies=["Reconstructor"]
    ))

.. _practical_examples:

Practical Examples
------------------

Example: Complete Pipeline with Control
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from daolite import Pipeline, PipelineComponent, ComponentType
    from daolite.pipeline.camera import PCOCamLink
    from daolite.pipeline.calibration import PixelCalibration
    from daolite.pipeline.centroider import Centroider
    from daolite.pipeline.reconstruction import Reconstruction
    from daolite.pipeline.control import FullFrameControl
    from daolite.compute import hardware
    import numpy as np
    
    # Create pipeline
    pipeline = Pipeline()
    
    # Define compute resources
    cpu = hardware.intel_xeon_gold_6342()
    gpu = hardware.nvidia_rtx_4090()
    
    # System parameters
    n_subaps = 80 * 80
    n_acts = 81 * 81
    n_pixels = 1024 * 1024
    n_groups = 50
    
    # Define agendas
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
        params={"centroid_agenda": centroid_agenda, "n_acts": n_acts},
        dependencies=["Centroider"]
    ))
    
    # Add controller
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.CONTROL,
        name="Controller",
        compute=cpu,
        function=FullFrameControl,
        params={
            "n_acts": n_acts,
            "operations": ["integration", "offset", "saturation", "dm_power"]
        },
        dependencies=["Reconstructor"]
    ))
    
    # Run pipeline
    results = pipeline.run()
    print(f"Control time: {results['Controller'].duration:.2f} µs")

.. _performance_considerations:

Performance Considerations
--------------------------

Several factors affect controller performance:

.. _system_size:

System Size
~~~~~~~~~~~

The computational requirements generally scale linearly with the number of actuators for basic control operations like integration.

.. _algorithm_complexity:

Algorithm Computational Complexity
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Different control operations have different computational costs:

* **Integration**: O(n) - Vector addition and scaling
* **Offset**: O(n) - Vector addition  
* **Saturation**: O(n) - Conditional operations on actuator commands
* **DM Power**: O(n) - Power calculation for actuator commands

Related Topics
--------------

* :ref:`reconstruction` - Provides inputs to the control system
* :ref:`centroider` - Wavefront measurements
* :ref:`pipeline` - Integration into complete AO pipeline

API Reference
-------------

For complete API details, see the :ref:`api_control` section.
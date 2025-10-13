.. _pipeline:

Pipeline Architecture
=====================

.. _pipeline_overview:

Overview
--------

The Pipeline Architecture is the core of daolite, providing a flexible way to model complex Adaptive Optics processing chains. It allows you to define components, their dependencies, and compute resources to accurately model the timing behavior of real-world AO systems.

.. _pipeline_features:

Key Features
------------

* **Dependency Management**: Automatically handles dependencies between components
* **Heterogeneous Computing**: Support for different compute resources per component
* **Flexible Component Ordering**: Define components in any order, dependencies determine execution
* **Visualization**: Built-in timing visualization tools
* **Custom Components**: Easily add custom processing stages

.. _pipeline_concepts:

Pipeline Concepts
-----------------

The daolite pipeline is based on these fundamental concepts:

.. _pipeline_components:

Components
~~~~~~~~~~

A pipeline is composed of individual components, each representing a specific processing step in the AO chain:

.. code-block:: python

    from daolite import Pipeline, PipelineComponent, ComponentType
    from daolite.pipeline.camera import PCOCamLink
    
    # Create a pipeline component
    camera_component = PipelineComponent(
        component_type=ComponentType.CAMERA,
        name="Camera",
        compute=cpu_resource,
        function=PCOCamLink,
        params={
            "n_pixels": 1024*1024,
            "group": 10,
            "readout": "rolling"
        }
    )

.. _component_types:

Component Types
~~~~~~~~~~~~~~~

daolite defines standard component types for AO systems:

* ``ComponentType.CAMERA``: Camera readout and initial data acquisition
* ``ComponentType.CALIBRATION``: Pixel calibration operations
* ``ComponentType.CENTROIDER``: Wavefront sensing/centroiding
* ``ComponentType.RECONSTRUCTION``: Wavefront reconstruction
* ``ComponentType.CONTROL``: DM control operations
* ``ComponentType.NETWORK``: Network data transfer
* ``ComponentType.TRANSFER``: PCIe or other data transfer operations
* ``ComponentType.CUSTOM``: User-defined custom operations

.. _component_dependencies:

Dependencies
~~~~~~~~~~~~

Components can depend on other components, creating a directed graph of processing:

.. code-block:: python

    from daolite.pipeline.centroider import Centroider
    import numpy as np
    
    # Create a component that depends on the camera component
    n_subaps = 6400
    centroid_agenda = np.ones(50, dtype=int) * (n_subaps // 50)
    
    centroider_component = PipelineComponent(
        component_type=ComponentType.CENTROIDER,
        name="Centroider",
        compute=gpu_resource,
        function=Centroider,
        params={
            "centroid_agenda": centroid_agenda,
            "n_pix_per_subap": 16*16
        },
        dependencies=["Camera"]  # This component depends on "Camera"
    )

Compute Resources
~~~~~~~~~~~~~~~~~

Each component can use a different compute resource, allowing modeling of heterogeneous systems:

.. code-block:: python

    # Define different compute resources
    cpu_resource = amd_epyc_7763()  # CPU for camera and control
    gpu_resource = nvidia_rtx_4090()  # GPU for centroiding and reconstruction
    
    # Use different resources for different components
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.CAMERA,
        name="Camera",
        compute=cpu_resource,  # CPU resource
        # ...other parameters...
    ))
    
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.CENTROIDER,
        name="Centroider", 
        compute=gpu_resource,  # GPU resource
        # ...other parameters...
    ))


see also: :ref:`hardware_compute_resources` for more details on compute resources.

.. _creating_pipeline:

Creating a Pipeline
-------------------

.. _basic_pipeline:

Basic Pipeline
~~~~~~~~~~~~~~

Here's how to create a basic AO pipeline:

.. code-block:: python

    from daolite import Pipeline, PipelineComponent, ComponentType
    from daolite.compute import hardware
    from daolite.pipeline.camera import PCOCamLink
    from daolite.pipeline.centroider import Centroider
    from daolite.pipeline.reconstruction import Reconstruction
    from daolite.pipeline.control import FullFrameControl
    import numpy as np
    
    # Create compute resources
    cpu = hardware.amd_epyc_7763()
    gpu = hardware.nvidia_rtx_4090()
    
    # System parameters
    n_subaps = 6400
    n_acts = 81 * 81
    n_pixels = 1024 * 1024
    n_groups = 50
    
    # Define agendas
    centroid_agenda = np.ones(n_groups, dtype=int) * (n_subaps // n_groups)
    
    # Create a new pipeline
    pipeline = Pipeline(name="SCAO System")
    
    # Add components in any order
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.CAMERA,
        name="Camera",
        compute=cpu,
        function=PCOCamLink,
        params={"n_pixels": n_pixels, "group": n_groups, "readout": "rolling"}
    ))
    
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.CENTROIDER,
        name="Centroider",
        compute=gpu,
        function=Centroider,
        params={"centroid_agenda": centroid_agenda, "n_pix_per_subap": 16*16},
        dependencies=["Camera"]
    ))
    
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.RECONSTRUCTOR,
        name="Reconstructor",
        compute=gpu,
        function=Reconstruction,
        params={"centroid_agenda": centroid_agenda, "n_acts": n_acts},
        dependencies=["Centroider"]
    ))
    
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.CONTROL,
        name="Controller",
        compute=cpu,
        function=FullFrameControl,
        params={"n_acts": n_acts, "operations": ["integration", "offset", "saturation"]},
        dependencies=["Reconstructor"]
    ))
    
    # Run the pipeline
    results = pipeline.run()
    
    # Visualize the results
    pipeline.visualize(title="AO Pipeline Timing")

.. _complex_pipeline:

Complex Pipelines
~~~~~~~~~~~~~~~~~

More complex pipelines can include branching, multiple dependencies, and transfer operations:

.. code-block:: python

    # Create a pipeline with branching and transfers
    pipeline = Pipeline(name="MCAO System")
    
    # Add camera component
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.CAMERA,
        name="WFS Camera",
        compute=cpu,
        function=PCOCamLink,
        params={"n_pixels": 1024*1024, "group": 10, "readout": "rolling"}
    ))
    
    # Add multiple centroiders for different guide stars
    for i in range(3):
        centroid_agenda = np.ones(20, dtype=int) * (1024 // 20)
        pipeline.add_component(PipelineComponent(
            component_type=ComponentType.CENTROIDER,
            name=f"Centroider GS{i+1}",
            compute=gpu,
            function=Centroider,
            params={"centroid_agenda": centroid_agenda, "n_pix_per_subap": 16*16},
            dependencies=["WFS Camera"]
        ))
    
    # Add reconstructor that depends on all centroiders
    centroid_agenda_recon = np.ones(20, dtype=int) * (3072 // 20)  # Total slopes from 3 GS
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.RECONSTRUCTOR,
        name="Reconstructor",
        compute=gpu,
        function=Reconstruction,
        params={"centroid_agenda": centroid_agenda_recon, "n_acts": 10000},
        dependencies=["Centroider GS1", "Centroider GS2", "Centroider GS3"]
    ))
    
    # Add DM controller
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.CONTROL,
        name="DM Controller",
        compute=cpu,
        function=FullFrameControl,
        params={"n_acts": 10000, "operations": ["integration", "offset", "saturation"]},
        dependencies=["Reconstructor"]
    ))

.. _analyzing_pipelines:

Running and Analyzing Pipelines
-------------------------------

.. _running_pipeline:

Running a Pipeline
~~~~~~~~~~~~~~~~~~

Once a pipeline is defined, you can run it to calculate timing:

.. code-block:: python

    # Run the pipeline with debug information
    results = pipeline.run(debug=True)
    
    # Get the total latency
    total_latency = pipeline.get_total_latency()
    print(f"Total pipeline latency: {total_latency} µs")
    
    # Get component-specific latencies
    component_latencies = pipeline.get_component_latencies()
    for component, latency in component_latencies.items():
        print(f"{component}: {latency} µs")

.. _pipeline_visualization:

Pipeline Visualization
~~~~~~~~~~~~~~~~~~~~~~

daolite provides built-in visualization tools for pipeline timing:

.. code-block:: python

    # Generate a timing visualization
    fig = pipeline.visualize(
        title="AO Pipeline Timing",
        xlabel="Time (µs)",
        save_path="pipeline_timing.png",
        figsize=(12, 8)
    )
    
    # For more control over the visualization:
    from daolite.utils.visualization import create_pipeline_gantt_chart
    
    custom_fig = create_pipeline_gantt_chart(
        pipeline_results=results,
        title="Custom Pipeline Visualization",
        component_colors={
            "Camera": "blue",
            "Centroider": "green",
            "Reconstructor": "red"
        },
        show_critical_path=True
    )

.. _pipeline_summary:

Pipeline Summary
~~~~~~~~~~~~~~~~

Generate a summary of the pipeline performance:

.. code-block:: python

    # Print a summary of the pipeline
    pipeline.print_summary()
    
    # Get a dictionary with the summary data
    summary = pipeline.get_summary()
    
    # Example output:
    # {
    #   'total_latency': 523.45,
    #   'components': {
    #     'Camera': {'start': 0.0, 'end': 150.0, 'latency': 150.0, 'resource': 'CPU'},
    #     'Centroider': {'start': 150.0, 'end': 320.5, 'latency': 170.5, 'resource': 'GPU'},
    #     # ...more components...
    #   },
    #   'critical_path': ['Camera', 'Centroider', 'Reconstructor', 'Control']
    # }

.. _custom_pipeline_functions:

Custom Pipeline Functions
-------------------------

You can create custom functions for use in pipeline components:

.. code-block:: python

    def my_custom_processor(compute, n_elements, scale_factor=1.0, debug=False):
        """
        A custom processing function for use in a pipeline component.
        
        Args:
            compute: The compute resource to use
            n_elements: Number of elements to process
            scale_factor: Optional scaling factor
            debug: Whether to print debug information
            
        Returns:
            A numpy array with timing information
        """
        # Calculate processing time based on compute resource
        if compute.hardware == "GPU":
            # GPU processing model
            mem_time = (n_elements * 4) / compute.memory_bandwidth
            compute_time = (n_elements * 10) / compute.flops  # 10 ops per element
        else:
            # CPU processing model
            mem_time = (n_elements * 4) / (compute.memory_channels * 
                                         compute.memory_width * 
                                         compute.memory_frequency / 8)
            compute_time = (n_elements * 10) / (compute.cores * 
                                              compute.core_frequency * 
                                              compute.flops_per_cycle)
        
        # Scale by implementation efficiency
        compute_time *= scale_factor
        
        # Use the limiting factor
        processing_time = max(mem_time, compute_time)
        
        if debug:
            print(f"Memory time: {mem_time} µs")
            print(f"Compute time: {compute_time} µs")
            print(f"Processing time: {processing_time} µs")
        
        # Create timing array (single timing entry)
        timing = np.zeros([1, 2])
        timing[0, 1] = processing_time
        
        return timing
    
    # Use in a pipeline component
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.CUSTOM,
        name="My Custom Component",
        compute=cpu,
        function=my_custom_processor,
        params={
            "n_elements": 10000,
            "scale_factor": 1.2,
            "debug": True
        },
        dependencies=["Previous Component"]
    ))

.. _pipeline_examples:

Pipeline Examples
-----------------

Here are some complete examples of different pipeline configurations:

.. _scao_pipeline_example:

SCAO Pipeline
~~~~~~~~~~~~~

A complete Single Conjugate Adaptive Optics pipeline:

.. code-block:: python

    from daolite import Pipeline, PipelineComponent, ComponentType
    from daolite import amd_epyc_7763, nvidia_rtx_4090
    from daolite.simulation.camera import simulate_camera_readout
    from daolite.pipeline.centroider import weighted_center_of_gravity
    from daolite.pipeline.reconstruction import mvm_reconstruction
    from daolite.pipeline.control import integrator_control
    from daolite.pipeline.transfer import pcie_transfer
    
    # Create compute resources
    cpu = amd_epyc_7763()
    gpu = nvidia_rtx_4090()
    
    # Create SCAO pipeline
    scao = Pipeline(name="SCAO System")
    
    # System parameters
    n_subaps = 50 * 50
    n_acts = 51 * 51
    n_pixels = 800 * 800
    n_groups = 50
    
    # Define agendas
    centroid_agenda = np.ones(n_groups, dtype=int) * (n_subaps // n_groups)
    
    # Add camera component
    scao.add_component(PipelineComponent(
        component_type=ComponentType.CAMERA,
        name="Shack-Hartmann Camera",
        compute=cpu,
        function=PCOCamLink,
        params={
            "n_pixels": n_pixels,
            "group": n_groups,
            "readout": "global"
        }
    ))
    
    # Add centroider component
    scao.add_component(PipelineComponent(
        component_type=ComponentType.CENTROIDER,
        name="Centroider",
        compute=gpu,
        function=Centroider,
        params={
            "centroid_agenda": centroid_agenda,
            "n_pix_per_subap": 16*16
        },
        dependencies=["Shack-Hartmann Camera"]
    ))
    
    # Add reconstructor component
    scao.add_component(PipelineComponent(
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
    
    # Add controller component
    scao.add_component(PipelineComponent(
        component_type=ComponentType.CONTROL,
        name="Controller",
        compute=cpu,
        function=FullFrameControl,
        params={
            "n_acts": n_acts,
            "operations": ["integration", "offset", "saturation"]
        },
        dependencies=["Reconstructor"]
    ))
    
    # Run the pipeline
    results = scao.run()
    
    # Show the results
    scao.visualize(title="SCAO Pipeline Timing")
    scao.print_summary()

.. _mcao_pipeline_example:

MCAO Pipeline
~~~~~~~~~~~~~

A Multi Conjugate Adaptive Optics pipeline with multiple wavefront sensors and deformable mirrors:

.. code-block:: python

    from daolite import Pipeline, PipelineComponent, ComponentType
    from daolite import amd_epyc_7763, nvidia_a100_80gb
    from daolite.simulation.camera import simulate_camera_readout
    from daolite.pipeline.centroider import weighted_center_of_gravity
    from daolite.pipeline.reconstruction import tomographic_reconstruction
    from daolite.pipeline.control import multi_dm_control
    from daolite.pipeline.transfer import pcie_transfer
    
    # Create compute resources
    cpu = amd_epyc_7763()
    gpu = nvidia_a100_80gb()
    
    # Create MCAO pipeline
    mcao = Pipeline(name="MCAO System")
    
    # Add multiple WFS cameras
    for i in range(5):
        mcao.add_component(PipelineComponent(
            component_type=ComponentType.CAMERA,
            name=f"LGS Camera {i+1}",
            compute=cpu,
            function=PCOCamLink,
            params={
                "n_pixels": 600*600,
                "group": 10,
                "readout": "global"
            }
        ))
        
        # Add centroider for each camera
        n_subaps = 40 * 40
        centroid_agenda = np.ones(30, dtype=int) * (n_subaps // 30)
        mcao.add_component(PipelineComponent(
            component_type=ComponentType.CENTROIDER,
            name=f"Centroider {i+1}",
            compute=gpu,
            function=Centroider,
            params={
                "centroid_agenda": centroid_agenda,
                "n_pix_per_subap": 15*15
            },
            dependencies=[f"LGS Camera {i+1}"]
        ))
    
    # Add reconstructor that depends on all centroiders
    # Combine all slopes
    total_slopes = 5 * 40 * 40  # 5 guide stars
    combined_agenda = np.ones(30, dtype=int) * (total_slopes // 30)
    total_acts = 61*61 + 31*31 + 19*19  # 3 DMs
    
    mcao.add_component(PipelineComponent(
        component_type=ComponentType.RECONSTRUCTOR,
        name="Reconstructor",
        compute=gpu,
        function=Reconstruction,
        params={
            "centroid_agenda": combined_agenda,
            "n_acts": total_acts
        },
        dependencies=[f"Centroider {i+1}" for i in range(5)]
    ))
    
    # Add controller
    mcao.add_component(PipelineComponent(
        component_type=ComponentType.CONTROL,
        name="Controller",
        compute=cpu,
        function=FullFrameControl,
        params={
            "n_acts": total_acts,
            "operations": ["integration", "offset", "saturation"]
        },
        dependencies=["Reconstructor"]
    ))
    
    # Run the pipeline
    results = mcao.run()
    
    # Show the results
    mcao.visualize(title="MCAO Pipeline Timing")
    mcao.print_summary()


.. _related_topics_pipeline:

Related Topics
--------------

* :ref:`camera` - Camera component details
* :ref:`centroider` - Centroiding component details
* :ref:`reconstruction` - Reconstruction component details
* :ref:`control` - Control component details
* :ref:`network` - Network transfer component details
* :ref:`hardware_compute_resources` - Compute resource models
* :ref:`latency_model` - Understanding timing and latency in AO systems

.. _pipeline_api_reference:

API Reference
-------------

For complete API details, see the :ref:`api_pipeline` section.
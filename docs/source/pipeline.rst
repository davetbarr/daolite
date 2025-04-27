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
    
    # Create a pipeline component
    camera_component = PipelineComponent(
        component_type=ComponentType.CAMERA,
        name="Camera",
        compute=cpu_resource,
        function=simulate_camera_readout,
        params={
            "n_pixels": 1024*1024,
            "readout_time": 500  # µs
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

    # Create a component that depends on the camera component
    centroider_component = PipelineComponent(
        component_type=ComponentType.CENTROIDER,
        name="Centroider",
        compute=gpu_resource,
        function=cross_correlation_centroider,
        params={
            "n_subaps": 4096,
            "pixels_per_subap": 256
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
    from daolite import amd_epyc_7763, nvidia_rtx_4090
    
    # Create compute resources
    cpu = amd_epyc_7763()
    gpu = nvidia_rtx_4090()
    
    # Create a new pipeline
    pipeline = Pipeline(name="SCAO System")
    
    # Add components in any order
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.CAMERA,
        name="Camera",
        compute=cpu,
        function=simulate_camera_readout,
        params={"n_pixels": 1024*1024}
    ))
    
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.CENTROIDER,
        name="Centroider",
        compute=gpu,
        function=cross_correlation_centroider,
        params={"n_subaps": 4096, "pixels_per_subap": 256},
        dependencies=["Camera"]
    ))
    
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.RECONSTRUCTION,
        name="Reconstructor",
        compute=gpu,
        function=mvr_reconstruction,
        params={"n_slopes": 8192, "n_actuators": 5000},
        dependencies=["Centroider"]
    ))
    
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.CONTROL,
        name="Controller",
        compute=cpu,
        function=dm_control,
        params={"n_actuators": 5000},
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
        function=simulate_camera_readout,
        params={"n_pixels": 1024*1024}
    ))
    
    # Add PCIe transfer
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.TRANSFER,
        name="CPU to GPU Transfer",
        compute=cpu,
        function=pcie_transfer,
        params={"data_size": 1024*1024*4},  # 4 bytes per pixel
        dependencies=["WFS Camera"]
    ))
    
    # Add multiple centroiders for different guide stars
    for i in range(3):
        pipeline.add_component(PipelineComponent(
            component_type=ComponentType.CENTROIDER,
            name=f"Centroider GS{i+1}",
            compute=gpu,
            function=cross_correlation_centroider,
            params={"n_subaps": 1024, "pixels_per_subap": 256},
            dependencies=["CPU to GPU Transfer"]
        ))
    
    # Add tomographic reconstructor that depends on all centroiders
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.RECONSTRUCTION,
        name="Tomographic Reconstructor",
        compute=gpu,
        function=tomographic_reconstruction,
        params={"n_slopes": 6144, "n_actuators": 10000},
        dependencies=["Centroider GS1", "Centroider GS2", "Centroider GS3"]
    ))
    
    # Add transfer back to CPU
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.TRANSFER,
        name="GPU to CPU Transfer",
        compute=gpu,
        function=pcie_transfer,
        params={"data_size": 10000*4},  # 4 bytes per actuator
        dependencies=["Tomographic Reconstructor"]
    ))
    
    # Add multiple DM controllers
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.CONTROL,
        name="High-altitude DM",
        compute=cpu,
        function=dm_control,
        params={"n_actuators": 4000},
        dependencies=["GPU to CPU Transfer"]
    ))
    
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.CONTROL,
        name="Ground-layer DM",
        compute=cpu,
        function=dm_control,
        params={"n_actuators": 6000},
        dependencies=["GPU to CPU Transfer"]
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
    
    # Add camera component
    scao.add_component(PipelineComponent(
        component_type=ComponentType.CAMERA,
        name="Shack-Hartmann Camera",
        compute=cpu,
        function=simulate_camera_readout,
        params={
            "n_pixels": 800*800,
            "readout_mode": "global",
            "bit_depth": 12,
            "frame_rate": 1000
        }
    ))
    
    # Add CPU to GPU transfer
    scao.add_component(PipelineComponent(
        component_type=ComponentType.TRANSFER,
        name="Camera to GPU Transfer",
        compute=cpu,
        function=pcie_transfer,
        params={
            "data_size": 800*800*2,  # 2 bytes per pixel (12-bit)
            "transfer_type": "host_to_device"
        },
        dependencies=["Shack-Hartmann Camera"]
    ))
    
    # Add centroider component
    scao.add_component(PipelineComponent(
        component_type=ComponentType.CENTROIDER,
        name="WCoG Centroider",
        compute=gpu,
        function=weighted_center_of_gravity,
        params={
            "n_subaps": 50*50,
            "pixels_per_subap": 16*16,
            "weight_sigma": 2.0
        },
        dependencies=["Camera to GPU Transfer"]
    ))
    
    # Add reconstructor component
    scao.add_component(PipelineComponent(
        component_type=ComponentType.RECONSTRUCTION,
        name="MVM Reconstructor",
        compute=gpu,
        function=mvm_reconstruction,
        params={
            "n_slopes": 50*50*2,
            "n_actuators": 51*51,
            "control_matrix_type": "dense"
        },
        dependencies=["WCoG Centroider"]
    ))
    
    # Add GPU to CPU transfer
    scao.add_component(PipelineComponent(
        component_type=ComponentType.TRANSFER,
        name="GPU to DM Transfer",
        compute=gpu,
        function=pcie_transfer,
        params={
            "data_size": 51*51*4,  # 4 bytes per actuator
            "transfer_type": "device_to_host"
        },
        dependencies=["MVM Reconstructor"]
    ))
    
    # Add controller component
    scao.add_component(PipelineComponent(
        component_type=ComponentType.CONTROL,
        name="Integrator Controller",
        compute=cpu,
        function=integrator_control,
        params={
            "n_actuators": 51*51,
            "gain": 0.4,
            "type": "leaky",
            "leak_factor": 0.01
        },
        dependencies=["GPU to DM Transfer"]
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
            function=simulate_camera_readout,
            params={
                "n_pixels": 600*600,
                "readout_mode": "global",
                "bit_depth": 12,
                "frame_rate": 800
            }
        ))
        
        # Add transfer to GPU for each camera
        mcao.add_component(PipelineComponent(
            component_type=ComponentType.TRANSFER,
            name=f"Camera {i+1} to GPU",
            compute=cpu,
            function=pcie_transfer,
            params={
                "data_size": 600*600*2,
                "transfer_type": "host_to_device"
            },
            dependencies=[f"LGS Camera {i+1}"]
        ))
        
        # Add centroider for each camera
        mcao.add_component(PipelineComponent(
            component_type=ComponentType.CENTROIDER,
            name=f"WCoG Centroider {i+1}",
            compute=gpu,
            function=weighted_center_of_gravity,
            params={
                "n_subaps": 40*40,
                "pixels_per_subap": 15*15,
                "weight_sigma": 1.8
            },
            dependencies=[f"Camera {i+1} to GPU"]
        ))
    
    # Add tomographic reconstructor that depends on all centroiders
    mcao.add_component(PipelineComponent(
        component_type=ComponentType.RECONSTRUCTION,
        name="Tomographic Reconstructor",
        compute=gpu,
        function=tomographic_reconstruction,
        params={
            "n_wfs": 5,
            "n_slopes_per_wfs": 40*40*2,
            "n_dm": 3,
            "n_actuators_per_dm": [61*61, 31*31, 19*19],
            "dm_altitudes": [0, 4500, 9000],
            "gs_directions": [[0,0], [30,0], [0,30], [-30,0], [0,-30]],
            "gs_altitudes": [90000, 90000, 90000, 90000, 90000]
        },
        dependencies=[f"WCoG Centroider {i+1}" for i in range(5)]
    ))
    
    # Add transfer back to CPU
    mcao.add_component(PipelineComponent(
        component_type=ComponentType.TRANSFER,
        name="GPU to DM Transfer",
        compute=gpu,
        function=pcie_transfer,
        params={
            "data_size": (61*61 + 31*31 + 19*19)*4,  # Combined actuator data
            "transfer_type": "device_to_host"
        },
        dependencies=["Tomographic Reconstructor"]
    ))
    
    # Add multi-DM controller
    mcao.add_component(PipelineComponent(
        component_type=ComponentType.CONTROL,
        name="Multi-DM Controller",
        compute=cpu,
        function=multi_dm_control,
        params={
            "n_dm": 3,
            "n_actuators_per_dm": [61*61, 31*31, 19*19],
            "gains": [0.4, 0.35, 0.3],
            "controller_types": ["leaky", "leaky", "leaky"],
            "leak_factors": [0.02, 0.02, 0.02]
        },
        dependencies=["GPU to DM Transfer"]
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
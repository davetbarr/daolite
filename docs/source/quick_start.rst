.. _quick_start:

Quick Start Guide
=================

This guide will help you quickly get started with DaoLITE by walking through the basic steps of setting up and running an AO pipeline simulation.

Installation
------------

If you haven't installed DaoLITE yet, refer to :ref:`installation` for detailed installation instructions. In short:

.. code-block:: bash

    pip install daolite

Basic Pipeline Example
----------------------

Let's create a simple Single Conjugate Adaptive Optics (SCAO) pipeline:

.. code-block:: python

    import numpy as np
    from daolite import Pipeline, PipelineComponent, ComponentType
    from daolite import amd_epyc_7763, nvidia_rtx_4090
    from daolite.simulation.camera import simulate_camera_readout
    from daolite.pipeline.calibration import pixel_calibration
    from daolite.pipeline.centroider import center_of_gravity
    from daolite.pipeline.reconstruction import mvm_reconstruction
    from daolite.pipeline.control import integrator_control
    
    # Create a pipeline
    pipeline = Pipeline()
    
    # Define compute resources
    cpu = amd_epyc_7763()
    gpu = nvidia_rtx_4090()
    
    # Step 1: Add camera component
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.CAMERA,
        name="WFS Camera",
        compute=cpu,
        function=simulate_camera_readout,
        params={
            "n_pixels": 240*240,  # Total pixels
            "readout_mode": "global",
            "bit_depth": 12,
            "frame_rate": 1000  # 1 kHz frame rate
        }
    ))
    
    # Step 2: Add pixel calibration component
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.CALIBRATION,
        name="Pixel Calibration",
        compute=cpu,
        function=pixel_calibration,
        params={
            "n_pixels": 240*240,
            "operations": ["dark_subtract", "flat_field", "threshold"],
            "threshold": 100
        },
        dependencies=["WFS Camera"]  # Depends on camera output
    ))
    
    # Step 3: Add centroider component
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.CENTROIDER,
        name="CoG Centroider",
        compute=gpu,  # Using GPU for centroiding
        function=center_of_gravity,
        params={
            "n_subaps": 20*20,  # 20×20 subapertures
            "pixels_per_subap": 12*12,  # 12×12 pixels per subaperture
        },
        dependencies=["Pixel Calibration"]
    ))
    
    # Step 4: Add reconstructor component
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.RECONSTRUCTION,
        name="MVM Reconstructor",
        compute=gpu,  # Using GPU for reconstruction
        function=mvm_reconstruction,
        params={
            "n_slopes": 20*20*2,  # x and y slopes for each subaperture
            "n_actuators": 21*21,  # 21×21 actuator DM
            "sparse_fraction": 0.1  # 10% non-zero elements in control matrix
        },
        dependencies=["CoG Centroider"]
    ))
    
    # Step 5: Add DM controller component
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.CONTROL,
        name="DM Controller",
        compute=cpu,
        function=integrator_control,
        params={
            "n_actuators": 21*21,
            "gain": 0.4,
            "use_integrator": True
        },
        dependencies=["MVM Reconstructor"]
    ))
    
    # Run the pipeline simulation
    results = pipeline.run()
    
    # Print results
    pipeline.print_summary()
    
    # Plot the timing diagram
    pipeline.plot_timing()

Running this code will simulate a basic AO pipeline, calculate the latency of each component, and generate a timing diagram.

Key Concepts
------------

1. **Pipeline and Component Structure**
---------------------------------------

The DaoLITE pipeline is composed of components that represent different processing steps in an adaptive optics system. Each component has:

- A component type (e.g., CAMERA, CALIBRATION)
- A name
- A compute resource (CPU, GPU)
- A function representing the operation
- Parameters that configure the function
- Dependencies on other components

2. **Compute Resources**
------------------------

DaoLITE includes models for various CPUs and GPUs. You can use predefined resources or create custom ones:

.. code-block:: python

    # Using predefined resources
    from daolite import amd_epyc_7763, nvidia_rtx_4090
    
    cpu = amd_epyc_7763()
    gpu = nvidia_rtx_4090()
    
    # Or create a custom CPU
    from daolite import CPU
    
    custom_cpu = CPU(
        cores=64,
        core_frequency=3.5e9,  # 3.5 GHz
        memory_channels=8,
        memory_frequency=3200e6,  # 3200 MHz
        memory_width=8,  # Bytes (64-bit)
        flops_per_cycle=16  # AVX-512 instructions
    )

3. **Component Configuration**
------------------------------

Each component type has specific parameters. For example, for a camera:

.. code-block:: python

    # Camera parameters
    params={
        "n_pixels": 240*240,       # Total pixels
        "readout_mode": "global",  # Global shutter
        "bit_depth": 12,           # 12-bit ADC
        "frame_rate": 1000,        # 1 kHz
        "packetization": True,     # Enable packetized readout
        "group_size": 64,          # Packets per group
    }

Refer to the component documentation for specific parameter details.

4. **Results Analysis**
-----------------------

After running a pipeline, you can analyze the results in several ways:

.. code-block:: python

    # Print a summary of component execution times
    pipeline.print_summary()
    
    # Get the total pipeline latency
    total_latency = pipeline.get_total_latency()
    print(f"Total pipeline latency: {total_latency:.2f} microseconds")
    
    # Plot the timing diagram
    pipeline.plot_timing(save_path="ao_timing.png")  # Optional: save the plot
    
    # Get detailed timing data for custom analysis
    timing_data = pipeline.get_timing_data()
    
    # Calculate the frame rate
    framerate = 1e6 / total_latency
    print(f"Maximum frame rate: {framerate:.2f} Hz")

Example Pipeline Configurations
-------------------------------

SCAO System
~~~~~~~~~~~

The example above shows a basic SCAO system. You can modify it by changing the parameters.

MCAO System
~~~~~~~~~~~

For Multi-Conjugate Adaptive Optics, you'll need multiple guide stars, wavefront sensors, and deformable mirrors:

.. code-block:: python

    # Sample MCAO configuration (abbreviated)
    # Guide Star 1 components
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.CAMERA,
        name="WFS Camera 1",
        # ... parameters ...
    ))
    
    # Add calibration, centroiding for GS1
    # ...
    
    # Guide Star 2 components
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.CAMERA,
        name="WFS Camera 2",
        # ... parameters ...
    ))
    
    # Add calibration, centroiding for GS2
    # ...
    
    # Tomographic reconstruction
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.RECONSTRUCTION,
        name="Tomographic Reconstructor",
        compute=gpu,
        function=tomographic_reconstruction,
        params={
            "n_guide_stars": 2,
            # ... more parameters ...
        },
        dependencies=["Centroider 1", "Centroider 2"]
    ))
    
    # Multiple DM control
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.CONTROL,
        name="Multi-DM Controller",
        # ... parameters ...
        dependencies=["Tomographic Reconstructor"]
    ))

See complete examples in the :ref:`mcao_pipeline_example` section.

Solar AO System
~~~~~~~~~~~~~~~

For solar adaptive optics, you might have a high-resolution wavefront sensor with correlation centroiding:

.. code-block:: python

    # Solar AO configuration (abbreviated)
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.CAMERA,
        name="Solar WFS Camera",
        compute=cpu,
        function=simulate_camera_readout,
        params={
            "n_pixels": 1024*1024,  # 1K x 1K sensor
            "frame_rate": 2000,      # 2 kHz
            # ... more parameters ...
        }
    ))
    
    # ... calibration component ...
    
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.CENTROIDER,
        name="Correlation Centroider",
        compute=gpu,
        function=cross_correlation_centroider,
        params={
            "n_subaps": 80*80,        # 80×80 subapertures
            "pixels_per_subap": 12*12, # 12×12 pixels per subaperture
            "template_size": 6,        # 6×6 template
            # ... more parameters ...
        },
        dependencies=["Pixel Calibration"]
    ))
    
    # ... reconstruction and control components ...

See complete examples in the :ref:`basic_pipeline` section.

Next Steps
----------

- Explore the :ref:`examples` section for more detailed examples
- Read the component documentation for a deeper understanding of each component
- Check the :ref:`api_pipeline` section for complete API reference
- Experiment with different hardware configurations to optimize your AO system
.. _quick_start:

Quick Start Guide
=================

This guide will help you quickly get started with daolite by walking through the basic steps of setting up and running an AO pipeline simulation.

.. raw:: html

    <div class="hero-section placeholder-hero" style="background:#444;color:white;padding:1.5em;border-radius:8px;margin-bottom:1em;text-align:center;">
        <h2>Placeholder Quick Start Hero</h2>
        <p>Edit this block in `docs/source/quick_start.rst` to customize the quick start splash.</p>
    </div>

Installation
------------

If you haven't installed daolite yet, refer to :ref:`installation` for detailed installation instructions. In short:

.. code-block:: bash

    pip install daolite

Basic Pipeline Example
----------------------

Let's create a simple Single Conjugate Adaptive Optics (SCAO) pipeline:

.. code-block:: python

    import numpy as np
    from daolite import Pipeline, PipelineComponent, ComponentType
    from daolite.compute import hardware
    from daolite.simulation.camera import PCOCamLink
    from daolite.pipeline.calibration import PixelCalibration
    from daolite.pipeline.centroider import Centroider
    from daolite.pipeline.reconstruction import Reconstruction
    from daolite.pipeline.control import FullFrameControl
    
    # Create a pipeline
    pipeline = Pipeline()
    
    # Define system parameters
    n_pixels = 1024 * 1024       # 1 megapixel camera
    n_subaps = 80 * 80            # 80x80 subaperture grid
    n_valid_subaps = int(n_subaps * 0.8)  # 80% illuminated
    n_pix_per_subap = 16 * 16     # 16x16 pixels per subaperture
    n_acts = 5000                 # 5000 DM actuators
    n_groups = 50                 # Readout in 50 groups
    
    # Create agendas (how many items processed per iteration)
    pixel_agenda = np.ones(n_groups, dtype=int) * (n_pixels // n_groups)
    centroid_agenda = np.ones(n_groups, dtype=int) * (n_valid_subaps // n_groups)
    
    # Step 1: Add camera component
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.CAMERA,
        name="WFS Camera",
        compute=hardware.amd_epyc_7763(),  # CPU
        function=PCOCamLink,
        params={
            "n_pixels": n_pixels,
            "group": n_groups,
            "readout": 500.0  # 500 µs readout time
        }
    ))
    
    # Step 2: Add pixel calibration component
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.CALIBRATION,
        name="Pixel Calibration",
        compute=hardware.amd_epyc_7763(),  # CPU
        function=PixelCalibration,
        params={
            "pixel_agenda": pixel_agenda,
            "bit_depth": 16
        },
        dependencies=["WFS Camera"]  # Depends on camera output
    ))
    
    # Step 3: Add centroider component
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.CENTROIDER,
        name="Centroider",
        compute=hardware.nvidia_rtx_4090(),  # GPU for centroiding
        function=Centroider,
        params={
            "centroid_agenda": centroid_agenda,
            "n_pix_per_subap": n_pix_per_subap
        },
        dependencies=["Pixel Calibration"]
    ))
    
    # Step 4: Add reconstructor component
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.RECONSTRUCTION,
        name="Reconstructor",
        compute=hardware.nvidia_rtx_4090(),  # GPU for reconstruction
        function=Reconstruction,
        params={
            "n_slopes": n_valid_subaps * 2,  # x and y slopes
            "n_acts": n_acts,
            "centroid_agenda": centroid_agenda
        },
        dependencies=["Centroider"]
    ))
    
    # Step 5: Add DM controller component
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.CONTROL,
        name="DM Controller",
        compute=hardware.amd_epyc_7763(),  # CPU for control
        function=FullFrameControl,
        params={
            "n_acts": n_acts
        },
        dependencies=["Reconstructor"]
    ))
    
    # Run the pipeline simulation
    results = pipeline.run(debug=True)
    
    # Visualize the timing diagram
    pipeline.visualize(
        title="AO Pipeline Timing",
        save_path="ao_pipeline_timing.png"
    )
    
    # Calculate frame rate
    total_latency = results["DM Controller"][-1, 1]  # End time in microseconds
    max_framerate = 1e6 / total_latency
    print(f"Total latency: {total_latency:.2f} µs")
    print(f"Maximum frame rate: {max_framerate:.1f} Hz")

Running this code will simulate a basic AO pipeline, calculate the latency of each component, and generate a timing diagram.

Key Concepts
------------

1. **Pipeline and Component Structure**
---------------------------------------

The daolite pipeline is composed of components that represent different processing steps in an adaptive optics system. Each component has:

- A component type (e.g., CAMERA, CALIBRATION)
- A name
- A compute resource (CPU, GPU)
- A function representing the operation
- Parameters that configure the function
- Dependencies on other components

2. **Compute Resources**
------------------------

daolite includes models for various CPUs and GPUs. You can use predefined resources or create custom ones:

.. code-block:: python

    # Using predefined resources
    from daolite.compute import hardware
    
    cpu = hardware.amd_epyc_7763()
    gpu = hardware.nvidia_rtx_4090()
    
    # Or create a custom resource
    from daolite.compute import create_compute_resources
    
    custom_cpu = create_compute_resources(
        cores=64,
        core_frequency=3.5e9,  # 3.5 GHz
        memory_channels=8,
        memory_frequency=3200e6,  # 3200 MHz
        memory_width=64,  # Bits
        flops_per_cycle=16,  # AVX-512 instructions
        network_speed=100e9,  # 100 Gbps
        time_in_driver=5.0  # Driver overhead in µs
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
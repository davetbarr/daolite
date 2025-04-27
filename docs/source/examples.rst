.. _examples:

Examples
========

The following example scripts are available in the ``examples/`` directory. Each demonstrates a specific feature or use case of daolite. To run an example, use:

.. code-block:: bash

    python examples/<script_name>.py

Detailed Example Analyses
-------------------------

basic_pipeline.py
~~~~~~~~~~~~~~~~~
A minimal, end-to-end AO pipeline using the Pipeline API. Demonstrates how to build a pipeline with camera, calibration, centroiding, reconstruction, and control components, assign CPU/GPU resources, and visualize timing. Uses the Reconstruction function for the reconstruction stage.

**Key code:**

.. code-block:: python

    from daolite.pipeline.pipeline import Pipeline, PipelineComponent, ComponentType
    from daolite.compute.compute_resources import hardware
    from daolite.simulation.camera import PCOCamLink
    from daolite.pipeline.centroider import Centroider
    from daolite.pipeline.reconstruction import Reconstruction
    from daolite.pipeline.control import FullFrameControl
    from daolite.pipeline.calibration import PixelCalibration

    pipeline = Pipeline()
    n_pixels = 1024 * 1024
    n_subaps = 80 * 80
    n_pix_per_subap = 16 * 16
    n_valid_subaps = int(n_subaps * 0.8)
    n_acts = 5000
    n_groups = 50
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.CAMERA,
        name="Camera",
        compute=hardware.amd_epyc_7763(),
        function=PCOCamLink,
        params={"n_pixels": n_pixels, "group": n_groups},
    ))
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.CALIBRATION,
        name="Calibration",
        compute=hardware.amd_epyc_7763(),
        function=PixelCalibration,
        params={"n_pixels": n_pixels, "group": n_groups},
        dependencies=["Camera"],
    ))
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.CENTROIDER,
        name="Centroider",
        compute=hardware.nvidia_rtx_4090(),
        function=Centroider,
        params={"n_valid_subaps": n_valid_subaps, "n_pix_per_subap": n_pix_per_subap},
        dependencies=["Calibration"],
    ))
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.RECONSTRUCTION,
        name="Reconstructor",
        compute=hardware.nvidia_rtx_4090(),
        function=Reconstruction,
        params={"n_slopes": n_valid_subaps * 2, "n_acts": n_acts},
        dependencies=["Centroider"],
    ))
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.CONTROL,
        name="DM Controller",
        compute=hardware.amd_epyc_7763(),
        function=FullFrameControl,
        params={"n_acts": n_acts},
        dependencies=["Reconstructor"],
    ))
    results = pipeline.run(debug=True)
    pipeline.visualize(title="Basic AO Pipeline Timing", save_path="basic_pipeline_timing.png")

**What it shows:**
- Modular pipeline construction
- Assigning hardware resources
- Visualization of timing

config_example.json & json_pipeline.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Defines a pipeline in JSON and runs it programmatically.

**Key code:**

.. code-block:: python

    import json
    from daolite.pipeline.json_runner import run_pipeline_from_json
    with open("examples/config_example.json") as f:
        config = json.load(f)
    results = run_pipeline_from_json(config)

**What it shows:**
- Using configuration files for reproducible pipeline setups
- Decoupling pipeline definition from code

custom_resource_example.py
~~~~~~~~~~~~~~~~~~~~~~~~~~
Demonstrates creating and using a custom compute resource.

**Key code:**

.. code-block:: python

    from daolite.compute import create_compute_resources
    from daolite.pipeline.pipeline import Pipeline, PipelineComponent, ComponentType
    from daolite.simulation.camera import PCOCamLink
    custom_cpu = create_compute_resources(
        cores=16,
        core_frequency=2.5e9,
        flops_per_cycle=16,
        memory_channels=2,
        memory_width=64,
        memory_frequency=2400e6,
        network_speed=25e9,
        time_in_driver=10,
    )
    pipeline = Pipeline()
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.CAMERA,
        name="Camera",
        compute=custom_cpu,
        function=PCOCamLink,
        params={"n_pixels": 512 * 512, "group": 10},
    ))
    results = pipeline.run(debug=True)
    print("Custom resource timing:", results)

**What it shows:**
- Modeling arbitrary hardware resources
- Integrating custom hardware into the pipeline

hardware_comparison.py
~~~~~~~~~~~~~~~~~~~~~~
Compares performance of different hardware resources loaded from YAML files and visualizes the results.

**Key code:**

.. code-block:: python

    from daolite.compute import create_compute_resources_from_yaml, hardware
    import numpy as np
    import matplotlib.pyplot as plt
    custom_cpu = create_compute_resources_from_yaml("examples/custom_cpu.yaml")
    custom_gpu = create_compute_resources_from_yaml("examples/custom_gpu.yaml")
    # ...compare total_time for various workloads and plot results...
    plt.savefig("hardware_comparison.png")

**What it shows:**
- Hardware choice affects pipeline performance
- Benchmarking and visualization

hardware_import_example.py
~~~~~~~~~~~~~~~~~~~~~~~~~~
Demonstrates importing hardware resource definitions from a YAML file.

**Key code:**

.. code-block:: python

    from daolite.compute import create_compute_resources_from_yaml
    custom_cpu = create_compute_resources_from_yaml("examples/custom_cpu.yaml")
    print("Imported custom CPU:", custom_cpu)

**What it shows:**
- Managing hardware definitions externally
- Using YAML for hardware configuration

visualize_timing_example.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~
Shows how to generate and save a pipeline timing plot.

**Key code:**

.. code-block:: python

    from daolite.pipeline.pipeline import Pipeline, PipelineComponent, ComponentType
    from daolite.simulation.camera import PCOCamLink
    from daolite.compute import hardware
    pipeline = Pipeline()
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.CAMERA,
        name="Camera",
        compute=hardware.amd_epyc_7763(),
        function=PCOCamLink,
        params={"n_pixels": 256 * 256, "group": 5},
    ))
    pipeline.run()
    pipeline.visualize(title="Timing Plot Example", save_path="timing_plot_example.png")
    print("Timing plot saved as timing_plot_example.png")

**What it shows:**
- Producing visual timing diagnostics

camera_example.py
~~~~~~~~~~~~~~~~~
Runs only the camera simulation component using a custom compute resource.

**Key code:**

.. code-block:: python

    from daolite.compute import create_compute_resources
    from daolite.simulation.camera import PCOCamLink
    compute = create_compute_resources(
        cores=8,
        core_frequency=2.5e9,
        flops_per_cycle=16,
        memory_channels=2,
        memory_width=64,
        memory_frequency=2400e6,
        network_speed=25e9,
        time_in_driver=10,
    )
    result = PCOCamLink(compute, n_pixels=512 * 512, group=10)
    print("Camera simulation timing:", result)

**What it shows:**
- Benchmarking a single pipeline component

centroider_example.py
~~~~~~~~~~~~~~~~~~~~~
Runs only the centroiding component using a hardware resource and numpy start_times.

**Key code:**

.. code-block:: python

    from daolite.pipeline.centroider import Centroider
    from daolite.compute import hardware
    import numpy as np
    start_times = np.array([...])
    result = Centroider(start_times=start_times, n_valid_subaps=100, n_pix_per_subap=16, compute_resources=hardware.amd_epyc_7763())
    print("Centroiding timing:", result)

**What it shows:**
- Isolated performance testing for centroiding

reconstruction_example.py
~~~~~~~~~~~~~~~~~~~~~~~~~
Runs only the reconstruction component using the Reconstruction function and numpy start_times.

**Key code:**

.. code-block:: python

    from daolite.pipeline.reconstruction import Reconstruction
    from daolite.compute import hardware
    import numpy as np
    start_times = np.zeros([1, 2])
    result = Reconstruction(n_slopes=200, n_acts=500, compute_resources=hardware.amd_epyc_7763(), start_times=start_times)
    print("Reconstruction timing:", result)

**What it shows:**
- Isolated performance testing for reconstruction

control_example.py
~~~~~~~~~~~~~~~~~~
Runs only the control component using FullFrameControl.

**Key code:**

.. code-block:: python

    from daolite.pipeline.control import FullFrameControl
    from daolite.compute import hardware
    result = FullFrameControl(n_acts=500, combine=4, overhead=8, compute_resources=hardware.amd_epyc_7763())
    print("Control timing:", result)

**What it shows:**
- Isolated performance testing for control

network_timing_example.py
~~~~~~~~~~~~~~~~~~~~~~~~~
Models network or PCIe transfer timing using TimeOnNetwork and PCIE.

**Key code:**

.. code-block:: python

    from daolite.compute import create_compute_resources
    from daolite.utils.network import TimeOnNetwork, PCIE
    import numpy as np
    compute = create_compute_resources(...)
    network_time = TimeOnNetwork(n_bits=1024*1024*8, compute_resources=compute)
    print("Network transfer timing (1MB):", network_time)
    start_times = np.zeros([1, 2])
    pcie_time = PCIE(n_bits=1024*1024*8, compute_resources=compute, start_times=start_times)
    print("PCIe transfer timing (1MB):", pcie_time)

**What it shows:**
- Estimating data transfer times for hardware modeling

test_validation_example.py
~~~~~~~~~~~~~~~~~~~~~~~~~~
Shows a simple test/validation pattern for pipeline components.

**Key code:**

.. code-block:: python

    from daolite.simulation.camera import PCOCamLink
    from daolite.compute import create_compute_resources
    compute = create_compute_resources(...)
    output = PCOCamLink(compute, n_pixels=128*128, group=4)
    assert output > 0, "Timing should be positive"
    print("Test passed. Output:", output)

**What it shows:**
- Writing basic tests for pipeline components

migrate_packtise_pipeline.py & migrate_packtise_pipeline_gpu.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Advanced examples for packetized processing and GPU-accelerated pipelines. These scripts show both legacy and modern daolite approaches, including YAML config loading, packetization, and visualization.

**Key code:**

.. code-block:: python

    # See detailed implementation in examples/migrate_packtise_pipeline.py
    # and examples/migrate_packtise_pipeline_gpu.py
    # Demonstrates chunked/packetized data processing and GPU streams

**What it shows:**
- Reducing latency with packetized processing
- Modeling parallelism and resource partitioning on GPUs
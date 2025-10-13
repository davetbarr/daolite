.. _dao:

DAO - Durham Adaptive Optics
=============================

Overview
--------

**DAO** (Durham Adaptive Optics) is a high-performance, real-time software framework designed for adaptive optics systems. It provides a modular and flexible architecture that allows for easy integration of various components, such as wavefront sensors, deformable mirrors, and control algorithms. DAO is built to handle the demanding requirements of adaptive optics applications, including low latency, high throughput, and robust error handling.

daolite was developed in conjunction with DAO to provide accurate latency modeling and performance prediction for real-time control systems built using the DAO framework.

Core Architecture
-----------------

Shared Memory Design
~~~~~~~~~~~~~~~~~~~~

At its heart, DAO is a shared memory library with additional features to make it easier to use in adaptive optics systems. It works using a series of **shared memory blocks** to pass data between processes, enabling:

- **High-speed data transfer**: Direct memory access without copying overhead
- **Low latency**: Minimal inter-process communication delays
- **Process isolation**: Independent processes can fail without affecting the entire system
- **Flexibility**: Easy to add or modify components without recompiling the entire system

This architecture is particularly well-suited for real-time adaptive optics where multiple processes (camera readout, wavefront sensing, reconstruction, control) need to exchange data with minimal delay.

State Machine Management
~~~~~~~~~~~~~~~~~~~~~~~~

DAO includes a state machine to manage the different operational states of the system, such as:

- **Initialization**: Setting up hardware and software components
- **Calibration**: Measuring system response and creating calibration data
- **Operation**: Running the closed-loop AO system
- **Diagnostics**: Testing and troubleshooting

The state machine is **optional** - DAO can be used purely as a shared memory library for applications that don't require state management.

Key Features
------------

High Performance
~~~~~~~~~~~~~~~~

- **Zero-copy data transfer**: Direct access to shared memory eliminates copying overhead
- **Lock-free algorithms**: Minimize contention between processes
- **Real-time optimized**: Designed for deterministic, low-jitter operation
- **Scalable**: Handles systems from small laboratory setups to large telescope AO systems

Modularity
~~~~~~~~~~

- **Component-based**: Each AO component (WFS, DM, reconstructor) runs in its own process
- **Hot-swappable**: Replace or upgrade components without stopping the entire system
- **Language agnostic**: Components can be written in C, C++, Python, or other languages
- **Standard interfaces**: Consistent API across all components

Robustness
~~~~~~~~~~

- **Process isolation**: Component failures don't crash the entire system
- **Error propagation**: Structured error handling and reporting
- **Watchdog timers**: Detect and recover from hung processes
- **Graceful degradation**: System continues operating when non-critical components fail

Development Tools
~~~~~~~~~~~~~~~~~

- **Monitoring utilities**: Real-time visualization of system state and performance
- **Debugging tools**: Inspect shared memory contents and data flow
- **Configuration management**: Easily save and load system configurations
- **Performance profiling**: Identify bottlenecks and optimize performance

DAO Repositories
----------------

DAO is split into several repositories to make it easier to manage and maintain:

daoBase
~~~~~~~

**Repository**: https://github.com/Durham-Adaptive-Optics/daoBase

The core library providing the shared memory functionality and basic data structures. This is the foundation of the DAO framework and includes:

- Shared memory allocation and management
- Inter-process synchronization primitives
- Basic data types for AO systems (images, slopes, commands)
- State machine implementation
- Configuration file handling
- Logging and error reporting

daoTools
~~~~~~~~

**Repository**: https://github.com/Durham-Adaptive-Optics/daoTools

A collection of utility functions and tools for working with the DAO framework, including:

- Data visualization tools (real-time display of WFS images, slopes, etc.)
- System monitoring utilities (performance metrics, system health)
- Configuration editors (GUI tools for system setup)
- Data recording and playback (save telemetry for offline analysis)
- Calibration utilities (interaction matrix measurement, response analysis)
- Diagnostic scripts (system testing and validation)

daoHw
~~~~~

**Repository**: https://github.com/Durham-Adaptive-Optics/daoHw

A hardware abstraction layer for interfacing with various hardware components used in adaptive optics systems:

- **Camera interfaces**: PCO, Andor, Basler, and other manufacturers
- **Deformable mirror drivers**: ALPAO, Boston Micromachines, Iris AO
- **Tip-tilt stages**: Physik Instrumente, Newport, and others
- **Network protocols**: Camera Link, GigE Vision, USB3 Vision
- **Custom hardware**: Framework for integrating proprietary devices

The hardware abstraction layer ensures that high-level control logic remains the same regardless of which specific hardware is used.

Using DAO with daolite
-----------------------

Complementary Tools
~~~~~~~~~~~~~~~~~~~

daolite and DAO are complementary tools designed to work together:

- **DAO**: Real-time control system for running actual AO systems
- **daolite**: Performance modeling tool for designing and optimizing AO systems

Typical Workflow
~~~~~~~~~~~~~~~~

1. **Design with daolite**:
   
   - Model your proposed AO system architecture
   - Estimate latencies for different hardware configurations
   - Identify performance bottlenecks
   - Optimize component allocation (CPU vs GPU)
   - Validate that the design meets latency requirements

2. **Implement with DAO**:
   
   - Build the real-time control system using DAO framework
   - Implement components identified in daolite model
   - Configure shared memory based on data flow design
   - Deploy on target hardware

3. **Validate and Iterate**:
   
   - Measure actual performance using DAO profiling tools
   - Compare real measurements to daolite predictions
   - Refine daolite model scaling factors if needed
   - Optimize implementation based on real-world results

Example: Modeling a DAO-based System
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Here's how you might model a DAO-based AO system in daolite:

.. code-block:: python

    from daolite import Pipeline, PipelineComponent, ComponentType
    from daolite.compute import hardware
    from daolite.pipeline.camera import PCOCamLink
    from daolite.pipeline.calibration import PixelCalibration
    from daolite.pipeline.centroider import Centroider
    from daolite.pipeline.reconstruction import Reconstruction
    from daolite.pipeline.control import FullFrameControl
    import numpy as np
    
    # Model a DAO system with separate processes for each component
    pipeline = Pipeline(name="DAO-based AO System")
    
    # Camera process (DAO daoHw camera interface)
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.CAMERA,
        name="Camera",
        compute=hardware.intel_xeon_gold_6342(),  # CPU for camera readout
        function=PCOCamLink,
        params={"n_pixels": 1024*1024, "group": 50, "readout": "rolling"}
    ))
    
    # Calibration process (reads from camera shared memory)
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.CALIBRATION,
        name="Calibration",
        compute=hardware.intel_xeon_gold_6342(),  # CPU
        function=PixelCalibration,
        params={"pixel_agenda": np.ones(50) * (1024*1024 // 50), "bit_depth": 16},
        dependencies=["Camera"]
    ))
    
    # Centroider process (GPU-accelerated, reads from calibration shared memory)
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.CENTROIDER,
        name="Centroider",
        compute=hardware.nvidia_rtx_4090(),  # GPU
        function=Centroider,
        params={
            "centroid_agenda": np.ones(50) * (6400 // 50),
            "n_pix_per_subap": 16*16
        },
        dependencies=["Calibration"]
    ))
    
    # Reconstructor process (GPU, reads slopes from centroider shared memory)
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.RECONSTRUCTOR,
        name="Reconstructor",
        compute=hardware.nvidia_rtx_4090(),  # GPU
        function=Reconstruction,
        params={
            "centroid_agenda": np.ones(50) * (6400 // 50),
            "n_acts": 5000
        },
        dependencies=["Centroider"]
    ))
    
    # Controller process (CPU, writes commands to DM shared memory)
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.CONTROL,
        name="Controller",
        compute=hardware.intel_xeon_gold_6342(),  # CPU
        function=FullFrameControl,
        params={
            "n_acts": 5000,
            "operations": ["integration", "offset", "saturation"]
        },
        dependencies=["Reconstructor"]
    ))
    
    # Run latency analysis
    results = pipeline.run(debug=True)
    pipeline.visualize(title="DAO System Latency")
    
    # Check if system meets requirements
    total_latency = results["Controller"][-1, 1]  # microseconds
    print(f"Total system latency: {total_latency:.1f} µs")
    print(f"Maximum frame rate: {1e6/total_latency:.1f} Hz")

This model helps you understand whether your DAO system design will meet performance requirements before you implement it.

Shared Memory Overhead
~~~~~~~~~~~~~~~~~~~~~~

When modeling DAO systems, consider adding small overhead for shared memory operations:

- **Memory barriers**: ~10-50 ns per barrier
- **Lock acquisition**: ~50-200 ns (if using locks)
- **Cache line bouncing**: Depends on access patterns
- **NUMA effects**: Add latency for cross-node memory access

These are typically negligible compared to computation time, but can matter for very high-speed systems.

Community and Support
---------------------

Development
~~~~~~~~~~~

DAO is actively developed and maintained by the Durham University Adaptive Optics group. Contributions are welcome!

- **GitHub Organization**: https://github.com/Durham-Adaptive-Optics
- **Issue Tracking**: Report bugs and request features on GitHub
- **Pull Requests**: Contributions are welcome and encouraged

Documentation
~~~~~~~~~~~~~

- **daoBase documentation**: Available in the repository README
- **daoTools documentation**: User guides for each utility
- **daoHw documentation**: Hardware-specific integration guides

Getting Started with DAO
~~~~~~~~~~~~~~~~~~~~~~~~~

1. Clone the repositories:

   .. code-block:: bash

       git clone https://github.com/Durham-Adaptive-Optics/daoBase.git
       git clone https://github.com/Durham-Adaptive-Optics/daoTools.git
       git clone https://github.com/Durham-Adaptive-Optics/daoHw.git

2. Follow the build instructions in each repository's README

3. Explore the example configurations and scripts

4. Join the community discussions on GitHub

Related Topics
--------------

- :ref:`about` - Overview of daolite's capabilities
- :ref:`pipeline` - Pipeline architecture for modeling AO systems
- :ref:`latency_model` - Technical details of latency calculations
- :ref:`projects` - Projects using daolite and DAO

Citation
--------

If you use DAO in your research, please acknowledge the Durham Adaptive Optics group and cite the relevant publications.

.. note::
   
   DAO and daolite are complementary tools: use daolite to **design** your AO system, then use DAO to **build and operate** it in real-time.

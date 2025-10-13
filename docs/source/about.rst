.. _about:

About daolite
=============

What is daolite?
----------------

**daolite** (**D**\ urham **A**\ daptive **O**\ ptics **L**\ atency **I**\ nspection and **T**\ iming **E**\ stimator) is a Python package for modeling and analyzing the computational latency of Adaptive Optics (AO) real-time control systems. It provides accurate timing models for various AO pipeline components, allowing researchers and engineers to design, optimize, and understand the performance characteristics of complex AO systems before implementation.

How daolite Works
-----------------

Core Architecture
~~~~~~~~~~~~~~~~~

daolite uses a **component-based pipeline architecture** where AO systems are modeled as a series of connected processing stages:

1. **Component Definition**: Each processing stage (camera, centroider, reconstructor, etc.) is represented as a ``PipelineComponent`` with:
   
   - A component type (CAMERA, CALIBRATION, CENTROIDER, RECONSTRUCTION, CONTROL, etc.)
   - Assigned compute resources (CPU or GPU specifications)
   - A timing estimation function
   - Parameters specific to that component
   - Dependencies on other components

2. **Dependency Resolution**: The pipeline automatically resolves dependencies between components to determine execution order, handling complex workflows with branching and parallel processing.

3. **Timing Estimation**: Each component's timing function estimates processing time based on:
   
   - Hardware specifications (compute capability, memory bandwidth, network speed)
   - Algorithm complexity (FLOPs, memory access patterns)
   - Data size and structure
   - Whether the operation is memory-bound or compute-bound

4. **Packetization**: daolite models the realistic, packet-by-packet processing of data as it flows through the pipeline, not just end-to-end latency.

Timing Model Principles
~~~~~~~~~~~~~~~~~~~~~~~

The latency estimation in daolite follows these key principles:

**Memory vs. Compute Bound Operations**

For each operation, daolite determines whether it's limited by:

- **Memory bandwidth**: Time = (Data size × Access patterns) / Memory bandwidth
- **Computational throughput**: Time = Required FLOPs / Available FLOPs

The component uses whichever is more limiting (the bottleneck).

**Hardware Modeling**

daolite models computational resources with realistic parameters:

.. code-block:: python

   # CPU model includes:
   - Number of cores
   - Core frequency
   - FLOPs per cycle
   - Memory bandwidth (channels, width, frequency)
   - Network speed
   - Driver overhead
   
   # GPU model includes:
   - Total FLOPs
   - Memory bandwidth
   - PCIe transfer rates
   - Kernel launch overhead

**Dependency and Scheduling**

- Components start when their dependencies complete
- Supports partial dependencies (start when first data packet arrives)
- Models realistic scheduling and data transfer between compute resources
- Accounts for PCIe transfers between CPU and GPU

What Can You Model?
-------------------

AO System Architectures
~~~~~~~~~~~~~~~~~~~~~~~

- **Single Conjugate AO (SCAO)**: Single wavefront sensor and deformable mirror
- **Multi-Conjugate AO (MCAO)**: Multiple wavefront sensors, multiple DMs at different altitudes
- **Laser Tomography AO (LTAO)**: Tomographic wavefront reconstruction
- **Ground Layer AO (GLAO)**: Wide field correction
- **Extreme AO (ExAO)**: High-order systems with thousands of actuators

Pipeline Components
~~~~~~~~~~~~~~~~~~~

**Sensors and Readout**

- Camera readout (rolling shutter, global shutter)
- Various interfaces (CameraLink, GigE Vision, custom)
- Pixel transfer and buffering

**Wavefront Sensing**

- Shack-Hartmann centroiding (CoG, correlation, matched filter)
- Pyramid wavefront sensing (slopes, intensity, extended source)
- Extended source correlation
- Curvature sensing

**Processing Stages**

- Pixel calibration and flat-fielding
- Slope calculation and referencing
- Wavefront reconstruction (matrix-vector multiply, Fourier methods)
- Tomographic reconstruction
- Deformable mirror control (integrator, optimal control)

**Data Transfer**

- Network transfers (10GbE, 100GbE, InfiniBand)
- PCIe transfers (Gen3, Gen4, Gen5)
- Driver and DMA overhead
- Switch latency

Hardware Configurations
~~~~~~~~~~~~~~~~~~~~~~~

**Predefined Resources**

daolite includes models for modern hardware:

- **CPUs**: AMD EPYC 7763, Intel Xeon 8480, and others
- **GPUs**: NVIDIA RTX 4090, H100, AMD MI250X
- Custom YAML-based hardware definitions

**Mixed Compute**

- Assign different components to different hardware
- Model CPU-GPU hybrid systems
- Optimize hardware allocation for minimum latency

Use Cases
---------

System Design
~~~~~~~~~~~~~

- **Pre-implementation Analysis**: Estimate system performance before building hardware
- **Hardware Selection**: Compare different CPU/GPU combinations
- **Bottleneck Identification**: Find which component limits system performance
- **Upgrade Planning**: Predict performance improvements from hardware upgrades

Algorithm Development
~~~~~~~~~~~~~~~~~~~~~

- **Algorithm Comparison**: Compare latency of different algorithms (e.g., CoG vs. correlation centroiding)
- **Optimization Validation**: Verify that algorithm optimizations reduce latency as expected
- **Scaling Analysis**: Understand how performance scales with system size

Real-time Control Design
~~~~~~~~~~~~~~~~~~~~~~~~

- **Frame Rate Estimation**: Calculate maximum achievable frame rates
- **Timing Budget**: Allocate time budgets to different processing stages
- **Latency Requirements**: Verify system meets latency requirements for telescope tracking
- **Multi-system Coordination**: Model synchronized operation of multiple subsystems

Key Features
------------

Flexible and Powerful
~~~~~~~~~~~~~~~~~~~~~

- **Any Component Order**: Define components in any order, dependencies determine execution
- **Heterogeneous Computing**: Mix CPUs and GPUs in the same pipeline
- **Custom Components**: Easily add custom processing stages
- **YAML Configuration**: Define systems in readable configuration files

Accurate and Realistic
~~~~~~~~~~~~~~~~~~~~~~

- **Hardware-specific Models**: Based on actual CPU/GPU specifications
- **Packetized Processing**: Models realistic data flow, not just end-to-end timing
- **Memory and Compute**: Considers both memory bandwidth and computational limits
- **Network Overhead**: Includes driver delays, switch latency, protocol overhead

Easy to Use
~~~~~~~~~~~

- **Simple API**: Intuitive Python API for defining pipelines
- **Built-in Components**: Pre-built functions for common AO operations
- **Visualization**: Automatic generation of timing diagrams
- **JSON Runner**: Run pipelines from JSON configuration files

Extensible
~~~~~~~~~~

- **Custom Hardware**: Define custom CPU/GPU specifications
- **Custom Algorithms**: Add your own timing estimation functions
- **Plugin Architecture**: Extend with new component types
- **Open Source**: Modify and adapt to your needs

Example Workflow
----------------

A typical daolite workflow looks like this:

.. code-block:: python

   from daolite import Pipeline, PipelineComponent, ComponentType
   from daolite.compute import hardware
   from daolite.simulation.camera import PCOCamLink
   from daolite.pipeline.centroider import Centroider
   from daolite.pipeline.reconstruction import Reconstruction
   from daolite.pipeline.control import FullFrameControl
   
   # Create pipeline
   pipeline = Pipeline()
   
   # Add camera component
   pipeline.add_component(PipelineComponent(
       component_type=ComponentType.CAMERA,
       name="WFS Camera",
       compute=hardware.amd_epyc_7763(),  # CPU
       function=PCOCamLink,
       params={"n_pixels": 1024*1024, "group": 50}
   ))
   
   # Add centroider on GPU
   pipeline.add_component(PipelineComponent(
       component_type=ComponentType.CENTROIDER,
       name="Centroider",
       compute=hardware.nvidia_rtx_4090(),  # GPU
       function=Centroider,
       params={"n_valid_subaps": 6400},
       dependencies=["WFS Camera"]
   ))
   
   # Add reconstructor
   pipeline.add_component(PipelineComponent(
       component_type=ComponentType.RECONSTRUCTION,
       name="Reconstructor",
       compute=hardware.nvidia_rtx_4090(),  # GPU
       function=Reconstruction,
       params={"n_slopes": 12800, "n_acts": 5000},
       dependencies=["Centroider"]
   ))
   
   # Add DM controller on CPU
   pipeline.add_component(PipelineComponent(
       component_type=ComponentType.CONTROL,
       name="DM Control",
       compute=hardware.amd_epyc_7763(),  # CPU
       function=FullFrameControl,
       params={"n_acts": 5000},
       dependencies=["Reconstructor"]
   ))
   
   # Run and visualize
   results = pipeline.run(debug=True)
   pipeline.visualize(title="AO Pipeline Timing")
   
   # Calculate frame rate
   total_time = results["DM Control"][-1, 1]  # in microseconds
   max_fps = 1e6 / total_time
   print(f"Maximum frame rate: {max_fps:.1f} Hz")

This produces a timing diagram showing when each component executes and the total system latency.

Accuracy and Limitations
-------------------------

Accuracy
~~~~~~~~

daolite timing estimates are typically within **10-30%** of real-world performance when:

- Hardware specifications are accurate
- Algorithm complexity is correctly characterized
- System architecture matches the model
- Similar types of hardware are compared

The model is most accurate for:

- **Relative comparisons** between different configurations
- **Bottleneck identification** (which component is limiting)
- **Scaling analysis** (how performance changes with problem size)
- **Hardware selection** (comparing CPU vs GPU implementations)

Limitations
~~~~~~~~~~~

- **Does not account for**:
  
  - OS scheduling jitter
  - Cache effects (assumes ideal cache behavior)
  - Thermal throttling
  - Power management scaling
  - Contention from other processes

- **Simplifications**:
  
  - Assumes optimal memory access patterns
  - Does not model low-level CPU/GPU microarchitecture details
  - Network model is simplified (no packet loss, constant latency)

- **Use for**:
  
  - System design and planning
  - Algorithm comparison
  - Hardware selection
  - Bottleneck analysis

- **Not suitable for**:
  
  - Exact real-time scheduling (use real-time OS tools)
  - Compliance testing (use actual hardware)
  - Safety-critical timing guarantees (verify on hardware)

Getting Started
---------------

To start using daolite, see:

- :ref:`installation` - Install daolite and dependencies
- :ref:`quick_start` - Your first pipeline in 5 minutes
- :ref:`pipeline` - Understanding the pipeline architecture
- :ref:`examples` - Complete example pipelines

Development and Community
--------------------------

daolite is open source and welcomes contributions:

- **Repository**: https://github.com/davetbarr/daolite
- **Documentation**: https://daolite.readthedocs.io
- **Issues**: Report bugs and request features on GitHub
- **Contributing**: See :ref:`contributing` for guidelines

License
-------

daolite is licensed under the GNU General Public License v3.0 (GPL-3.0). See the LICENSE file for details.

Citation
--------

If you use daolite in your research, please cite:

.. code-block:: text

   daolite: Durham Adaptive Optics Latency Inspection and Timing Estimator
   David Barr
   https://github.com/davetbarr/daolite
   
   (BibTeX entry coming soon)

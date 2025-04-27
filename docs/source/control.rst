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

Adding a controller to your AO pipeline:

.. code-block:: python

    from daolite import Pipeline, PipelineComponent, ComponentType
    from daolite.pipeline.control import dm_control
    from daolite import intel_xeon_gold_6342
    
    # Create a pipeline
    pipeline = Pipeline()
    
    # Define a CPU resource for control
    cpu = intel_xeon_gold_6342()
    
    # Add controller component
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.CONTROL,
        name="DM Controller",
        compute=cpu,
        function=dm_control,
        params={
            "n_actuators": 41*41,  # 41×41 actuator grid
            "gain": 0.3  # Controller gain
        },
        dependencies=["MVM Reconstructor"]
    ))

.. _control_algorithms:

Control Algorithms
------------------

daolite provides timing models for several control algorithms, each with different performance characteristics and stability properties.

.. _dm_control:

DM Control
~~~~~~~~~~

The primary control approach for AO systems:

.. code-block:: python

    from daolite.pipeline.control import dm_control
    
    # Add DM controller to pipeline
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.CONTROL,
        name="DM Controller",
        compute=cpu,
        function=dm_control,
        params={
            "n_actuators": 41*41,
            "gain": 0.3  # Controller gain
        }
    ))

.. _planned_control_algorithms:

Planned Control Algorithms
~~~~~~~~~~~~~~~~~~~~~~~~~~~

The following control algorithms are planned for future implementation:

* **Leaky Integrator**: Integrator with a leak term to prevent wind-up
* **Modal Control**: Control with mode-dependent gains
* **Linear Quadratic Gaussian (LQG) Control**: Advanced control method using state-space modeling
* **Predictive Control**: Control system that predicts future wavefront errors
* **Anti-Windup Control**: Controller with anti-windup protection for saturating actuators

.. _practical_examples:

Practical Examples
------------------

Example 1: SCAO System with DM Control
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Controller configuration for a high-order SCAO system:

.. code-block:: python

    # Add DM controller to pipeline
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.CONTROL,
        name="SCAO DM Controller",
        compute=cpu,
        function=dm_control,
        params={
            "n_actuators": 75*75,  # 75×75 actuator grid
            "gain": 0.3  # Controller gain
        },
        dependencies=["SCAO Reconstructor"]
    ))

Example 2: MCAO System with Multi-DM Control
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Controller for a multi-conjugate AO system with three DMs:

.. code-block:: python

    # MCAO controller with separate control for each DM
    pipeline.add_component(PipelineComponent(
        component_type=ComponentType.CONTROL,
        name="MCAO Controller",
        compute=cpu,
        function=dm_control,
        params={
            "n_dm": 3,  # 3 deformable mirrors
            "n_actuators_per_dm": [61*61, 31*31, 19*19],  # Actuator counts for each DM
            "gains": [0.4, 0.35, 0.3]  # Different gains for each DM
        },
        dependencies=["MCAO Reconstructor"]
    ))

.. _performance_considerations:

Performance Considerations
--------------------------

Several factors affect controller performance:

.. _system_size:

System Size and Dimensionality
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The computational requirements generally scale with:
* **Number of actuators**: O(n²) for a square DM

.. _algorithm_complexity:

Algorithm Computational Complexity
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Different control algorithms have different computational costs:

* **DM Control**: O(n) - Simple vector operations

.. _memory_vs_compute:

Memory Bandwidth vs. Computation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Control algorithms may be either:

* **Memory bandwidth limited**: Simple operations like DM control

.. _realtime_constraints:

Real-Time Constraints
~~~~~~~~~~~~~~~~~~~~~

Controllers must operate with fixed, deterministic timing:

* **Jitter**: Timing variability can affect stability
* **Worst-case execution time**: Must be predictable and bounded
* **Synchronization**: Proper synchronization with other AO components

.. _performance_metrics:

Performance Metrics
-------------------

Controller performance in daolite is typically evaluated by timing analysis, latency, and throughput of the control loop. For more details on how to interpret these metrics and optimize controller performance, see the :ref:`latency_model` section.

.. _related_topics:

Related Topics
--------------

* :ref:`reconstruction` - Provides inputs to the control system
* :ref:`centroider` - Initial wavefront measurements used in the AO loop
* :ref:`hardware_compute_resources` - Hardware considerations for controller implementation
* :ref:`pipeline` - Integration of control into the complete AO pipeline
* :ref:`latency_model` - Understanding timing and latency impacts on control performance

.. _api_reference:

API Reference
-------------

For complete API details, see the :ref:`api_control` section.

.. seealso::
   
   * :ref:`performance_metrics` - For detailed information on evaluating controller performance
   * :ref:`practical_examples` - For practical implementation examples
   * Example configuration files in the ``examples/`` directory
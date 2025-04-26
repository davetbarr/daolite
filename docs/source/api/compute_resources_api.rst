.. _api_compute_resources:

Compute Resources API Reference
===============================

This page documents the API for the compute resource components in daolite.


Compute Resource Classes
------------------------

.. autoclass:: daolite.compute.resources.ComputeResources
   :members:
   :undoc-members:
   :show-inheritance:

Compute Resource Functions
--------------------------

.. autofunction:: daolite.compute.resources.create_compute_resources
.. autofunction:: daolite.compute.resources.register_hardware_profile

Resource File Operations
------------------------

.. autofunction:: daolite.compute.resources.load_resources_from_file

.. autofunction:: daolite.compute.resources.save_resources_to_file

Benchmarking Functions
----------------------

.. autofunction:: daolite.compute.benchmark_cpu

.. autofunction:: daolite.compute.benchmark_gpu

.. autofunction:: daolite.compute.estimate_memory_bandwidth

.. autofunction:: daolite.compute.estimate_flops
.. daolite documentation master file, created by
   sphinx-quickstart on Mon Aug 19 11:36:33 2024.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to daolite's documentation!
===================================

daolite (**D**\ urham **A**\ daptive **O**\ ptics **L**\ atency **I**\ nspection and **T**\ iming **E**\ stimator) is a Python package for
modeling and simulating the performance of adaptive optics systems. daolite provides detailed timing models
for various AO pipeline components, allowing users to understand and optimize the latency performance
of real-time adaptive optics systems.

.. toctree::
   :maxdepth: 2
   :caption: Getting Started:

   install
   quick_start
   latency_model
   compute_resources
   pipeline
   examples
   tests
   building_docs

.. toctree::
   :maxdepth: 2
   :caption: Components:

   camera
   calibration
   centroider
   reconstruction
   control
   network
   pipeline_designer
   json_pipeline

.. toctree::
   :maxdepth: 2
   :caption: API Reference:

   api/camera_api
   api/calibration_api
   api/centroider_api
   api/reconstruction_api
   api/control_api
   api/network_api
   api/pipeline_api
   api/compute_resources_api

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

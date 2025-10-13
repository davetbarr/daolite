.. daolite documentation master file

daolite — Adaptive Optics Latency Analysis
===========================================

.. raw:: html

   <div class="hero-section">
      <img src="_static/images/daoliteLogoSmall.png" alt="daolite" class="hero-logo"/>
      <div class="hero-text">
        <h1>daolite</h1>
        <p class="tagline">Model and optimize computational latency in Adaptive Optics real-time control systems.</p>
        <p class="description">Estimate per-component timing, compare hardware configurations (CPUs, GPUs, network), and iterate on pipeline designs to meet real-time constraints.</p>
        <div class="cta-buttons">
           <a href="quick_start.html" class="cta-button">Get Started</a>
           <a href="install.html" class="cta-button secondary">Install</a>
           <a href="projects.html" class="cta-button secondary">Used In</a>
        </div>
      </div>
   </div>

What is daolite?
================

daolite is a Python package for modeling the computational timing and latency of adaptive optics (AO) systems. It helps you:

* **Design AO Systems**: Compare different hardware configurations before building
* **Identify Bottlenecks**: Find which components limit your frame rate
* **Optimize Performance**: Test different algorithms and processing strategies
* **Validate Timing**: Ensure your system meets real-time requirements

.. raw:: html

   <div class="feature-grid">
      <div class="feature-card">
         <h3><span class="icon">🔬</span>Component-Based Modeling</h3>
         <p>Model cameras, calibration, centroiders, reconstructors, and controllers with accurate timing estimates based on hardware specifications.</p>
      </div>
      <div class="feature-card">
         <h3><span class="icon">⚙️</span>Hardware Comparison</h3>
         <p>Compare CPUs, GPUs, and network configurations. Use built-in hardware profiles or define your own custom resources.</p>
      </div>
      <div class="feature-card">
         <h3><span class="icon">�</span>Pipeline Visualization</h3>
         <p>Generate timing diagrams showing when each component runs, where dependencies occur, and total pipeline latency.</p>
      </div>
      <div class="feature-card">
         <h3><span class="icon">🎯</span>Agenda-Based API</h3>
         <p>Model pipelined and grouped processing patterns that match real RTC implementations for accurate timing predictions.</p>
      </div>
      <div class="feature-card">
         <h3><span class="icon">🔗</span>Flexible Dependencies</h3>
         <p>Build complex multi-guide star, multi-DM systems with automatic dependency resolution and parallel component execution.</p>
      </div>
      <div class="feature-card">
         <h3><span class="icon">�</span>JSON Configuration</h3>
         <p>Define pipelines in JSON for reproducible experiments, parameter sweeps, and version-controlled system designs.</p>
      </div>
   </div>

Key Features
============

**Comprehensive Component Library**
   Built-in models for all major AO pipeline stages: PCO cameras, pixel calibration, Shack-Hartmann centroiders, matrix-vector multiplication reconstruction, and DM control.

**Realistic Hardware Models**
   Pre-configured profiles for AMD EPYC CPUs, Intel Xeon processors, NVIDIA GPUs (RTX, A100, H100), and various network technologies.

**YAML-Based Hardware Definitions**
   Easily add new hardware by creating YAML configuration files with memory bandwidth, FLOP rates, and other specifications.

**Python and JSON APIs**
   Build pipelines programmatically with Python or define them declaratively in JSON for easy sharing and reproducibility.

Documentation
=============

.. toctree::
   :maxdepth: 2
   :caption: Getting Started:

   about
   install
   quick_start
   contributing
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
   :caption: Community:

   projects

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
.. daolite documentation master file

daolite — Latency-aware AO pipeline tools
=========================================

.. raw:: html

   <div class="hero-section">
      <h1>daolite</h1>
      <p class="tagline">Latency and timing analysis for Adaptive Optics pipelines</p>
      <p class="description">daolite provides tools to model, simulate and measure latency across AO pipeline components, helping you tune and understand end-to-end timing.</p>
      <div class="cta-buttons">
         <a href="quick_start.html" class="cta-button">Get Started</a>
         <a href="install.html" class="cta-button secondary">Install</a>
      </div>
   </div>

Why choose daolite?
====================

.. raw:: html

   <div class="feature-grid">
      <div class="feature-card">
         <h3><span class="icon">⚡</span>Fast Timing Analysis</h3>
         <p>Profile and model per-component latency to find bottlenecks in AO pipelines.</p>
      </div>
      <div class="feature-card">
         <h3><span class="icon">🔧</span>Modular Components</h3>
         <p>Compose flexible pipelines from cameras, calibrations, centroiders and controllers.</p>
      </div>
      <div class="feature-card">
         <h3><span class="icon">📈</span>Insightful Visualisation</h3>
         <p>Generate timing diagrams and reports to visualize pipeline performance.</p>
      </div>
   </div>

Quick Start
===========

.. raw:: html

   <div class="quick-start">
      <h2>Get up and running quickly</h2>
      <p>Use the Quick Start guide to create a basic pipeline and run a timing analysis in minutes.</p>
   </div>

Repository Structure
====================

.. raw:: html

   <div class="repo-badges">
      <a href="#" class="repo-badge">🏗️ daolite - Core Timing Tools</a>
      <a href="#" class="repo-badge">🛠️ daolite-examples</a>
   </div>

Overview
========

daolite provides timing and latency modelling for AO components. The docs below will guide you through installation, building and running example pipelines.

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
.. daolite documentation master file, created by
   sphinx-quickstart on Mon Aug 19 11:36:33 2024.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

.. raw:: html

   <div class="hero-section">
      <h1>daolite</h1>
      <p class="tagline">Latency and timing analysis for Adaptive Optics pipelines</p>
      <p class="description">daolite provides tools to model, simulate and measure latency across AO pipeline components, helping you tune and understand end-to-end timing.</p>
      <div class="cta-buttons">
         <a href="quick_start.html" class="cta-button">Get Started</a>
         <a href="install.html" class="cta-button secondary">Install</a>
      </div>
   </div>

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

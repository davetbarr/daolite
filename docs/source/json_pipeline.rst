.. _json_pipeline:

JSON Pipeline Runner
====================

Overview
--------

The JSON Pipeline Runner allows you to define and execute daolite AO pipelines using a JSON configuration file. This is useful for scripting, automation, and reproducible pipeline setups.

Features
--------
- Define pipeline components and connections in a JSON file
- Map JSON component types to actual daolite classes/functions
- Run pipelines from the command line
- Supports all major pipeline component types (camera, centroider, calibration, reconstruction, control, network)

Usage
-----

To run a pipeline from a JSON file:

.. code-block:: bash

    daolite-pipeline-json path/to/pipeline.json

or, if running from source:

.. code-block:: bash

    python -m daolite.pipeline.json_runner path/to/pipeline.json

Or directly:

.. code-block:: bash

    python daolite/pipeline/json_runner.py path/to/pipeline.json

JSON Format
-----------

A pipeline JSON file should define components and their connections. Example:

.. code-block:: json

    {
      "components": [
        {"type": "CAMERA", "name": "Camera1", "params": {"n_pixels": 1024}},
        {"type": "CENTROIDER", "name": "Centroider1", "params": {"n_subaps": 16}}
      ],
      "connections": [
        {"start": "Camera1", "end": "Centroider1"}
      ]
    }

API Reference
-------------

.. automodule:: daolite.pipeline.json_runner
   :members:
   :undoc-members:
   :show-inheritance:

.. _pipeline_designer:

Pipeline Designer GUI
=====================

Overview
--------

The Pipeline Designer is a graphical application for creating and editing DaoLITE AO pipelines. It is especially useful for designing complex, multi-node, or networked AO systems.

Features
--------
- Drag-and-drop interface for adding pipeline components
- Visual editing of component parameters and connections
- Support for network and multi-compute node configurations
- Export pipelines to JSON for use with the JSON pipeline runner

Launching the Designer
----------------------

To start the Pipeline Designer GUI, run:

.. code-block:: bash

    python pipeline_designer.py

This will launch the graphical application.

Implementation
--------------

The designer is implemented in ``pipeline_designer.py`` and uses ``daolite.gui.designer.PipelineDesignerApp`` as the main application class.

API Reference
-------------

.. automodule:: daolite.gui.pipeline_designer
   :members:
   :undoc-members:
   :show-inheritance:

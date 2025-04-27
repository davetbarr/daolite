.. _installation:

Installation
=============

daolite (Durham Adaptive Optics Latency Inspection Tool Environment) provides tools to estimate computational latency in Adaptive Optics (AO) real-time control systems.

Requirements
------------

daolite requires the following dependencies:
- Python 3.8 or higher
- NumPy
- Matplotlib
- PyYAML
- SciPy (optional, for advanced reconstruction methods)

Installation Methods
--------------------

Standard Installation
~~~~~~~~~~~~~~~~~~~~~

To install daolite, run the following commands:

.. code-block:: bash

    pip install -r requirements.txt
    python setup.py install

Development Installation
~~~~~~~~~~~~~~~~~~~~~~~~

For development purposes, you can install daolite in development mode:

.. code-block:: bash

    pip install -e .

This will install the package in development mode, allowing you to modify the source code without reinstalling.

Verifying Installation
----------------------

After installation, you can verify that daolite is installed correctly by running:

.. code-block:: python

    import daolite
    print(daolite.__version__)

Platform Support
----------------

daolite is compatible with:
- Linux (recommended for performance analysis)
- macOS
- Windows

GPU Support
-----------

While daolite itself does not require a GPU to run, it can model performance of GPU-accelerated systems. The modeling capabilities support:
- NVIDIA GPUs
- AMD GPUs
- Intel GPUs

Additional Components
---------------------

For some advanced features, you may need additional packages:
- CuPy (for CUDA integration testing)
- Bokeh (for interactive visualizations)
- sphinx (for building documentation)

These can be installed with:

.. code-block:: bash

    pip install daolite[extras]

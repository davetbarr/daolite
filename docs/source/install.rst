.. _installation:

Installation
=============

daolite (Durham Adaptive Optics Latency Inspection Tool Environment) provides tools to estimate computational latency in Adaptive Optics (AO) real-time control systems.

.. raw:: html

    <div class="hero-section placeholder-hero" style="background:#333;color:white;padding:1.5em;border-radius:8px;margin-bottom:1em;text-align:center;">
        <h2>Placeholder Install Hero</h2>
        <p>Edit this block in `docs/source/install.rst` to customize the installation splash.</p>
    </div>

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

Setting Up Pre-commit Hooks
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

daolite uses pre-commit hooks to maintain code quality. These hooks automatically run linting, formatting, and import sorting before each commit.

**Install and setup pre-commit:**

.. code-block:: bash

    # Install pre-commit
    pip install pre-commit

    # Install the git hooks
    pre-commit install

**Run pre-commit manually:**

.. code-block:: bash

    # Run all hooks on all files
    pre-commit run --all-files

    # Or run individual tools
    ruff check --fix .     # Linting with auto-fix
    black .                # Code formatting
    isort .                # Import sorting

The pre-commit hooks will automatically run when you commit changes. If any issues are found:

1. Auto-fixable issues (formatting, import order) will be fixed automatically
2. The commit will be blocked if there are remaining issues
3. Fix the issues and commit again

**Pre-commit configuration:**

The project uses the following tools (configured in ``.pre-commit-config.yaml``):

- **Ruff**: Fast Python linter (replaces flake8, pylint, etc.)
- **Black**: Code formatter for consistent style
- **isort**: Import statement organizer

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

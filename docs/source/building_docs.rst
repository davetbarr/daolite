.. _building_docs:

Building Documentation
======================

This guide explains how to build the daolite documentation locally and contribute to documentation improvements.

Prerequisites
-------------

To build the documentation, you'll need Sphinx and several extensions:

.. code-block:: bash

    pip install sphinx sphinx-rtd-theme sphinx-autodoc-typehints sphinx-copybutton

Building HTML Documentation
---------------------------

To build the documentation as HTML files:

.. code-block:: bash

    # Navigate to the documentation directory
    cd doc
    
    # Build HTML documentation
    make html

The HTML output will be in the `doc/build/html/` directory. Open `index.html` to view it:

.. code-block:: bash

    # On macOS
    open build/html/index.html
    
    # On Linux
    xdg-open build/html/index.html
    
    # On Windows
    start build/html/index.html

Building PDF Documentation
--------------------------

To build a PDF version of the documentation (requires LaTeX):

.. code-block:: bash

    # First, install LaTeX if you don't have it
    # macOS: brew install --cask mactex
    # Ubuntu: apt-get install texlive-full
    
    # Then build the PDF
    cd doc
    make latexpdf
    
    # The PDF will be in build/latex/daolite.pdf
    open build/latex/daolite.pdf

Clean Build
-----------

To perform a clean build (remove all previous build artifacts):

.. code-block:: bash

    cd doc
    make clean
    make html

Documentation Structure
-----------------------

The documentation source files are organized as follows:

- `source/index.rst`: Main documentation entry point
- `source/*.rst`: Top-level documentation pages
- `source/api/*.rst`: API reference documentation
- `source/examples/*.rst`: Example documentation

Adding New Documentation
------------------------

To add a new documentation page:

1. Create a new `.rst` file in the appropriate directory
2. Add a reference to your new file in the appropriate toctree in `index.rst`
3. Build the documentation to verify it appears correctly

Documenting Code for API Reference
----------------------------------

daolite uses autodoc to generate API documentation from docstrings. When writing docstrings, please follow these guidelines:

1. Use NumPy-style docstrings
2. Document all parameters, return values, and exceptions
3. Include examples where appropriate
4. Use type hints consistent with the code

Example docstring:

.. code-block:: python

    def center_of_gravity(compute, n_subaps, pixels_per_subap, debug=False):
        """
        Calculate timing for center of gravity centroiding.
        
        Parameters
        ----------
        compute : ComputeResource
            The compute resource to use for the calculation.
        n_subaps : int
            Number of subapertures.
        pixels_per_subap : int
            Number of pixels per subaperture.
        debug : bool, optional
            If True, print debug information. Default is False.
            
        Returns
        -------
        numpy.ndarray
            Array with shape (1, 2) containing start and end times.
            
        Examples
        --------
        >>> from daolite import amd_epyc_7763
        >>> cpu = amd_epyc_7763()
        >>> timing = center_of_gravity(cpu, 100, 256)
        >>> timing.shape
        (1, 2)
        """
        # Function implementation...

Cross-Referencing
-----------------

Use intersphinx to link to external documentation:

.. code-block:: rst

    See :py:func:`numpy.fft.fft` for the FFT implementation.
    
For internal references, use:

.. code-block:: rst

    See :ref:`centroider` for centroiding documentation.
    
    See :py:class:`daolite.Pipeline` for the pipeline class.

Math Equations
--------------

Use LaTeX for mathematical equations:

.. code-block:: rst

    .. math::
        
        S_{x,y} = \frac{\sum_i \sum_j I(i,j) \cdot (i,j)}{\sum_i \sum_j I(i,j)}

Images and Figures
------------------

To include images:

.. code-block:: rst

    .. figure:: images/pipeline_diagram.png
        :width: 80%
        :align: center
        :alt: daolite Pipeline Diagram
        
        Diagram of the daolite pipeline architecture.

Documentation Testing
---------------------

To test documentation examples, use doctest:

.. code-block:: bash

    cd doc
    make doctest

Troubleshooting
---------------

If you encounter issues building the documentation:

1. Check the Sphinx error messages for specific file and line references
2. Verify that all required packages are installed
3. Ensure that any modules referenced by autodoc are importable
4. Check for syntax errors in reStructuredText files

Deployment
----------

The documentation is automatically built and deployed through GitHub Pages when changes are pushed to the main branch.

Contributing to Documentation
-----------------------------

Contributions to documentation are welcome! Please follow these steps:

1. Fork the repository on GitHub
2. Make your documentation changes
3. Build the documentation locally to verify your changes
4. Submit a pull request with a clear description of your documentation improvements
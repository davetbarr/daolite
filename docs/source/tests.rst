.. _tests:

Running Tests
=============

Overview
--------

Testing is an essential part of maintaining DaoLITE (**D**\ urham **A**\ daptive **O**\ ptics **L**\ atency **I**\ nspection and **T**\ iming **E**\ stimator) and ensuring that all components work correctly. This guide explains how to run the test suite, generate coverage reports, and contribute new tests to the project.

Prerequisites
-------------

To run the DaoLITE tests, you'll need pytest and several testing-related packages:

.. code-block:: bash

    pip install pytest pytest-cov pytest-xdist pytest-benchmark

Running the Test Suite
----------------------

To run the complete test suite:

.. code-block:: bash

    # Navigate to the project root directory
    cd /path/to/DaoLITE
    
    # Run all tests
    pytest

This will discover and run all tests in the `tests/` directory.

Running Specific Tests
----------------------

To run a specific test file or test function:

.. code-block:: bash

    # Run tests in a specific file
    pytest tests/test_camera.py
    
    # Run a specific test function
    pytest tests/test_camera.py::test_global_shutter_readout
    
    # Run tests matching a pattern
    pytest -k "camera or centroider"

Generating Coverage Reports
---------------------------

To generate a test coverage report:

.. code-block:: bash

    # Run tests with coverage
    pytest --cov=DaoLite
    
    # Generate an HTML report
    pytest --cov=DaoLite --cov-report=html
    
    # Open the HTML report
    open htmlcov/index.html

Parallel Test Execution
-----------------------

For faster test execution on multi-core systems:

.. code-block:: bash

    # Run tests in parallel using available CPU cores
    pytest -xvs -n auto

Benchmarking Tests
------------------

To benchmark performance-critical code:

.. code-block:: bash

    # Run benchmark tests
    pytest tests/test_centroider.py --benchmark-only
    
    # Compare against previous benchmark results
    pytest-benchmark compare --group-by=name

Running Tests with Different Python Versions
--------------------------------------------

For testing compatibility with multiple Python versions:

.. code-block:: bash

    # Using tox (first install with: pip install tox)
    tox

This requires a configured `tox.ini` file in the project root.

Continuous Integration
----------------------

The DaoLITE project uses GitHub Actions for continuous integration testing. When a pull request is submitted, the test suite automatically runs on:

* Different operating systems (Linux, macOS, Windows)
* Different Python versions (3.8, 3.9, 3.10, 3.11)
* Different configurations (with/without GPU support)

Adding New Tests
----------------

When adding new functionality to DaoLITE, you should also add corresponding tests:

1. Create test functions in an appropriate file in the `tests/` directory
2. Use the pytest framework for assertions and fixtures
3. Follow the naming convention `test_*.py` for test files and `test_*` for test functions
4. Include tests for both normal operation and edge cases

Example test function:

.. code-block:: python

    # tests/test_new_feature.py
    import pytest
    import numpy as np
    from DaoLite.your_module import your_function
    
    def test_your_function_basic():
        """Test basic functionality of your_function."""
        result = your_function(param1=10, param2=20)
        assert result.shape == (10, 2)
        assert np.isclose(result.mean(), 15.0, rtol=1e-5)
    
    def test_your_function_edge_case():
        """Test your_function with edge case inputs."""
        with pytest.raises(ValueError):
            your_function(param1=-1, param2=20)  # Should raise ValueError for negative param1

Test Fixtures
-------------

DaoLITE tests use pytest fixtures for setup and teardown of test resources:

.. code-block:: python

    # tests/conftest.py (shared fixtures)
    import pytest
    import numpy as np
    from DaoLite import amd_epyc_7763
    
    @pytest.fixture
    def cpu_resource():
        """Return a CPU compute resource for testing."""
        return amd_epyc_7763()
    
    @pytest.fixture
    def sample_data():
        """Generate sample data for testing."""
        return np.random.rand(100, 100)
    
    # In your test file
    def test_with_fixtures(cpu_resource, sample_data):
        """Test using the fixtures."""
        result = your_function(cpu_resource, sample_data)
        assert result is not None

Mocking External Dependencies
-----------------------------

For testing components that depend on external systems:

.. code-block:: python

    import pytest
    from unittest.mock import MagicMock, patch
    
    @patch('DaoLite.external_module.external_function')
    def test_with_mock(mock_external):
        """Test with mocked external dependency."""
        # Configure the mock
        mock_external.return_value = 42
        
        # Test your function that calls the external dependency
        from DaoLite.your_module import function_that_uses_external
        result = function_that_uses_external()
        
        # Assert the result and that the mock was called
        assert result == 42
        mock_external.assert_called_once()


Property-Based Testing
----------------------

For more thorough testing with varied inputs:

.. code-block:: bash

    # Install hypothesis
    pip install hypothesis

.. code-block:: python

    from hypothesis import given, strategies as st
    
    @given(data=st.lists(st.floats(min_value=0, max_value=1000), min_size=10, max_size=100))
    def test_property_based(data):
        """Test function with many random inputs."""
        result = your_function(data)
        # Assert properties that should hold for any valid input
        assert len(result) == len(data)
        assert all(r >= 0 for r in result)

Test Documentation
------------------

All tests should include clear docstrings explaining:

1. What functionality is being tested
2. What inputs are being used
3. What the expected outcome is

Example:

.. code-block:: python

    def test_center_of_gravity():
        """
        Test the center_of_gravity function.
        
        This test verifies that:
        1. The function returns an array of the expected shape
        2. Centroids are calculated correctly for a known input
        3. The function handles edge cases appropriately
        """
        # Test code here...

Troubleshooting Tests
---------------------

Common issues and their solutions:

- **Tests not discovered**: Ensure test files and functions follow the naming convention (`test_*.py` and `test_*`)
- **Import errors**: Check that the package is installed in development mode (`pip install -e .`)
- **Failing assertions**: Use pytest's verbose mode (`pytest -v`) to see detailed output
- **Hanging tests**: Use pytest's timeout plugin (`pip install pytest-timeout` and `pytest --timeout=30`)
- **Segmentation faults**: These often indicate memory errors in C extensions

Getting Support
---------------

If you need help with running tests or adding new tests, please:

1. Check the existing test files for examples
2. Review pytest documentation at https://docs.pytest.org/
3. Ask for help in the DaoLITE GitHub repository by opening an issue

Contributing Tests
------------------

Contributions of new tests are welcome! Please follow these guidelines:

1. Ensure your tests are well-documented with clear assertions
2. Include both basic functionality tests and edge cases
3. Keep tests focused and small (test one thing per test function)
4. Follow the existing coding style
5. Include your tests in a pull request with the code they're testing
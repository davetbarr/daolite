.. _contributing:

Contributing to daolite
========================

Thank you for your interest in contributing to daolite! This guide will help you get started with development.

Getting Started
---------------

1. **Fork the repository** and clone your fork:

   .. code-block:: bash

      git clone https://github.com/yourusername/daolite.git
      cd daolite

2. **Install in development mode:**

   .. code-block:: bash

      pip install -e .
      pip install -r requirements.txt

3. **Install pre-commit hooks:**

   .. code-block:: bash

      pip install pre-commit
      pre-commit install

Development Workflow
--------------------

Code Quality Standards
~~~~~~~~~~~~~~~~~~~~~~

This project uses automated tools to maintain code quality:

- **Ruff**: Fast Python linter for catching errors and enforcing style
- **Black**: Automatic code formatter
- **isort**: Import statement organizer
- **pytest**: Testing framework

Pre-commit Hooks (Required)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Pre-commit hooks are **required** and will run automatically before each commit. They ensure:

- Code is properly formatted
- Imports are sorted correctly
- Linting rules are followed
- No obvious errors are present

**Running pre-commit manually:**

.. code-block:: bash

   # Run on all files
   pre-commit run --all-files

   # Run specific tools
   ruff check --fix .    # Lint and auto-fix
   black .               # Format code
   isort .               # Sort imports

If pre-commit finds issues:

1. Auto-fixable issues will be corrected automatically
2. You'll need to stage the fixed files and commit again
3. For non-auto-fixable issues, fix them manually and retry

Running Tests
~~~~~~~~~~~~~

Before submitting a pull request, ensure all tests pass:

.. code-block:: bash

   # Run all tests
   pytest

   # Run with coverage report
   pytest --cov=daolite

   # Run specific test files
   pytest tests/test_camera.py

All pull requests must maintain or improve code coverage.

Making Changes
~~~~~~~~~~~~~~

1. **Create a new branch** for your feature or bugfix:

   .. code-block:: bash

      git checkout -b feature/your-feature-name
      # or
      git checkout -b fix/your-bugfix-name

2. **Make your changes** following the coding standards

3. **Write or update tests** for your changes

4. **Run tests and linting:**

   .. code-block:: bash

      pytest
      ruff check .

5. **Commit your changes:**

   .. code-block:: bash

      git add .
      git commit -m "Description of your changes"
   
   The pre-commit hooks will run automatically. If they fail, fix the issues and commit again.

6. **Push to your fork:**

   .. code-block:: bash

      git push origin feature/your-feature-name

7. **Open a Pull Request** on GitHub

Coding Standards
----------------

Python Style
~~~~~~~~~~~~

- Follow PEP 8 with Black's formatting
- Maximum line length: 88 characters (Black default)
- Use type hints where appropriate
- Write descriptive docstrings for all public functions and classes

Naming Conventions
~~~~~~~~~~~~~~~~~~

- **Classes**: PascalCase (e.g., ``ComputeResources``)
- **Functions/methods**: snake_case (e.g., ``create_compute_resources``)
- **Constants**: UPPER_SNAKE_CASE (e.g., ``DEFAULT_TIMEOUT``)
- **Factory functions**: May use PascalCase for API consistency (e.g., ``PCOCamLink``, ``Centroider``)

Documentation
~~~~~~~~~~~~~

- Use NumPy-style docstrings
- Include parameter types and return types
- Provide usage examples for complex functions
- Update documentation when changing APIs

Example docstring:

.. code-block:: python

   def create_compute_resources(cores, core_frequency, flops_per_cycle):
       """
       Create a ComputeResources object from hardware specifications.

       Parameters
       ----------
       cores : int
           Number of CPU cores
       core_frequency : float
           CPU frequency in Hz
       flops_per_cycle : float
           Floating point operations per cycle

       Returns
       -------
       ComputeResources
           Configured compute resource object

       Examples
       --------
       >>> cpu = create_compute_resources(16, 2.6e9, 32)
       >>> print(cpu.flops)
       1.3312e12
       """
       ...

Testing
~~~~~~~

- Write unit tests for new features
- Aim for >90% code coverage
- Use descriptive test names: ``test_<functionality>_<condition>``
- Group related tests in test classes

Example test:

.. code-block:: python

   class TestComputeResources:
       def test_create_compute_resources_calculation(self):
           """Test FLOPS calculation from CPU parameters."""
           cpu = create_compute_resources(
               cores=16,
               core_frequency=2.6e9,
               flops_per_cycle=32
           )
           expected_flops = 16 * 2.6e9 * 32
           assert cpu.flops == expected_flops

Documentation
-------------

Building Documentation
~~~~~~~~~~~~~~~~~~~~~~

The documentation uses Sphinx and can be built locally:

.. code-block:: bash

   cd docs
   make html
   open build/html/index.html

Documentation Style
~~~~~~~~~~~~~~~~~~~

- Write clear, concise explanations
- Include code examples
- Add diagrams where helpful (in ``docs/source/images/``)
- Update API documentation for new features
- Use reStructuredText format for consistency

Pull Request Guidelines
------------------------

Before Submitting
~~~~~~~~~~~~~~~~~

Checklist:

- ☐ All tests pass
- ☐ Code is formatted (Black, isort)
- ☐ No linting errors (Ruff)
- ☐ Documentation is updated
- ☐ Commit messages are clear and descriptive
- ☐ Pre-commit hooks have run successfully

PR Description Template
~~~~~~~~~~~~~~~~~~~~~~~

Include in your pull request:

1. **What**: Brief description of the changes
2. **Why**: Motivation for the changes
3. **How**: Technical approach (if complex)
4. **Testing**: How you tested the changes
5. **Related Issues**: Link to relevant issues (e.g., "Closes #123")

Example:

.. code-block:: text

   ## What
   Add support for AMD GPU hardware models

   ## Why
   Users requested the ability to model AMD GPUs in their pipelines

   ## How
   - Added AMD GPU specifications to hardware module
   - Extended ComputeResources to handle AMD-specific parameters
   - Updated documentation with examples

   ## Testing
   - Added unit tests for AMD GPU creation
   - Verified timing calculations match expected values
   - Ran full test suite (121 tests passing)

   ## Related Issues
   Closes #45

Review Process
~~~~~~~~~~~~~~

1. Automated checks (CI) must pass
2. At least one maintainer review required
3. Address review feedback promptly
4. Once approved, a maintainer will merge your PR

Reporting Issues
----------------

When reporting bugs or requesting features:

1. **Check existing issues first** to avoid duplicates
2. **Use issue templates** when available
3. **Provide detailed information:**

   - daolite version
   - Python version
   - Operating system
   - Steps to reproduce (for bugs)
   - Expected vs actual behavior
   - Code samples or error messages

Bug Report Template
~~~~~~~~~~~~~~~~~~~

.. code-block:: text

   **Description**
   Clear description of the bug

   **To Reproduce**
   Steps to reproduce the behavior:
   1. Install daolite version X.Y.Z
   2. Run this code: ...
   3. See error

   **Expected Behavior**
   What you expected to happen

   **Environment**
   - OS: [e.g., Ubuntu 22.04, macOS 13.0]
   - Python version: [e.g., 3.11.0]
   - daolite version: [e.g., 0.2.0]

   **Additional Context**
   Any other relevant information

Linting Configuration
---------------------

The project uses Ruff for linting with custom configuration in ``.ruff.toml``:

.. code-block:: toml

   line-length = 88
   target-version = "py38"

   [lint]
   select = ["E", "F", "W", "I", "N", "UP", "B", "C4", "NPY"]
   
   # Exemptions for scientific code conventions
   ignore = [
       "E501",   # Line too long (Black handles this)
       "E741",   # Ambiguous variable names (common in math)
       "N803",   # Argument name should be lowercase
       "N806",   # Variable in function should be lowercase
   ]

Code of Conduct
---------------

This project follows the `Contributor Covenant Code of Conduct <https://www.contributor-covenant.org/>`_. 

Key principles:

- Be respectful and constructive
- Welcome newcomers and help them learn
- Focus on what is best for the community
- Show empathy towards other community members

Getting Help
------------

If you need help or have questions:

- **Documentation**: Check the `online documentation <https://daolite.readthedocs.io>`_
- **GitHub Discussions**: Start a discussion for general questions
- **GitHub Issues**: Report bugs or request features
- **Pull Requests**: Ask questions in PR comments
- **Email**: Contact the maintainers directly

Release Process
---------------

For maintainers releasing new versions:

1. Update version in ``setup.py`` and ``daolite/__init__.py``
2. Update ``CHANGELOG.md`` with release notes
3. Create a git tag: ``git tag v0.2.0``
4. Push tag: ``git push origin v0.2.0``
5. GitHub Actions will automatically build and publish to PyPI

Thank you for contributing to daolite! 🎉

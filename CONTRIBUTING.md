# Contributing to daolite

Thank you for your interest in contributing to daolite!

## Quick Start for Contributors

1. Fork and clone the repository
2. Install in development mode: `pip install -e .`
3. **Install pre-commit hooks**: `pip install pre-commit && pre-commit install`
4. Make your changes and run tests: `pytest`
5. Commit (pre-commit hooks will run automatically)
6. Push and open a Pull Request

## Pre-commit Hooks Required

This project uses pre-commit hooks to maintain code quality. They will run automatically on `git commit`:

```bash
# Install hooks (required)
pre-commit install

# Run manually on all files
pre-commit run --all-files
```

## Full Contributing Guide

For detailed contributing guidelines, coding standards, testing requirements, and more, please see our comprehensive documentation:

**📖 [Full Contributing Guide](https://daolite.readthedocs.io/en/latest/contributing.html)**

Or read it locally:
- `docs/source/contributing.rst`
- Build docs: `cd docs && make html && open build/html/contributing.html`

## Quick Links

- [Installation Guide](https://daolite.readthedocs.io/en/latest/install.html)
- [Running Tests](https://daolite.readthedocs.io/en/latest/tests.html)
- [Code of Conduct](CODE_OF_CONDUCT.md)

## Questions?

- Open a [GitHub Discussion](https://github.com/davetbarr/daolite/discussions)
- Report bugs via [GitHub Issues](https://github.com/davetbarr/daolite/issues)


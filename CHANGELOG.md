# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.1] - 2025-10-13

### Fixed
- **Hardware YAML files now included in package**: Fixed missing hardware configuration files (29 YAML files) that were not being installed, which caused GUI tools to fail with import errors
- **Circular import in GUI**: Fixed circular dependency between `menu.py` and `centroid_agenda_tool.py` by lazy-loading the import
- **Custom latency measurement**: Added `latency_start` and `latency_end` optional parameters to `pipeline.visualize()` to allow measuring latency between specific pipeline components

### Changed
- Updated `pyproject.toml` to include `compute/hardware/*.yaml` in package data
- Modified `visualize()` method in `Pipeline` class to accept custom latency measurement points
- Updated `generate_chrono_plot_packetize()` to support custom start/end indices for latency calculation

## [0.1.0] - 2025-10-12

### Added
- Initial release of daolite
- Core pipeline framework for AO latency estimation
- Support for camera, calibration, centroiding, reconstruction, and control components
- Hardware configurations for 29 different CPUs and GPUs
- GUI tools: Pipeline Designer and Centroid Agenda Tool
- JSON-based pipeline runner
- Comprehensive documentation with Sphinx
- Zenodo DOI integration (10.5281/zenodo.17342890)

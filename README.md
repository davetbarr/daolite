# daolite

<p align="center">
    <img src="docs/source/_static/images/daoliteLogoCrop.png" alt="daolite Logo" width="400"/>
</p>

<p align="center">
    <strong>D</strong>urham <strong>A</strong>daptive <strong>O</strong>ptics <strong>L</strong>atency <strong>I</strong>nspection and <strong>T</strong>iming <strong>E</strong>stimator
</p>

<p align="center">
    <a href="https://doi.org/10.5281/zenodo.17342890"><img src="https://zenodo.org/badge/DOI/10.5281/zenodo.17342890.svg" alt="DOI"></a>
    <a href="https://daolite.readthedocs.io/en/latest/?badge=latest"><img src="https://readthedocs.org/projects/daolite/badge/?version=latest" alt="Documentation Status"></a>
    <a href="https://pypi.org/project/daolite/"><img src="https://img.shields.io/pypi/v/daolite.svg" alt="PyPI version"></a>
    <a href="https://www.python.org/"><img src="https://img.shields.io/badge/python-3.8%2B-blue.svg" alt="Python 3.8+"></a>
    <a href="LICENSE"><img src="https://img.shields.io/badge/License-GPLv3-blue.svg" alt="License: GPL v3"></a>
</p>

A Python package for estimating latency in Adaptive Optics Real-time Control Systems, with a focus on Durham Adaptive Optics (DAO) RTC systems.

## Overview

daolite provides tools to estimate the computational latency of various components in an adaptive optics (AO) real-time control system. This helps in system design and benchmarking by modeling:

- Camera readout and data transfer timing
- Pixel calibration processing
- Wavefront sensing (centroiding)
- Wavefront reconstruction
- Deformable mirror control
- Network and PCIe transfer timing

## Installation

Install from PyPI:

```bash
pip install daolite
```

Or for development:

```bash
git clone https://github.com/davetbarr/daolite.git
cd daolite
pip install -e .
```

## Documentation

Full documentation is available at **[daolite.readthedocs.io](https://daolite.readthedocs.io/)**

- [Quick Start Guide](https://daolite.readthedocs.io/en/latest/quick_start.html)
- [API Reference](https://daolite.readthedocs.io/en/latest/api/pipeline_api.html)
- [Examples](https://daolite.readthedocs.io/en/latest/examples.html)
- [Component Documentation](https://daolite.readthedocs.io/en/latest/pipeline.html)

## Development Setup

### Pre-commit Hooks

This project uses pre-commit hooks to ensure code quality. The hooks will automatically run linting (Ruff), code formatting (Black), and import sorting (isort) before each commit.

**Install pre-commit hooks:**

```bash
# Install pre-commit (if not already installed)
pip install pre-commit

# Install the git hooks
pre-commit install
```

**Run pre-commit manually on all files:**

```bash
# Run all hooks on all files
pre-commit run --all-files

# Or just run Ruff linter
ruff check --fix .

# Format code with Black
black .
```

The pre-commit hooks will automatically run on `git commit`. If any issues are found, the commit will be blocked until you fix them or the auto-fixes are applied.

## Running Tests

daolite includes a comprehensive test suite to ensure all components work correctly:

```bash
# Run all tests
pytest

# Run tests for specific components
pytest tests/test_camera.py
pytest tests/test_centroider.py

# Run tests with coverage report
pytest --cov=daolite
```

## Building Documentation

The documentation is built using Sphinx:

```bash
# Navigate to the documentation directory
cd doc

# Build HTML documentation
make html

# Build PDF documentation (requires LaTeX)
make latexpdf

# Open the HTML documentation
open build/html/index.html
```

## Package Structure

daolite is organized into several subpackages:

- `compute`: Hardware specification and computational resource modeling
  - `resources`: Library of predefined compute resources (CPUs and GPUs)
- `pipeline`: Flexible processing pipeline components for AO systems
  - `centroider`: Wavefront sensing algorithms
  - `reconstruction`: Wavefront reconstruction methods
  - `control`: Deformable mirror control algorithms
  - `calibration`: Pixel calibration operations
- `simulation`: Camera and hardware simulation tools
- `utils`: Utility functions for timing analysis and visualization

## Quick Start

Here's a simple example to estimate the latency of an AO system using the new flexible pipeline:

```python
import numpy as np
from daolite import Pipeline, PipelineComponent, ComponentType
from daolite.compute import hardware
from daolite.simulation.camera import PCOCamLink
from daolite.pipeline.calibration import PixelCalibration
from daolite.pipeline.centroider import Centroider
from daolite.pipeline.reconstruction import Reconstruction
from daolite.pipeline.control import FullFrameControl

# Create a pipeline
pipeline = Pipeline()

# Define AO system parameters
n_pixels = 1024 * 1024  # 1MP camera
n_subaps = 80 * 80      # 80x80 subaperture grid
n_valid_subaps = int(n_subaps * 0.8)  # Valid subapertures (80% of grid)
n_actuators = 5000      # Number of DM actuators
n_groups = 50           # Number of processing groups

# Create agendas for the new agenda-based API
pixel_agenda = np.ones(n_groups, dtype=int) * (n_pixels // n_groups)
centroid_agenda = np.ones(n_groups, dtype=int) * (n_valid_subaps // n_groups)

# Add components to the pipeline in any order with different compute resources
# The pipeline will automatically handle dependencies

# Camera readout on a CPU
pipeline.add_component(PipelineComponent(
    component_type=ComponentType.CAMERA,
    name="Camera",
    compute=hardware.amd_epyc_7763(),  # CPU resource
    function=PCOCamLink,
    params={
        "n_pixels": n_pixels,
        "group": n_groups
    }
))

# Pixel calibration
pipeline.add_component(PipelineComponent(
    component_type=ComponentType.CALIBRATION,
    name="Calibration",
    compute=hardware.amd_epyc_7763(),
    function=PixelCalibration,
    params={
        "pixel_agenda": pixel_agenda
    },
    dependencies=["Camera"]
))

# Centroiding on a GPU
pipeline.add_component(PipelineComponent(
    component_type=ComponentType.CENTROIDER,
    name="Centroider",
    compute=hardware.nvidia_rtx_4090(),  # GPU resource
    function=Centroider,
    params={
        "n_pix_per_subap": 16 * 16,
        "centroid_agenda": centroid_agenda
    },
    dependencies=["Calibration"]  # Depends on calibration
))

# Reconstruction on the same GPU
pipeline.add_component(PipelineComponent(
    component_type=ComponentType.RECONSTRUCTION,
    name="Reconstructor",
    compute=hardware.nvidia_rtx_4090(),  # Same GPU resource
    function=Reconstruction,
    params={
        "centroid_agenda": centroid_agenda,
        "n_acts": n_actuators
    },
    dependencies=["Centroider"]  # Depends on centroider output
))

# Control on a CPU
pipeline.add_component(PipelineComponent(
    component_type=ComponentType.CONTROL,
    name="DM Controller",
    compute=hardware.amd_epyc_7763(),  # CPU resource
    function=FullFrameControl,
    params={
        "n_acts": n_actuators
    },
    dependencies=["Reconstructor"]  # Depends on reconstruction output
))

# Run the pipeline
timing_results = pipeline.run(debug=True)

# Visualize the pipeline timing
pipeline.visualize(
    title="AO Pipeline Timing", 
    save_path="ao_pipeline_timing.png"
)
```

## Compute Resources Library

daolite includes a comprehensive library of predefined compute resources for modern CPUs and GPUs:

```python
from daolite.compute import hardware, create_compute_resources

# Use pre-defined resources
cpu_resource = hardware.amd_epyc_7763()
gpu_resource = hardware.nvidia_rtx_4090()

# Or create custom resources
custom_resource = create_compute_resources(
    cores=32,
    core_frequency=3.0e9,
    flops_per_cycle=32,
    memory_channels=4,
    memory_width=64,
    memory_frequency=3200e6,
    network_speed=100e9,
    time_in_driver=5
)
```

## Configuration System

daolite includes a configuration system to easily define and modify AO system parameters:

```python
from daolite import (
    CameraConfig, OpticsConfig, PipelineConfig, SystemConfig
)

# Create using individual components
camera = CameraConfig(
    n_pixels=1024 * 1024,
    n_subapertures=80 * 80,
    pixels_per_subaperture=16 * 16
)
optics = OpticsConfig(n_actuators=5000)
pipeline = PipelineConfig(use_square_diff=True)

# Create a complete system configuration
config = SystemConfig(camera, optics, pipeline)

# Save configuration to YAML
config.to_yaml('my_ao_config.yaml')

# Load configuration from YAML
loaded_config = SystemConfig.from_yaml('my_ao_config.yaml')
```

## Flexible Pipeline Architecture

The new pipeline architecture in daolite allows for:

1. **Component Arrangement**: Define components in any order with automatic dependency resolution
2. **Different Compute Resources**: Assign different hardware to each component
3. **Mixed Hardware**: Combine CPUs and GPUs in the same pipeline
4. **Automatic Timing**: Track data flow between components for accurate latency modeling

## Examples

See the `examples` directory for complete examples:

- `ao_pipeline.py`: Complete AO pipeline simulation with visualization
- `ao_config.yaml`: Example configuration file

To run the example pipeline:

```bash
python examples/ao_pipeline.py
```

Or with a custom configuration:

```bash
python examples/ao_pipeline.py examples/ao_config.yaml
```

## Features

- **Hardware Modeling**: Model different computational resources including CPU cores, memory bandwidth, and network capabilities
- **Compute Resources Library**: Predefined configurations for modern CPUs and GPUs
- **Flexible Pipeline Architecture**: Arrange components in any order on different compute resources
- **Pipeline Components**: 
  - Camera readout and data transfer simulation
  - Pixel calibration timing estimation  
  - Centroid computation modeling with cross-correlation and square difference methods
  - Wavefront reconstruction timing for different approaches
  - DM control timing including integration, offset, saturation handling
- **Network Analysis**: Model network and PCIe transfer times including driver overhead and switch delays
- **Visualization**: Generate chronological plots of pipeline timing data
- **Configuration System**: Easy specification of AO system parameters via YAML files

## Contributing

Contributions are welcome! Please read our [Contributing Guidelines](CONTRIBUTING.md) before submitting pull requests.

### Quick Development Setup

1. Fork and clone the repository
2. Install in development mode: `pip install -e .`
3. Install pre-commit hooks: `pip install pre-commit && pre-commit install`
4. Make your changes and ensure tests pass: `pytest`
5. Pre-commit hooks will run automatically on commit

For detailed guidelines, see [CONTRIBUTING.md](CONTRIBUTING.md).

## Citation

If you use daolite in your research, please cite:

**BibTeX:**
```bibtex
@software{david_2025_17342890,
  author       = {David, Barr},
  title        = {davetbarr/daolite: v0.1.0 - First Public Alpha},
  month        = oct,
  year         = 2025,
  publisher    = {Zenodo},
  version      = {v0.1.0},
  doi          = {10.5281/zenodo.17342890},
  url          = {https://doi.org/10.5281/zenodo.17342890},
}
```

**APA:**
> David, B. (2025). davetbarr/daolite: v0.1.0 - First Public Alpha (v0.1.0). Zenodo. https://doi.org/10.5281/zenodo.17342890

## Links

- **Documentation**: https://daolite.readthedocs.io/
- **PyPI Package**: https://pypi.org/project/daolite/
- **GitHub Repository**: https://github.com/davetbarr/daolite
- **Issue Tracker**: https://github.com/davetbarr/daolite/issues
- **Zenodo Archive**: https://doi.org/10.5281/zenodo.17342890
- **Durham AO**: https://github.com/Durham-Adaptive-Optics

## License

This project is licensed under the GNU General Public License v3.0 - see LICENSE file for details.

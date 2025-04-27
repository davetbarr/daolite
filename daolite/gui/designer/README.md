# daolite Pipeline Designer

A visual tool for designing AO pipeline configurations with emphasis on network and multi-compute node configurations.

## Overview

The daolite Pipeline Designer provides a graphical interface for designing adaptive optics pipelines using a drag-and-drop interface. It allows you to:

1. Visually place AO components (camera, centroider, reconstruction, etc.)
2. Connect components to show data flow between them
3. Configure compute resources for each component (CPUs, GPUs, etc.)
4. Set component-specific parameters
5. Generate runnable Python code for your pipeline design

The designer especially emphasizes network components and multi-compute node configurations, helping you visualize and optimize pipeline performance across distributed systems.

## Getting Started

### Requirements

- Python 3.7+
- PyQt5 (install with `pip install PyQt5`)
- daolite package

### Running the Designer

Simply run the `pipeline_designer.py` script from the root of the daolite package:

```bash
python pipeline_designer.py
```

## Using the Pipeline Designer

### Adding Components

Use the toolbar buttons on the left to add components to your pipeline:

- **Camera**: Add a camera readout component
- **Network**: Add a network transfer component (for multi-node configurations)
- **Calibration**: Add a pixel calibration component
- **Centroider**: Add a centroider for wavefront sensing
- **Reconstruction**: Add a wavefront reconstruction component
- **Control**: Add a DM control component

### Connecting Components

To connect components and show data flow:

1. Click on an output port (green circle) of a component
2. Drag to an input port (blue circle) of another component
3. Release to create the connection

Connections automatically establish dependencies between components.

### Configuring Components

To configure a component:

1. Select the component by clicking on it
2. Click "Set Compute" to assign a compute resource (CPU or GPU)
3. Click "Set Parameters" to configure component-specific parameters

You can also right-click on components for additional options.

### Generating Code

Once your pipeline is designed:

1. Click File → Generate Code
2. Choose a location to save the Python file
3. The generated code will create a daolite pipeline that matches your design

## Network and Multi-Compute Emphasis

This designer is particularly useful for visualizing and optimizing pipelines that span multiple compute nodes. Use the Network components to represent data transfers between different compute resources.

## Tips for Optimal Performance

- Place computationally intensive components (centroider, reconstruction) on GPUs
- Minimize network transfers between components
- Group related components on the same compute node when possible
- Consider the impact of data transfer times between components
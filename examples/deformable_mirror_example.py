"""
Example showing how to use DeformableMirror components in a DaoLite pipeline.

This example creates a simple pipeline with a camera, a reconstruction step,
and different types of deformable mirror components to demonstrate how
pipeline termination works with DM devices.
"""

import numpy as np
from daolite import Pipeline, PipelineComponent, ComponentType
from daolite.compute import create_compute_resources
from daolite.simulation.camera import PCOCamLink
from daolite.simulation.deformable_mirror import StandardDM, DMController, WavefrontCorrector
from daolite.pipeline.reconstruction import Reconstruction
from daolite.utils.network import network_transfer

# Create compute resources for our pipeline components
compute_resources = create_compute_resources(
    cores=16,
    core_frequency=3.0e9,
    flops_per_cycle=32,
    memory_frequency=3200e6,
    memory_width=64,
    memory_channels=8,
    network_speed=40e9,
    time_in_driver=5,
)

# Create DM resources with different characteristics
dm_resources = create_compute_resources(
    cores=4,
    core_frequency=1.5e9,
    flops_per_cycle=16,
    memory_frequency=2400e6,
    memory_width=64,
    memory_channels=4,
    network_speed=10e9,  # Lower network speed for the DM
    time_in_driver=10,   # Higher driver overhead for external device
)


def run_standard_dm_example():
    """Run a pipeline with a standard deformable mirror component."""
    print("\n===== Standard DM Example =====")
    pipeline = Pipeline()

    # Add a camera component
    pipeline.add_component(
        PipelineComponent(
            component_type=ComponentType.CAMERA,
            name="Camera",
            compute=compute_resources,
            function=PCOCamLink,
            params={"n_pixels": 1024 * 1024, "group": 10},
        )
    )

    # Add a reconstruction component that depends on the camera
    pipeline.add_component(
        PipelineComponent(
            component_type=ComponentType.RECONSTRUCTION,
            name="Reconstruction",
            compute=compute_resources,
            function=Reconstruction,
            params={"n_slopes": 6400, "n_acts": 5000, "group": 10},
            dependencies=["Camera"],
        )
    )

    # Add a network transfer component to represent data being sent to the external DM
    pipeline.add_component(
        PipelineComponent(
            component_type=ComponentType.NETWORK,
            name="Network_Transfer",
            compute=compute_resources,
            function=network_transfer,
            params={"n_bits": 5000 * 32, "group": 10},  # 5000 32-bit actuators
            dependencies=["Reconstruction"],
        )
    )

    # Add a standard DM component that terminates the pipeline
    pipeline.add_component(
        PipelineComponent(
            component_type=ComponentType.DM,
            name="StandardDM",
            compute=dm_resources,
            function=StandardDM,
            params={"processing_delay": 50.0},  # 50 μs processing delay
            dependencies=["Network_Transfer"],
        )
    )

    # Run the pipeline
    results = pipeline.run(debug=True)

    # Visualize the pipeline
    fig, ax, latency = pipeline.visualize(
        title="Standard DM Example",
        xlabel="Time (μs)",
    )

    print(f"Total pipeline latency: {latency:.2f} μs")


def run_dm_controller_example():
    """Run a pipeline with a DMController component."""
    print("\n===== DM Controller Example =====")
    pipeline = Pipeline()

    # Add a camera component
    pipeline.add_component(
        PipelineComponent(
            component_type=ComponentType.CAMERA,
            name="Camera",
            compute=compute_resources,
            function=PCOCamLink,
            params={"n_pixels": 1024 * 1024, "group": 10},
        )
    )

    # Add a reconstruction component that depends on the camera
    pipeline.add_component(
        PipelineComponent(
            component_type=ComponentType.RECONSTRUCTION,
            name="Reconstruction",
            compute=compute_resources,
            function=Reconstruction,
            params={"n_slopes": 6400, "n_acts": 5000, "group": 10},
            dependencies=["Camera"],
        )
    )

    # Add a network transfer component to represent data being sent to the DM controller
    pipeline.add_component(
        PipelineComponent(
            component_type=ComponentType.NETWORK,
            name="Network_Transfer",
            compute=compute_resources,
            function=network_transfer,
            params={"n_bits": 5000 * 32, "group": 10},  # 5000 32-bit actuators
            dependencies=["Reconstruction"],
        )
    )

    # Add a DMController component that terminates the pipeline
    pipeline.add_component(
        PipelineComponent(
            component_type=ComponentType.DM,
            name="DMController",
            compute=dm_resources,
            function=DMController,
            params={
                "n_actuators": 5000,  # 5000 actuators (ELT-scale)
                "actuator_latency": 10.0,  # 10 μs per actuator group
                "settling_time": 100.0,  # 100 μs settling time
            },
            dependencies=["Network_Transfer"],
        )
    )

    # Run the pipeline
    results = pipeline.run(debug=True)

    # Visualize the pipeline
    fig, ax, latency = pipeline.visualize(
        title="DM Controller Example",
        xlabel="Time (μs)",
    )

    print(f"Total pipeline latency: {latency:.2f} μs")


def run_wavefront_corrector_example():
    """Run a pipeline with a wavefront corrector component."""
    print("\n===== Wavefront Corrector Example =====")
    pipeline = Pipeline()

    # Add a camera component
    pipeline.add_component(
        PipelineComponent(
            component_type=ComponentType.CAMERA,
            name="Camera",
            compute=compute_resources,
            function=PCOCamLink,
            params={"n_pixels": 1024 * 1024, "group": 10},
        )
    )

    # Add a reconstruction component that depends on the camera
    pipeline.add_component(
        PipelineComponent(
            component_type=ComponentType.RECONSTRUCTION,
            name="Reconstruction",
            compute=compute_resources,
            function=Reconstruction,
            params={"n_slopes": 6400, "n_acts": 5000, "group": 10},
            dependencies=["Camera"],
        )
    )

    # Add a network transfer component to represent data being sent to the wavefront corrector
    pipeline.add_component(
        PipelineComponent(
            component_type=ComponentType.NETWORK,
            name="Network_Transfer",
            compute=compute_resources,
            function=network_transfer,
            params={"n_bits": 5000 * 32, "group": 10},  # 5000 32-bit actuators
            dependencies=["Reconstruction"],
        )
    )

    # Add a wavefront corrector component that terminates the pipeline
    pipeline.add_component(
        PipelineComponent(
            component_type=ComponentType.DM,
            name="WavefrontCorrector",
            compute=dm_resources,
            function=WavefrontCorrector,
            params={
                "data_size": 5000 * 4,  # 5000 actuators * 4 bytes per actuator
                "buffer_size": 4096,  # 4KB buffer
            },
            dependencies=["Network_Transfer"],
        )
    )

    # Run the pipeline
    results = pipeline.run(debug=True)

    # Visualize the pipeline
    fig, ax, latency = pipeline.visualize(
        title="Wavefront Corrector Example",
        xlabel="Time (μs)",
    )

    print(f"Total pipeline latency: {latency:.2f} μs")


if __name__ == "__main__":
    run_standard_dm_example()
    run_dm_controller_example()
    run_wavefront_corrector_example()
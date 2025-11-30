"""
Example script demonstrating the daolite pipeline for latency estimation.

This script shows how to use daolite to model a complete AO pipeline,
from camera readout to deformable mirror control, with timing visualization.
"""

import matplotlib.pyplot as plt
import numpy as np

from daolite.compute import create_compute_resources
from daolite.config import CameraConfig, OpticsConfig, PipelineConfig, SystemConfig
from daolite.pipeline.calibration import PixelCalibration
from daolite.pipeline.centroider import Centroider
from daolite.pipeline.control import FullFrameControl
from daolite.pipeline.reconstruction import Reconstruction
from daolite.simulation.camera import PCOCamLink, simulate_pco_readout
from daolite.utils.chronograph import generate_chrono_plot_packetize
from daolite.utils.network import TimeOnNetwork
from daolite.utils.sh_utility import (
    calculate_centroid_agenda,
    genSHSubApMap,
    getSubApCentrePoints,
    readout_by_pixel_agenda,
)


def run_single_pipeline(config_file=None):
    """
    Run a single AO pipeline simulation with timing analysis.

    Args:
        config_file: Path to configuration YAML file (optional)
    """
    if config_file:
        # Load configuration from file
        config = SystemConfig.from_yaml(config_file)
    else:
        # Create default configuration
        camera = CameraConfig(
            n_pixels=1024 * 1024,  # 1MP camera
            n_subapertures=50 * 50,  # 50x50 subaperture grid
            pixels_per_subaperture=10 * 10,  # 12x12 pixels per subaperture
        )

        optics = OpticsConfig(
            n_actuators=5000,  # 500 actuator DM
            n_combine=1,
            calibration_scale=1.0,
            centroid_scale=1.0,
            reconstruction_scale=1.0,
            control_scale=1.0,
        )

        pipeline = PipelineConfig(use_square_diff=False, use_sorting=False, n_workers=4)

        compute = create_compute_resources(
            cores=16,
            core_frequency=2.6e9,
            flops_per_cycle=32,
            memory_channels=4,
            memory_width=64,
            memory_frequency=3200e6,
            network_speed=100e9,
            time_in_driver=5,
        )

        config = SystemConfig(camera, optics, pipeline, compute)

    # Print configuration summary
    print("\n===== AO System Configuration =====")
    print(
        f"Camera: {config.camera.n_subapertures} subapertures, "
        f"{config.camera.pixels_per_subaperture} pixels per subaperture"
    )
    print(f"DM: {config.optics.n_actuators} actuators")
    print(f"Compute: {config.compute.flops} TFLOPS")
    print(f"Compute: {config.compute.get_memory_bandwidth} GB/s")
    print(f"Network: {config.compute.network_speed/1e9} Gbps")
    print("===================================\n")

    # Calculate total number of valid subapertures
    # In a real system, not all subapertures would be valid due to telescope pupil shape
    # n_valid_subaps = int(config.camera.n_subapertures * 0.8)  # Assume 80% are valid
    pixel_agenda_1d = np.array(
        [1024 * 1024 // 50 + (1 if i < 1024 * 1024 % 50 else 0) for i in range(50)],
        dtype=int,
    )
    # Convert to 2D format for compatibility with readout_by_pixel_agenda
    pixel_agenda = np.column_stack((np.arange(50), pixel_agenda_1d))
    # Calculate group size based on packetization
    n_groups = 50  # Default packet count

    subApMap = genSHSubApMap(50, 50, 2, 50 // 2, mask=False)

    nSlopes = np.sum(subApMap > 0) * 2  # *2 for x and y slopes
    print(f"Number of slopes: {nSlopes}")
    readout_pattern = simulate_pco_readout(1024, 1024)
    packet_map = readout_by_pixel_agenda(readout_pattern, pixel_agenda)
    centres = getSubApCentrePoints(subApMap, 10, 1024, 1024, 0)
    # Calculate when each centroid becomes available
    centroid_agenda = calculate_centroid_agenda(packet_map, centres, 10)

    print(f"Using {50} valid subapertures for centroiding.")
    print(f"Centroid agenda (subaps per group): {centroid_agenda}")
    print(f"Pixel agenda (pixels per group): {pixel_agenda}\n")

    # ======= Pipeline Timing Simulation =======

    # 1. Camera readout and data transfer
    camera_timing = PCOCamLink(
        compute_resources=config.compute,
        n_pixels=config.camera.n_pixels,
        group=n_groups,
        readout=config.camera.readout_time,
        debug=True,
    )

    # 2. Pixel calibration
    calibration_timing = PixelCalibration(
        compute_resources=config.compute,
        start_times=camera_timing,
        pixel_agenda=pixel_agenda[:, 1],
        flop_scale=0.5,
        mem_scale=0.5,
        debug=True,
    )

    # 3. Centroiding
    centroid_timing = Centroider(
        compute_resources=config.compute,
        start_times=calibration_timing,
        centroid_agenda=centroid_agenda,
        n_pix_per_subap=10,
        flop_scale=0.125,
        mem_scale=0.125,
        sort=True,
        debug=True,
    )

    # 4. Wavefront reconstruction
    reconstruction_timing = Reconstruction(
        compute_resources=config.compute,
        start_times=centroid_timing,
        centroid_agenda=centroid_agenda,
        n_acts=config.optics.n_actuators,
        flop_scale=0.125,
        mem_scale=0.125,
        debug=True,
    )

    # 5. Network transfer to DM controller
    # Assume 32 bits per actuator
    network_time = TimeOnNetwork(
        n_bits=config.optics.n_actuators * 32,
        compute_resources=config.compute,
        debug=True,
    )

    network_timing = np.zeros([1, 2])
    network_timing[0, 0] = reconstruction_timing[-1, 1]
    network_timing[0, 1] = network_timing[0, 0] + network_time

    # 6. DM control
    control_time = FullFrameControl(
        n_acts=config.optics.n_actuators,
        compute_resources=config.compute,
        scale=config.optics.control_scale,
        combine=config.optics.n_combine,
        debug=True,
    )

    control_timing = np.zeros([1, 2])
    control_timing[0, 0] = reconstruction_timing[-1, 1]
    control_timing[0, 1] = control_timing[0, 0] + control_time

    # Create readout timing for visualization
    readout_timing = np.zeros([1, 2])
    readout_timing[0, 0] = 0
    readout_timing[0, 1] = config.camera.readout_time

    # ======= Visualize Results =======

    # Create dataset for chronograph
    data_set = [
        [readout_timing, "Camera Readout"],
        [camera_timing, "Pixel Transfer"],
        [calibration_timing, "Calibration"],
        [centroid_timing, "Centroiding"],
        [reconstruction_timing, "Reconstruction"],
        [control_timing, "DM Control"],
    ]

    # Create chronograph visualization
    fig, ax, latency = generate_chrono_plot_packetize(
        data_list=data_set,
        title="AO Pipeline Timing",
        xlabel="Time (μs)",
        multiplot=False,
    )

    # Calculate total latency from camera readout to DM control
    total_latency = control_timing[0, 1] - readout_timing[0, 0]

    print(f"\nTotal pipeline latency: {total_latency:.2f} μs")
    print(f"Frame rate potential: {1e6/total_latency:.2f} Hz")

    # Save and show plot
    plt.savefig("ao_pipeline_timing.png", dpi=300, bbox_inches="tight")
    plt.show()

    # Return results for analysis
    return {
        "config": config,
        "latency": total_latency,
        "frame_rate": 1e6 / total_latency,
        "pipeline_stages": {
            "camera": camera_timing[-1, 1] - camera_timing[0, 0],
            "calibration": calibration_timing[-1, 1] - calibration_timing[0, 0],
            "centroiding": centroid_timing[-1, 1] - centroid_timing[0, 0],
            "reconstruction": reconstruction_timing[-1, 1]
            - reconstruction_timing[0, 0],
            "network": network_timing[0, 1] - network_timing[0, 0],
            "control": control_timing[0, 1] - control_timing[0, 0],
        },
    }


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        # Run with specified config file
        results = run_single_pipeline(sys.argv[1])
    else:
        # Run with default config
        results = run_single_pipeline()

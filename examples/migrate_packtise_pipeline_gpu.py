"""
Migration example: Converting packtisePipelineGPU.py to DaoLITE

This example demonstrates how to migrate the Performance Estimation GPU-based
packtisePipelineGPU to the new DaoLITE framework.
"""

import numpy as np
import yaml
import sys
import re
import matplotlib.pyplot as plt

# DaoLITE imports - replaces the old imports
from daolite import Pipeline, PipelineComponent, ComponentType
from daolite.compute import create_compute_resources
from daolite.simulation.camera import PCOCamLink
from daolite.pipeline.calibration import PixelCalibration
from daolite.pipeline.centroider import Centroider
from daolite.pipeline.reconstruction import Reconstruction
from daolite.pipeline.control import FullFrameControl
from daolite.utils.network import TimeOnNetwork, PCIE
from daolite.utils.chronograph import generate_chrono_plot_packetize
from daolite.utils.sh_utility import genSHSubApMap


# Example 1: Direct migration using the old style API
# This shows how to use the same API style as Performance Estimation
def run_old_style_migration(config_file=None):
    """Run a GPU pipeline using the old style API but with DaoLITE classes"""
    if config_file is None:
        config_file = "examples/ao_config_gpu.yaml"

    # Load configuration
    with open(config_file) as stream:
        data = yaml.safe_load(stream)

    name = data["name"]["name"]
    nPixels = data["defines"]["nPixels"]
    readoutTime = data["defines"]["readoutTime"]
    nSubs = data["defines"]["nSubs"]
    nPixPerSub = data["defines"]["nPixPerSub"]
    nActs = data["defines"]["nActs"]
    bitDepth = data["defines"]["bitDepth"]
    nWorkers = data["defines"]["nWorkers"]
    nCombine = data["defines"]["nCombine"]

    # Handle optional parameters
    try:
        nLinesOfSight = data["defines"]["nLinesOfSight"]
    except KeyError:
        nLinesOfSight = 1
    try:
        square_diff = data["defines"]["square_diff"]
    except KeyError:
        square_diff = False
    try:
        sort = data["defines"]["sort"]
    except KeyError:
        sort = False

    # Generate subaperture map
    if nSubs <= 1:
        nValidSubAps = nSubs * nLinesOfSight
        centroid_agenda = np.zeros([50, 1])
        centroid_agenda[-1] = nValidSubAps
    else:
        subApMap = genSHSubApMap(nSubs, nSubs, 0.1 * nSubs, nSubs // 2, mask=True)
        nValidSubAps = int(np.sum(subApMap)) * nLinesOfSight
        centroid_agenda = np.sum(subApMap, axis=1) * nLinesOfSight

    # Print configuration details
    print(f"****************************************************************")
    print(f"Configuration: {config_file}")
    print(f"Name: {name}")
    print(f"nPix: {nPixels}")
    print(f"nSubs: {nSubs}")
    print(f"ReadoutTime: {readoutTime}")
    print(f"nPixPerSub: {nPixPerSub}")
    print(f"nActs: {nActs}")
    print(f"nValidSubAps: {nValidSubAps}")
    print(f"nWorkers: {nWorkers}")
    print(f"nLinesOfSight: {nLinesOfSight}")
    print(f"nCombine: {nCombine}")

    # Create GPU compute resources
    GPU = ComputeResources(
        hardware="GPU",
        memory_bandwidth=data["compRes"]["memBand"],
        flops=data["compRes"]["flops"],
        network_speed=data["compRes"]["networkSpeed"],
        time_in_driver=data["compRes"]["timeInDriver"],
    )

    # Create CPU compute resources for control
    comp = create_compute_resources(
        cores=data["compResControl"]["cores"],
        core_frequency=data["compResControl"]["core_frequnecy"],
        flops_per_cycle=data["compResControl"]["flops_per_cycle"],
        memory_channels=data["compResControl"]["memory_channels"],
        memory_width=data["compResControl"]["memory_width"],
        memory_frequency=data["compResControl"]["memory_frequnecy"],
        network_speed=data["compResControl"]["networkSpeed"],
        time_in_driver=data["compResControl"]["timeInDriver"],
    )

    # Get computation scales
    calScale = data["computationScale"]["Calibration"]
    centScale = data["computationScale"]["Centroid"]
    mvmScale = data["computationScale"]["MVM"]
    controlScale = data["computationScale"]["Control"]

    # Create pipeline steps - same API as old packtisePipelineGPU.py but using DaoLITE classes
    packetTrain = PCOCamLink(
        comp, nPixels, group=len(centroid_agenda), readout=readoutTime
    )

    # Transfer to GPU
    transTime = PCIE((nPixels * nPixels * bitDepth // nWorkers), comp, packetTrain)

    # GPU operations
    calTime = PixelCalibration(
        nPixels,
        GPU,
        transTime,
        group=len(centroid_agenda),
        scale=calScale,
        n_workers=nWorkers,
    )
    centTime = Centroider(
        nValidSubAps,
        nPixPerSub,
        GPU,
        calTime,
        group=len(centroid_agenda),
        n_workers=nWorkers,
        scale=centScale,
        square_diff=square_diff,
        agenda=centroid_agenda,
        sort=True,
    )
    mvmTime = Reconstruction(
        nValidSubAps * 2,
        nActs,
        GPU,
        start_times=centTime,
        n_workers=nWorkers,
        scale=mvmScale,
        agenda=centroid_agenda,
        group=len(centroid_agenda),
    )

    # Transfer back to CPU
    transTime2 = PCIE((nActs * 32), GPU, mvmTime)

    # CPU operations
    networkHop = TimeOnNetwork(nActs * 32, comp, debug=True)
    control = FullFrameControl(nActs, comp, scale=controlScale, combine=nCombine)

    # Network timing
    netTime = np.zeros([1, 2])
    netTime[0, 0] = transTime2[-1, 1]
    netTime[0, 1] = netTime[0, 0] + networkHop

    # Control timing
    controlTime = np.zeros([1, 2])
    controlTime[0, 0] = netTime[0, 1]
    controlTime[0, 1] = controlTime[0, 0] + control

    # Create readout timing array
    readout = np.zeros([1, 2])
    readout[0, 1] = readoutTime

    # Create dataset for visualization
    data_set = []
    data_set.append([readout, "readout"])
    data_set.append([packetTrain, "pixelTransfer"])
    data_set.append([transTime, "Transfer to GPU"])
    data_set.append([calTime, "Calibration"])
    data_set.append([centTime, "Centroiding"])
    data_set.append([mvmTime, "Reconstruction"])
    data_set.append([transTime2, "Transfer from GPU"])
    data_set.append([netTime, "Network"])
    data_set.append([controlTime, "Control"])

    # Generate chronograph
    fig, ax, latency = generate_chrono_plot_packetize(data_set, name, r"time ($\mu$s)")

    # Adjust figure size
    width = fig.get_figwidth()
    height = fig.get_figheight()
    fig.set_figwidth(width * 3)
    fig.set_figheight(height * 2)

    # Save figure
    plt.savefig(f"Images/{name}_migrated.png")
    print(f"Total latency: {latency} μs")

    # Save results to CSV
    with open("Results.csv", "a") as f:
        f.write(f"{name}, {latency}\n")

    return fig, latency


# Example 2: Modern DaoLITE approach using the Pipeline interface
def run_modern_pipeline(config_file=None):
    """Run a GPU pipeline using the new DaoLITE Pipeline interface"""
    if config_file is None:
        config_file = "examples/ao_config_gpu.yaml"

    # Load configuration
    with open(config_file) as stream:
        data = yaml.safe_load(stream)

    name = data["name"]["name"]
    nPixels = data["defines"]["nPixels"]
    readoutTime = data["defines"]["readoutTime"]
    nSubs = data["defines"]["nSubs"]
    nPixPerSub = data["defines"]["nPixPerSub"]
    nActs = data["defines"]["nActs"]
    bitDepth = data["defines"]["bitDepth"]
    nWorkers = data["defines"]["nWorkers"]
    nCombine = data["defines"]["nCombine"]

    # Handle optional parameters
    try:
        nLinesOfSight = data["defines"]["nLinesOfSight"]
    except KeyError:
        nLinesOfSight = 1
    try:
        square_diff = data["defines"]["square_diff"]
    except KeyError:
        square_diff = False
    try:
        sort = data["defines"]["sort"]
    except KeyError:
        sort = True  # Default to true for GPU sort

    # Generate subaperture map
    if nSubs <= 1:
        nValidSubAps = nSubs * nLinesOfSight
    else:
        subApMap = genSHSubApMap(nSubs, nSubs, 0.1 * nSubs, nSubs // 2, mask=True)
        nValidSubAps = int(np.sum(subApMap)) * nLinesOfSight

    # Create GPU compute resources
    gpu = ComputeResources(
        hardware="GPU",
        memory_bandwidth=data["compRes"]["memBand"],
        flops=data["compRes"]["flops"],
        network_speed=data["compRes"]["networkSpeed"],
        time_in_driver=data["compRes"]["timeInDriver"],
    )

    # Create CPU compute resources for control
    cpu = create_compute_resources(
        cores=data["compResControl"]["cores"],
        core_frequency=data["compResControl"]["core_frequnecy"],
        flops_per_cycle=data["compResControl"]["flops_per_cycle"],
        memory_channels=data["compResControl"]["memory_channels"],
        memory_width=data["compResControl"]["memory_width"],
        memory_frequency=data["compResControl"]["memory_frequnecy"],
        network_speed=data["compResControl"]["networkSpeed"],
        time_in_driver=data["compResControl"]["timeInDriver"],
    )

    # Get computation scales
    calScale = data["computationScale"]["Calibration"]
    centScale = data["computationScale"]["Centroid"]
    mvmScale = data["computationScale"]["MVM"]
    controlScale = data["computationScale"]["Control"]

    # Create a new Pipeline
    pipeline = Pipeline(name=name)

    # Group size for packetization
    n_groups = 50

    # Add Camera component (CPU)
    pipeline.add_component(
        PipelineComponent(
            component_type=ComponentType.CAMERA,
            name="Camera",
            compute=cpu,
            function=PCOCamLink,
            params={"n_pixels": nPixels, "group": n_groups, "readout": readoutTime},
        )
    )

    # Add PCIe Transfer component (CPU to GPU)
    pipeline.add_component(
        PipelineComponent(
            component_type=ComponentType.TRANSFER,
            name="PCIe Transfer to GPU",
            compute=cpu,
            function=PCIE,
            params={"n_bits": nPixels * nPixels * bitDepth // nWorkers},
            dependencies=["Camera"],
        )
    )

    # Add Calibration component (GPU)
    pipeline.add_component(
        PipelineComponent(
            component_type=ComponentType.CALIBRATION,
            name="Calibration",
            compute=gpu,
            function=PixelCalibration,
            params={
                "n_pixels": nPixels,
                "group": n_groups,
                "scale": calScale,
                "n_workers": nWorkers,
            },
            dependencies=["PCIe Transfer to GPU"],
        )
    )

    # Add Centroiding component (GPU)
    pipeline.add_component(
        PipelineComponent(
            component_type=ComponentType.CENTROIDER,
            name="Centroider",
            compute=gpu,
            function=Centroider,
            params={
                "n_valid_subaps": nValidSubAps,
                "n_pix_per_subap": nPixPerSub,
                "scale": centScale,
                "square_diff": square_diff,
                "sort": sort,
                "n_workers": nWorkers,
            },
            dependencies=["Calibration"],
        )
    )

    # Add Reconstruction component (GPU)
    pipeline.add_component(
        PipelineComponent(
            component_type=ComponentType.RECONSTRUCTION,
            name="Reconstructor",
            compute=gpu,
            function=Reconstruction,
            params={
                "n_slopes": nValidSubAps * 2,
                "n_acts": nActs,
                "scale": mvmScale,
                "n_workers": nWorkers,
            },
            dependencies=["Centroider"],
        )
    )

    # Add PCIe Transfer component (GPU to CPU)
    pipeline.add_component(
        PipelineComponent(
            component_type=ComponentType.TRANSFER,
            name="PCIe Transfer to CPU",
            compute=gpu,
            function=PCIE,
            params={"n_bits": nActs * 32},
            dependencies=["Reconstructor"],
        )
    )

    # Add Network Transfer component (CPU)
    pipeline.add_component(
        PipelineComponent(
            component_type=ComponentType.NETWORK,
            name="Network",
            compute=cpu,
            function=TimeOnNetwork,
            params={"n_bits": nActs * 32, "debug": True},
            dependencies=["PCIe Transfer to CPU"],
        )
    )

    # Add Control component (CPU)
    pipeline.add_component(
        PipelineComponent(
            component_type=ComponentType.CONTROL,
            name="Control",
            compute=cpu,
            function=FullFrameControl,
            params={"n_acts": nActs, "scale": controlScale, "combine": nCombine},
            dependencies=["Network"],
        )
    )

    # Run the pipeline simulation
    results = pipeline.run(debug=True)

    # Visualize the pipeline
    fig = pipeline.visualize(
        title=name,
        xlabel=r"time ($\mu$s)",
        save_path=f"Images/{name}_modern.png",
        figsize=(24, 16),  # Larger figure size for complex pipelines
    )

    # Print summary
    pipeline.print_summary()

    # Save results to CSV
    with open("Results.csv", "a") as f:
        f.write(f"{name}_modern, {pipeline.get_total_latency()}\n")

    return pipeline


if __name__ == "__main__":
    # Run either example based on command line arguments
    if len(sys.argv) > 2:
        config_file = sys.argv[2]
        if sys.argv[1] == "old":
            run_old_style_migration(config_file)
        elif sys.argv[1] == "new":
            run_modern_pipeline(config_file)
        else:
            print(
                "Usage: python migrate_packtise_pipeline_gpu.py [old|new] [config_file]"
            )
    elif len(sys.argv) > 1:
        if sys.argv[1] == "old":
            run_old_style_migration()
        elif sys.argv[1] == "new":
            run_modern_pipeline()
        else:
            config_file = sys.argv[1]
            # Run both examples
            print("Running old style migration...")
            run_old_style_migration(config_file)
            print("\nRunning modern pipeline approach...")
            run_modern_pipeline(config_file)
    else:
        # Run both examples with default configuration
        print("Running old style migration...")
        run_old_style_migration()
        print("\nRunning modern pipeline approach...")
        run_modern_pipeline()

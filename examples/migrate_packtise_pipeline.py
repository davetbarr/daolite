"""
Migration example: Converting packtisePipeline.py to DaoLITE

This example demonstrates how to migrate the Performance Estimation CPU-based
packtisePipeline to the new DaoLITE framework.
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
from daolite.utils.network import TimeOnNetwork
from daolite.utils.chronograph import generate_chrono_plot_packetize
from daolite.utils.sh_utility import genSHSubApMap


# Example 1: Direct migration using the old style API
# This shows how to use the same API style as Performance Estimation
def run_old_style_migration(config_file=None):
    """Run a pipeline using the old style API but with DaoLITE classes"""
    if config_file is None:
        config_file = "examples/ao_config.yaml"

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
        centroid_agenda = np.sum(subApMap, axis=1)

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
    print(f"nLinesOfSight: {nLinesOfSight}")
    print(f"nCombine: {nCombine}")

    # Create compute resources
    comp = create_compute_resources(
        cores=data["compRes"]["cores"],
        core_frequency=data["compRes"]["core_frequnecy"],
        flops_per_cycle=data["compRes"]["flops_per_cycle"],
        memory_channels=data["compRes"]["memory_channels"],
        memory_width=data["compRes"]["memory_width"],
        memory_frequency=data["compRes"]["memory_frequnecy"],
        network_speed=data["compRes"]["networkSpeed"],
        time_in_driver=data["compRes"]["timeInDriver"],
    )

    # Get computation scales
    calScale = data["computationScale"]["Calibration"]
    centScale = data["computationScale"]["Centroid"]
    mvmScale = data["computationScale"]["MVM"]
    controlScale = data["computationScale"]["Control"]

    # Create pipeline steps - same API as old packtisePipeline.py but using DaoLITE classes
    packetTrain = PCOCamLink(
        comp, nPixels, group=len(centroid_agenda), readout=readoutTime
    )
    calTime = PixelCalibration(
        nPixels, comp, packetTrain, group=len(centroid_agenda), scale=calScale
    )
    centTime = Centroider(
        nValidSubAps,
        nPixPerSub,
        comp,
        calTime,
        scale=centScale,
        delayStart=0,
        square_diff=square_diff,
        agenda=centroid_agenda,
        sort=sort,
    )
    mvmTime = Reconstruction(
        nValidSubAps * 2,
        nActs,
        comp,
        start_times=centTime,
        scale=mvmScale,
        agenda=centroid_agenda,
    )
    networkHop = TimeOnNetwork(nActs * 32, comp)
    control = FullFrameControl(nActs, comp, scale=controlScale, combine=nCombine)

    # Create timing arrays for network and control
    netTime = np.zeros([1, 2])
    netTime[0, 0] = mvmTime[-1, 1]
    netTime[0, 1] = netTime[0, 0] + networkHop

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
    data_set.append([calTime, "Calibration"])
    data_set.append([centTime, "Centroiding"])
    data_set.append([mvmTime, "Reconstruction"])
    data_set.append([netTime, "Network"])
    data_set.append([controlTime, "Control"])

    # Generate chronograph
    fig, ax, latency = generate_chrono_plot_packetize(
        data_set, name, r"time ($\mu$s)", multiplot=False
    )

    # Save figure
    plt.savefig(f"Images/{name}_migrated.png")
    print(f"Total latency: {latency} μs")

    return fig, latency


# Example 2: Modern DaoLITE approach using the Pipeline interface
def run_modern_pipeline(config_file=None):
    """Run a pipeline using the new DaoLITE Pipeline interface"""
    if config_file is None:
        config_file = "examples/ao_config.yaml"

    # Load configuration
    with open(config_file) as stream:
        data = yaml.safe_load(stream)

    name = data["name"]["name"]
    nPixels = data["defines"]["nPixels"]
    readoutTime = data["defines"]["readoutTime"]
    nSubs = data["defines"]["nSubs"]
    nPixPerSub = data["defines"]["nPixPerSub"]
    nActs = data["defines"]["nActs"]
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
    else:
        subApMap = genSHSubApMap(nSubs, nSubs, 0.1 * nSubs, nSubs // 2, mask=True)
        nValidSubAps = int(np.sum(subApMap)) * nLinesOfSight

    # Get computation scales
    calScale = data["computationScale"]["Calibration"]
    centScale = data["computationScale"]["Centroid"]
    mvmScale = data["computationScale"]["MVM"]
    controlScale = data["computationScale"]["Control"]

    # Create compute resources
    comp = create_compute_resources(
        cores=data["compRes"]["cores"],
        core_frequency=data["compRes"]["core_frequnecy"],
        flops_per_cycle=data["compRes"]["flops_per_cycle"],
        memory_channels=data["compRes"]["memory_channels"],
        memory_width=data["compRes"]["memory_width"],
        memory_frequency=data["compRes"]["memory_frequnecy"],
        network_speed=data["compRes"]["networkSpeed"],
        time_in_driver=data["compRes"]["timeInDriver"],
    )

    # Create a new Pipeline
    pipeline = Pipeline(name=name)

    # Group size for packetization
    n_groups = 50

    # Add Camera component
    pipeline.add_component(
        PipelineComponent(
            component_type=ComponentType.CAMERA,
            name="Camera",
            compute=comp,
            function=PCOCamLink,
            params={"n_pixels": nPixels, "group": n_groups, "readout": readoutTime},
        )
    )

    # Add Calibration component
    pipeline.add_component(
        PipelineComponent(
            component_type=ComponentType.CALIBRATION,
            name="Calibration",
            compute=comp,
            function=PixelCalibration,
            params={"n_pixels": nPixels, "group": n_groups, "scale": calScale},
            dependencies=["Camera"],
        )
    )

    # Add Centroiding component
    pipeline.add_component(
        PipelineComponent(
            component_type=ComponentType.CENTROIDER,
            name="Centroider",
            compute=comp,
            function=Centroider,
            params={
                "n_valid_subaps": nValidSubAps,
                "n_pix_per_subap": nPixPerSub,
                "scale": centScale,
                "square_diff": square_diff,
                "sort": sort,
            },
            dependencies=["Calibration"],
        )
    )

    # Add Reconstruction component
    pipeline.add_component(
        PipelineComponent(
            component_type=ComponentType.RECONSTRUCTION,
            name="Reconstructor",
            compute=comp,
            function=Reconstruction,
            params={"n_slopes": nValidSubAps * 2, "n_acts": nActs, "scale": mvmScale},
            dependencies=["Centroider"],
        )
    )

    # Add Network Transfer component
    pipeline.add_component(
        PipelineComponent(
            component_type=ComponentType.NETWORK,
            name="Network",
            compute=comp,
            function=TimeOnNetwork,
            params={"n_bits": nActs * 32},
            dependencies=["Reconstructor"],
        )
    )

    # Add Control component
    pipeline.add_component(
        PipelineComponent(
            component_type=ComponentType.CONTROL,
            name="Control",
            compute=comp,
            function=FullFrameControl,
            params={"n_acts": nActs, "scale": controlScale, "combine": nCombine},
            dependencies=["Network"],
        )
    )

    # Run the pipeline simulation
    results = pipeline.run(debug=True)

    # Visualize the pipeline
    fig = pipeline.visualize(
        title=name, xlabel=r"time ($\mu$s)", save_path=f"Images/{name}_modern.png"
    )

    # Print summary
    pipeline.print_summary()

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
            print("Usage: python migrate_packtise_pipeline.py [old|new] [config_file]")
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

import json
import argparse
from daolite import Pipeline, PipelineComponent, ComponentType
from daolite.compute import create_compute_resources
from daolite.simulation.camera import PCOCamLink, GigeVisionCamera, RollingShutterCamera
from daolite.pipeline.centroider import CrossCorrelate
from daolite.pipeline.reconstruction import Reconstruction
from daolite.pipeline.control import FullFrameControl
from daolite.pipeline.calibration import PixelCalibration
from daolite.utils.network import TimeOnNetwork

FUNCTION_MAP = {
    "PCOCamLink": PCOCamLink,
    "GigeVisionCamera": GigeVisionCamera,
    "RollingShutterCamera": RollingShutterCamera,
    "cross_correlation_centroider": CrossCorrelate,
    "mvr_reconstruction": Reconstruction,
    "dm_control": FullFrameControl,
    "PixelCalibration": PixelCalibration,
    "TimeOnNetwork": TimeOnNetwork,
}


def run_pipeline_from_json(json_path):
    with open(json_path, "r") as f:
        data = json.load(f)
    pipeline = Pipeline()
    name_to_component = {}
    # Create components
    for comp in data["components"]:
        comp_type = ComponentType[comp["type"]]
        name = comp["name"]
        params = comp.get("params", {})
        compute = create_compute_resources(
            cores=16,
            core_frequency=2.6e9,
            flops_per_cycle=32,
            memory_frequency=3.2e9,
            memory_width=64,
            memory_channels=8,
            network_speed=100e9,
            time_in_driver=5.0,
        )
        func_name = (
            params.get("camera_function", None)
            if comp_type == ComponentType.CAMERA
            else None
        )
        if not func_name:
            func_name = {
                ComponentType.CAMERA: "PCOCamLink",
                ComponentType.CENTROIDER: "cross_correlation_centroider",
                ComponentType.RECONSTRUCTION: "mvr_reconstruction",
                ComponentType.CONTROL: "dm_control",
                ComponentType.CALIBRATION: "PixelCalibration",
                ComponentType.NETWORK: "TimeOnNetwork",
            }.get(comp_type, None)
        function = FUNCTION_MAP.get(func_name)
        if function is None:
            raise TypeError(
                f"Function '{func_name}' not found for component '{name}' of type '{comp_type.name}'"
            )
        pipeline_comp = PipelineComponent(
            component_type=comp_type,
            name=name,
            compute=compute,
            function=function,
            params=params,
            dependencies=[],
        )
        pipeline.add_component(pipeline_comp)
        name_to_component[name] = pipeline_comp
    # Set dependencies
    for idx, comp in enumerate(data["components"]):
        comp_name = comp["name"]
        pipeline_comp = name_to_component[comp_name]
        deps = [
            conn["start"] for conn in data["connections"] if conn["end"] == comp_name
        ]
        pipeline_comp.dependencies = deps
    # Run the pipeline
    results = pipeline.run(debug=True)
    return results


def main():
    parser = argparse.ArgumentParser(
        description="Run a DaoLITE pipeline from a JSON file."
    )
    parser.add_argument("json_file", help="Path to the pipeline JSON file")
    args = parser.parse_args()
    print(f"Running pipeline from {args.json_file} ...")
    results = run_pipeline_from_json(args.json_file)
    print("Pipeline run complete.")
    # Optionally print results summary
    if results is not None:
        print("Results:")
        print(results)


if __name__ == "__main__":
    main()

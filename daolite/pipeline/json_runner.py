import json
import argparse
import inspect
from daolite import Pipeline, PipelineComponent, ComponentType
from daolite.compute import create_compute_resources
from daolite.simulation.camera import PCOCamLink, GigeVisionCamera, RollingShutterCamera
from daolite.pipeline.centroider import CrossCorrelate
from daolite.pipeline.reconstruction import Reconstruction
from daolite.pipeline.control import FullFrameControl
from daolite.pipeline.calibration import PixelCalibration
from daolite.utils.network import TimeOnNetwork, network_transfer

FUNCTION_MAP = {
    "PCOCamLink": PCOCamLink,
    "GigeVisionCamera": GigeVisionCamera,
    "RollingShutterCamera": RollingShutterCamera,
    "cross_correlation_centroider": CrossCorrelate,
    "mvr_reconstruction": Reconstruction,
    "dm_control": FullFrameControl,
    "PixelCalibration": PixelCalibration,
    "TimeOnNetwork": TimeOnNetwork,
    "network_transfer": network_transfer,
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
        
        # Add default parameters for specific component types if they're missing
        if comp_type == ComponentType.CAMERA and not params:
            # Default camera parameters
            params = {
                "n_pixels": 1024 * 1024,  # 1MP camera
                "group": 50,              # Default packet count
                "bit_depth": 16           # Default bit depth
            }
        elif comp_type == ComponentType.CALIBRATION and not params:
            # Default calibration parameters
            params = {
                "n_pixels": 1024 * 1024,  # 1MP
                "group": 50               # Default group size
            }
        elif comp_type == ComponentType.CENTROIDER and not params:
            # Default centroider parameters
            params = {
                "n_valid_subaps": 6400,   # 80x80
                "group": 50               # Default group size
            }
        
        compute = None
        if "compute" in comp:
            from daolite.compute.base_resources import ComputeResources
            # Only use fields that are valid for ComputeResources
            valid_fields = {
                'hardware', 'memory_bandwidth', 'flops', 'network_speed', 'time_in_driver',
                'core_fudge', 'mem_fudge', 'network_fudge', 'adjust', 'cores', 'core_frequency',
                'flops_per_cycle', 'memory_frequency', 'memory_width', 'memory_channels'
            }
            compute_dict = {k: v for k, v in comp["compute"].items() if k in valid_fields}
            compute = ComputeResources.from_dict(compute_dict)
        else:
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
        
        # Filter params to only those accepted by the function
        sig = inspect.signature(function)
        
        # Check if function requires parameters that aren't in params
        required_params = {
            param.name for param in sig.parameters.values() 
            if param.default == inspect.Parameter.empty and param.name != 'self'
        }
        
        # Check if we're missing any required parameters and try to provide sensible defaults
        missing_params = required_params - set(params.keys())
        if missing_params:
            print(f"Warning: Missing required parameters for {name} ({comp_type.name}): {missing_params}")
            
            # Add sensible defaults based on component type
            if comp_type == ComponentType.CAMERA:
                if "n_pixels" in missing_params:
                    params["n_pixels"] = 1024 * 1024  # 1MP
                if "group" in missing_params:
                    params["group"] = 50
            elif comp_type == ComponentType.CALIBRATION:
                if "n_pixels" in missing_params:
                    params["n_pixels"] = 1024 * 1024
            elif comp_type == ComponentType.CENTROIDER:
                if "n_valid_subaps" in missing_params:
                    params["n_valid_subaps"] = 6400  # 80x80
            elif comp_type == ComponentType.RECONSTRUCTION:
                if "n_acts" in missing_params:
                    params["n_acts"] = 5000  # Default actuator count for ELT
            
        filtered_params = {k: v for k, v in params.items() if k in sig.parameters}
        
        # Double-check we've got all required parameters
        for param in required_params:
            if param not in filtered_params:
                print(f"Error: Required parameter '{param}' is missing for {name} ({comp_type.name})")
        
        pipeline_comp = PipelineComponent(
            component_type=comp_type,
            name=name,
            compute=compute,
            function=function,
            params=filtered_params,
            dependencies=[],
        )
        pipeline.add_component(pipeline_comp)
        name_to_component[name] = pipeline_comp
    
    # Process transfer components
    for transfer in data.get("transfers", []):
        source = transfer.get("source")
        destination = transfer.get("destination")
        transfer_type = transfer.get("transfer_type", "Network")
        transfer_name = transfer.get("name", f"{transfer_type}_Transfer_{source}_to_{destination}")
        params = transfer.get("params", {})
        
        # If data_size not in params but in transfer, add it
        if "n_bits" not in params and "data_size" in transfer:
            params["n_bits"] = transfer["data_size"]
        
        # Ensure required parameters are set for network transfers
        if transfer_type.lower() == "network":
            # Default group size if not specified
            if "group" not in params:
                params["group"] = 50
                
            # Check for required parameters
            if "n_bits" not in params:
                # Try to estimate data size based on the source component type
                if source in name_to_component:
                    src_comp = name_to_component[source]
                    if src_comp.component_type == ComponentType.CAMERA:
                        # Camera outputs pixel data
                        n_pixels = src_comp.params.get("n_pixels", 1024 * 1024)  # Default 1MP
                        bit_depth = src_comp.params.get("bit_depth", 16)  # Default 16-bit
                        params["n_bits"] = n_pixels * bit_depth
                        print(f"Auto-estimated data size for {transfer_name}: {params['n_bits']} bits")
                    elif src_comp.component_type == ComponentType.CALIBRATION:
                        # Calibration outputs processed pixel data
                        n_pixels = src_comp.params.get("n_pixels", 1024 * 1024)
                        bit_depth = src_comp.params.get("bit_depth", 16)
                        params["n_bits"] = n_pixels * bit_depth
                    elif src_comp.component_type == ComponentType.CENTROIDER:
                        # Centroider outputs slope measurements
                        n_subaps = src_comp.params.get("n_valid_subaps", 6400)  # Default 80×80
                        params["n_bits"] = n_subaps * 2 * 32  # X and Y slopes, float32
                    elif src_comp.component_type == ComponentType.RECONSTRUCTION:
                        # Reconstruction outputs actuator commands
                        n_acts = src_comp.params.get("n_acts", 5000)  # Default ELT scale
                        params["n_bits"] = n_acts * 32  # Float32 actuator values
                    else:
                        # Default to 1MB if we can't determine
                        params["n_bits"] = 8 * 1024 * 1024
                        print(f"Warning: Could not determine data size for {transfer_name}, using default of 8MB")
                else:
                    # Default data size if source component not found
                    params["n_bits"] = 8 * 1024 * 1024  # Default to 8MB
                    print(f"Warning: Source component '{source}' not found for {transfer_name}, using default data size of 8MB")
            
            # Add network-specific parameters
            if "transfer_type" not in params:
                params["transfer_type"] = "network"
            
            # Set destination network parameters if not already set
            if destination in name_to_component:
                dest_comp = name_to_component[destination]
                dest_compute = dest_comp.compute
                
                if dest_compute and "use_dest_network" not in params:
                    params["use_dest_network"] = True
                    
                    # Add destination network speed if available and not already set
                    if hasattr(dest_compute, 'network_speed') and "dest_network_speed" not in params:
                        params["dest_network_speed"] = dest_compute.network_speed
                        
                    # Add destination driver time if available and not already set
                    if hasattr(dest_compute, 'time_in_driver') and "dest_time_in_driver" not in params:
                        params["dest_time_in_driver"] = dest_compute.time_in_driver
        
        # Create transfer component
        function = network_transfer  # Default to network_transfer
        if "function" in transfer:
            function = FUNCTION_MAP.get(transfer["function"], network_transfer)
            
        compute = None
        if "compute" in transfer:
            from daolite.compute.base_resources import ComputeResources
            valid_fields = {
                'hardware', 'memory_bandwidth', 'flops', 'network_speed', 'time_in_driver',
                'core_fudge', 'mem_fudge', 'network_fudge', 'adjust', 'cores', 'core_frequency',
                'flops_per_cycle', 'memory_frequency', 'memory_width', 'memory_channels'
            }
            compute_dict = {k: v for k, v in transfer["compute"].items() if k in valid_fields}
            compute = ComputeResources.from_dict(compute_dict)
        else:
            # Use source component's compute resources if available
            if source in name_to_component:
                compute = name_to_component[source].compute
            else:
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
        
        # Add transfer component to pipeline
        transfer_comp = PipelineComponent(
            component_type=ComponentType.NETWORK,
            name=transfer_name,
            compute=compute,
            function=function,
            params=params,
            dependencies=[source] if source else []
        )
        pipeline.add_component(transfer_comp)
        name_to_component[transfer_name] = transfer_comp
        
        # Update destination component to depend on transfer instead of source
        if destination in name_to_component:
            dest_comp = name_to_component[destination]
            # Replace direct source dependency with transfer dependency
            if source in dest_comp.dependencies:
                dest_comp.dependencies.remove(source)
            if transfer_name not in dest_comp.dependencies:
                dest_comp.dependencies.append(transfer_name)
    
    # Set dependencies for direct connections
    for idx, comp in enumerate(data["components"]):
        comp_name = comp["name"]
        pipeline_comp = name_to_component[comp_name]
        # Find all connections where this component is the destination
        direct_deps = []
        for conn in data["connections"]:
            if conn["end"] == comp_name:
                # Check if this connection should be via a transfer
                source = conn["start"]
                has_transfer = False
                for transfer in data.get("transfers", []):
                    if transfer.get("source") == source and transfer.get("destination") == comp_name:
                        has_transfer = True
                        break
                
                # Only add direct dependency if there's no transfer component
                if not has_transfer and source not in pipeline_comp.dependencies:
                    direct_deps.append(source)
        
        # Add any direct dependencies that aren't already in the component's dependencies
        for dep in direct_deps:
            if dep not in pipeline_comp.dependencies:
                pipeline_comp.dependencies.append(dep)
    
    # Run the pipeline
    results = pipeline.run(debug=True)
    return results


def main():
    parser = argparse.ArgumentParser(
        description="Run a daolite pipeline from a JSON file."
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

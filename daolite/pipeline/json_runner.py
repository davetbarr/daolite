import json
import argparse
import inspect
import logging
from daolite import Pipeline, PipelineComponent, ComponentType
from daolite.compute import create_compute_resources
from daolite.simulation.camera import PCOCamLink, GigeVisionCamera, RollingShutterCamera
from daolite.simulation.deformable_mirror import StandardDM, DMController, WavefrontCorrector
from daolite.pipeline.centroider import Centroider
from daolite.pipeline.reconstruction import Reconstruction
from daolite.pipeline.control import FullFrameControl
from daolite.pipeline.calibration import PixelCalibration
from daolite.utils.network import TimeOnNetwork, network_transfer
from daolite.utils import chronograph
import numpy as np
import matplotlib.pyplot as plt
import tempfile

logging.getLogger("matplotlib").setLevel(logging.WARNING)

FUNCTION_MAP = {
    # Camera components
    "PCOCamLink": PCOCamLink,
    "GigeVisionCamera": GigeVisionCamera,
    "RollingShutterCamera": RollingShutterCamera,
    
    # Pipeline components
    "Centroider": Centroider,
    "Reconstruction": Reconstruction,
    "FullFrameControl": FullFrameControl,
    "PixelCalibration": PixelCalibration,
    
    # Network/transfer components
    "TimeOnNetwork": TimeOnNetwork,
    "network_transfer": network_transfer,
    
    # DeformableMirror components
    "StandardDM": StandardDM,
    "DMController": DMController,
    "WavefrontCorrector": WavefrontCorrector,
}


def run_pipeline_and_return_pipe(json_path, debug=False):
    """
    Run a pipeline from a JSON file and return both the pipeline object and results.
    
    Args:
        json_path: Path to the JSON file defining the pipeline
        debug: Enable debug output for pipeline components
        
    Returns:
        tuple: (pipeline, results, pipeline_title) - the pipeline object, execution results, and pipeline title
    """
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger("json_runner")

    with open(json_path, "r") as f:
        data = json.load(f)
    # Get pipeline title if present
    pipeline_title = data.get("title", "Pipeline Timing")
    pipeline = Pipeline()
    name_to_component = {}
    
    # Build a lookup for container compute resources
    container_compute = {}
    for container in data.get("containers", []):
        if container.get("type") == "ComputeBox" and "name" in container and "compute" in container:
            container_compute[container["name"]] = container["compute"]

    # Create components
    for comp in data["components"]:
        comp_type = ComponentType[comp["type"]]
        name = comp["name"]
        params = comp.get("params", {})
        logger.debug(f"Processing component: {name} ({comp_type})")
        
        # Add default parameters for specific component types if they're missing
        if comp_type == ComponentType.CAMERA and not params:
            # Default camera parameters
            params = {
                "n_pixels": 1024 * 1024,  # 1MP camera
                "group": 50,              # Default packet count
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
            valid_fields = {
                'hardware', 'memory_bandwidth', 'flops', 'network_speed', 'time_in_driver',
                'core_fudge', 'mem_fudge', 'network_fudge', 'adjust', 'cores', 'core_frequency',
                'flops_per_cycle', 'memory_frequency', 'memory_width', 'memory_channels'
            }
            compute_dict = {k: v for k, v in comp["compute"].items() if k in valid_fields}
            compute = ComputeResources.from_dict(compute_dict)
            logger.info(f"Component '{name}' uses direct compute resource: {compute_dict}")
        else:
            parent_type = comp.get("parent_type")
            parent_name = comp.get("parent_name")
            parent_compute = None
            if parent_type == "ComputeBox" and parent_name in container_compute:
                compute_dict = container_compute[parent_name]
                valid_fields = {
                    'hardware', 'memory_bandwidth', 'flops', 'network_speed', 'time_in_driver',
                    'core_fudge', 'mem_fudge', 'network_fudge', 'adjust', 'cores', 'core_frequency',
                    'flops_per_cycle', 'memory_frequency', 'memory_width', 'memory_channels'
                }
                compute_dict = {k: v for k, v in compute_dict.items() if k in valid_fields}
                from daolite.compute.base_resources import ComputeResources
                parent_compute = ComputeResources.from_dict(compute_dict)
                logger.info(f"Component '{name}' inherits compute resource from parent '{parent_name}': {compute_dict}")
            # Always use parent compute if found, else fallback
            if parent_compute is not None:
                compute = parent_compute
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
                logger.warning(f"Component '{name}' uses default compute resource.")
        logger.debug(f"Final compute resource for '{name}': {getattr(compute, 'hardware', None)}, {vars(compute) if compute else None}")
        
        func_name = (
            params.get("camera_function", None)
            if comp_type == ComponentType.CAMERA
            else None
        )
        if not func_name:
            func_name = {
                ComponentType.CAMERA: "PCOCamLink",
                ComponentType.CENTROIDER: "Centroider",
                ComponentType.RECONSTRUCTION: "Reconstruction",
                ComponentType.CONTROL: "FullFrameControl",
                ComponentType.CALIBRATION: "PixelCalibration",
                ComponentType.NETWORK: "TimeOnNetwork",
                ComponentType.DM: "StandardDM",  # Default to StandardDM for DM type
            }.get(comp_type, None)
            
            # For DM components, check for specific DM types in params
            if comp_type == ComponentType.DM and "dm_type" in params:
                dm_type = params["dm_type"]
                if dm_type == "dm_controller":
                    func_name = "DMController"
                elif dm_type == "wavefront_corrector":
                    func_name = "WavefrontCorrector"
                # Remove the dm_type param as it's not needed by the function
                params.pop("dm_type", None)
                
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
            and param.kind != inspect.Parameter.VAR_KEYWORD  # Ignore **kwargs
        }
        # Remove parameters that will be injected later
        ignorable_params = {"compute_resources", "start_times"}
        missing_params = required_params - set(params.keys()) - ignorable_params
        
        # Also check if we'll get agenda params from old-style params
        # This prevents spurious warnings when using backward compatibility
        if missing_params:
            satisfied_by_compat = set()
            # Check if we have old-style params that will satisfy agenda requirements
            if comp_type == ComponentType.CENTROIDER:
                if "n_valid_subaps" in params and "centroid_agenda" in missing_params:
                    satisfied_by_compat.add("centroid_agenda")
            elif comp_type == ComponentType.CALIBRATION:
                if "n_pixels" in params and "pixel_agenda" in missing_params:
                    satisfied_by_compat.add("pixel_agenda")
            elif comp_type == ComponentType.RECONSTRUCTION:
                if "n_slopes" in params and "centroid_agenda" in missing_params:
                    satisfied_by_compat.add("centroid_agenda")
            
            missing_params = missing_params - satisfied_by_compat
            if missing_params:
                print(f"Warning: Missing required parameters for {name} ({comp_type.name}): {missing_params}")
        
        # Add sensible defaults based on component type (no duplicate warning)
        missing_params_for_defaults = required_params - set(params.keys())
        if comp_type == ComponentType.CAMERA:
            if "n_pixels" in missing_params_for_defaults:
                params["n_pixels"] = 1024 * 1024  # 1MP
            if "group" in missing_params_for_defaults:
                params["group"] = 50
        elif comp_type == ComponentType.CALIBRATION:
            if "n_pixels" in missing_params_for_defaults:
                params["n_pixels"] = 1024 * 1024
        elif comp_type == ComponentType.CENTROIDER:
            if "n_valid_subaps" in missing_params_for_defaults:
                params["n_valid_subaps"] = 6400  # 80x80
        elif comp_type == ComponentType.RECONSTRUCTION:
            if "n_acts" in missing_params_for_defaults:
                params["n_acts"] = 5000  # Default actuator count for ELT
        
        # Transform old API parameters to new agenda-based API
        # This allows backward compatibility with old JSON files
        if comp_type == ComponentType.CENTROIDER:
            if "n_valid_subaps" in params and "centroid_agenda" not in params:
                # Create a default centroid_agenda from n_valid_subaps
                # We'll create it as a single-element agenda in the pipeline execution
                # For now, just store the n_valid_subaps value
                params["_n_valid_subaps_compat"] = params.pop("n_valid_subaps")
        elif comp_type == ComponentType.CALIBRATION:
            if "n_pixels" in params and "pixel_agenda" not in params:
                # Store for compatibility transformation
                params["_n_pixels_compat"] = params.pop("n_pixels")
        elif comp_type == ComponentType.RECONSTRUCTION:
            if "n_slopes" in params and "centroid_agenda" not in params:
                # Store for compatibility transformation  
                params["_n_slopes_compat"] = params.pop("n_slopes")
        
        # Keep compatibility params even if they're not in the function signature
        compat_params = {k: v for k, v in params.items() if k.startswith("_") and k.endswith("_compat")}
        filtered_params = {k: v for k, v in params.items() if k in sig.parameters}
        # Add back the compat params
        filtered_params.update(compat_params)
        
        # Build set of satisfied parameters including those satisfied by compat params
        satisfied_params = set(filtered_params.keys())
        # Map compat params to the params they satisfy
        if "_n_valid_subaps_compat" in satisfied_params:
            satisfied_params.add("centroid_agenda")
        if "_n_pixels_compat" in satisfied_params:
            satisfied_params.add("pixel_agenda")
        if "_n_slopes_compat" in satisfied_params:
            satisfied_params.add("centroid_agenda")
        
        # Double-check we've got all required parameters (excluding ignorable)
        for param in required_params:
            if param not in satisfied_params and param not in ignorable_params:
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
                        
        # For PCIe transfers, ensure PCIe-specific parameters
        elif transfer_type.lower() == "pcie":
            # For PCIe transfer, we need to filter the parameters to only those
            # accepted by the pcie_transfer function
            # Check the function signature: pcie_transfer(n_bits, compute_resources, debug=False)
            # Filter params to only include n_bits (all other parameters will be injected)
            filtered_params = {}
            if "n_bits" in params:
                filtered_params["n_bits"] = params["n_bits"]
            params = filtered_params
        
        # Determine the appropriate transfer function
        function = None
        if transfer_type.lower() == "network":
            function = network_transfer
            # Also add to FUNCTION_MAP
            FUNCTION_MAP["network_transfer"] = network_transfer
        elif transfer_type.lower() == "pcie":
            # Import pcie_transfer if not already in FUNCTION_MAP
            if "pcie_transfer" not in FUNCTION_MAP:
                try:
                    from daolite.utils.network import pcie_transfer
                    FUNCTION_MAP["pcie_transfer"] = pcie_transfer
                    function = pcie_transfer
                except ImportError:
                    print(f"Warning: pcie_transfer not found, using network_transfer for {transfer_name}")
                    function = network_transfer
            else:
                function = FUNCTION_MAP["pcie_transfer"]
        
        # Default to network_transfer if no specific function determined
        if not function:
            function = network_transfer
            
        # Set or get dependencies 
        dependencies = transfer.get("dependencies", [])
        # If no dependencies specified but source exists, depend on source
        if not dependencies and source and source in name_to_component:
            dependencies = [source]
        
        # Create compute resource for the transfer
        compute = None
        if "compute" in transfer and transfer["compute"] is not None:
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
            dependencies=dependencies
        )
        pipeline.add_component(transfer_comp)
        name_to_component[transfer_name] = transfer_comp
    
    # Set up connection dependencies based on transfer chains
    for conn in data.get("connections", []):
        source = conn.get("start")
        destination = conn.get("end")
        transfer_chain = conn.get("transfers", [])
        
        # Skip if source or destination doesn't exist
        if source not in name_to_component or destination not in name_to_component:
            logger.warning(f"Skipping connection {source} → {destination}: component not found")
            continue
        
        # Get the components
        source_comp = name_to_component[source]
        dest_comp = name_to_component[destination]
        
        if transfer_chain:
            # Connection uses transfer chain
            logger.debug(f"Processing transfer chain for {source} → {destination}: {transfer_chain}")
            
            # Verify all transfers in the chain exist
            missing_transfers = [t for t in transfer_chain if t not in name_to_component]
            if missing_transfers:
                # Some transfers are missing - we need to auto-create them
                logger.warning(f"Missing transfers in chain: {missing_transfers} - will auto-create")
                
                # Auto-create transfer chain - this would require more complex logic
                # For now we'll fall back to direct dependency
                if source not in dest_comp.dependencies:
                    dest_comp.dependencies.append(source)
                continue
            
            # First transfer must depend on source
            first_transfer = name_to_component[transfer_chain[0]]
            if source not in first_transfer.dependencies:
                first_transfer.dependencies.append(source)
            
            # Each subsequent transfer depends on the previous one
            for i in range(1, len(transfer_chain)):
                curr_transfer = name_to_component[transfer_chain[i]]
                prev_transfer = name_to_component[transfer_chain[i-1]]
                if prev_transfer.name not in curr_transfer.dependencies:
                    curr_transfer.dependencies.append(prev_transfer.name)
            
            # Destination depends on last transfer
            last_transfer = name_to_component[transfer_chain[-1]]
            # Remove direct dependency on source if it exists
            if source in dest_comp.dependencies:
                dest_comp.dependencies.remove(source)
            # Add dependency on last transfer
            if last_transfer.name not in dest_comp.dependencies:
                dest_comp.dependencies.append(last_transfer.name)
            
            logger.debug(f"Transfer chain dependencies set up: {source} → {' → '.join(transfer_chain)} → {destination}")
        else:
            # No transfer chain specified - check if we need to auto-insert transfers
            # For now, just set up direct dependency
            if source not in dest_comp.dependencies:
                dest_comp.dependencies.append(source)
    
    # Run the pipeline
    results = pipeline.run(debug=debug)
    return pipeline, results, pipeline_title


def visualize_pipeline(pipeline, title=None, save_path=None, show=True):
    """
    Visualize the pipeline execution timeline using the chronograph utility.
    
    Args:
        pipeline: The Pipeline object to visualize
        title: Title for the visualization
        save_path: Path to save the visualization (if None, won't save)
        show: Whether to display the visualization (default True)
    """
    try:
        # Check if the pipeline has timing data
        if not hasattr(pipeline, "execution_order") or not hasattr(pipeline, "timing_results"):
            print("Error: Pipeline has no timing data to visualize.")
            return
            
        # Extract timing data
        execution_order = pipeline.execution_order
        timing_results = pipeline.timing_results
        
        # Ensure we have timing results
        if not timing_results:
            print("Error: No timing results available for visualization.")
            return
        
        # Create dataset for chronograph (matching the format used in Pipeline.visualize)
        data_set = []
        for name in execution_order:
            component = pipeline.components[name]
            timing = timing_results[name]

            # Handle scalar timing results (convert to array form)
            if not isinstance(timing, np.ndarray) or len(timing.shape) == 0:
                # If previous component exists, use its end time as start
                if data_set:
                    prev_timing = data_set[-1][0]
                    start_time = (
                        prev_timing[-1, 1]
                        if len(prev_timing.shape) > 1
                        else prev_timing[1]
                    )
                else:
                    start_time = 0

                arr_timing = np.zeros([1, 2])
                arr_timing[0, 0] = start_time
                arr_timing[0, 1] = start_time + timing
                timing = arr_timing

            # Add to dataset with component name and type as label
            data_set.append([timing, f"{name} ({component.component_type.value})"])

        # Use title if provided, else fallback
        plot_title = title if title else "Pipeline Timing"
        if data_set:
            try:
                fig, ax, latency = chronograph.generate_chrono_plot_packetize(
                    data_list=data_set, 
                    title=plot_title, 
                    xlabel="Time (μs)", 
                    multiplot=False
                )
                
                # Save if path provided
                if save_path:
                    fig.savefig(save_path, dpi=300, bbox_inches='tight')
                    print(f"Visualization saved to {save_path}")
                
                # Show if requested
                if show:
                    plt.show()
                else:
                    plt.close(fig)
                    
                return fig, ax, latency
            except Exception as e:
                print(f"Error generating chronograph: {str(e)}")
        else:
            print("No timing data to visualize.")
            
    except ImportError:
        print("Error: Matplotlib is required for visualization. Install with 'pip install matplotlib'.")
    except Exception as e:
        print(f"Error creating visualization: {str(e)}")
        
    return None, None


def run_pipeline_from_json(json_path):
    """Run a pipeline from a JSON file and return results."""
    pipeline, results, _ = run_pipeline_and_return_pipe(json_path)
    return results


def main():
    import logging
    logfile = tempfile.NamedTemporaryFile(prefix="daolite_", suffix=".log", delete=False)
    logging.basicConfig(filename=logfile.name, level=logging.INFO, filemode='w')
    print(f"Logging to {logfile.name}")
    
    parser = argparse.ArgumentParser(
        description="Run a daolite pipeline from a JSON file."
    )
    parser.add_argument("json_file", help="Path to the pipeline JSON file")
    parser.add_argument("--show", action="store_true", help="Show visualization of pipeline execution timeline")
    parser.add_argument("--no-show", action="store_true", help="Don't show visualization (overrides --show)")
    parser.add_argument("--save", help="Save visualization to specified file path", default=None)
    parser.add_argument("--debug", action="store_true", help="Enable debug output for pipeline components")
    args = parser.parse_args()
    
    print(f"Running pipeline from {args.json_file} ...")
    pipeline, results, pipeline_title = run_pipeline_and_return_pipe(args.json_file, debug=args.debug)
    print("Pipeline run complete.")
    
    # Optionally print results summary
    if results is not None:
        # print("Results:")
        # print(results)
        # Print a basic summary
        print("\nPipeline Summary:")
        end_to_end_start = None
        end_to_end_end = None
        # Find the last pixel received (end of network transfer to calibration)
        network_key = None
        for k in results:
            if k.lower().startswith("network_transfer") and "cal" in k.lower():
                network_key = k
                break
        if network_key and hasattr(results[network_key], 'shape') and results[network_key].ndim == 2:
            end_to_end_start = results[network_key][-1, 1]
        # Find the last command calculated (end of last control or reconstruction)
        ctrl_end = None
        recn_end = None
        if 'Ctrl' in results and not isinstance(results['Ctrl'], np.ndarray):
            # Scalar, use Recn if available
            if 'Recn' in results and hasattr(results['Recn'], 'shape') and results['Recn'].ndim == 2:
                recn_end = results['Recn'][-1, 1]
        elif 'Ctrl' in results and hasattr(results['Ctrl'], 'shape') and results['Ctrl'].ndim == 2:
            ctrl_end = results['Ctrl'][-1, 1]
        elif 'Recn' in results and hasattr(results['Recn'], 'shape') and results['Recn'].ndim == 2:
            recn_end = results['Recn'][-1, 1]
        # Print per-component summary (true compute time: sum of durations)
        for name, result in results.items():
            if hasattr(result, 'shape') and result.ndim == 2 and result.shape[1] == 2:
                durations = result[:, 1] - result[:, 0]
                total_compute = durations.sum()
                print(f"  {name}: {total_compute:.2f} μs (sum of group durations)")
            elif hasattr(result, 'shape') and result.ndim == 1:
                print(f"  {name}: array shape {result.shape}")
            else:
                try:
                    print(f"  {name}: {float(result):.2f} μs")
                except Exception:
                    print(f"  {name}: {result}")
        # Print end-to-end latency
        if end_to_end_start is not None:
            final_end = ctrl_end if ctrl_end is not None else recn_end
            if final_end is not None:
                end_to_end_latency = final_end - end_to_end_start
                print(f"\nEnd-to-end latency (last pixel received to last command calculated): {end_to_end_latency:.2f} μs")
    
    # Visualize pipeline if requested
    if args.save or args.show:
        title = pipeline_title
        save_path = args.save
        # Only show if --show is set and --no-show is not set
        show_viz = args.show and not args.no_show
        visualize_pipeline(pipeline, title, save_path, show=show_viz)


if __name__ == "__main__":
    main()

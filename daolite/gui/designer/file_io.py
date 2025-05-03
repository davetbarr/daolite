"""
File I/O utilities for the pipeline designer.

This module handles saving and loading pipeline designs to/from files.
"""

import json
import logging
from PyQt5.QtCore import QRectF
from daolite.common import ComponentType
from daolite.compute.hardware import (
    amd_epyc_7763,
    amd_epyc_9654,
    intel_xeon_8480,
    intel_xeon_8462,
    amd_ryzen_7950x,
    nvidia_a100_80gb,
    nvidia_h100_80gb,
    nvidia_rtx_4090,
    amd_mi300x,
)
from daolite.compute import create_compute_resources

from .components import ComputeBox, GPUBox, ComponentBlock
from .connection import Connection
from .connection_manager import update_connection_indicators
from .data_transfer import estimate_data_size

# Set up logging
logger = logging.getLogger('FileIO')

def _to_dict_recursive(obj):
    if hasattr(obj, 'to_dict') and callable(obj.to_dict):
        d = obj.to_dict().copy()
        # Recursively convert attached_gpus if present
        if 'attached_gpus' in d and isinstance(d['attached_gpus'], list):
            d['attached_gpus'] = [_to_dict_recursive(g) for g in d['attached_gpus']]
        return d
    elif isinstance(obj, list):
        return [_to_dict_recursive(i) for i in obj]
    return obj

def save_pipeline_to_file(scene, components, connections, filename):
    """
    Save pipeline design to a JSON file.
    
    Args:
        scene: The QGraphicsScene containing the pipeline
        components: List of component blocks
        connections: List of connections
        filename: Path to save the JSON file
        
    Returns:
        bool: True if save was successful, False otherwise
    """
    data = {
        "containers": [],
        "components": [], 
        "connections": [],
        "transfers": []
    }
    
    # Save compute and GPU boxes first
    for item in scene.items():
        if isinstance(item, ComputeBox):
            container_data = {
                "type": "ComputeBox",
                "name": item.name,
                "pos": (item.pos().x(), item.pos().y()),
                "size": (item.size.width(), item.size.height()),
            }
            if item.compute is not None:
                compute_dict = _to_dict_recursive(item.compute)
                if "name" in compute_dict:
                    container_data["resource_name"] = compute_dict["name"]
                    del compute_dict["name"]
                container_data["compute"] = compute_dict
            
            # Store GPU boxes inside this compute box
            gpu_boxes = []
            for child in item.childItems():
                if isinstance(child, GPUBox):
                    gpu_data = {
                        "type": "GPUBox",
                        "name": child.name,
                        "pos": (child.pos().x(), child.pos().y()),
                        "size": (child.size.width(), child.size.height()),
                    }
                    if child.compute is not None:
                        gpu_compute_dict = _to_dict_recursive(child.compute)
                        if "name" in gpu_compute_dict:
                            gpu_data["resource_name"] = gpu_compute_dict["name"]
                            del gpu_compute_dict["name"]
                        gpu_data["compute"] = gpu_compute_dict
                    gpu_boxes.append(gpu_data)
            
            container_data["gpu_boxes"] = gpu_boxes
            data["containers"].append(container_data)
    
    # Save components
    components_by_name = {}  # Map names to components for easier lookup
    for comp in components:
        parent_container = None
        parent_type = None
        parent_name = None
        gpu_parent_name = None
        
        # Find which container this component belongs to
        parent = comp.parentItem()
        if parent:
            if isinstance(parent, ComputeBox):
                parent_type = "ComputeBox"
                parent_name = parent.name
            elif isinstance(parent, GPUBox):
                parent_type = "GPUBox"
                parent_name = parent.name
                # Also get the grandparent (ComputeBox) if it exists
                grandparent = parent.parentItem()
                if grandparent and isinstance(grandparent, ComputeBox):
                    gpu_parent_name = grandparent.name
        
        # Fill in default params if missing
        params = comp.params.copy() if comp.params else {}
        ctype = comp.component_type.name if hasattr(comp, 'component_type') else comp.type
        if ctype == "CAMERA":
            if "n_pixels" not in params:
                params["n_pixels"] = 1048576
            if "group" not in params:
                params["group"] = 50
        elif ctype == "CALIBRATION":
            if "n_pixels" not in params:
                params["n_pixels"] = 1048576
            if "group" not in params:
                params["group"] = 50
        elif ctype == "CENTROIDER":
            if "n_valid_subaps" not in params:
                params["n_valid_subaps"] = 6400
            if "n_pix_per_subap" not in params:
                params["n_pix_per_subap"] = 16
            if "group" not in params:
                params["group"] = 50
        elif ctype == "RECONSTRUCTION":
            if "n_slopes" not in params:
                params["n_slopes"] = 12800
            if "n_acts" not in params:
                params["n_acts"] = 5000
            if "group" not in params:
                params["group"] = 50
        elif ctype == "CONTROL":
            if "n_acts" not in params:
                params["n_acts"] = 5000
        
        # --- Fix: Only save centroid_agenda as a filename and use proper parameter name ---
        if "centroid_agenda" in params:
            if "centroid_agenda_path" in params:
                params["agenda"] = params["centroid_agenda_path"]  # Use "agenda" to match function signature
            elif isinstance(params["centroid_agenda"], str):
                params["agenda"] = params["centroid_agenda"]  # Use "agenda" to match function signature
            
            # Keep centroid_agenda_path for backwards compatibility
            if "centroid_agenda_path" in params:
                params["centroid_agenda_path"] = params["centroid_agenda_path"]
                
            # Remove the old parameter name
            if "centroid_agenda" in params:
                del params["centroid_agenda"]
        
        # Ensure all params are JSON serializable
        for k, v in list(params.items()):
            # Convert ComputeResources or similar objects to dict
            if hasattr(v, 'to_dict') and callable(v.to_dict):
                params[k] = v.to_dict()
        
        comp_data = {
            "type": comp.component_type.name,
            "name": comp.name,
            "pos": (comp.pos().x(), comp.pos().y()),
            "params": params,
            "parent_type": parent_type,
            "parent_name": parent_name,
            "gpu_parent_name": gpu_parent_name
        }
        data["components"].append(comp_data)
        components_by_name[comp.name] = comp
    
    # Get the transfer chain generation logic
    from .code_generator import CodeGenerator
    code_generator = CodeGenerator(components)
    
    # Dictionary to store transfer chains by connection (source->dest)
    connection_transfer_chains = {}
    
    # Process generated transfer components
    generated_transfers = getattr(code_generator, 'generated_transfer_components', [])
    
    # Group transfers by connection
    for transfer in generated_transfers:
        src_comp = transfer.get('src_comp')
        dest_comp = transfer.get('dest_comp')
        
        if src_comp and dest_comp:
            # This is a direct connection transfer
            key = f"{src_comp.name}->{dest_comp.name}"
            if key not in connection_transfer_chains:
                connection_transfer_chains[key] = []
            connection_transfer_chains[key].append(transfer)
        else:
            # This is a transfer in a chain - find which chain it belongs to by dependency
            dependencies = transfer.get('dependencies', [])
            for dep in dependencies:
                # Find if this depends on an existing transfer
                for existing_key, existing_transfers in connection_transfer_chains.items():
                    for existing_transfer in existing_transfers:
                        if existing_transfer.get('name') == dep:
                            # This transfer belongs to this chain
                            connection_transfer_chains[existing_key].append(transfer)
                            break
                    else:
                        continue
                    break
    
    # Sort each chain by dependencies
    for key, chain in connection_transfer_chains.items():
        # Create a dependency graph
        depends_on = {}
        names_to_transfers = {}
        for transfer in chain:
            name = transfer.get('name')
            names_to_transfers[name] = transfer
            depends_on[name] = transfer.get('dependencies', [])
        
        # Topological sort by dependencies
        sorted_transfers = []
        no_deps = [name for name, deps in depends_on.items() 
                   if not deps or all(dep not in names_to_transfers for dep in deps)]
        
        while no_deps:
            name = no_deps.pop(0)
            sorted_transfers.append(name)
            
            # Find transfers that depend on this one
            for dep_name, deps in list(depends_on.items()):
                if name in deps:
                    deps.remove(name)
                    if not deps:
                        no_deps.append(dep_name)
        
        # Add any that couldn't be sorted (should be rare)
        for name in names_to_transfers:
            if name not in sorted_transfers:
                sorted_transfers.append(name)
        
        # Replace with sorted list
        connection_transfer_chains[key] = [names_to_transfers[name] for name in sorted_transfers]
    
    # Save each transfer component
    for chain_key, chain in connection_transfer_chains.items():
        for transfer in chain:
            transfer_name = transfer.get('name')
            
            # Skip if already added
            if any(t["name"] == transfer_name for t in data["transfers"]):
                continue
            
            # Get source and destination component details
            source_comp = transfer.get('src_comp')
            dest_comp = transfer.get('dest_comp')
            source_name = source_comp.name if source_comp else None
            dest_name = dest_comp.name if dest_comp else None
            
            # Create transfer data
            transfer_data = {
                "type": "NETWORK",  # All transfers are network type components
                "name": transfer_name,
                "transfer_type": transfer.get('transfer_type', "Network"),
                "source": source_name,
                "destination": dest_name,
                "data_size": transfer.get('data_size', 1024 * 1024),
                "params": transfer.get('params', {}).copy(),
                "dependencies": transfer.get('dependencies', []),
                # Include compute resources if available
                "compute": None
            }
            
            # Add compute resources if available (copying from source component)
            if source_comp and hasattr(source_comp, 'get_compute_resource'):
                compute_resource = source_comp.get_compute_resource()
                if compute_resource:
                    transfer_data["compute"] = _to_dict_recursive(compute_resource)
            
            data["transfers"].append(transfer_data)
    
    # Save connections with transfer chains
    for conn in connections:
        # Get source and destination components
        src_name = conn.start_block.name
        dest_name = conn.end_block.name
        
        # Check if this connection has an associated transfer chain
        connection_key = f"{src_name}->{dest_name}"
        transfer_chain = []
        
        if connection_key in connection_transfer_chains:
            # Get the transfer chain for this connection
            chain = connection_transfer_chains[connection_key]
            transfer_chain = [transfer["name"] for transfer in chain]
        
        # Save connection data
        conn_data = {
            "start": src_name,
            "end": dest_name,
        }
        
        # Add transfer chain if it exists
        if transfer_chain:
            conn_data["transfers"] = transfer_chain
        
        data["connections"].append(conn_data)
    
    try:
        with open(filename, "w") as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error saving pipeline to {filename}: {str(e)}")
        return False

def load_pipeline(scene, filename, component_counts):
    """
    Load pipeline design from a JSON file.
    
    Args:
        scene: The QGraphicsScene to load the pipeline into
        filename: Path to the JSON file
        component_counts: Dictionary to update with component counts
        
    Returns:
        bool: True if load was successful, False otherwise
    """
    try:
        # Clear existing scene
        scene.clear()
        scene.connections = []
        
        # Load data from file
        with open(filename, "r") as f:
            data = json.load(f)
        
        # Recreate compute and GPU boxes first
        compute_boxes = {}  # Map names to objects
        gpu_boxes = {}      # Map names to objects
        
        # Create compute boxes
        for container in data.get("containers", []):
            if container.get("type") == "ComputeBox":
                name = container.get("name", "Computer")
                pos = container.get("pos", (0, 0))
                size = container.get("size", (320, 220))
                
                # Create compute resource if provided
                compute_resource = None
                if "compute" in container:
                    compute_dict = container["compute"].copy()
                    # Always reconstruct from parameters if present
                    valid_params = {
                        'hardware', 'cores', 'core_frequency', 'flops_per_cycle',
                        'memory_channels', 'memory_width', 'memory_frequency',
                        'network_speed', 'time_in_driver', 'core_fudge', 
                        'mem_fudge', 'network_fudge', 'adjust'
                    }
                    filtered_dict = {k: v for k, v in compute_dict.items() if k in valid_params}
                    try:
                        compute_resource = create_compute_resources(**filtered_dict)
                    except Exception as e:
                        logger.error(f"Error creating compute resource: {str(e)}")
                        compute_resource = amd_epyc_7763()
                
                # Create the compute box
                compute_box = ComputeBox(name, compute=compute_resource)
                compute_box.size = QRectF(0, 0, size[0], size[1])
                compute_box.setPos(pos[0], pos[1])
                scene.addItem(compute_box)
                compute_boxes[name] = compute_box
                
                # Create GPU boxes inside this compute box
                for gpu_data in container.get("gpu_boxes", []):
                    gpu_name = gpu_data.get("name", "GPU")
                    gpu_pos = gpu_data.get("pos", (30, 60))
                    gpu_size = gpu_data.get("size", (200, 140))
                    
                    # Create GPU resource if provided
                    gpu_resource = None
                    if "compute" in gpu_data:
                        gpu_dict = gpu_data["compute"].copy()
                        valid_params = {
                            'hardware', 'cores', 'core_frequency', 'flops_per_cycle',
                            'memory_channels', 'memory_width', 'memory_frequency',
                            'network_speed', 'time_in_driver', 'core_fudge', 
                            'mem_fudge', 'network_fudge', 'adjust'
                        }
                        filtered_dict = {k: v for k, v in gpu_dict.items() if k in valid_params}
                        try:
                            if 'hardware' not in filtered_dict:
                                filtered_dict['hardware'] = 'GPU'
                            gpu_resource = create_compute_resources(**filtered_dict)
                        except Exception as e:
                            logger.error(f"Error creating GPU resource: {str(e)}")
                            gpu_resource = nvidia_rtx_4090()
                    
                    # Create the GPU box
                    gpu_box = GPUBox(gpu_name, gpu_resource=gpu_resource)
                    gpu_box.size = QRectF(0, 0, gpu_size[0], gpu_size[1])
                    gpu_box.setPos(gpu_pos[0], gpu_pos[1])
                    compute_box.add_child(gpu_box)
                    scene.addItem(gpu_box)
                    gpu_boxes[gpu_name] = gpu_box
        
        # Map to keep track of component names to objects
        components = {}
        
        # Create components
        for comp_data in data.get("components", []):
            comp_type_str = comp_data.get("type", "CAMERA")
            try:
                comp_type = ComponentType[comp_type_str]
            except KeyError:
                # Default to camera if type is invalid
                comp_type = ComponentType.CAMERA
            
            name = comp_data.get("name", f"{comp_type.value}1")
            pos = comp_data.get("pos", (0, 0))
            params = comp_data.get("params", {})
            
            # Create component
            component = ComponentBlock(comp_type, name)
            component.params = params
            
            # Find parent container
            parent_type = comp_data.get("parent_type", None)
            parent_name = comp_data.get("parent_name", None)
            gpu_parent_name = comp_data.get("gpu_parent_name", None)
            
            # Add to scene with proper parenting
            if parent_type == "ComputeBox" and parent_name in compute_boxes:
                parent = compute_boxes[parent_name]
                component.setParentItem(parent)
                component.setPos(pos[0], pos[1])
                if hasattr(parent, 'compute'):
                    component.compute = parent.compute
                if hasattr(parent, 'child_items') and component not in parent.child_items:
                    parent.child_items.append(component)
            elif parent_type == "GPUBox" and parent_name in gpu_boxes:
                parent = gpu_boxes[parent_name]
                component.setParentItem(parent)
                component.setPos(pos[0], pos[1])
                if hasattr(parent, 'gpu_resource'):
                    component.compute = parent.gpu_resource
                if hasattr(parent, 'child_items') and component not in parent.child_items:
                    parent.child_items.append(component)
            else:
                # No parent or parent not found
                component.setPos(pos[0], pos[1])
            
            scene.addItem(component)
            components[name] = component
            
            # Update component counts
            try:
                # Extract the numeric part from the component name
                name_without_prefix = name
                prefix = comp_type.value
                if name.startswith(prefix):
                    name_without_prefix = name[len(prefix):]
                
                # Convert to int if possible, otherwise use 0
                comp_number = 0
                if name_without_prefix.isdigit():
                    comp_number = int(name_without_prefix)
                
                # Update the counter
                component_counts[comp_type] = max(
                    component_counts[comp_type],
                    comp_number
                )
            except Exception as e:
                logger.debug(f"Could not update component count from name {name}: {str(e)}")
                # Just increment the count if we can't parse the name
                component_counts[comp_type] += 1
        
        # Create transfer components in the scene first
        # This ensures they exist when connections are created
        for transfer_data in data.get("transfers", []):
            transfer_name = transfer_data.get("name", "Transfer")
            transfer_type_str = transfer_data.get("type", "NETWORK")
            params = transfer_data.get("params", {})
            
            try:
                # Convert type string to ComponentType
                transfer_type = ComponentType[transfer_type_str]
            except KeyError:
                # Default to NETWORK for transfers
                transfer_type = ComponentType.NETWORK
            
            # Create the transfer component
            transfer_comp = ComponentBlock(transfer_type, transfer_name)
            transfer_comp.params = params.copy()
            
            # Store the transfer component type in the params
            if "transfer_type" not in transfer_comp.params:
                # Get from higher level field or default to "Network"
                transfer_comp.params["transfer_type"] = transfer_data.get("transfer_type", "Network").lower()
            
            # Add the transfer component (not shown in the UI)
            transfer_comp._is_synthetic = True  # Mark as synthetic to not display
            components[transfer_name] = transfer_comp
            
            # Add it to the scene but make it invisible
            transfer_comp.setVisible(False)
            scene.addItem(transfer_comp)
            
            logger.debug(f"Created transfer component: {transfer_name}")
        
        # Create connections with proper transfer chains
        connection_map = {}  # Map to store connections for transfer setup
        connections_with_transfer_chains = {}  # Map to store connection->transfers associations
        
        for conn in data.get("connections", []):
            start_name = conn.get("start")
            end_name = conn.get("end")
            transfer_chain = conn.get("transfers", [])
            
            # Store connection transfer chain if present
            if transfer_chain:
                connections_with_transfer_chains[(start_name, end_name)] = transfer_chain
            
            if start_name in components and end_name in components:
                start_block = components[start_name]
                end_block = components[end_name]
                
                # Find appropriate ports
                start_port = start_block.output_ports[0] if start_block.output_ports else None
                end_port = end_block.input_ports[0] if end_block.input_ports else None
                
                if start_port and end_port:
                    # Create connection
                    connection = Connection(start_block, start_port)
                    if connection.complete_connection(end_block, end_port):
                        scene.connections.append(connection)
                        scene.addItem(connection)
                        
                        # Store connection for transfer setup
                        connection_key = f"{start_name}_{end_name}"
                        connection_map[connection_key] = connection
                        
                        # If this connection has a transfer chain, store the information
                        # but don't modify component _dependencies attributes directly
                        if (start_name, end_name) in connections_with_transfer_chains:
                            # We'll use the synthetic _modified_dependencies attribute for code generation
                            chain = connections_with_transfer_chains[(start_name, end_name)]
                            
                            # Store dependency information for later use
                            if len(chain) > 0:
                                # First transfer depends on source
                                first_transfer = components.get(chain[0])
                                if first_transfer and first_transfer != start_block:
                                    # Use _modified_dependencies instead of _dependencies
                                    if not hasattr(first_transfer, '_modified_dependencies'):
                                        first_transfer._modified_dependencies = first_transfer.get_dependencies().copy()
                                    if start_name not in first_transfer._modified_dependencies:
                                        first_transfer._modified_dependencies.append(start_name)
                                
                                # Each subsequent transfer depends on the previous transfer
                                for i in range(1, len(chain)):
                                    prev_transfer = components.get(chain[i-1])
                                    curr_transfer = components.get(chain[i])
                                    if curr_transfer and prev_transfer and curr_transfer != prev_transfer:
                                        if not hasattr(curr_transfer, '_modified_dependencies'):
                                            curr_transfer._modified_dependencies = curr_transfer.get_dependencies().copy()
                                        if chain[i-1] not in curr_transfer._modified_dependencies:
                                            curr_transfer._modified_dependencies.append(chain[i-1])
                                
                                # Destination depends on last transfer
                                if len(chain) > 0:
                                    last_transfer_name = chain[-1]
                                    if end_block:
                                        if not hasattr(end_block, '_modified_dependencies'):
                                            end_block._modified_dependencies = end_block.get_dependencies().copy()
                                        # Replace dependency on source with dependency on last transfer
                                        if start_name in end_block._modified_dependencies:
                                            end_block._modified_dependencies.remove(start_name)
                                        if last_transfer_name not in end_block._modified_dependencies:
                                            end_block._modified_dependencies.append(last_transfer_name)
        
        # If no transfer chain is found but the connection crosses resource boundaries,
        # auto-insert transfer components
        from .code_generator import CodeGenerator
        # Just create the code generator - it will auto-generate transfer components
        CodeGenerator(list(components.values()))
        
        # Final pass: Update connection indicators for all connections
        # This will create visual indicators for each transfer
        for connection in scene.connections:
            update_connection_indicators(scene, connection)
        
        logger.info(f"Pipeline loaded from {filename}")
        return True
    except Exception as e:
        logger.error(f"Error loading pipeline: {str(e)}")
        return False
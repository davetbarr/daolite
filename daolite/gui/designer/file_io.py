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
                compute_dict = item.compute.to_dict().copy()
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
                        gpu_compute_dict = child.compute.to_dict().copy()
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
    
    # Save connections
    for conn in connections:
        # Save basic connection information
        data["connections"].append({
            "start": conn.start_block.name,
            "end": conn.end_block.name,
        })
        
        # Handle camera connections as network
        if conn.start_block.component_type == ComponentType.CAMERA:
            # Camera components always output via network
            logger.debug(f"Detected camera connection from {conn.start_block.name} to {conn.end_block.name}")
            
            # Get destination compute resource details
            dest_comp = conn.end_block
            dest_res = dest_comp.get_compute_resource()
            network_speed = None
            if dest_res:
                network_speed = getattr(dest_res, 'network_speed', 100e9)
            
            # Determine data size based on camera parameters
            n_pixels = conn.start_block.params.get("n_pixels", 1024 * 1024)  # Default 1MP
            bit_depth = conn.start_block.params.get("bit_depth", 16)  # Default 16-bit
            data_size = n_pixels * bit_depth
            
            # Generate a unique name for the transfer component
            transfer_name = f"Network_Transfer_{conn.start_block.name}_to_{conn.end_block.name}"
            
            # Create transfer record
            transfer_data = {
                "type": "NETWORK",
                "name": transfer_name,
                "transfer_type": "Network",
                "source": conn.start_block.name,
                "destination": conn.end_block.name,
                "data_size": data_size,
                "params": {
                    "n_bits": data_size,
                    "transfer_type": "network",
                    "use_dest_network": True
                }
            }
            
            # Add network speed if available
            if network_speed:
                transfer_data["params"]["dest_network_speed"] = network_speed
            
            # Always add network transfers for camera connections
            data["transfers"].append(transfer_data)
            logger.debug(f"Added network transfer for camera: {transfer_name}")
        else:
            # For other components, check compute resources to determine transfer type
            src_comp = conn.start_block
            dest_comp = conn.end_block
            
            # Skip if either component doesn't exist (should never happen)
            if not src_comp or not dest_comp:
                continue
            
            # Get compute resources for source and destination
            src_res = src_comp.get_compute_resource()
            dest_res = dest_comp.get_compute_resource()
            
            # Get parent containers
            src_parent = src_comp.parentItem()
            dest_parent = dest_comp.parentItem()
            
            # Only add transfer if components are in different containers or hardware types
            transfer_type = None
            
            # Different compute boxes always use network
            if (src_parent and dest_parent and 
                src_parent != dest_parent and
                isinstance(src_parent, ComputeBox) and 
                isinstance(dest_parent, ComputeBox)):
                transfer_type = "Network"
            # CPU-GPU transfers use PCIe
            elif ((isinstance(src_parent, GPUBox) and not isinstance(dest_parent, GPUBox)) or
                (not isinstance(src_parent, GPUBox) and isinstance(dest_parent, GPUBox))):
                transfer_type = "PCIe"
            # Check hardware type
            elif src_res and dest_res:
                src_hw = getattr(src_res, 'hardware', 'CPU')
                dest_hw = getattr(dest_res, 'hardware', 'CPU')
                if src_hw != dest_hw:
                    if 'GPU' in (src_hw, dest_hw):
                        transfer_type = "PCIe"
                    else:
                        transfer_type = "Network"
            
            # If we've identified a transfer type, add it to the transfers list
            if transfer_type:
                # Generate a unique name
                transfer_name = f"{transfer_type}_Transfer_{src_comp.name}_to_{dest_comp.name}"
                
                # Estimate data size
                data_size = estimate_data_size(src_comp, dest_comp)
                
                # Create transfer record
                transfer_data = {
                    "type": "NETWORK",
                    "name": transfer_name,
                    "transfer_type": transfer_type,
                    "source": src_comp.name,
                    "destination": dest_comp.name,
                    "data_size": data_size,
                    "params": {
                        "n_bits": data_size,
                        "transfer_type": transfer_type.lower(),
                        "group": 50  # Default group size
                    }
                }
                
                # Add network-specific parameters
                if transfer_type == "Network":
                    # For network transfers, add destination network speed
                    if dest_res:
                        network_speed = getattr(dest_res, 'network_speed', 100e9)
                        transfer_data["params"]["dest_network_speed"] = network_speed
                        transfer_data["params"]["use_dest_network"] = True
                        transfer_data["params"]["dest_time_in_driver"] = getattr(dest_res, 'time_in_driver', 5)
                
                data["transfers"].append(transfer_data)
                logger.debug(f"Added {transfer_type} transfer: {transfer_name}")
    
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
        
        # Create connections
        connection_map = {}  # Map to store connections for transfer setup
        for conn in data.get("connections", []):
            start_name = conn.get("start")
            end_name = conn.get("end")
            
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
        
        # Process transfer information and add indicators
        for transfer in data.get("transfers", []):
            source_name = transfer.get("source")
            dest_name = transfer.get("destination")
            transfer_type = transfer.get("transfer_type")
            
            if source_name and dest_name:
                # Find the connection this transfer is associated with
                connection_key = f"{source_name}_{dest_name}"
                connection = connection_map.get(connection_key)
                
                if connection:
                    # Update connection indicators for this connection
                    logger.debug(f"Creating {transfer_type} transfer indicator for {source_name} → {dest_name}")
                    update_connection_indicators(scene, connection)
        
        logger.info(f"Pipeline loaded from {filename}")
        return True
    except Exception as e:
        logger.error(f"Error loading pipeline: {str(e)}")
        return False
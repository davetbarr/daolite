"""
Connection management utilities for the pipeline designer.

This module handles connection indicators and connection-related operations
between components in different compute resources.
"""

import logging
from PyQt5.QtCore import QPointF, QLineF
from daolite.common import ComponentType

from .component_container import GPUBox, ComputeBox
from .connection import TransferIndicator
from .data_transfer import determine_transfer_type, determine_transfer_chain

# Set up logging
logger = logging.getLogger('ConnectionManager')

def update_connection_indicators(scene, connection):
    """
    Update or create transfer indicators for a connection that crosses resource boundaries.
    
    Args:
        scene: The graphics scene containing the connection
        connection: The connection to update indicators for
    """
    # Remove any existing indicators for this connection
    for item in scene.items():
        if isinstance(item, TransferIndicator) and hasattr(item, 'connection') and item.connection == connection:
            logger.debug(f"Removing existing transfer indicator for connection")
            scene.removeItem(item)
    
    # Create new indicators based on source and destination resources
    src_block = connection.start_block
    dst_block = connection.end_block
    src_compute = src_block.get_compute_resource()
    dst_compute = dst_block.get_compute_resource()
    
    if not hasattr(connection, 'start_port') or not hasattr(connection, 'end_port'):
        logger.warning("Connection missing start_port or end_port attributes")
        return
    
    if not connection.start_port or not connection.end_port:
        logger.warning("Connection has null start_port or end_port")
        return
    
    # Get transfer chain to determine needed indicators
    transfer_chain = determine_transfer_chain(src_block, dst_block)
    
    # Early exit for local transfers (no indicators needed)
    if not transfer_chain:
        logger.debug(f"No transfer indicators needed for local transfer between {src_block.name} and {dst_block.name}")
        return
    
    logger.debug(f"Transfer chain between {src_block.name} and {dst_block.name}: {transfer_chain}")
    
    # Helper function to determine if a component runs on a GPU
    def is_gpu(comp, res):
        # Check hardware field
        if res and getattr(res, 'hardware', '').lower() == 'gpu':
            return True
        # Check parent container type
        parent = comp.parentItem() if hasattr(comp, 'parentItem') else None
        if parent and isinstance(parent, GPUBox):
            return True
        # Check if the parent name contains 'gpu' (case insensitive)
        if parent and hasattr(parent, 'name') and parent.name and 'gpu' in parent.name.lower():
            return True
        # Special handling for AMD MI series which are GPUs
        if parent and hasattr(parent, 'name') and parent.name and 'mi' in parent.name.lower() and 'amd' in parent.name.lower():
            return True
        return False
    
    # Helper to get parent ComputeBox - returns None if not found
    def get_compute_box(comp):
        parent = comp.parentItem() if hasattr(comp, 'parentItem') else None
        if parent and isinstance(parent, ComputeBox):
            return parent
        if parent and isinstance(parent, GPUBox):
            grandparent = parent.parentItem() if hasattr(parent, 'parentItem') else None
            if grandparent and isinstance(grandparent, ComputeBox):
                return grandparent
        return None
    
    # --- NEW: Robust boundary intersection ---
    def find_boundary_intersection(start_pos, end_pos, container):
        """Return the intersection point of the line (start_pos, end_pos) with the container's bounding rect, or None."""
        if not container:
            return None
        rect = container.mapToScene(container.boundingRect()).boundingRect()
        line = QLineF(start_pos, end_pos)
        candidates = []
        # Top
        top = QLineF(rect.topLeft(), rect.topRight())
        pt = QPointF()
        if line.intersect(top, pt) == QLineF.BoundedIntersection:
            candidates.append(QPointF(pt))
        # Right
        right = QLineF(rect.topRight(), rect.bottomRight())
        pt = QPointF()
        if line.intersect(right, pt) == QLineF.BoundedIntersection:
            candidates.append(QPointF(pt))
        # Bottom
        bottom = QLineF(rect.bottomLeft(), rect.bottomRight())
        pt = QPointF()
        if line.intersect(bottom, pt) == QLineF.BoundedIntersection:
            candidates.append(QPointF(pt))
        # Left
        left = QLineF(rect.topLeft(), rect.bottomLeft())
        pt = QPointF()
        if line.intersect(left, pt) == QLineF.BoundedIntersection:
            candidates.append(QPointF(pt))
        if not candidates:
            return None
        # Return the intersection closest to end_pos (for outgoing), or start_pos (for incoming)
        return min(candidates, key=lambda p: QLineF(p, end_pos).length())

    # --- NEW: Minimal indicator position logic ---
    def calculate_indicator_position(point, line, indicator_type):
        """Return the position for the indicator: exactly at the point, or fallback along the line."""
        # No offset by default; can add a small offset if needed for clarity
        return QPointF(point)
    
    # Get connection endpoints in scene coordinates
    start_pos = connection.start_port.get_scene_position()
    end_pos = connection.end_port.get_scene_position()
    connection_line = QLineF(start_pos, end_pos)
    
    # Get source and destination parent containers
    src_parent = src_block.parentItem()
    dst_parent = dst_block.parentItem()
    
    # Check container types directly
    src_is_gpu_container = isinstance(src_parent, GPUBox)
    dst_is_gpu_container = isinstance(dst_parent, GPUBox)
    
    # Determine component types and locations
    src_is_gpu = is_gpu(src_block, src_compute)
    dst_is_gpu = is_gpu(dst_block, dst_compute)
    src_compute_box = get_compute_box(src_block)
    dst_compute_box = get_compute_box(dst_block)
    different_computers = src_compute_box and dst_compute_box and src_compute_box != dst_compute_box
    
    # Log containers with their actual types
    src_container_name = getattr(src_parent, 'name', 'None') if src_parent else 'None'
    dst_container_name = getattr(dst_parent, 'name', 'None') if dst_parent else 'None'
    src_container_type = "GPU" if src_is_gpu_container else "CPU"
    dst_container_type = "GPU" if dst_is_gpu_container else "CPU"
    logger.debug(f"Connection container path: {src_container_name}({src_container_type}) → {dst_container_name}({dst_container_type})")
    
    # Check if source is a camera component
    is_camera_connection = src_block.component_type == ComponentType.CAMERA
    if is_camera_connection:
        logger.debug(f"Camera connection detected: {src_block.name} → {dst_block.name}")
        
    # Check if destination is a DM component (new special case)
    is_dm_connection = dst_block.component_type == ComponentType.DM
    if is_dm_connection:
        logger.debug(f"DM connection detected: {src_block.name} → {dst_block.name}")
    
    # Create appropriate transfer indicators based on the container types and component types
    transfer_indicators = []
    
    # SPECIAL CASE: Always add Network indicator for DM components receiving from any compute
    if is_dm_connection and src_parent:
        logger.debug(f"Adding Network transfer indicator for connection to DM")
        
        # Find intersection with source compute box boundary
        src_compute_boundary = None
        
        # First try to find the compute box
        if src_compute_box:
            src_compute_boundary = find_boundary_intersection(start_pos, end_pos, src_compute_box)
        
        # Place on the compute box boundary if found
        if src_compute_boundary:
            logger.debug(f"Network transfer indicator added for DM at source compute box boundary: {src_compute_boundary.x():.1f}, {src_compute_boundary.y():.1f}")
            indicator = TransferIndicator("Network")
            indicator_pos = calculate_indicator_position(src_compute_boundary, connection_line, "Network")
            indicator.setPos(indicator_pos)
            indicator.set_connection(connection)
            transfer_indicators.append(indicator)
        else:
            # If no intersection found, place indicator at 2/3 along the connection line
            point = connection_line.pointAt(2/3)
            logger.debug(f"Placing Network indicator along line for DM connection at {point.x():.1f}, {point.y():.1f}")
            indicator = TransferIndicator("Network")
            
            # Use the helper function for better positioning
            indicator_pos = calculate_indicator_position(point, connection_line, "Network")
            indicator.setPos(indicator_pos)
            indicator.set_connection(connection)
            transfer_indicators.append(indicator)
        
        # If source is GPU, also add PCIe indicator
        src_is_gpu_container = isinstance(src_parent, GPUBox)
        
        # More robust check for GPU source
        is_source_gpu = src_is_gpu or src_is_gpu_container
        
        # Additional check for GPU indicators in container name
        if not is_source_gpu and src_parent and hasattr(src_parent, 'name'):
            parent_name = src_parent.name.lower() if src_parent.name else ""
            if ('gpu' in parent_name or 'mi' in parent_name or 'rtx' in parent_name or 
                'a100' in parent_name or 'h100' in parent_name):
                is_source_gpu = True
                logger.debug(f"Detected GPU source from container name: {src_parent.name}")

        # Explicitly log GPU detection status
        logger.debug(f"Source GPU detection: src_is_gpu={src_is_gpu}, src_is_gpu_container={src_is_gpu_container}, final determination={is_source_gpu}")
        
        if is_source_gpu:
            logger.debug(f"Adding PCIe indicator for GPU source to DM connection: {src_block.name}")
            # First try to find GPU container
            gpu_container = None
            if isinstance(src_parent, GPUBox):
                gpu_container = src_parent
                logger.debug(f"Found GPU container: {gpu_container.name if hasattr(gpu_container, 'name') else 'unnamed'}")
            
            # If we found a GPU container, place at its boundary
            if gpu_container:
                gpu_boundary = find_boundary_intersection(start_pos, end_pos, gpu_container)
                if gpu_boundary:
                    logger.debug(f"PCIe transfer indicator added for GPU->DM at GPU boundary: {gpu_boundary.x():.1f}, {gpu_boundary.y():.1f}")
                    indicator = TransferIndicator("PCIe")
                    indicator_pos = calculate_indicator_position(gpu_boundary, connection_line, "PCIe")
                    indicator.setPos(indicator_pos)
                    indicator.set_connection(connection)
                    transfer_indicators.append(indicator)
                else:
                    # Fallback: place PCIe indicator at 1/3 along the connection line
                    point = connection_line.pointAt(1/3)
                    logger.debug(f"Placing PCIe indicator along line for GPU->DM (no boundary) at {point.x():.1f}, {point.y():.1f}")
                    indicator = TransferIndicator("PCIe")
                    
                    # Use the helper function for better positioning
                    indicator_pos = calculate_indicator_position(point, connection_line, "PCIe")
                    indicator.setPos(indicator_pos)
                    indicator.set_connection(connection)
                    transfer_indicators.append(indicator)
            else:
                # No GPU container found, but source is a GPU resource
                # Place at 1/3 along the connection line
                point = connection_line.pointAt(1/3)
                logger.debug(f"Placing PCIe indicator along line for GPU->DM (no GPU container) at {point.x():.1f}, {point.y():.1f}")
                indicator = TransferIndicator("PCIe")
                
                # Use the helper function for better positioning
                indicator_pos = calculate_indicator_position(point, connection_line, "PCIe")
                indicator.setPos(indicator_pos)
                indicator.set_connection(connection)
                transfer_indicators.append(indicator)
                logger.debug(f"Added PCIe indicator for GPU source without container")
        else:
            logger.debug(f"No PCIe indicator needed - source is not GPU: {src_block.name}")
    
    # SPECIAL CASE: Always add Network indicator for camera components connecting to any compute
    elif is_camera_connection and dst_parent:
        logger.debug(f"Adding Network transfer indicator for camera connection to compute")
        
        # Find intersection with destination compute box boundary
        dst_compute_boundary = None
        
        # First try to find the compute box itself
        if dst_compute_box:
            dst_compute_boundary = find_boundary_intersection(start_pos, end_pos, dst_compute_box)
        
        # Place on the compute box boundary if found
        if dst_compute_boundary:
            logger.debug(f"Network transfer indicator added for camera at destination compute box boundary: {dst_compute_boundary.x():.1f}, {dst_compute_boundary.y():.1f}")
            indicator = TransferIndicator("Network")
            indicator_pos = calculate_indicator_position(dst_compute_boundary, connection_line, "Network")
            indicator.setPos(indicator_pos)
            indicator.set_connection(connection)
            transfer_indicators.append(indicator)
        else:
            # If no intersection found, place indicator at 1/3 along the connection line - offset from connection
            point = connection_line.pointAt(1/3)
            logger.debug(f"Placing Network indicator along line for camera connection at {point.x():.1f}, {point.y():.1f}")
            indicator = TransferIndicator("Network")
            
            # Use the helper function for better positioning
            indicator_pos = calculate_indicator_position(point, connection_line, "Network")
            indicator.setPos(indicator_pos)
            indicator.set_connection(connection)
            transfer_indicators.append(indicator)
        
        # If destination is GPU, also add PCIe indicator
        # FIXED: Enhanced GPU detection for destination to check multiple conditions
        dst_is_gpu_container = isinstance(dst_parent, GPUBox)
        
        # More robust check for GPU destination - check all possible ways it could be a GPU
        is_dest_gpu = dst_is_gpu or dst_is_gpu_container
        
        # Additional check for GPU indicators in container name
        if not is_dest_gpu and dst_parent and hasattr(dst_parent, 'name'):
            parent_name = dst_parent.name.lower() if dst_parent.name else ""
            if ('gpu' in parent_name or 'mi' in parent_name or 'rtx' in parent_name or 
                'a100' in parent_name or 'h100' in parent_name):
                is_dest_gpu = True
                logger.debug(f"Detected GPU destination from container name: {dst_parent.name}")

        # Explicitly log GPU detection status
        logger.debug(f"Destination GPU detection: dst_is_gpu={dst_is_gpu}, dst_is_gpu_container={dst_is_gpu_container}, final determination={is_dest_gpu}")
        
        if is_dest_gpu:
            logger.debug(f"Adding PCIe indicator for camera connection to GPU destination: {dst_block.name}")
            # First try to find GPU container
            gpu_container = None
            if isinstance(dst_parent, GPUBox):
                gpu_container = dst_parent
                logger.debug(f"Found GPU container: {gpu_container.name if hasattr(gpu_container, 'name') else 'unnamed'}")
            
            # Check for nested GPU (component inside GPUBox inside ComputeBox)
            elif dst_compute_box and any(isinstance(child, GPUBox) for child in dst_compute_box.childItems()):
                for child in dst_compute_box.childItems():
                    if isinstance(child, GPUBox):
                        if dst_block in child.childItems():
                            gpu_container = child
                            logger.debug(f"Found nested GPU container: {gpu_container.name if hasattr(gpu_container, 'name') else 'unnamed'}")
                            break
            
            # If we found a GPU container, place at its boundary
            if gpu_container:
                gpu_boundary = find_boundary_intersection(end_pos, start_pos, gpu_container)
                if gpu_boundary:
                    logger.debug(f"PCIe transfer indicator added for camera->GPU at GPU boundary: {gpu_boundary.x():.1f}, {gpu_boundary.y():.1f}")
                    indicator = TransferIndicator("PCIe")
                    indicator_pos = calculate_indicator_position(gpu_boundary, connection_line, "PCIe")
                    indicator.setPos(indicator_pos)
                    indicator.set_connection(connection)
                    transfer_indicators.append(indicator)
                else:
                    # Fallback: place PCIe indicator at 2/3 along the connection line
                    point = connection_line.pointAt(2/3)
                    logger.debug(f"Placing PCIe indicator along line for camera->GPU (no boundary) at {point.x():.1f}, {point.y():.1f}")
                    indicator = TransferIndicator("PCIe")
                    
                    # Use the helper function for better positioning
                    indicator_pos = calculate_indicator_position(point, connection_line, "PCIe")
                    indicator.setPos(indicator_pos)
                    indicator.set_connection(connection)
                    transfer_indicators.append(indicator)
            else:
                # IMPROVED FALLBACK: No GPU container found, but destination is a GPU resource
                # Place at 2/3 along the connection line with prominent offset to make it visible
                point = connection_line.pointAt(2/3)
                logger.debug(f"Placing PCIe indicator along line for camera->GPU (no GPU container) at {point.x():.1f}, {point.y():.1f}")
                indicator = TransferIndicator("PCIe")
                
                # Use the helper function for better positioning
                indicator_pos = calculate_indicator_position(point, connection_line, "PCIe")
                indicator.setPos(indicator_pos)
                indicator.set_connection(connection)
                transfer_indicators.append(indicator)
                logger.debug(f"Added PCIe indicator for GPU destination without container")
        else:
            logger.debug(f"No PCIe indicator needed - destination is not GPU: {dst_block.name}")
    
    # GPU → GPU (different computers)
    elif src_is_gpu and dst_is_gpu and different_computers:
        # Chain: PCIe (GPU1→host) → Network (host1→host2) → PCIe (host2→GPU2)
        
        # 1. PCIe from GPU1 to host1
        if src_is_gpu_container:
            # Find the exact boundary intersection with the GPU box
            src_gpu_boundary = find_boundary_intersection(start_pos, end_pos, src_parent)
            if src_gpu_boundary:
                logger.debug(f"PCIe transfer indicator added at source GPU boundary: {src_gpu_boundary.x():.1f}, {src_gpu_boundary.y():.1f}")
                indicator = TransferIndicator("PCIe")
                indicator_pos = calculate_indicator_position(src_gpu_boundary, connection_line, "PCIe")
                indicator.setPos(indicator_pos)
                indicator.set_connection(connection)
                transfer_indicators.append(indicator)
            else:
                # Fallback: place at 1/6 along the line
                point = connection_line.pointAt(1/6)
                indicator = TransferIndicator("PCIe")
                indicator_pos = calculate_indicator_position(point, connection_line, "PCIe")
                indicator.setPos(indicator_pos)
                indicator.set_connection(connection)
                transfer_indicators.append(indicator)
        
        # 2. Network from host1 to host2
        # Find boundaries of both compute boxes
        src_comp_boundary = find_boundary_intersection(start_pos, end_pos, src_compute_box) 
        dst_comp_boundary = find_boundary_intersection(end_pos, start_pos, dst_compute_box)
        
        # Place network indicator at either boundary intersection or midpoint 
        if src_comp_boundary and dst_comp_boundary:
            # Place at midpoint between the two computer boundaries
            midpoint = QPointF((src_comp_boundary.x() + dst_comp_boundary.x()) / 2,
                            (src_comp_boundary.y() + dst_comp_boundary.y()) / 2)
            logger.debug(f"Network transfer indicator added at midpoint between compute boxes: {midpoint.x():.1f}, {midpoint.y():.1f}")
            indicator = TransferIndicator("Network")
            indicator_pos = calculate_indicator_position(midpoint, connection_line, "Network")
            indicator.setPos(indicator_pos)
            indicator.set_connection(connection)
            transfer_indicators.append(indicator)
        elif src_comp_boundary:
            # Place at source compute box boundary
            logger.debug(f"Network transfer indicator added at source compute boundary: {src_comp_boundary.x():.1f}, {src_comp_boundary.y():.1f}")
            indicator = TransferIndicator("Network")
            indicator_pos = calculate_indicator_position(src_comp_boundary, connection_line, "Network")
            indicator.setPos(indicator_pos)
            indicator.set_connection(connection)
            transfer_indicators.append(indicator)
        elif dst_comp_boundary:
            # Place at destination compute box boundary
            logger.debug(f"Network transfer indicator added at destination compute boundary: {dst_comp_boundary.x():.1f}, {dst_comp_boundary.y():.1f}")
            indicator = TransferIndicator("Network")
            indicator_pos = calculate_indicator_position(dst_comp_boundary, connection_line, "Network")
            indicator.setPos(indicator_pos)
            indicator.set_connection(connection)
            transfer_indicators.append(indicator)
        else:
            # Fallback: place at 1/2 along the line
            point = connection_line.pointAt(0.5)
            indicator = TransferIndicator("Network")
            indicator_pos = calculate_indicator_position(point, connection_line, "Network")
            indicator.setPos(indicator_pos)
            indicator.set_connection(connection)
            transfer_indicators.append(indicator)
        
        # 3. PCIe from host2 to GPU2
        if dst_is_gpu_container:
            dst_gpu_boundary = find_boundary_intersection(end_pos, start_pos, dst_parent)
            if dst_gpu_boundary:
                logger.debug(f"PCIe transfer indicator added at dest GPU boundary: {dst_gpu_boundary.x():.1f}, {dst_gpu_boundary.y():.1f}")
                indicator = TransferIndicator("PCIe")
                indicator_pos = calculate_indicator_position(dst_gpu_boundary, connection_line, "PCIe")
                indicator.setPos(indicator_pos)
                indicator.set_connection(connection)
                transfer_indicators.append(indicator)
            else:
                # Fallback: place at 5/6 along the line
                point = connection_line.pointAt(5/6) 
                indicator = TransferIndicator("PCIe")
                indicator_pos = calculate_indicator_position(point, connection_line, "PCIe")
                indicator.setPos(indicator_pos)
                indicator.set_connection(connection)
                transfer_indicators.append(indicator)
                
    # GPU → CPU (different computers)
    elif src_is_gpu and not dst_is_gpu and different_computers:
        # Chain: PCIe (GPU→host) → Network (host→host)
        
        # 1. PCIe from GPU to host
        if src_is_gpu_container:
            src_gpu_boundary = find_boundary_intersection(start_pos, end_pos, src_parent)
            if src_gpu_boundary:
                logger.debug(f"PCIe transfer indicator added at source GPU boundary: {src_gpu_boundary.x():.1f}, {src_gpu_boundary.y():.1f}")
                indicator = TransferIndicator("PCIe")
                indicator_pos = calculate_indicator_position(src_gpu_boundary, connection_line, "PCIe")
                indicator.setPos(indicator_pos)
                indicator.set_connection(connection)
                transfer_indicators.append(indicator)
            else:
                # Fallback: place at 1/3 along the line
                point = connection_line.pointAt(1/3)
                indicator = TransferIndicator("PCIe")
                indicator_pos = calculate_indicator_position(point, connection_line, "PCIe")
                indicator.setPos(indicator_pos)
                indicator.set_connection(connection)
                transfer_indicators.append(indicator)
        
        # 2. Network from host1 to host2
        # Find intersection with compute box boundaries
        src_comp_boundary = find_boundary_intersection(start_pos, end_pos, src_compute_box)
        dst_comp_boundary = find_boundary_intersection(end_pos, start_pos, dst_compute_box)
        
        # Place network indicator at either boundary intersection or midpoint
        if src_comp_boundary and dst_comp_boundary:
            # Place at midpoint between the two computer boundaries
            midpoint = QPointF((src_comp_boundary.x() + dst_comp_boundary.x()) / 2,
                            (src_comp_boundary.y() + dst_comp_boundary.y()) / 2)
            logger.debug(f"Network transfer indicator added at midpoint between compute boxes: {midpoint.x():.1f}, {midpoint.y():.1f}")
            indicator = TransferIndicator("Network")
            indicator_pos = calculate_indicator_position(midpoint, connection_line, "Network")
            indicator.setPos(indicator_pos)
            indicator.set_connection(connection)
            transfer_indicators.append(indicator)
        elif src_comp_boundary:
            # Place at source compute box boundary
            logger.debug(f"Network transfer indicator added at source compute boundary: {src_comp_boundary.x():.1f}, {src_comp_boundary.y():.1f}")
            indicator = TransferIndicator("Network") 
            indicator_pos = calculate_indicator_position(src_comp_boundary, connection_line, "Network")
            indicator.setPos(indicator_pos)
            indicator.set_connection(connection)
            transfer_indicators.append(indicator)
        elif dst_comp_boundary:
            # Place at destination compute box boundary
            logger.debug(f"Network transfer indicator added at destination compute boundary: {dst_comp_boundary.x():.1f}, {dst_comp_boundary.y():.1f}")
            indicator = TransferIndicator("Network")
            indicator_pos = calculate_indicator_position(dst_comp_boundary, connection_line, "Network")
            indicator.setPos(indicator_pos)
            indicator.set_connection(connection)
            transfer_indicators.append(indicator)
        else:
            # Fallback: place at 2/3 along the line
            point = connection_line.pointAt(2/3)
            indicator = TransferIndicator("Network")
            indicator_pos = calculate_indicator_position(point, connection_line, "Network")
            indicator.setPos(indicator_pos)
            indicator.set_connection(connection)
            transfer_indicators.append(indicator)
            
    # CPU → GPU (different computers)
    elif not src_is_gpu and dst_is_gpu and different_computers:
        # Chain: Network (host→host) → PCIe (host→GPU)
        
        # 1. Network from host1 to host2
        src_comp_boundary = find_boundary_intersection(start_pos, end_pos, src_compute_box)
        dst_comp_boundary = find_boundary_intersection(end_pos, start_pos, dst_compute_box)
        
        # Place network indicator at either boundary intersection or midpoint
        if src_comp_boundary and dst_comp_boundary:
            # Place at midpoint between the two computer boundaries
            midpoint = QPointF((src_comp_boundary.x() + dst_comp_boundary.x()) / 2,
                            (src_comp_boundary.y() + dst_comp_boundary.y()) / 2)
            logger.debug(f"Network transfer indicator added at midpoint between compute boxes: {midpoint.x():.1f}, {midpoint.y():.1f}")
            indicator = TransferIndicator("Network")
            indicator_pos = calculate_indicator_position(midpoint, connection_line, "Network")
            indicator.setPos(indicator_pos)
            indicator.set_connection(connection)
            transfer_indicators.append(indicator)
        elif src_comp_boundary:
            # Place at source compute box boundary
            logger.debug(f"Network transfer indicator added at source compute boundary: {src_comp_boundary.x():.1f}, {src_comp_boundary.y():.1f}")
            indicator = TransferIndicator("Network")
            indicator_pos = calculate_indicator_position(src_comp_boundary, connection_line, "Network")
            indicator.setPos(indicator_pos)
            indicator.set_connection(connection)
            transfer_indicators.append(indicator)
        elif dst_comp_boundary:
            # Place at destination compute box boundary
            logger.debug(f"Network transfer indicator added at destination compute boundary: {dst_comp_boundary.x():.1f}, {dst_comp_boundary.y():.1f}")
            indicator = TransferIndicator("Network")
            indicator_pos = calculate_indicator_position(dst_comp_boundary, connection_line, "Network")
            indicator.setPos(indicator_pos)
            indicator.set_connection(connection)
            transfer_indicators.append(indicator)
        else:
            # Fallback: place at 1/3 along the line
            point = connection_line.pointAt(1/3)
            indicator = TransferIndicator("Network")
            indicator_pos = calculate_indicator_position(point, connection_line, "Network")
            indicator.setPos(indicator_pos)
            indicator.set_connection(connection)
            transfer_indicators.append(indicator)
            
        # 2. PCIe from host2 to GPU
        if dst_is_gpu_container:
            dst_gpu_boundary = find_boundary_intersection(end_pos, start_pos, dst_parent)
            if dst_gpu_boundary:
                logger.debug(f"PCIe transfer indicator added at dest GPU boundary: {dst_gpu_boundary.x():.1f}, {dst_gpu_boundary.y():.1f}")
                indicator = TransferIndicator("PCIe")
                indicator_pos = calculate_indicator_position(dst_gpu_boundary, connection_line, "PCIe")
                indicator.setPos(indicator_pos)
                indicator.set_connection(connection)
                transfer_indicators.append(indicator)
            else:
                # Fallback: place at 2/3 along the line
                point = connection_line.pointAt(2/3)
                indicator = TransferIndicator("PCIe")
                indicator_pos = calculate_indicator_position(point, connection_line, "PCIe")
                indicator.setPos(indicator_pos)
                indicator.set_connection(connection)
                transfer_indicators.append(indicator)
                
    # CPU → CPU (different computers)
    elif not src_is_gpu and not dst_is_gpu and different_computers:
        # Chain: Network (host→host)
        src_comp_boundary = find_boundary_intersection(start_pos, end_pos, src_compute_box)
        dst_comp_boundary = find_boundary_intersection(end_pos, start_pos, dst_compute_box)
        
        # Place network indicator at either boundary intersection or midpoint
        if src_comp_boundary and dst_comp_boundary:
            # Place at midpoint between the two computer boundaries
            midpoint = QPointF((src_comp_boundary.x() + dst_comp_boundary.x()) / 2,
                            (src_comp_boundary.y() + dst_comp_boundary.y()) / 2)
            logger.debug(f"Network transfer indicator added at midpoint between compute boxes: {midpoint.x():.1f}, {midpoint.y():.1f}")
            indicator = TransferIndicator("Network")
            indicator_pos = calculate_indicator_position(midpoint, connection_line, "Network")
            indicator.setPos(indicator_pos)
            indicator.set_connection(connection)
            transfer_indicators.append(indicator)
        elif src_comp_boundary:
            # Place at source compute box boundary
            logger.debug(f"Network transfer indicator added at source compute boundary: {src_comp_boundary.x():.1f}, {src_comp_boundary.y():.1f}")
            indicator = TransferIndicator("Network")
            indicator_pos = calculate_indicator_position(src_comp_boundary, connection_line, "Network")
            indicator.setPos(indicator_pos)
            indicator.set_connection(connection)
            transfer_indicators.append(indicator)
        elif dst_comp_boundary:
            # Place at destination compute box boundary
            logger.debug(f"Network transfer indicator added at destination compute boundary: {dst_comp_boundary.x():.1f}, {dst_comp_boundary.y():.1f}")
            indicator = TransferIndicator("Network")
            indicator_pos = calculate_indicator_position(dst_comp_boundary, connection_line, "Network")
            indicator.setPos(indicator_pos)
            indicator.set_connection(connection)
            transfer_indicators.append(indicator)
        else:
            # Fallback: place at midpoint of the line
            point = connection_line.pointAt(0.5)
            indicator = TransferIndicator("Network")
            indicator_pos = calculate_indicator_position(point, connection_line, "Network")
            indicator.setPos(indicator_pos)
            indicator.set_connection(connection)
            transfer_indicators.append(indicator)
            
    # CPU ↔ GPU (same computer) - Check based on container types
    elif ((src_is_gpu_container and not dst_is_gpu_container) or
         (not src_is_gpu_container and dst_is_gpu_container)):
        
        logger.debug(f"Adding PCIe transfer indicator for CPU-GPU container connection")
        
        # Find GPU container
        gpu_container = src_parent if src_is_gpu_container else dst_parent
        
        # Find intersection with GPU container boundary
        if gpu_container:
            # Determine which direction we're going
            start = start_pos if src_is_gpu_container else end_pos
            end = end_pos if src_is_gpu_container else start_pos
            
            # Get the intersection point with the GPU box boundary
            gpu_boundary = find_boundary_intersection(start, end, gpu_container)
            if gpu_boundary:
                logger.debug(f"PCIe transfer indicator added at GPU box boundary: {gpu_boundary.x():.1f}, {gpu_boundary.y():.1f}")
                indicator = TransferIndicator("PCIe")
                indicator_pos = calculate_indicator_position(gpu_boundary, connection_line, "PCIe")
                indicator.setPos(indicator_pos)
                indicator.set_connection(connection)
                transfer_indicators.append(indicator)
            else:
                # Fallback: place at midpoint of the line
                point = connection_line.pointAt(0.5)
                indicator = TransferIndicator("PCIe")
                indicator_pos = calculate_indicator_position(point, connection_line, "PCIe")
                indicator.setPos(indicator_pos)
                indicator.set_connection(connection)
                transfer_indicators.append(indicator)
                logger.debug(f"Failed to find GPU boundary intersection, placed PCIe at midpoint instead")
        else:
            # Traditional CPU-GPU transfer based on hardware type 
            if (src_compute and dst_compute and 
                    ((getattr(src_compute, 'hardware', 'CPU') == 'CPU' and 
                    getattr(dst_compute, 'hardware', 'CPU') == 'GPU') or 
                    (getattr(src_compute, 'hardware', 'CPU') == 'GPU' and 
                    getattr(dst_compute, 'hardware', 'CPU') == 'CPU'))):
                
                # No container found, place at midpoint
                logger.debug(f"Adding PCIe transfer indicator at midpoint (no containers)")
                point = connection_line.pointAt(0.5)
                indicator = TransferIndicator("PCIe")
                indicator_pos = calculate_indicator_position(point, connection_line, "PCIe")
                indicator.setPos(indicator_pos)
                indicator.set_connection(connection)
                transfer_indicators.append(indicator)
    
    # GPU -> GPU on same GPU (add a GPU-Local indicator)
    elif src_is_gpu and dst_is_gpu and not different_computers and "GPU-Local" in transfer_chain:
        logger.debug(f"Adding GPU-Local transfer indicator for GPU-to-GPU connection on same GPU")
        
        # Place at midpoint of the line
        point = connection_line.pointAt(0.5)
        indicator = TransferIndicator("GPU-Local")
        indicator_pos = calculate_indicator_position(point, connection_line, "GPU-Local")
        indicator.setPos(indicator_pos)
        indicator.set_connection(connection)
        transfer_indicators.append(indicator)
    
    # Local CPU-to-CPU on same computer - no indicator needed
    elif not transfer_chain or (len(transfer_chain) == 1 and transfer_chain[0] == "Local"):
        logger.debug(f"No transfer indicator needed for local RAM transfer between {src_block.name} and {dst_block.name}")
        return
    
    # Add all the indicators to the scene
    for indicator in transfer_indicators:
        scene.addItem(indicator)
        logger.debug(f"Added {indicator.transfer_type} indicator to scene")
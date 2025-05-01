"""
Connection management utilities for the pipeline designer.

This module handles connection indicators and connection-related operations
between components in different compute resources.
"""

import logging
from PyQt5.QtCore import QPointF
from daolite.common import ComponentType

from .components import GPUBox, ComputeBox, TransferIndicator

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
    
    # Get source and destination parent containers
    src_parent = src_block.parentItem()
    dst_parent = dst_block.parentItem()
    
    # Check container types directly
    src_is_gpu_container = isinstance(src_parent, GPUBox)
    dst_is_gpu_container = isinstance(dst_parent, GPUBox)
    
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
    
    # Create appropriate transfer indicators based on the container types
    transfer_indicators = []
    
    # Helper function to find intersection of a line with a container boundary
    def find_boundary_intersection(start_pos, end_pos, container):
        if not container:
            return None
            
        # Get container boundary in scene coordinates
        container_rect = container.sceneBoundingRect()
        
        # Simple line-rectangle intersection
        x1, y1 = start_pos.x(), start_pos.y()
        x2, y2 = end_pos.x(), end_pos.y()
        
        # Line equation parameters: y = mx + b
        if x2 - x1 != 0:
            m = (y2 - y1) / (x2 - x1)
            b = y1 - m * x1
            
            # Intersections with vertical boundaries (left, right)
            left_x = container_rect.left()
            left_y = m * left_x + b
            if container_rect.top() <= left_y <= container_rect.bottom():
                if (x1 < left_x < x2) or (x2 < left_x < x1):
                    return QPointF(left_x, left_y)
            
            right_x = container_rect.right()
            right_y = m * right_x + b
            if container_rect.top() <= right_y <= container_rect.bottom():
                if (x1 < right_x < x2) or (x2 < right_x < x1):
                    return QPointF(right_x, right_y)
            
            # Intersections with horizontal boundaries (top, bottom)
            top_y = container_rect.top()
            top_x = (top_y - b) / m if m != 0 else None
            if top_x and container_rect.left() <= top_x <= container_rect.right():
                if (y1 < top_y < y2) or (y2 < top_y < y1):
                    return QPointF(top_x, top_y)
            
            bottom_y = container_rect.bottom()
            bottom_x = (bottom_y - b) / m if m != 0 else None
            if bottom_x and container_rect.left() <= bottom_x <= container_rect.right():
                if (y1 < bottom_y < y2) or (y2 < bottom_y < y1):
                    return QPointF(bottom_x, bottom_y)
        else:
            # Vertical line case
            if container_rect.left() <= x1 <= container_rect.right():
                if (y1 < container_rect.top() < y2) or (y2 < container_rect.top() < y1):
                    return QPointF(x1, container_rect.top())
                if (y1 < container_rect.bottom() < y2) or (y2 < container_rect.bottom() < y1):
                    return QPointF(x1, container_rect.bottom())
        
        return None
    
    # Get connection endpoints in scene coordinates
    if connection.start_port and connection.end_port:
        start_pos = connection.start_port.get_scene_position()
        end_pos = connection.end_port.get_scene_position()
        
        # SPECIAL CASE: Always add Network indicator for camera components connecting to any compute
        # Camera is considered a generator that connects via network to compute components
        if is_camera_connection and dst_parent:
            logger.debug(f"Adding Network transfer indicator for camera connection to compute")
            
            # Find intersection with destination container boundary (where camera connects to)
            dst_intersect = find_boundary_intersection(end_pos, start_pos, dst_parent)
            if dst_intersect:
                logger.debug(f"Network transfer indicator added for camera at destination: {dst_intersect.x():.1f}, {dst_intersect.y():.1f}")
                indicator = TransferIndicator("Network")
                indicator.setPos(dst_intersect.x() - 12, dst_intersect.y() - 8)
                indicator.set_connection(connection)
                transfer_indicators.append(indicator)
            else:
                # If no intersection found, place indicator near the destination component
                logger.debug(f"Placing Network indicator near destination for camera connection")
                indicator = TransferIndicator("Network")
                indicator.setPos(end_pos.x() - 30, end_pos.y() - 8)
                indicator.set_connection(connection)
                transfer_indicators.append(indicator)
            
        # Calculate transfer indicator positions for non-camera components
        # Different compute boxes = Network transfer
        elif (src_parent and dst_parent and 
            src_parent != dst_parent and
            isinstance(src_parent, ComputeBox) and 
            isinstance(dst_parent, ComputeBox)):
            
            logger.debug(f"Adding Network transfer indicators for connection across computers")
            
            # Find intersection with source container boundary
            src_intersect = find_boundary_intersection(start_pos, end_pos, src_parent)
            if src_intersect:
                logger.debug(f"Network transfer indicator added at source boundary: {src_intersect.x():.1f}, {src_intersect.y():.1f}")
                indicator = TransferIndicator("Network")
                indicator.setPos(src_intersect.x() - 12, src_intersect.y() - 8)
                indicator.set_connection(connection)
                transfer_indicators.append(indicator)
            else:
                logger.debug(f"Failed to find source boundary intersection for Network transfer")
            
            # Find intersection with destination container boundary
            dst_intersect = find_boundary_intersection(end_pos, start_pos, dst_parent)
            if dst_intersect and (not src_intersect or 
                                 (src_intersect.x() != dst_intersect.x() or 
                                  src_intersect.y() != dst_intersect.y())):
                logger.debug(f"Network transfer indicator added at destination boundary: {dst_intersect.x():.1f}, {dst_intersect.y():.1f}")
                indicator = TransferIndicator("Network")
                indicator.setPos(dst_intersect.x() - 12, dst_intersect.y() - 8)
                indicator.set_connection(connection)
                transfer_indicators.append(indicator)
            else:
                logger.debug(f"Failed to find destination boundary intersection for Network transfer")
        
        # CPU to GPU or GPU to CPU - check based on container types not hardware
        elif ((src_is_gpu_container and not dst_is_gpu_container) or
             (not src_is_gpu_container and dst_is_gpu_container)):
            
            logger.debug(f"Adding PCIe transfer indicator for CPU-GPU container connection")
            
            # Find GPU container
            gpu_container = src_parent if src_is_gpu_container else dst_parent
            
            # Find intersection with GPU container boundary
            if gpu_container:
                start = start_pos if src_is_gpu_container else end_pos
                end = end_pos if src_is_gpu_container else start_pos
                intersect_point = find_boundary_intersection(start, end, gpu_container)
                if intersect_point:
                    logger.debug(f"PCIe transfer indicator added at {intersect_point.x():.1f}, {intersect_point.y():.1f}")
                    indicator = TransferIndicator("PCIe")
                    indicator.setPos(intersect_point.x() - 12, intersect_point.y() - 8)
                    indicator.set_connection(connection)
                    transfer_indicators.append(indicator)
                else:
                    logger.debug(f"Failed to find GPU boundary intersection for PCIe transfer")
        
        # Traditional CPU-GPU transfer based on hardware type 
        elif (src_compute and dst_compute and 
                ((getattr(src_compute, 'hardware', 'CPU') == 'CPU' and 
                getattr(dst_compute, 'hardware', 'CPU') == 'GPU') or 
                (getattr(src_compute, 'hardware', 'CPU') == 'GPU' and 
                getattr(dst_compute, 'hardware', 'CPU') == 'CPU'))):
            
            logger.debug(f"Adding PCIe transfer indicator based on hardware type")
            
            # Find GPU container
            gpu_container = None
            if getattr(src_compute, 'hardware', 'CPU') == 'GPU':
                gpu_container = src_parent
            else:
                gpu_container = dst_parent
            
            # Find intersection with GPU container boundary
            if gpu_container:
                intersect_point = find_boundary_intersection(start_pos, end_pos, gpu_container)
                if intersect_point:
                    logger.debug(f"PCIe transfer indicator added at {intersect_point.x():.1f}, {intersect_point.y():.1f}")
                    indicator = TransferIndicator("PCIe")
                    indicator.setPos(intersect_point.x() - 12, intersect_point.y() - 8)
                    indicator.set_connection(connection)
                    transfer_indicators.append(indicator)
                else:
                    logger.debug(f"Failed to find GPU boundary intersection for PCIe transfer")
    
    # Add all the indicators to the scene
    for indicator in transfer_indicators:
        scene.addItem(indicator)
        logger.debug(f"Added {indicator.transfer_type} indicator to scene")
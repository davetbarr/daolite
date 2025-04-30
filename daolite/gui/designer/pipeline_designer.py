"""
Main application for the daolite pipeline designer.

This module provides the main application window and functionality for
the visual pipeline designer, with emphasis on network and multi-compute
node configurations.
"""

import sys
import logging
from typing import List
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QGraphicsScene,
    QGraphicsView,
    QToolBar,
    QPushButton,
    QComboBox,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QAction,
    QFileDialog,
    QMessageBox,
    QInputDialog,
    QDialog,
    QFormLayout,
    QLineEdit,
    QGraphicsItem,
    QGraphicsRectItem,
    QGraphicsTextItem,
)
from PyQt5.QtCore import Qt, QRectF, QPointF
from PyQt5.QtGui import QPainter, QPen, QColor, QFont, QBrush

from daolite.common import ComponentType
from daolite.compute import create_compute_resources
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
from daolite.config import SystemConfig, CameraConfig, OpticsConfig, PipelineConfig

from .components import ComponentBlock, ComputeBox, GPUBox, TransferIndicator
from .connection import Connection
from .code_generator import CodeGenerator
from .parameter_dialog import ComponentParametersDialog

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger('PipelineDesigner')


def update_connection_indicators(scene, connection):
    """
    Update or create transfer indicators for a connection that crosses resource boundaries.
    
    Args:
        scene: The graphics scene containing the connection
        connection: The connection to update indicators for
    """
    from .components import GPUBox, ComputeBox, TransferIndicator
    
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


class PipelineScene(QGraphicsScene):
    """
    Custom graphics scene for the pipeline designer.

    Handles interactions, connections, and component management.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSceneRect(0, 0, 2000, 1500)

        # Currently active connection during creation
        self.current_connection = None
        self.start_port = None
        self.start_block = None

        # List of all connections
        self.connections = []

        # Click-to-connect state
        self.click_connect_mode = False
        self.selected_port = None
        self.selected_block = None

    def dragMoveEvent(self, event):
        event.accept()

    def dropEvent(self, event):
        event.accept()

    def mousePressEvent(self, event):
        """Handle mouse press events for connection creation."""
        pos = event.scenePos()
        item = self.itemAt(pos, self.views()[0].transform())

        if event.button() == Qt.LeftButton:
            if isinstance(item, ComponentBlock):
                port = item.find_port_at_point(pos)
                if port:
                    # Click-to-connect logic
                    if not self.click_connect_mode:
                        # First click: select port
                        self.selected_port = port
                        self.selected_block = item
                        self.click_connect_mode = True
                        self.update()  # For visual feedback
                        return
                    else:
                        # Second click: try to connect
                        if port is not self.selected_port and self.selected_port is not None:
                            # Only allow output->input or input->output
                            if self.selected_port.port_type != port.port_type:
                                # Always connect output to input
                                if self.selected_port.port_type == port.port_type.INPUT:
                                    src_block, src_port = item, port
                                    dst_block, dst_port = self.selected_block, self.selected_port
                                else:
                                    src_block, src_port = self.selected_block, self.selected_port
                                    dst_block, dst_port = item, port
                                # Create connection
                                conn = Connection(src_block, src_port)
                                if conn.complete_connection(dst_block, dst_port):
                                    self.connections.append(conn)
                                    self.addItem(conn)
                                # Reset state
                                self.selected_port = None
                                self.selected_block = None
                                self.click_connect_mode = False
                                self.update()
                                return
                        # If invalid, just reset
                        self.selected_port = None
                        self.selected_block = None
                        self.click_connect_mode = False
                        self.update()
                        return
            # Drag-to-connect fallback
            if not self.click_connect_mode:
                if isinstance(item, ComponentBlock):
                    port = item.find_port_at_point(pos)
                    if port:
                        self.start_port = port
                        self.start_block = item
                        self.current_connection = Connection(item, port)
                        self.addItem(self.current_connection)
                        self.current_connection.set_temp_end_point(pos)
                        return
        # Connection selection for deletion
        if event.button() == Qt.RightButton:
            if isinstance(item, Connection):
                # Show context menu for deletion
                from PyQt5.QtWidgets import QMenu
                menu = QMenu()
                delete_action = menu.addAction("Delete Connection")
                action = menu.exec_(event.screenPos())
                if action == delete_action:
                    item.disconnect()
                    if item in self.connections:
                        self.connections.remove(item)
                    self.removeItem(item)
                    self.update()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """Handle mouse move events for connection creation and live box highlight."""
        # Live highlight for ComputeBox/GPUBox when moving a ComponentBlock
        selected = self.selectedItems()
        moving_block = None
        if len(selected) == 1 and isinstance(selected[0], ComponentBlock):
            moving_block = selected[0]
        if moving_block and moving_block.isUnderMouse():
            # Get the block bounding rect in scene coordinates
            block_rect = moving_block.sceneBoundingRect()
            highlight_box = None
            
            # Check all items that might be under the block
            for item in self.items():
                if isinstance(item, (ComputeBox, GPUBox)) and item is not moving_block:
                    # Check if the block significantly overlaps with the container
                    container_rect = item.sceneBoundingRect()
                    intersection = block_rect.intersected(container_rect)
                    
                    # If the intersection area is more than 30% of the block area,
                    # consider it a potential parent
                    if (intersection.width() * intersection.height()) > 0.3 * (block_rect.width() * block_rect.height()):
                        highlight_box = item
                        break
            
            # Highlight the potential parent container
            for item in self.items():
                if hasattr(item, 'set_highlight'):
                    item.set_highlight(item is highlight_box)
        else:
            for item in self.items():
                if hasattr(item, 'set_highlight'):
                    item.set_highlight(False)
                    
        # Update the end point of the current connection
        if self.current_connection:
            self.current_connection.set_temp_end_point(event.scenePos())
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        # GPU containment check - ensure all GPUs are fully inside their parent CPUs
        # and expand the parent CPU if needed
        for item in self.items():
            if isinstance(item, GPUBox) and item.parentItem() and isinstance(item.parentItem(), ComputeBox):
                gpu = item
                cpu = item.parentItem()
                
                # Get GPU bounds relative to the parent CPU
                gpu_rect = gpu.mapToParent(gpu.boundingRect()).boundingRect()
                cpu_rect = QRectF(0, 0, cpu.size.width(), cpu.size.height())
                
                # Check if GPU is partially outside CPU
                if not cpu_rect.contains(gpu_rect):
                    # Calculate how much to expand the CPU
                    margin = 20
                    new_width = max(cpu.size.width(), gpu_rect.right() + margin)
                    new_height = max(cpu.size.height(), gpu_rect.bottom() + margin)
                    
                    # Resize the CPU if needed
                    if new_width > cpu.size.width() or new_height > cpu.size.height():
                        cpu.size = QRectF(0, 0, new_width, new_height)
                        cpu.prepareGeometryChange()
                        cpu.update()
        
        # Original mouseReleaseEvent logic for grouping
        selected = self.selectedItems()
        if len(selected) == 1 and isinstance(selected[0], ComponentBlock):
            block = selected[0]
            # Store the original scene position before any parent changes
            orig_scene_pos = block.scenePos()
            
            # Check if this component has connections and log that it's being moved
            has_connections = False
            connections_to_check = []
            for conn in self.connections:
                if conn.start_block == block or conn.end_block == block:
                    has_connections = True
                    connections_to_check.append(conn)
            
            if has_connections:
                logger.debug(f"Moving component '{block.name}' with connections. Original pos: {orig_scene_pos.x():.1f}, {orig_scene_pos.y():.1f}")
            
            # Get the block's scene bounding rectangle
            block_scene_rect = block.sceneBoundingRect()
            
            # Find the best candidate container (computer box or GPU)
            parent_box = None
            max_overlap_area = 0
            
            for item in self.items():
                if isinstance(item, (ComputeBox, GPUBox)) and item is not block:
                    container_rect = item.sceneBoundingRect()
                    intersection = block_scene_rect.intersected(container_rect)
                    overlap_area = intersection.width() * intersection.height()
                    
                    # If there's meaningful overlap, consider this container
                    if overlap_area > max_overlap_area:
                        max_overlap_area = overlap_area
                        parent_box = item
            
            # Only consider it a drop into container if at least 25% of the component overlaps
            block_area = block_scene_rect.width() * block_scene_rect.height()
            if parent_box and max_overlap_area > (0.25 * block_area):
                # Convert position to parent coordinates
                local_pos = parent_box.mapFromScene(block.scenePos())
                old_parent = block.parentItem()
                block.setParentItem(parent_box)
                block.setPos(local_pos)
                # Assign compute resource
                if hasattr(parent_box, 'compute'):
                    block.compute = parent_box.compute
                elif hasattr(parent_box, 'gpu_resource'):
                    block.compute = parent_box.gpu_resource
                if hasattr(parent_box, 'child_items') and block not in parent_box.child_items:
                    parent_box.child_items.append(block)
                
                # Log component placement in container
                if has_connections:
                    compute_type = getattr(parent_box, 'compute', None)
                    if compute_type:
                        hardware_type = getattr(compute_type, 'hardware', 'CPU')
                        logger.debug(f"Component '{block.name}' with connections placed in {hardware_type} container '{parent_box.name}'")
                        
                        # Process all connections to check for boundary crossings
                        for conn in connections_to_check:
                            update_connection_indicators(self, conn)
                
                # Only adjust position if the component is outside the container bounds
                # or overlapping with other components
                is_outside = False
                box_rect = QRectF(0, 0, parent_box.size.width(), parent_box.size.height())
                block_rect = block.boundingRect()
                block_pos_rect = QRectF(block.pos().x(), block.pos().y(), 
                                        block_rect.width(), block_rect.height())
                
                # Check if block is outside parent bounds
                if not box_rect.contains(block_pos_rect):
                    is_outside = True
                
                # Check for overlaps with siblings
                is_overlapping = False
                for sibling in parent_box.childItems():
                    if sibling is not block and isinstance(sibling, ComponentBlock):
                        sibling_rect = QRectF(sibling.pos().x(), sibling.pos().y(),
                                            sibling.boundingRect().width(), 
                                            sibling.boundingRect().height())
                        if block_pos_rect.intersects(sibling_rect):
                            is_overlapping = True
                            break
                
                # Only adjust position if necessary
                if is_outside or is_overlapping:
                    if hasattr(parent_box, 'snap_child_fully_inside'):
                        parent_box.snap_child_fully_inside(block)
            else:
                # We're moving to no parent (dragging out of a container)
                # Preserve the exact scene position
                old_parent = block.parentItem()
                if old_parent:
                    block.setParentItem(None)
                    block.setPos(orig_scene_pos)
                    # Remove from previous parent's child_items list if applicable
                    if hasattr(old_parent, 'child_items') and block in old_parent.child_items:
                        old_parent.child_items.remove(block)
                    
                    # Reset block compute resource if it came from the parent
                    if hasattr(old_parent, 'compute') and block.compute is old_parent.compute:
                        # Reset to a default based on component type
                        app = self.parent()
                        if app and hasattr(app, '_get_default_compute_for_type'):
                            block.compute = app._get_default_compute_for_type(block.component_type)
                        
            # Remove all highlights
            for item in self.items():
                if hasattr(item, 'set_highlight'):
                    item.set_highlight(False)
        
        # Connection completion logic
        if self.current_connection and event.button() == Qt.LeftButton:
            pos = event.scenePos()
            item = self.itemAt(pos, self.views()[0].transform())
            if isinstance(item, ComponentBlock):
                port = item.find_port_at_point(pos)
                if port and port is not self.start_port:
                    # Complete the connection first
                    if self.current_connection.complete_connection(item, port):
                        self.connections.append(self.current_connection)
                        connection = self.current_connection
                        
                        # Get source and destination blocks and their compute resources
                        src_block = self.start_block
                        dst_block = item
                        src_compute = src_block.get_compute_resource()
                        dst_compute = dst_block.get_compute_resource()
                        
                        # Log the connection creation
                        logger.debug(f"Connection created from '{src_block.name}' to '{dst_block.name}'")
                        
                        # Update connection indicators
                        update_connection_indicators(self, connection)
                        
                        self.current_connection = None
                        self.start_port = None
                        self.start_block = None
                        self.update()
                        return
            
            # Remove incomplete connection
            self.removeItem(self.current_connection)
            self.current_connection = None
            self.start_port = None
            self.start_block = None
            
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        """Handle key press events for deleting items and zooming."""
        if event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            for item in self.selectedItems():
                # Delete connections
                if isinstance(item, Connection):
                    # The disconnect method now removes associated transfer indicators
                    item.disconnect()
                    if item in self.connections:
                        self.connections.remove(item)
                    self.removeItem(item)
                # Delete components
                elif hasattr(item, '_on_delete'):
                    # Before deleting, find and remove any transfer indicators 
                    # associated with connections to this component
                    if isinstance(item, ComponentBlock):
                        for conn in list(self.connections):
                            if conn.start_block == item or conn.end_block == item:
                                # Remove associated transfer indicators
                                for indicator in self.items():
                                    if (isinstance(indicator, TransferIndicator) and 
                                            hasattr(indicator, 'connection') and
                                            indicator.connection == conn):
                                        logger.debug(f"Removing {indicator.transfer_type} indicator during component deletion")
                                        self.removeItem(indicator)
                    
                    item._on_delete()
            self.update()
        elif event.key() in (Qt.Key_Plus, Qt.Key_Equal):
            # Zoom in
            for view in self.views():
                view.scale(1.2, 1.2)
        elif event.key() in (Qt.Key_Minus, Qt.Key_Underscore):
            # Zoom out
            for view in self.views():
                view.scale(0.8, 0.8)
        else:
            super().keyPressEvent(event)

    def drawForeground(self, painter, rect):
        """Draw visual feedback for click-to-connect."""
        if self.click_connect_mode and self.selected_port:
            painter.save()
            painter.setPen(QPen(Qt.red, 2, Qt.DashLine))
            pos = self.selected_port.get_scene_position()
            painter.drawEllipse(pos, 10, 10)
            painter.restore()
        super().drawForeground(painter, rect)


class ResourceSelectionDialog(QDialog):
    """
    Dialog for selecting or configuring compute resources.

    Allows users to choose from predefined resources or specify custom ones.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Compute Resource")
        self.resize(400, 300)

        layout = QVBoxLayout()

        # Predefined resources section
        layout.addWidget(QLabel("<b>Predefined Resources</b>"))

        # CPUs
        layout.addWidget(QLabel("CPUs:"))
        self.cpu_combo = QComboBox()
        self.cpu_combo.addItems(
            [
                "AMD EPYC 7763 (Milan)",
                "AMD EPYC 9654 (Genoa)",
                "Intel Xeon 8480+ (Sapphire Rapids)",
                "Intel Xeon 8462Y+ (Emerald Rapids)",
                "AMD Ryzen 9 7950X",
            ]
        )
        layout.addWidget(self.cpu_combo)

        # GPUs
        layout.addWidget(QLabel("GPUs:"))
        self.gpu_combo = QComboBox()
        self.gpu_combo.addItems(
            [
                "NVIDIA A100 80GB",
                "NVIDIA H100 80GB",
                "NVIDIA RTX 4090",
                "AMD Instinct MI300X",
            ]
        )
        layout.addWidget(self.gpu_combo)

        # Custom resource section
        layout.addWidget(QLabel("<b>Custom Resource</b>"))

        form_layout = QFormLayout()

        self.cores_edit = QLineEdit("16")
        form_layout.addRow("Cores:", self.cores_edit)

        self.freq_edit = QLineEdit("2.6e9")
        form_layout.addRow("Core Frequency (Hz):", self.freq_edit)

        self.flops_edit = QLineEdit("32")
        form_layout.addRow("FLOPS per cycle:", self.flops_edit)

        self.mem_channels_edit = QLineEdit("4")
        form_layout.addRow("Memory Channels:", self.mem_channels_edit)

        self.mem_width_edit = QLineEdit("64")
        form_layout.addRow("Memory Width (bits):", self.mem_width_edit)

        self.mem_freq_edit = QLineEdit("3200e6")
        form_layout.addRow("Memory Frequency (Hz):", self.mem_freq_edit)

        self.network_edit = QLineEdit("100e9")
        form_layout.addRow("Network Speed (bps):", self.network_edit)

        layout.addLayout(form_layout)

        # Buttons
        button_layout = QHBoxLayout()

        self.use_cpu_btn = QPushButton("Use Selected CPU")
        self.use_cpu_btn.clicked.connect(self.accept_cpu)
        button_layout.addWidget(self.use_cpu_btn)

        self.use_gpu_btn = QPushButton("Use Selected GPU")
        self.use_gpu_btn.clicked.connect(self.accept_gpu)
        button_layout.addWidget(self.use_gpu_btn)

        self.use_custom_btn = QPushButton("Use Custom Resource")
        self.use_custom_btn.clicked.connect(self.accept_custom)
        button_layout.addWidget(self.use_custom_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        layout.addLayout(button_layout)

        self.setLayout(layout)

        self.result_type = None
        self.result_index = None

    def accept_cpu(self):
        """Accept with CPU selection."""
        self.result_type = "cpu"
        self.result_index = self.cpu_combo.currentIndex()
        self.accept()

    def accept_gpu(self):
        """Accept with GPU selection."""
        self.result_type = "gpu"
        self.result_index = self.gpu_combo.currentIndex()
        self.accept()

    def accept_custom(self):
        """Accept with custom resource."""
        self.result_type = "custom"
        self.accept()

    def get_selected_resource(self):
        """
        Get the selected compute resource.

        Returns:
            ComputeResources: The selected compute resource
        """
        if self.result_type == "cpu":
            cpu_map = {
                0: amd_epyc_7763,
                1: amd_epyc_9654,
                2: intel_xeon_8480,
                3: intel_xeon_8462,
                4: amd_ryzen_7950x,
            }
            return cpu_map.get(self.result_index, amd_epyc_7763)()

        elif self.result_type == "gpu":
            gpu_map = {
                0: nvidia_a100_80gb,
                1: nvidia_h100_80gb,
                2: nvidia_rtx_4090,
                3: amd_mi300x,
            }
            return gpu_map.get(self.result_index, nvidia_rtx_4090)()

        elif self.result_type == "custom":
            # Create custom compute resource
            return create_compute_resources(
                cores=int(self.cores_edit.text()),
                core_frequency=float(self.freq_edit.text()),
                flops_per_cycle=int(self.flops_edit.text()),
                memory_channels=int(self.mem_channels_edit.text()),
                memory_width=int(self.mem_width_edit.text()),
                memory_frequency=float(self.mem_freq_edit.text()),
                network_speed=float(self.network_edit.text()),
                time_in_driver=5,
            )

        # Default
        return create_compute_resources()


class PipelineDesignerApp(QMainWindow):
    """
    Main application window for the daolite pipeline designer.

    Provides a graphical interface for designing AO pipelines with emphasis on
    network and multi-compute node configurations.
    """

    def __init__(self):
        super().__init__()

        self.setWindowTitle("daolite Pipeline Designer")
        self.resize(1200, 800)

        # Set up the scene and view
        self.scene = PipelineScene(self)
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(
            QPainter.Antialiasing
        )  # Fixed: Using QPainter.Antialiasing instead of self.view.Antialiasing
        self.view.setDragMode(self.view.RubberBandDrag)
        self.view.setViewportUpdateMode(self.view.FullViewportUpdate)
        self.setCentralWidget(self.view)

        # Track component count for naming
        self.component_counts = {
            ComponentType.CAMERA: 0,
            ComponentType.CENTROIDER: 0,
            ComponentType.RECONSTRUCTION: 0,
            ComponentType.CONTROL: 0,
            ComponentType.CALIBRATION: 0,
            ComponentType.NETWORK: 0,
        }

        self._create_toolbar()
        self._create_menu()

        # Connect context menu actions
        self.scene.selectionChanged.connect(self._update_selection)
        self.selected_component = None

    def _create_toolbar(self):
        """Create component toolbar."""
        self.toolbar = QToolBar("Components")
        self.addToolBar(Qt.LeftToolBarArea, self.toolbar)

        # === Compute Section ===
        compute_label = QLabel("<b>Compute/Hardware</b>")
        self.toolbar.addWidget(compute_label)

        add_computer_btn = QPushButton("Add Computer")
        add_computer_btn.clicked.connect(self._add_compute_box)
        add_computer_btn.setToolTip("Add a compute box (computer node) to the scene")
        self.toolbar.addWidget(add_computer_btn)

        add_gpu_btn = QPushButton("Add GPU to Computer")
        add_gpu_btn.clicked.connect(self._add_gpu_box)
        add_gpu_btn.setToolTip("Add a GPU block inside a selected computer")
        self.toolbar.addWidget(add_gpu_btn)

        self.toolbar.addSeparator()

        # Add buttons for each component type
        camera_btn = QPushButton("Camera")
        camera_btn.clicked.connect(lambda: self._add_component(ComponentType.CAMERA))
        camera_btn.setToolTip("Add a camera component to the pipeline")
        self.toolbar.addWidget(camera_btn)

        network_btn = QPushButton("Network")
        network_btn.clicked.connect(lambda: self._add_component(ComponentType.NETWORK))
        network_btn.setToolTip(
            "Add a network transfer component (emphasizes multi-node configurations)"
        )
        self.toolbar.addWidget(network_btn)

        calibration_btn = QPushButton("Calibration")
        calibration_btn.clicked.connect(
            lambda: self._add_component(ComponentType.CALIBRATION)
        )
        calibration_btn.setToolTip("Add a pixel calibration component")
        self.toolbar.addWidget(calibration_btn)

        centroider_btn = QPushButton("Centroider")
        centroider_btn.clicked.connect(
            lambda: self._add_component(ComponentType.CENTROIDER)
        )
        centroider_btn.setToolTip("Add a centroider component for wavefront sensing")
        self.toolbar.addWidget(centroider_btn)

        reconstruction_btn = QPushButton("Reconstruction")
        reconstruction_btn.clicked.connect(
            lambda: self._add_component(ComponentType.RECONSTRUCTION)
        )
        reconstruction_btn.setToolTip("Add a wavefront reconstruction component")
        self.toolbar.addWidget(reconstruction_btn)

        control_btn = QPushButton("Control")
        control_btn.clicked.connect(lambda: self._add_component(ComponentType.CONTROL))
        control_btn.setToolTip("Add a DM control component")
        self.toolbar.addWidget(control_btn)

        # Add separator
        self.toolbar.addSeparator()

        # === Add Generate Pipeline Button ===
        generate_btn = QPushButton("Generate Pipeline")
        generate_btn.setStyleSheet(
            "font-size: 16px; font-weight: bold; background: #4CAF50; color: white; padding: 8px 16px;"
        )
        generate_btn.clicked.connect(self._generate_code)
        generate_btn.setToolTip("Generate Python code for the current pipeline design")
        self.toolbar.addWidget(generate_btn)
        
        # Add Run Pipeline section
        self.toolbar.addSeparator()
        
        # Execution method dropdown
        run_label = QLabel("<b>Run Pipeline:</b>")
        self.toolbar.addWidget(run_label)
        
        self.execution_method = QComboBox()
        self.execution_method.addItems(["Python", "JSON"])
        self.execution_method.setToolTip("Select pipeline execution method")
        self.execution_method.setStyleSheet("min-width: 120px;")
        self.toolbar.addWidget(self.execution_method)
        
        # Run button
        run_pipeline_btn = QPushButton("Run Pipeline")
        run_pipeline_btn.setStyleSheet(
            "font-size: 14px; font-weight: bold; background: #2196F3; color: white; padding: 6px 12px;"
        )
        run_pipeline_btn.clicked.connect(self._run_pipeline)
        run_pipeline_btn.setToolTip("Execute pipeline and display visualization")
        self.toolbar.addWidget(run_pipeline_btn)
        
        self.toolbar.addSeparator()

        # Add configuration buttons
        if_selected = QLabel("With selected component:")
        self.toolbar.addWidget(if_selected)

        compute_btn = QPushButton("Set Compute")
        compute_btn.clicked.connect(self._configure_compute)
        compute_btn.setToolTip("Configure compute resource for selected component")
        self.toolbar.addWidget(compute_btn)

        params_btn = QPushButton("Set Parameters")
        params_btn.clicked.connect(self._configure_params)
        params_btn.setToolTip("Configure parameters for selected component")
        self.toolbar.addWidget(params_btn)

    def _add_compute_box(self):
        """Add a ComputeBox (computer node) to the scene."""
        name, ok = QInputDialog.getText(self, "Add Computer", "Enter computer name:", text="Computer")
        if not ok or not name:
            return
        # Prompt for compute resource
        dlg = ResourceSelectionDialog(self)
        compute_resource = None
        if dlg.exec_():
            compute_resource = dlg.get_selected_resource()
        compute_box = ComputeBox(name, compute=compute_resource)
        view_center = self.view.mapToScene(self.view.viewport().rect().center())
        compute_box.setPos(view_center.x() - 160, view_center.y() - 110)
        self.scene.addItem(compute_box)

    def _add_gpu_box(self):
        """Add a GPUBox inside a selected ComputeBox."""
        # Find selected ComputeBox
        selected = self.scene.selectedItems()
        compute_box = None
        for item in selected:
            if isinstance(item, ComputeBox):
                compute_box = item
                break
        if not compute_box:
            QMessageBox.information(self, "No Computer Selected", "Please select a computer box to add a GPU to.")
            return
        name, ok = QInputDialog.getText(self, "Add GPU", "Enter GPU name:", text="GPU")
        if not ok or not name:
            return
        # Prompt for GPU resource
        dlg = ResourceSelectionDialog(self)
        gpu_resource = None
        if dlg.exec_():
            gpu_resource = dlg.get_selected_resource()
        gpu_box = GPUBox(name, gpu_resource=gpu_resource)
        # Place GPUBox at a default offset inside the ComputeBox
        gpu_box.setPos(30, 60 + 40 * len(compute_box.child_items))
        compute_box.add_child(gpu_box)
        self.scene.addItem(gpu_box)

    def _create_menu(self):
        """Create application menu."""
        menu_bar = self.menuBar()

        # File menu
        file_menu = menu_bar.addMenu("&File")

        new_action = QAction("&New Pipeline", self)
        new_action.triggered.connect(self._new_pipeline)
        file_menu.addAction(new_action)

        save_action = QAction("&Save Pipeline", self)
        save_action.triggered.connect(self._save_pipeline)
        file_menu.addAction(save_action)

        load_action = QAction("&Load Pipeline", self)
        load_action.triggered.connect(self._load_pipeline)
        file_menu.addAction(load_action)

        file_menu.addSeparator()

        generate_action = QAction("&Generate Code", self)
        generate_action.triggered.connect(self._generate_code)
        file_menu.addAction(generate_action)

        export_config_action = QAction("Export Config &YAML", self)
        export_config_action.triggered.connect(self._export_config)
        file_menu.addAction(export_config_action)

        file_menu.addSeparator()

        exit_action = QAction("E&xit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Edit menu
        edit_menu = menu_bar.addMenu("&Edit")

        rename_action = QAction("&Rename Selected", self)
        rename_action.triggered.connect(self._rename_selected)
        edit_menu.addAction(rename_action)

        delete_action = QAction("&Delete Selected", self)
        delete_action.triggered.connect(self._delete_selected)
        edit_menu.addAction(delete_action)

        # View menu
        view_menu = menu_bar.addMenu("&View")

        zoom_in_action = QAction("Zoom &In", self)
        zoom_in_action.triggered.connect(lambda: self.view.scale(1.2, 1.2))
        view_menu.addAction(zoom_in_action)

        zoom_out_action = QAction("Zoom &Out", self)
        zoom_out_action.triggered.connect(lambda: self.view.scale(0.8, 0.8))
        view_menu.addAction(zoom_out_action)

        reset_zoom_action = QAction("&Reset Zoom", self)
        reset_zoom_action.triggered.connect(lambda: self.view.resetTransform())
        view_menu.addAction(reset_zoom_action)

        # Help menu
        help_menu = menu_bar.addMenu("&Help")

        about_action = QAction("&About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _add_component(self, comp_type: ComponentType):
        """
        Add a new component to the scene.

        Args:
            comp_type: Type of component to add
        """
        # Generate a unique name
        self.component_counts[comp_type] += 1
        name = f"{comp_type.value}{self.component_counts[comp_type]}"

        # Create the component
        component = ComponentBlock(comp_type, name)

        # Position at center of view
        view_center = self.view.mapToScene(self.view.viewport().rect().center())
        component.setPos(view_center.x() - 90, view_center.y() - 40)

        # Add to scene
        self.scene.addItem(component)

        # For components needing a compute resource, prompt for it
        if comp_type != ComponentType.NETWORK:  # Network uses sources/targets compute
            component.compute = self._get_default_compute_for_type(comp_type)

    def _get_default_compute_for_type(self, comp_type: ComponentType):
        """Get a default compute resource based on component type."""
        if (
            comp_type == ComponentType.CENTROIDER
            or comp_type == ComponentType.RECONSTRUCTION
        ):
            # These typically benefit from GPU
            return nvidia_rtx_4090()
        else:
            # Others typically run on CPU
            return amd_epyc_7763()

    def _update_selection(self):
        """Update when selection changes."""
        selected_items = self.scene.selectedItems()

        if len(selected_items) == 1 and isinstance(selected_items[0], ComponentBlock):
            self.selected_component = selected_items[0]
        else:
            self.selected_component = None

    def _configure_compute(self):
        """Configure compute resource for selected component."""
        if not self.selected_component:
            QMessageBox.information(
                self, "No Selection", "Please select a component to configure."
            )
            return

        self._get_compute_resource(self.selected_component)

    def _configure_params(self):
        """Configure parameters for selected component."""
        if not self.selected_component:
            QMessageBox.information(
                self, "No Selection", "Please select a component to configure."
            )
            return

        # Show parameter dialog
        dlg = ComponentParametersDialog(
            self.selected_component.component_type, self.selected_component.params, self
        )

        if dlg.exec_():
            # Update component with new parameters
            self.selected_component.params = dlg.get_parameters()
            self.scene.update()

    def _rename_selected(self):
        """Rename the selected component."""
        if not self.selected_component:
            return

        name, ok = QInputDialog.getText(
            self,
            "Rename Component",
            "Enter new name:",
            text=self.selected_component.name,
        )

        if ok and name:
            self.selected_component.name = name
            self.scene.update()

    def _new_pipeline(self):
        """Create a new empty pipeline."""
        reply = QMessageBox.question(
            self,
            "New Pipeline",
            "Clear the current pipeline?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            self.scene.clear()
            self.scene.connections = []
            self.component_counts = {key: 0 for key in self.component_counts}

    def _delete_selected(self):
        """Delete selected items from the scene."""
        for item in self.scene.selectedItems():
            if isinstance(item, ComponentBlock):
                # Remove connections associated with this component
                for connection in list(self.scene.connections):
                    if connection.start_block == item or connection.end_block == item:
                        connection.disconnect()
                        self.scene.connections.remove(connection)
                        self.scene.removeItem(connection)

                self.scene.removeItem(item)

    def _get_compute_resource(self, item):
        """
        Show a dialog to select a compute resource.

        Args:
            item: The container or component to configure
        """
        dlg = ResourceSelectionDialog(self)
        if dlg.exec_():
            # Apply the resource to the container, not to individual components
            if isinstance(item, (ComputeBox, GPUBox)):
                item.compute = dlg.get_selected_resource()
                
                # If this is a container, update all its child components' display
                for child in item.childItems():
                    if isinstance(child, ComponentBlock):
                        # We just need to trigger a repaint, the compute is inherited
                        child.update()
            else:
                # For individual components, find their parent container and set it there
                parent = item.parentItem()
                if parent and isinstance(parent, (ComputeBox, GPUBox)):
                    parent.compute = dlg.get_selected_resource()
                    # Trigger an update of the component display
                    item.update()
                else:
                    # If no parent container, warn the user
                    QMessageBox.warning(
                        self, 
                        "No Container", 
                        "This component is not in a compute container. Please add it to a CPU or GPU container first."
                    )
            
            self.scene.update()

    def _get_all_components(self) -> List[ComponentBlock]:
        """
        Get all component blocks in the scene.

        Returns:
            List of all component blocks
        """
        return [item for item in self.scene.items() if isinstance(item, ComponentBlock)]

    def _generate_code(self):
        """Generate and save pipeline code."""
        components = self._get_all_components()

        if not components:
            QMessageBox.warning(
                self, "Empty Pipeline", "No components to generate code from."
            )
            return

        # Generate code
        generator = CodeGenerator(components)

        # Get save location
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Pipeline Code", "", "Python Files (*.py);;All Files (*)"
        )

        if filename:
            generator.export_to_file(filename)
            QMessageBox.information(
                self, "Code Generation Complete", f"Pipeline code saved to {filename}"
            )

    def _save_pipeline(self):
        """Save pipeline design to a file (not the code, but the design)."""
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Pipeline Design", "", "JSON Files (*.json)"
        )
        if filename:
            self._save_pipeline_to_file(filename)
            QMessageBox.information(
                self, "Pipeline Saved", f"Pipeline design saved to {filename}"
            )

    def _export_config(self):
        """Export configuration as YAML."""
        components = self._get_all_components()

        if not components:
            QMessageBox.warning(
                self, "Empty Pipeline", "No components to export configuration from."
            )
            return

        # Find camera and optics components
        camera_component = None
        actuator_count = 5000  # default

        for component in components:
            if component.component_type == ComponentType.CAMERA:
                camera_component = component
            elif component.component_type == ComponentType.CONTROL:
                if "n_actuators" in component.params:
                    actuator_count = component.params["n_actuators"]

        # Create configuration objects
        if camera_component and camera_component.params:
            # Extract parameters from camera component
            camera_params = camera_component.params
            camera_config = CameraConfig(
                n_pixels=camera_params.get("n_pixels", 1024 * 1024),
                n_subapertures=camera_params.get("n_subapertures", 80 * 80),
                pixels_per_subaperture=camera_params.get(
                    "pixels_per_subaperture", 16 * 16
                ),
                bit_depth=camera_params.get("bit_depth", 16),
                readout_time=camera_params.get("readout_time", 500.0),
            )
        else:
            # Default camera config
            camera_config = CameraConfig(
                n_pixels=1024 * 1024,
                n_subapertures=80 * 80,
                pixels_per_subaperture=16 * 16,
            )

        # Create optics config
        optics_config = OpticsConfig(n_actuators=actuator_count)

        # Create pipeline config
        use_square_diff = False
        use_sorting = False
        n_workers = 4

        for component in components:
            if component.component_type == ComponentType.CENTROIDER:
                if "square_diff" in component.params:
                    use_square_diff = component.params["square_diff"]
                if "sort" in component.params:
                    use_sorting = component.params["sort"]
                if "n_workers" in component.params:
                    n_workers = component.params["n_workers"]

        pipeline_config = PipelineConfig(
            use_square_diff=use_square_diff,
            use_sorting=use_sorting,
            n_workers=n_workers,
        )

        # Create system config
        system_config = SystemConfig(
            camera=camera_config, optics=optics_config, pipeline=pipeline_config
        )

        # Get save location
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Configuration YAML", "", "YAML Files (*.yaml);;All Files (*)"
        )

        if filename:
            system_config.to_yaml(filename)
            QMessageBox.information(
                self,
                "Configuration Export Complete",
                f"System configuration saved to {filename}",
            )

    def _load_pipeline(self):
        """Load pipeline design from a file."""
        filename, _ = QFileDialog.getOpenFileName(
            self, "Load Pipeline Design", "", "JSON Files (*.json);;All Files (*)"
        )
        if not filename:
            return
            
        try:
            import json
            
            # Clear existing scene
            self.scene.clear()
            self.scene.connections = []
            self.component_counts = {key: 0 for key in self.component_counts}
            
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
                        # Clean up compute dict to avoid duplicate parameters
                        compute_dict = container["compute"].copy()
                        
                        # Handle resource_name separately
                        if "resource_name" in container:
                            resource_name = container["resource_name"]
                            
                            # Check for predefined hardware resources
                            if "AMD EPYC 7763" in resource_name:
                                compute_resource = amd_epyc_7763()
                            elif "AMD EPYC 9654" in resource_name:
                                compute_resource = amd_epyc_9654()
                            elif "Intel Xeon 8480" in resource_name:
                                compute_resource = intel_xeon_8480()
                            elif "Intel Xeon 8462" in resource_name:
                                compute_resource = intel_xeon_8462()
                            elif "AMD Ryzen 7950X" in resource_name:
                                compute_resource = amd_ryzen_7950x()
                            elif "NVIDIA A100" in resource_name:
                                compute_resource = nvidia_a100_80gb()
                            elif "NVIDIA H100" in resource_name:
                                compute_resource = nvidia_h100_80gb()
                            elif "NVIDIA RTX 4090" in resource_name:
                                compute_resource = nvidia_rtx_4090()
                            elif "AMD MI300X" in resource_name:
                                compute_resource = amd_mi300x()
                        
                        # If no predefined resource was found, create from parameters
                        if compute_resource is None:
                            # Ensure only valid parameters are passed to create_compute_resources
                            valid_params = {
                                'hardware', 'cores', 'core_frequency', 'flops_per_cycle',
                                'memory_channels', 'memory_width', 'memory_frequency',
                                'network_speed', 'time_in_driver', 'core_fudge', 
                                'mem_fudge', 'network_fudge', 'adjust'
                            }
                            
                            # Filter to include only valid parameters
                            filtered_dict = {k: v for k, v in compute_dict.items() if k in valid_params}
                            
                            # Create resource
                            try:
                                compute_resource = create_compute_resources(**filtered_dict)
                            except Exception as e:
                                logger.error(f"Error creating compute resource: {str(e)}")
                                # Fallback to default
                                compute_resource = amd_epyc_7763()
                    
                    # Create the compute box
                    compute_box = ComputeBox(name, compute=compute_resource)
                    compute_box.size = QRectF(0, 0, size[0], size[1])
                    compute_box.setPos(pos[0], pos[1])
                    self.scene.addItem(compute_box)
                    compute_boxes[name] = compute_box
                    
                    # Create GPU boxes inside this compute box
                    for gpu_data in container.get("gpu_boxes", []):
                        gpu_name = gpu_data.get("name", "GPU")
                        gpu_pos = gpu_data.get("pos", (30, 60))
                        gpu_size = gpu_data.get("size", (200, 140))
                        
                        # Create GPU resource if provided
                        gpu_resource = None
                        if "compute" in gpu_data:
                            # Similar handling for GPU resources
                            if "resource_name" in gpu_data:
                                resource_name = gpu_data["resource_name"]
                                if "NVIDIA A100" in resource_name:
                                    gpu_resource = nvidia_a100_80gb()
                                elif "NVIDIA H100" in resource_name:
                                    gpu_resource = nvidia_h100_80gb()
                                elif "NVIDIA RTX 4090" in resource_name:
                                    gpu_resource = nvidia_rtx_4090()
                                elif "AMD MI300X" in resource_name:
                                    gpu_resource = amd_mi300x()
                            
                            # Create custom GPU resource if needed
                            if gpu_resource is None:
                                gpu_dict = gpu_data["compute"].copy()
                                valid_params = {
                                    'hardware', 'cores', 'core_frequency', 'flops_per_cycle',
                                    'memory_channels', 'memory_width', 'memory_frequency',
                                    'network_speed', 'time_in_driver', 'core_fudge', 
                                    'mem_fudge', 'network_fudge', 'adjust'
                                }
                                filtered_dict = {k: v for k, v in gpu_dict.items() if k in valid_params}
                                
                                try:
                                    # Ensure hardware type is set for GPUs
                                    if 'hardware' not in filtered_dict:
                                        filtered_dict['hardware'] = 'GPU'
                                    gpu_resource = create_compute_resources(**filtered_dict)
                                except Exception as e:
                                    logger.error(f"Error creating GPU resource: {str(e)}")
                                    # Fallback to default
                                    gpu_resource = nvidia_rtx_4090()
                        
                        # Create the GPU box
                        gpu_box = GPUBox(gpu_name, gpu_resource=gpu_resource)
                        gpu_box.size = QRectF(0, 0, gpu_size[0], gpu_size[1])
                        gpu_box.setPos(gpu_pos[0], gpu_pos[1])
                        compute_box.add_child(gpu_box)
                        self.scene.addItem(gpu_box)
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
                
                self.scene.addItem(component)
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
                    self.component_counts[comp_type] = max(
                        self.component_counts[comp_type],
                        comp_number
                    )
                except Exception as e:
                    logger.debug(f"Could not update component count from name {name}: {str(e)}")
                    # Just increment the count if we can't parse the name
                    self.component_counts[comp_type] += 1
            
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
                            self.scene.connections.append(connection)
                            self.scene.addItem(connection)
                            
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
                        update_connection_indicators(self.scene, connection)
            
            logger.info(f"Pipeline loaded from {filename}")
            QMessageBox.information(
                self, "Pipeline Loaded", f"Pipeline design loaded from {filename}"
            )
            
        except Exception as e:
            logger.error(f"Error loading pipeline: {str(e)}")
            QMessageBox.critical(
                self, "Load Error", f"Failed to load pipeline: {str(e)}"
            )

    def _show_about(self):
        """Show about dialog."""
        QMessageBox.about(
            self,
            "About daolite Pipeline Designer",
            """<b>daolite Pipeline Designer</b><br/><br/>
               A visual tool for designing AO pipelines with emphasis on 
               network and multi-compute node configurations.<br/><br/>
               Part of the daolite package for estimating latency in 
               Adaptive Optics Real-time Control Systems.""",
        )

    def _determine_transfer_type(self, src_comp, dest_comp):
        """
        Determine the type of transfer between two components.
        
        Args:
            src_comp: Source component
            dest_comp: Destination component
            
        Returns:
            str: Transfer type ('Network' or 'PCIe') or None if no transfer needed
        """
        # Get compute resources and parent containers
        src_res = src_comp.get_compute_resource()
        dest_res = dest_comp.get_compute_resource()
        src_parent = src_comp.parentItem()
        dest_parent = dest_comp.parentItem()
        
        # Camera components always connect via network
        if src_comp.component_type == ComponentType.CAMERA:
            return "Network"
        
        # Check if components are in different compute boxes
        if (src_parent and dest_parent and 
            src_parent != dest_parent and
            isinstance(src_parent, ComputeBox) and 
            isinstance(dest_parent, ComputeBox)):
            return "Network"
        
        # Check for CPU-GPU transfers
        from .components import GPUBox
        if ((isinstance(src_parent, GPUBox) and not isinstance(dest_parent, GPUBox)) or
            (not isinstance(src_parent, GPUBox) and isinstance(dest_parent, GPUBox))):
            return "PCIe"
        
        # Check based on hardware type
        if src_res and dest_res:
            src_hw = getattr(src_res, 'hardware', 'CPU')
            dest_hw = getattr(dest_res, 'hardware', 'CPU')
            if src_hw != dest_hw:
                if 'GPU' in (src_hw, dest_hw):
                    return "PCIe"
                else:
                    return "Network"
        
        # No transfer needed or couldn't determine
        return None

    def _estimate_data_size(self, src_comp, dest_comp):
        """
        Estimate data size transferred between components in bits.
        
        Args:
            src_comp: Source component
            dest_comp: Destination component
            
        Returns:
            int: Estimated data size in bits
        """
        # Default values for common AO data sizes
        if src_comp.component_type == ComponentType.CAMERA:
            # Camera output is typically pixel data
            n_pixels = src_comp.params.get("n_pixels", 1024 * 1024)  # Default 1MP
            bit_depth = src_comp.params.get("bit_depth", 16)  # Default 16-bit
            return n_pixels * bit_depth

        elif src_comp.component_type == ComponentType.CALIBRATION:
            # Calibration typically outputs calibrated pixel data
            n_pixels = src_comp.params.get("n_pixels", 1024 * 1024)
            bit_depth = src_comp.params.get("output_bit_depth", 16)
            return n_pixels * bit_depth
            
        elif src_comp.component_type == ComponentType.CENTROIDER:
            # Centroider outputs slope measurements
            n_subaps = src_comp.params.get("n_valid_subaps", 6400)  # Default 80×80
            bit_size = 32  # Usually float32
            return n_subaps * 2 * bit_size  # X and Y slopes
            
        elif src_comp.component_type == ComponentType.RECONSTRUCTION:
            # Reconstruction outputs actuator commands
            n_actuators = src_comp.params.get("n_acts", 5000)  # Default ELT scale
            bit_size = 32  # Usually float32
            return n_actuators * bit_size
            
        elif src_comp.component_type == ComponentType.CONTROL:
            # Control outputs actuator commands (possibly with telemetry)
            n_actuators = src_comp.params.get("n_acts", 5000)
            bit_size = 32
            return n_actuators * bit_size
        
        # Fallback to a reasonable default for AO data
        return 1024 * 1024 * 16  # 1MP at 16-bit

    def _run_pipeline(self):
        """Run the pipeline and display visualization in a popup window."""
        import os
        import subprocess
        import tempfile
        import sys
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QDialogButtonBox, QFileDialog, QSplitter
        from PyQt5.QtGui import QPixmap
        from PyQt5.QtCore import Qt, QByteArray, QBuffer, QIODevice
        
        components = self._get_all_components()
        if not components:
            QMessageBox.warning(self, "Empty Pipeline", "No components to run.")
            return
        
        # Determine which execution method to use
        method = self.execution_method.currentText()
        
        # First, save the pipeline to temporary files
        with tempfile.TemporaryDirectory() as temp_dir:
            # For either method, we need to save the pipeline design in JSON format
            json_path = os.path.join(temp_dir, "temp_pipeline.json")
            self._save_pipeline_to_file(json_path)
            
            # For Python method, also create a Python script
            if method == "Python":
                py_path = os.path.join(temp_dir, "temp_pipeline.py")
                generator = CodeGenerator(components)
                try:
                    generator.export_to_file(py_path)
                    # Add visualization code to the Python file
                    with open(py_path, 'a') as f:
                        f.write("\n\n# Visualize pipeline\n")
                        f.write("fig, ax, latency = pipeline.visualize('Pipeline Timing')\n")
                        
                        # Save the figure to a file instead of showing it
                        vis_path = os.path.join(temp_dir, "visualization.png")
                        f.write(f"fig.savefig('{vis_path}', dpi=300, bbox_inches='tight')\n")
                        f.write(f"print('\\nVisualization saved to: {vis_path}')\n")
                        f.write("print(f'Total pipeline latency: {latency:.2f} μs')\n")
                        # Don't call plt.show() - instead, just save the figure
                except Exception as e:
                    QMessageBox.critical(self, "Code Generation Error", f"Failed to generate Python code: {str(e)}")
                    return
            
            # Determine the visualization image path
            vis_path = os.path.join(temp_dir, "visualization.png")
            
            # Create a dialog to show execution progress
            progress_dialog = QDialog(self)
            progress_dialog.setWindowTitle("Running Pipeline")
            progress_dialog.resize(500, 300)
            
            layout = QVBoxLayout()
            status_label = QLabel("Executing pipeline, please wait...")
            layout.addWidget(status_label)
            
            button_box = QDialogButtonBox(QDialogButtonBox.Cancel)
            button_box.rejected.connect(progress_dialog.reject)
            layout.addWidget(button_box)
            
            progress_dialog.setLayout(layout)
            progress_dialog.show()
            
            # Construct the command based on execution method
            if method == "Python":
                # Set environment variable to force matplotlib to use Agg backend (non-interactive)
                my_env = os.environ.copy()
                my_env["MPLBACKEND"] = "Agg"  # Force non-interactive matplotlib backend
                cmd = [sys.executable, py_path]
            else:  # JSON
                my_env = os.environ.copy()
                my_env["MPLBACKEND"] = "Agg"  # Force non-interactive matplotlib backend
                cmd = [sys.executable, "-m", "daolite.pipeline.json_runner", json_path, "--save", vis_path, "--no-show"]
            
            # Run the command
            try:
                process = subprocess.Popen(
                    cmd, 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.STDOUT,
                    text=True,
                    cwd=temp_dir,
                    env=my_env
                )
                
                # Update status with output from the process
                output = []
                while True:
                    line = process.stdout.readline()
                    if not line and process.poll() is not None:
                        break
                    if line:
                        output.append(line.strip())
                        status_label.setText("\n".join(output[-10:]))  # Show last 10 lines
                        QApplication.processEvents()  # Update UI
                
                return_code = process.wait()
                
                # Check if execution was successful
                if return_code != 0:
                    # Show error dialog with full output
                    progress_dialog.close()
                    error_msg = "\n".join(output)
                    QMessageBox.critical(
                        self, 
                        "Pipeline Execution Failed", 
                        f"Pipeline execution returned code {return_code}.\n\nOutput:\n{error_msg}"
                    )
                    return
                
                # Close progress dialog
                progress_dialog.close()
                
                # Check if visualization file was created
                if not os.path.exists(vis_path):
                    QMessageBox.warning(
                        self, 
                        "Visualization Not Found", 
                        "Pipeline executed successfully, but no visualization was generated."
                    )
                    return
                
                # Show visualization in a new dialog
                self._show_visualization(vis_path, "\n".join(output))
                
            except Exception as e:
                progress_dialog.close()
                QMessageBox.critical(self, "Execution Error", f"Failed to execute pipeline: {str(e)}")
                return

    def _save_pipeline_to_file(self, filename):
        """Save pipeline to a JSON file without showing dialog."""
        import json

        data = {
            "containers": [],
            "components": [], 
            "connections": [],
            "transfers": []
        }
        
        # Save compute and GPU boxes first
        for item in self.scene.items():
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
        for comp in self._get_all_components():
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
            
            comp_data = {
                "type": comp.component_type.name,
                "name": comp.name,
                "pos": (comp.pos().x(), comp.pos().y()),
                "params": comp.params,
                "parent_type": parent_type,
                "parent_name": parent_name,
                "gpu_parent_name": gpu_parent_name
            }
            data["components"].append(comp_data)
            components_by_name[comp.name] = comp
        
        # Save connections
        for conn in self.scene.connections:
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
                    data_size = self._estimate_data_size(src_comp, dest_comp)
                    
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

    def _show_visualization(self, image_path, output_text):
        """Show the visualization image in a dialog with embedded matplotlib figure."""
        from PyQt5.QtWidgets import (
            QDialog, QVBoxLayout, QLabel, QDialogButtonBox, QScrollArea, 
            QFileDialog, QTextEdit, QSplitter, QWidget, QPushButton, QHBoxLayout
        )
        from PyQt5.QtGui import QPixmap
        from PyQt5.QtCore import Qt
        import matplotlib
        matplotlib.use('Qt5Agg')
        from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
        from matplotlib.figure import Figure
        import matplotlib.pyplot as plt
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Pipeline Visualization")
        dialog.resize(1000, 700)
        
        # Main layout
        main_layout = QVBoxLayout(dialog)
        
        # Create a splitter to allow resizing between visualization and text
        splitter = QSplitter(Qt.Vertical)
        splitter.setChildrenCollapsible(True)  # Allow sections to be collapsed
        
        # Top widget for visualization
        viz_widget = QWidget()
        viz_layout = QVBoxLayout(viz_widget)
        
        # Try to display the figure directly if possible, otherwise use the saved image
        try:
            # Load the image as a matplotlib figure
            img = plt.imread(image_path)
            fig = Figure(figsize=(10, 6))
            ax = fig.add_subplot(111)
            ax.imshow(img)
            ax.axis('off')  # Hide axes
            
            # Create a canvas to display the figure
            canvas = FigureCanvasQTAgg(fig)
            viz_layout.addWidget(canvas)
        except Exception as e:
            # Fallback to QPixmap if matplotlib embedding fails
            print(f"Error embedding matplotlib figure: {str(e)}")
            scroll_area = QScrollArea()
            scroll_area.setWidgetResizable(True)
            
            image_label = QLabel()
            pixmap = QPixmap(image_path)
            image_label.setPixmap(pixmap)
            image_label.setAlignment(Qt.AlignCenter)
            
            scroll_area.setWidget(image_label)
            viz_layout.addWidget(scroll_area)
        
        # Add the visualization widget to the splitter
        splitter.addWidget(viz_widget)
        
        # Bottom widget for text output
        text_widget = QWidget()
        text_layout = QVBoxLayout(text_widget)
        
        # Add a header with toggle button for the text section
        text_header = QWidget()
        header_layout = QHBoxLayout(text_header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        header_label = QLabel("<b>Pipeline Execution Output</b>")
        header_layout.addWidget(header_label)
        
        toggle_button = QPushButton("▼")  # Down arrow to indicate collapsible
        toggle_button.setMaximumWidth(30)
        toggle_button.setToolTip("Toggle output visibility")
        header_layout.addWidget(toggle_button)
        
        text_layout.addWidget(text_header)
        
        # Add the output text widget
        output_edit = QTextEdit()
        output_edit.setReadOnly(True)
        output_edit.setText(output_text)
        output_edit.setLineWrapMode(QTextEdit.NoWrap)  # Preserve formatting
        output_edit.setMinimumHeight(100)
        text_layout.addWidget(output_edit)
        
        # Add the text widget to the splitter
        splitter.addWidget(text_widget)
        
        # Set the initial sizes of the splitter (visualization larger than text)
        splitter.setSizes([700, 300])
        
        # Connect toggle button to hide/show text section
        def toggle_text_visibility():
            current_sizes = splitter.sizes()
            if current_sizes[1] == 0:  # If text is hidden
                # Show text (roughly 1/3 of the space)
                total_height = sum(current_sizes)
                splitter.setSizes([int(total_height * 0.7), int(total_height * 0.3)])
                toggle_button.setText("▼")  # Down arrow
            else:  # If text is visible
                # Hide text (save current proportions first)
                splitter.setSizes([current_sizes[0] + current_sizes[1], 0])
                toggle_button.setText("▲")  # Up arrow
        
        toggle_button.clicked.connect(toggle_text_visibility)
        
        # Add the splitter to the main layout
        main_layout.addWidget(splitter)
        
        # Add buttons
        button_box = QDialogButtonBox()
        
        # Add a save button
        save_button = button_box.addButton("Save Image", QDialogButtonBox.ActionRole)
        save_button.clicked.connect(lambda: self._save_visualization_image(image_path))
        
        # Add close button
        close_button = button_box.addButton(QDialogButtonBox.Close)
        close_button.clicked.connect(dialog.accept)
        
        main_layout.addWidget(button_box)
        
        dialog.exec_()

    def _save_visualization_image(self, source_path):
        """Save the visualization image to a user-selected location."""
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Visualization", "", "PNG Files (*.png);;All Files (*)"
        )
        
        if filename:
            from shutil import copyfile
            try:
                copyfile(source_path, filename)
                QMessageBox.information(self, "Image Saved", f"Visualization saved to {filename}")
            except Exception as e:
                QMessageBox.critical(self, "Save Error", f"Error saving image: {str(e)}")

    @staticmethod
    def run():
        """Run the pipeline designer application."""
        app = QApplication(sys.argv)
        window = PipelineDesignerApp()
        window.show()
        sys.exit(app.exec_())

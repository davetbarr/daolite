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
    QListWidget,
    QListWidgetItem,
    QWidget,
    QCheckBox,
    QUndoStack,
    QUndoCommand,
    QTextEdit,
    QToolButton,
    QFrame,
    QSizePolicy,
    QDialogButtonBox,
)
from PyQt5.QtCore import Qt, QRectF, QPointF, QSize
from PyQt5.QtGui import QPainter, QPen, QColor, QFont, QBrush, QKeySequence, QIcon, QLinearGradient

import inspect
import daolite.compute.hardware as hardware

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
from daolite.gui.centroid_agenda_tool import show_centroid_agenda_tool

from .components import ComponentBlock, ComputeBox, GPUBox, TransferIndicator
from .connection import Connection
from .code_generator import CodeGenerator
from .parameter_dialog import ComponentParametersDialog
from .connection_manager import update_connection_indicators
from .style_utils import set_app_style, StyledTextInputDialog, get_saved_theme, save_theme

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger('PipelineDesigner')


class ShortcutHelpDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        set_app_style(self)
        self.setWindowTitle("Keyboard Shortcuts")
        layout = QVBoxLayout(self)
        text = QTextEdit()
        text.setReadOnly(True)
        text.setPlainText(
            """
            Keyboard Shortcuts:
            ------------------
            ⌘N / Ctrl+N: New Pipeline
            ⌘O / Ctrl+O: Open Pipeline
            ⌘S / Ctrl+S: Save Pipeline
            ⌘Z / Ctrl+Z: Undo
            ⌘Y / Ctrl+Y: Redo
            Delete/Backspace: Delete Selected
            ⌘Q / Ctrl+Q: Quit
            ⌘G / Ctrl+G: Generate Code
            ⌘R / Ctrl+R: Run Pipeline
            ⌘E / Ctrl+E: Export Config
            ⌘H / Ctrl+H: Show Shortcuts
            ⌘+: Zoom In
            ⌘-: Zoom Out
            ⌘0: Reset Zoom
            """)
        layout.addWidget(text)
        btn = QPushButton("Close")
        btn.clicked.connect(self.accept)
        layout.addWidget(btn)


class StyledTextInputDialog(QDialog):
    def __init__(self, title, label, default_text="", parent=None):
        super().__init__(parent)
        set_app_style(self)
        self.setWindowTitle(title)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(label))
        self.line_edit = QLineEdit(default_text)
        layout.addWidget(self.line_edit)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def getText(self):
        return self.line_edit.text()


class PipelineScene(QGraphicsScene):
    """
    Custom graphics scene for the pipeline designer.

    Handles interactions, connections, and component management.
    """

    def __init__(self, parent=None, theme='light'):
        super().__init__(parent)
        self.setSceneRect(0, 0, 2000, 1500)
        self.theme = theme

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

    def set_theme(self, theme):
        self.theme = theme
        self.update()
        for item in self.items():
            if hasattr(item, 'set_theme'):
                item.set_theme(theme)

    def dragMoveEvent(self, event):
        event.accept()

    def dropEvent(self, event):
        event.accept()

    def mousePressEvent(self, event):
        """Handle mouse press events for connection creation."""
        pos = event.scenePos()
        item = self.itemAt(pos, self.views()[0].transform())
        port = None
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

    def drawBackground(self, painter, rect):
        theme = getattr(self, 'theme', 'light')
        if theme == 'dark':
            color1 = QColor(30, 36, 48)
            color2 = QColor(40, 48, 64)
        else:
            color1 = QColor(246, 248, 250)  # light blue/gray
            color2 = QColor(231, 242, 250)  # lighter blue
        grad = QLinearGradient(rect.topLeft(), rect.bottomRight())
        grad.setColorAt(0, color1)
        grad.setColorAt(1, color2)
        painter.fillRect(rect, grad)


class ResourceSelectionDialog(QDialog):
    """
    Dialog for selecting or configuring compute resources.
    Cleaned up: CPU dropdown (with custom), optional GPU (with custom),
    and only shows custom fields when needed.
    Now supports editing: pass existing_resource to pre-populate fields.
    """
    def __init__(self, parent=None, existing_resource=None):
        super().__init__(parent)
        set_app_style(self)
        self.setWindowTitle("Configure Computer Resource")
        self.resize(440, 420)
        self.cpu_name_string = None
        layout = QVBoxLayout()
        # Name field
        name_layout = QFormLayout()
        self.name_edit = QLineEdit("Computer")
        name_layout.addRow("Computer Name:", self.name_edit)
        layout.addLayout(name_layout)
        # --- Dynamic CPU list ---
        cpu_factories = [(name, func) for name, func in inspect.getmembers(hardware, inspect.isfunction) if name.startswith("amd_") or name.startswith("intel_")]
        self.cpu_names = []
        self.cpu_funcs = []
        for name, func in cpu_factories:
            try:
                res = func()
                label = getattr(res, "name", name.replace("_", " ").title())
            except Exception:
                label = name.replace("_", " ").title()
            self.cpu_names.append(label)
            self.cpu_funcs.append(func)
        self.cpu_names.append("Custom…")
        layout.addWidget(QLabel("CPU Model:"))
        self.cpu_combo = QComboBox()
        self.cpu_combo.addItems(self.cpu_names)
        layout.addWidget(self.cpu_combo)
        # Custom CPU fields (hidden by default)
        self.cpu_custom_fields = QFormLayout()
        self.cores_edit = QLineEdit("16")
        self.cpu_custom_fields.addRow("Cores:", self.cores_edit)
        self.freq_edit = QLineEdit("2.6e9")
        self.cpu_custom_fields.addRow("Core Frequency (Hz):", self.freq_edit)
        self.flops_edit = QLineEdit("32")
        self.cpu_custom_fields.addRow("FLOPS per cycle:", self.flops_edit)
        self.mem_channels_edit = QLineEdit("4")
        self.cpu_custom_fields.addRow("Memory Channels:", self.mem_channels_edit)
        self.mem_width_edit = QLineEdit("64")
        self.cpu_custom_fields.addRow("Memory Width (bits):", self.mem_width_edit)
        self.mem_freq_edit = QLineEdit("3200e6")
        self.cpu_custom_fields.addRow("Memory Frequency (Hz):", self.mem_freq_edit)
        self.network_edit = QLineEdit("100e9")
        self.cpu_custom_fields.addRow("Network Speed (bps):", self.network_edit)
        self.cpu_custom_fields_widget = QWidget()
        self.cpu_custom_fields_widget.setLayout(self.cpu_custom_fields)
        self.cpu_custom_fields_widget.setVisible(False)
        layout.addWidget(self.cpu_custom_fields_widget)
        self.cpu_name_string = self.cpu_combo.currentText()
        # --- Add GPU checkbox ---
        self.add_gpu_checkbox = QCheckBox("Add GPU")
        layout.addWidget(self.add_gpu_checkbox)
        # --- GPU dropdown (hidden by default) ---
        gpu_factories = [(name, func) for name, func in inspect.getmembers(hardware, inspect.isfunction) if name.startswith("nvidia_") or name.startswith("amd_mi")]
        self.gpu_names = []
        self.gpu_funcs = []
        for name, func in gpu_factories:
            try:
                res = func()
                label = getattr(res, "name", name.replace("_", " ").title())
            except Exception:
                label = name.replace("_", " ").title()
            self.gpu_names.append(label)
            self.gpu_funcs.append(func)
        self.gpu_names.append("Custom…")
        self.gpu_combo = QComboBox()
        self.gpu_combo.addItems(self.gpu_names)
        self.gpu_combo.setVisible(False)
        layout.addWidget(self.gpu_combo)
        # Custom GPU fields (hidden by default)
        self.gpu_custom_fields = QFormLayout()
        self.gpu_flops_edit = QLineEdit("1e12")
        self.gpu_custom_fields.addRow("FLOPS:", self.gpu_flops_edit)
        self.gpu_mem_bw_edit = QLineEdit("300e9")
        self.gpu_custom_fields.addRow("Memory Bandwidth (B/s):", self.gpu_mem_bw_edit)
        self.gpu_network_edit = QLineEdit("100e9")
        self.gpu_custom_fields.addRow("Network Speed (bps):", self.gpu_network_edit)
        self.gpu_time_in_driver_edit = QLineEdit("8")
        self.gpu_custom_fields.addRow("Time in Driver (us):", self.gpu_time_in_driver_edit)
        self.gpu_custom_fields_widget = QWidget()
        self.gpu_custom_fields_widget.setLayout(self.gpu_custom_fields)
        self.gpu_custom_fields_widget.setVisible(False)
        layout.addWidget(self.gpu_custom_fields_widget)
        # --- Button row ---
        button_layout = QHBoxLayout()
        self.add_btn = QPushButton("Add")
        self.add_btn.clicked.connect(self.accept)
        button_layout.addWidget(self.add_btn)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)
        self.setLayout(layout)
        # --- Signals ---
        self.cpu_combo.currentIndexChanged.connect(self._on_cpu_changed)
        self.add_gpu_checkbox.toggled.connect(self._on_add_gpu_toggled)
        self.gpu_combo.currentIndexChanged.connect(self._on_gpu_changed)
        # State
        self.result_type = None
        self.result_index = None
        # After all widgets are created, pre-populate if editing
        if existing_resource is not None:
            # Set name
            self.name_edit.setText(getattr(existing_resource, 'name', 'Computer'))
            # Try to match CPU in dropdown
            cpu_name = getattr(existing_resource, 'name', None)
            cpu_idx = None
            for i, label in enumerate(self.cpu_names):
                if label == cpu_name:
                    cpu_idx = i
                    break
            if cpu_idx is not None:
                self.cpu_combo.setCurrentIndex(cpu_idx)
            else:
                # Custom CPU
                self.cpu_combo.setCurrentIndex(len(self.cpu_names) - 1)
                self.cpu_custom_fields_widget.setVisible(True)
                # Fill custom fields if present
                self.cores_edit.setText(str(getattr(existing_resource, 'cores', '16')))
                self.freq_edit.setText(str(getattr(existing_resource, 'core_frequency', '2.6e9')))
                self.flops_edit.setText(str(getattr(existing_resource, 'flops_per_cycle', '32')))
                self.mem_channels_edit.setText(str(getattr(existing_resource, 'memory_channels', '4')))
                self.mem_width_edit.setText(str(getattr(existing_resource, 'memory_width', '64')))
                self.mem_freq_edit.setText(str(getattr(existing_resource, 'memory_frequency', '3200e6')))
                self.network_edit.setText(str(getattr(existing_resource, 'network_speed', '100e9')))
            # GPU
            attached_gpus = getattr(existing_resource, 'attached_gpus', [])
            if attached_gpus:
                self.add_gpu_checkbox.setChecked(True)
                self.gpu_combo.setVisible(True)
                gpu = attached_gpus[0]
                gpu_name = getattr(gpu, 'name', None)
                gpu_idx = None
                for i, label in enumerate(self.gpu_names):
                    if label == gpu_name:
                        gpu_idx = i
                        break
                if gpu_idx is not None:
                    self.gpu_combo.setCurrentIndex(gpu_idx)
                else:
                    # Custom GPU
                    self.gpu_combo.setCurrentIndex(len(self.gpu_names) - 1)
                    self.gpu_custom_fields_widget.setVisible(True)
                    self.gpu_flops_edit.setText(str(getattr(gpu, 'flops', '1e12')))
                    self.gpu_mem_bw_edit.setText(str(getattr(gpu, 'memory_bandwidth', '300e9')))
                    self.gpu_network_edit.setText(str(getattr(gpu, 'network_speed', '100e9')))
                    self.gpu_time_in_driver_edit.setText(str(getattr(gpu, 'time_in_driver', '8')))
    def _on_cpu_changed(self, idx):
        self.cpu_custom_fields_widget.setVisible(idx == len(self.cpu_names) - 1)
        self.cpu_name_string = self.cpu_combo.currentText()
    def _on_add_gpu_toggled(self, checked):
        self.gpu_combo.setVisible(checked)
        self.gpu_custom_fields_widget.setVisible(checked and self.gpu_combo.currentIndex() == len(self.gpu_names) - 1)
    def _on_gpu_changed(self, idx):
        self.gpu_custom_fields_widget.setVisible(idx == len(self.gpu_names) - 1 and self.add_gpu_checkbox.isChecked())
    def get_selected_resource(self):
        # CPU
        cpu_idx = self.cpu_combo.currentIndex()
        if cpu_idx == len(self.cpu_names) - 1:
            # Custom CPU
            cpu_resource = create_compute_resources(
                cores=int(self.cores_edit.text()),
                core_frequency=float(self.freq_edit.text()),
                flops_per_cycle=int(self.flops_edit.text()),
                memory_channels=int(self.mem_channels_edit.text()),
                memory_width=int(self.mem_width_edit.text()),
                memory_frequency=float(self.mem_freq_edit.text()),
                network_speed=float(self.network_edit.text()),
                time_in_driver=5,
            )
        else:
            cpu_func = self.cpu_funcs[cpu_idx]
            cpu_resource = cpu_func()
        cpu_resource.name = self.name_edit.text().strip()
        # GPU
        attached_gpus = []
        if self.add_gpu_checkbox.isChecked():
            gpu_idx = self.gpu_combo.currentIndex()
            if gpu_idx == len(self.gpu_names) - 1:
                # Custom GPU
                from daolite.compute.base_resources import create_gpu_resource
                gpu_resource = create_gpu_resource(
                    flops=float(self.gpu_flops_edit.text()),
                    memory_bandwidth=float(self.gpu_mem_bw_edit.text()),
                    network_speed=float(self.gpu_network_edit.text()),
                    time_in_driver=float(self.gpu_time_in_driver_edit.text()),
                )
            else:
                gpu_func = self.gpu_funcs[gpu_idx]
                gpu_resource = gpu_func()
            attached_gpus.append(gpu_resource)
        # Always update attached_gpus, even if empty (removes GPU if unchecked)
        cpu_resource.attached_gpus = attached_gpus
        return cpu_resource
    def get_name(self):
        return self.name_edit.text().strip()

    def cpu_name(self):
        return self.cpu_name_string


class PipelineDesignerApp(QMainWindow):
    """
    Main application window for the daolite pipeline designer.

    Provides a graphical interface for designing AO pipelines with emphasis on
    network and multi-compute node configurations.
    """

    def __init__(self, json_path=None):
        super().__init__()

        self.setWindowTitle("daolite Pipeline Designer")
        self.resize(1200, 800)

        # --- Theme selection ---
        self.theme = get_saved_theme()
        set_app_style(self, self.theme)
        font = QFont("Segoe UI", 11)
        self.setFont(font)

        # Set up the scene and view
        self.scene = PipelineScene(self, theme=self.theme)
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(
            QPainter.Antialiasing
        ) 
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

        self.pipeline_title = "AO Pipeline"  # Default pipeline title

        self.undo_stack = QUndoStack(self)

        # Initialize execution_method ComboBox with options
        self.execution_method = QComboBox()
        self.execution_method.addItems(["Python", "JSON"])
        self.execution_method.setCurrentText("Python")  # Default to Python

        self._create_toolbar()
        self._create_menu()

        # Connect context menu actions
        self.scene.selectionChanged.connect(self._update_selection)
        self.selected_component = None

        # Centroid agenda file path and array
        self.centroid_agenda_path = None
        self.centroid_agenda = None

        # If a JSON path is provided, try to load the pipeline
        if json_path:
            from .file_io import load_pipeline
            try:
                success = load_pipeline(self.scene, json_path, self.component_counts)
                if not success:
                    QMessageBox.warning(self, "Load Error", f"Failed to load pipeline from {json_path}")
            except Exception as e:
                QMessageBox.critical(self, "Load Error", f"Error loading pipeline: {e}")

    def _create_toolbar(self):
        from PyQt5.QtWidgets import QToolBar, QToolButton, QFrame, QSizePolicy
        from PyQt5.QtGui import QIcon
        from PyQt5.QtCore import QSize

        # Remove any existing toolbars
        for tb in self.findChildren(QToolBar):
            self.removeToolBar(tb)

        self.toolbar = QToolBar("Main Toolbar")
        self.toolbar.setMovable(False)
        self.toolbar.setFloatable(False)
        self.toolbar.setIconSize(QSize(32, 32))
        self.toolbar.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.addToolBar(Qt.TopToolBarArea, self.toolbar)

        # Set toolbar background color based on theme
        theme = getattr(self, 'theme', 'light')
        if theme == 'dark':
            self.toolbar.setStyleSheet("QToolBar { background: #232b3a; border: none; padding: 8px 4px; } QToolBar QLabel, QToolBar QPushButton, QToolBar QToolButton { color: #e0e6ef; }")
        else:
            self.toolbar.setStyleSheet("QToolBar { background: #e7f2fa; border: none; padding: 8px 4px; } QToolBar QLabel, QToolBar QPushButton, QToolBar QToolButton { color: #375a7f; }")

        def add_section_label(text):
            label = QLabel(f"  <b>{text}</b>  ")
            label.setStyleSheet("font-size: 14px; color: #1a1a1a; margin: 0 8px; letter-spacing: 0.5px;")
            self.toolbar.addWidget(label)

        def add_separator():
            sep = QFrame()
            sep.setFrameShape(QFrame.VLine)
            sep.setFrameShadow(QFrame.Sunken)
            sep.setStyleSheet("color: #b0c4de; margin: 0 8px;")
            sep.setFixedHeight(40)
            self.toolbar.addWidget(sep)

        # --- Add Computer Button (no label, prominent style) ---
        btn_add_computer = QToolButton()
        btn_add_computer.setIcon(QIcon.fromTheme("computer"))
        btn_add_computer.setText("Add Computer")
        btn_add_computer.setToolTip("Add a compute box (computer node) to the scene")
        btn_add_computer.clicked.connect(self._add_compute_box)
        btn_add_computer.setStyleSheet("color: #1976d2; font-weight: bold; font-size: 15px; margin-right: 12px;")
        self.toolbar.addWidget(btn_add_computer)
        add_separator()

        # --- File Dropdown (QToolButton with menu) ---
        file_menu_btn = QToolButton()
        file_menu_btn.setIcon(QIcon.fromTheme("document-new"))
        file_menu_btn.setText("File")
        file_menu_btn.setPopupMode(QToolButton.InstantPopup)
        file_menu_btn.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        file_menu_btn.setStyleSheet("color: #444; font-weight: bold; font-size: 13px;")
        from PyQt5.QtWidgets import QMenu
        file_menu = QMenu()
        act_new = file_menu.addAction(QIcon.fromTheme("document-new"), "New Pipeline")
        act_new.triggered.connect(self._new_pipeline)
        act_open = file_menu.addAction(QIcon.fromTheme("document-open"), "Open Pipeline")
        act_open.triggered.connect(self._load_pipeline)
        act_save = file_menu.addAction(QIcon.fromTheme("document-save"), "Save Pipeline")
        act_save.triggered.connect(self._save_pipeline)
        file_menu_btn.setMenu(file_menu)
        self.toolbar.addWidget(file_menu_btn)
        add_separator()

        # --- Components Section ---
        add_section_label("Components")
        comp_buttons = [
            ("Camera", ComponentType.CAMERA, "camera-photo"),
            ("Network", ComponentType.NETWORK, "network-wired"),
            ("Calibration", ComponentType.CALIBRATION, "color-balance"),
            ("Centroider", ComponentType.CENTROIDER, "view-split-left-right"),
            ("Reconstruction", ComponentType.RECONSTRUCTION, "system-run"),
            ("Control", ComponentType.CONTROL, "media-playback-start"),
        ]
        for label, ctype, icon in comp_buttons:
            btn = QToolButton()
            btn.setIcon(QIcon.fromTheme(icon))
            btn.setText(label)
            btn.setToolTip(f"Add a {label.lower()} component")
            btn.clicked.connect(lambda _, t=ctype: self._add_component(t))
            btn.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
            btn.setStyleSheet("color: #222; font-weight: 500;")
            self.toolbar.addWidget(btn)
        add_separator()

        # --- Actions Section ---
        add_section_label("Actions")
        # Generate button with dropdown for method selection
        btn_generate = QToolButton()
        btn_generate.setIcon(QIcon.fromTheme("document-export"))
        btn_generate.setText("Generate")
        btn_generate.setToolTip("Generate pipeline code")
        btn_generate.setStyleSheet("color: #222; font-weight: 500;")
        btn_generate.setPopupMode(QToolButton.MenuButtonPopup)
        from PyQt5.QtWidgets import QMenu
        generate_menu = QMenu()
        act_gen_python = generate_menu.addAction("Generate Python")
        act_gen_json = generate_menu.addAction("Generate JSON")
        def gen_python():
            self.execution_method.setCurrentText("Python")
            self._generate_code()
        def gen_json():
            self.execution_method.setCurrentText("JSON")
            self._generate_code()
        act_gen_python.triggered.connect(gen_python)
        act_gen_json.triggered.connect(gen_json)
        btn_generate.setMenu(generate_menu)
        btn_generate.clicked.connect(gen_python)  # Default to Python if main button is clicked
        self.toolbar.addWidget(btn_generate)

        # Run button with dropdown for method selection (unchanged)
        btn_run = QToolButton()
        btn_run.setIcon(QIcon.fromTheme("system-run"))
        btn_run.setText("Run")
        btn_run.setToolTip("Execute pipeline and display visualization")
        btn_run.setStyleSheet("color: #222; font-weight: 500;")
        btn_run.setPopupMode(QToolButton.MenuButtonPopup)
        run_menu = QMenu()
        act_run_python = run_menu.addAction("Run as Python")
        act_run_json = run_menu.addAction("Run as JSON")
        def run_python():
            self.execution_method.setCurrentText("Python")
            self._run_pipeline()
        def run_json():
            self.execution_method.setCurrentText("JSON")
            self._run_pipeline()
        act_run_python.triggered.connect(run_python)
        act_run_json.triggered.connect(run_json)
        btn_run.setMenu(run_menu)
        btn_run.clicked.connect(run_python)  # Default to Python if main button is clicked
        self.toolbar.addWidget(btn_run)
        add_separator()

        # --- View Section ---
        add_section_label("View")
        btn_zoom_in = QToolButton()
        btn_zoom_in.setIcon(QIcon.fromTheme("zoom-in"))
        btn_zoom_in.setText("Zoom In")
        btn_zoom_in.setToolTip("Zoom in on the pipeline view")
        btn_zoom_in.clicked.connect(lambda: self.view.scale(1.2, 1.2))
        btn_zoom_in.setStyleSheet("color: #222; font-weight: 500;")
        self.toolbar.addWidget(btn_zoom_in)
        btn_zoom_out = QToolButton()
        btn_zoom_out.setIcon(QIcon.fromTheme("zoom-out"))
        btn_zoom_out.setText("Zoom Out")
        btn_zoom_out.setToolTip("Zoom out on the pipeline view")
        btn_zoom_out.clicked.connect(lambda: self.view.scale(0.8, 0.8))
        btn_zoom_out.setStyleSheet("color: #222; font-weight: 500;")
        self.toolbar.addWidget(btn_zoom_out)
        add_separator()

        self.statusBar().showMessage("Ready")

    def _add_compute_box(self):
        """Add a ComputeBox (computer node) to the scene."""
        dlg = ResourceSelectionDialog(self)
        if dlg.exec_():
            cpu  = dlg.cpu_name()
            print(f"Selected CPU: {cpu}")
            compute_resource = dlg.get_selected_resource()
            cpu_name = getattr(compute_resource, "name", "Computer")
            compute_box = ComputeBox(cpu_name, compute=compute_resource, cpu_resource=cpu)
            view_center = self.view.mapToScene(self.view.viewport().rect().center())
            compute_box.setPos(view_center.x() - 160, view_center.y() - 110)
            self.scene.addItem(compute_box)
            # Add GPUBox(es) if any attached_gpus
            if hasattr(compute_resource, 'attached_gpus'):
                for idx, gpu_resource in enumerate(compute_resource.attached_gpus):
                    gpu_name = getattr(gpu_resource, 'name', f"GPU{idx+1}")
                    gpu_box = GPUBox(gpu_name, gpu_resource=gpu_resource)
                    # Place GPUBox at a default offset inside the ComputeBox
                    gpu_box.setPos(30, 60 + 40 * idx)
                    compute_box.add_child(gpu_box)
                    self.scene.addItem(gpu_box)

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
        dlg = StyledTextInputDialog("Add GPU", "Enter GPU name:", "GPU", self)
        if not dlg.exec_():
            return
        name = dlg.getText()
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
        new_action.setShortcut(QKeySequence.New)
        new_action.triggered.connect(self._new_pipeline)
        file_menu.addAction(new_action)

        save_action = QAction("&Save Pipeline", self)
        save_action.setShortcut(QKeySequence.Save)
        save_action.triggered.connect(self._save_pipeline)
        file_menu.addAction(save_action)

        load_action = QAction("&Load Pipeline", self)
        load_action.setShortcut(QKeySequence.Open)
        load_action.triggered.connect(self._load_pipeline)
        file_menu.addAction(load_action)

        file_menu.addSeparator()

        generate_action = QAction("&Generate Code", self)
        generate_action.setShortcut("Ctrl+G")
        generate_action.triggered.connect(self._generate_code)
        file_menu.addAction(generate_action)

        export_config_action = QAction("Export Config &YAML", self)
        export_config_action.setShortcut("Ctrl+E")
        export_config_action.triggered.connect(self._export_config)
        file_menu.addAction(export_config_action)

        # Add Centroid Agenda Tool action
        centroid_agenda_action = QAction("Centroid Agenda Tool", self)
        centroid_agenda_action.triggered.connect(lambda: show_centroid_agenda_tool(self))
        file_menu.addAction(centroid_agenda_action)

        file_menu.addSeparator()

        set_title_action = QAction("Set Pipeline Title...", self)
        set_title_action.triggered.connect(self._set_pipeline_title)
        file_menu.addAction(set_title_action)

        file_menu.addSeparator()

        exit_action = QAction("E&xit", self)
        exit_action.setShortcut(QKeySequence.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Edit menu
        edit_menu = menu_bar.addMenu("&Edit")

        undo_action = QAction("&Undo", self)
        undo_action.setShortcut(QKeySequence.Undo)
        undo_action.triggered.connect(self.undo_stack.undo)
        edit_menu.addAction(undo_action)

        redo_action = QAction("&Redo", self)
        redo_action.setShortcut(QKeySequence.Redo)
        redo_action.triggered.connect(self.undo_stack.redo)
        edit_menu.addAction(redo_action)

        rename_action = QAction("&Rename Selected", self)
        rename_action.setShortcut("Ctrl+R")
        rename_action.triggered.connect(self._rename_selected)
        edit_menu.addAction(rename_action)

        delete_action = QAction("&Delete Selected", self)
        delete_action.setShortcut(QKeySequence.Delete)
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

        # --- Theme submenu ---
        view_menu.addSeparator()
        theme_menu = view_menu.addMenu("Theme")
        theme_group = []
        for label, key in [("System Default", "system"), ("Light", "light"), ("Dark", "dark")]:
            act = QAction(label, self, checkable=True)
            act.setChecked(self.theme == key)
            act.triggered.connect(lambda checked, k=key: self._set_theme(k))
            theme_menu.addAction(act)
            theme_group.append(act)
        self._theme_actions = theme_group

        # Help menu
        help_menu = menu_bar.addMenu("&Help")

        about_action = QAction("&About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

        shortcut_action = QAction("Keyboard Shortcuts", self)
        shortcut_action.setShortcut("Ctrl+H")
        shortcut_action.triggered.connect(self._show_shortcuts)
        help_menu.addAction(shortcut_action)

    def _set_theme(self, theme):
        self.theme = theme
        save_theme(theme)
        set_app_style(self, theme)
        self.scene.set_theme(theme)
        # Update toolbar color
        self._create_toolbar()
        self.update()
        for widget in self.findChildren(QWidget):
            set_app_style(widget, theme)
        if hasattr(self, '_theme_actions'):
            for act in self._theme_actions:
                act.setChecked(act.text().lower().startswith(theme))

    def _show_shortcuts(self):
        dlg = ShortcutHelpDialog(self)
        dlg.exec_()

    def keyPressEvent(self, event):
        # Let QUndoStack handle undo/redo
        if event.matches(QKeySequence.Undo):
            self.undo_stack.undo()
            return
        if event.matches(QKeySequence.Redo):
            self.undo_stack.redo()
            return
        super().keyPressEvent(event)

    def _set_pipeline_title(self):
        dlg = StyledTextInputDialog("Set Pipeline Title", "Enter pipeline title:", self.pipeline_title, self)
        if dlg.exec_():
            self.pipeline_title = dlg.getText()
            self.statusBar().showMessage(f"Pipeline title set to: {self.pipeline_title}", 3000)

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
            # 5. Highlight connections for selected component
            for item in self.scene.items():
                if hasattr(item, 'set_highlight'):
                    item.set_highlight(False)
                if hasattr(item, 'highlight_connection'):
                    item.highlight_connection(False)
            for conn in getattr(self.scene, 'connections', []):
                if conn.start_block == self.selected_component or conn.end_block == self.selected_component:
                    if hasattr(conn, 'highlight_connection'):
                        conn.highlight_connection(True)
        else:
            self.selected_component = None
            # Remove all highlights
            for item in self.scene.items():
                if hasattr(item, 'set_highlight'):
                    item.set_highlight(False)
                if hasattr(item, 'highlight_connection'):
                    item.highlight_connection(False)

    def _quick_save_pipeline(self):
        """Quickly save pipeline design to a default file."""
        import os
        default_path = os.path.expanduser("~/daolite_quicksave.json")
        from .file_io import save_pipeline_to_file
        save_pipeline_to_file(
            self.scene,
            self._get_all_components(),
            self.scene.connections,
            default_path
        )
        self.statusBar().showMessage(f"Pipeline quick-saved to {default_path}", 3000)

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
        dlg = StyledTextInputDialog("Rename Component", "Enter new name:", self.selected_component.name, self)
        if dlg.exec_():
            name = dlg.getText()
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
        # Pass current resource for editing if available
        existing_resource = item.compute if hasattr(item, 'compute') else None
        dlg = ResourceSelectionDialog(self, existing_resource=existing_resource)
        if dlg.exec_():
            new_resource = dlg.get_selected_resource()
            if isinstance(item, ComputeBox):
                item.compute = new_resource
                # Remove all existing GPUBox children
                for child in list(item.childItems()):
                    if isinstance(child, GPUBox):
                        item.childItems().remove(child)
                        self.scene.removeItem(child)
                # Add GPUBox if attached_gpus present
                if hasattr(new_resource, 'attached_gpus') and new_resource.attached_gpus:
                    for idx, gpu_resource in enumerate(new_resource.attached_gpus):
                        gpu_name = getattr(gpu_resource, 'name', f"GPU{idx+1}")
                        gpu_box = GPUBox(gpu_name, gpu_resource=gpu_resource)
                        gpu_box.setPos(30, 60 + 40 * idx)
                        item.add_child(gpu_box)
                        self.scene.addItem(gpu_box)
                # Update all child components' display
                for child in item.childItems():
                    if isinstance(child, ComponentBlock):
                        child.update()
            elif isinstance(item, GPUBox):
                item.compute = new_resource
                for child in item.childItems():
                    if isinstance(child, ComponentBlock):
                        child.update()
            else:
                parent = item.parentItem()
                if parent and isinstance(parent, (ComputeBox, GPUBox)):
                    parent.compute = new_resource
                    item.update()
                else:
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
        # Prompt for pipeline title before saving
        dlg = StyledTextInputDialog("Set Pipeline Title", "Enter pipeline title:", self.pipeline_title, self)
        if not dlg.exec_():
            return  # User cancelled, do not proceed to save
        self.pipeline_title = dlg.getText()
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Pipeline Design", "", "JSON Files (*.json)"
        )
        if filename:
            from .file_io import save_pipeline_to_file
            success = save_pipeline_to_file(
                self.scene, 
                self._get_all_components(), 
                self.scene.connections, 
                filename
            )
            if success:
                QMessageBox.information(
                    self, "Pipeline Saved", f"Pipeline design saved to {filename}"
                )
            else:
                QMessageBox.warning(
                    self, "Save Error", f"Failed to save pipeline to {filename}"
                )

    def _load_pipeline(self):
        """Load pipeline design from a file."""
        from .file_io import load_pipeline
        filename, _ = QFileDialog.getOpenFileName(
            self, "Load Pipeline Design", "", "JSON Files (*.json);;All Files (*)"
        )
        if filename:
            success = load_pipeline(
                self.scene,
                filename,
                self.component_counts
            )
            if success:
                QMessageBox.information(
                    self, "Pipeline Loaded", f"Pipeline design loaded from {filename}"
                )
            else:
                QMessageBox.critical(
                    self, "Load Error", f"Failed to load pipeline from {filename}"
                )

    def _export_config(self):
        """Export configuration as YAML."""
        components = self._get_all_components()

        if not components:
            QMessageBox.warning(
                self, "Empty Pipeline", "No components to export configuration from."
            )
            return

        # Find camera and optics componentsØ
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
        filename, _ = QFileDialog.getOpenFileName(
            self, "Load Pipeline Design", "", "JSON Files (*.json);;All Files (*)"
        )
        if not filename:
            return
            
        # Use the extracted load_pipeline function from file_io module
        from .file_io import load_pipeline
        success = load_pipeline(
            self.scene,
            filename,
            self.component_counts
        )
        
        if success:
            QMessageBox.information(
                self, "Pipeline Loaded", f"Pipeline design loaded from {filename}"
            )
        else:
            QMessageBox.critical(
                self, "Load Error", f"Failed to load pipeline from {filename}"
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

    def _run_pipeline(self):
        """Run the pipeline and display visualization in a popup window."""
        # Use the extracted run_pipeline function from pipeline_executor module
        from .pipeline_executor import run_pipeline
        
        components = self._get_all_components()
        execution_method = self.execution_method.currentText()
        
        run_pipeline(self, components, self.scene, execution_method)

    @staticmethod
    def run(json_path=None):
        """Run the pipeline designer application."""
        app = QApplication(sys.argv)
        window = PipelineDesignerApp(json_path=json_path)
        window.show()
        sys.exit(app.exec_())

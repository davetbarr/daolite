"""
Connection classes for the daolite pipeline designer.

This module provides graphical representations of connections between components.
"""

from typing import Optional, List, Tuple, Any
from PyQt5.QtWidgets import QGraphicsPathItem, QMenu, QDialog, QFormLayout, QLineEdit, QDialogButtonBox, QLabel, QVBoxLayout
from PyQt5.QtCore import Qt, QPointF
from PyQt5.QtGui import QPen, QPainterPath, QColor

from .components import Port, ComponentBlock, PortType, TransferIndicator


class TransferPropertiesDialog(QDialog):
    def __init__(self, parent=None, data_size=None, grouping=None):
        super().__init__(parent)
        from daolite.gui.designer.style_utils import set_app_style
        set_app_style(self)
        self.setWindowTitle("Set Data Transfer Properties")
        self.resize(360, 140)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.data_size_edit = QLineEdit(str(data_size) if data_size is not None else "")
        self.data_size_edit.setPlaceholderText("e.g. 4096")
        self.grouping_edit = QLineEdit(str(grouping) if grouping is not None else "")
        self.grouping_edit.setPlaceholderText("e.g. 1 frame, 8 packets")
        form.addRow("<b>Data Size (bytes):</b>", self.data_size_edit)
        form.addRow("<b>Grouping:</b>", self.grouping_edit)
        layout.addLayout(form)
        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

    def get_values(self):
        return self.data_size_edit.text(), self.grouping_edit.text()


class Connection(QGraphicsPathItem):
    """
    A visual connection between component ports in the pipeline designer.

    Represents data flow between components with a configurable path.
    """

    def __init__(
        self,
        start_block: Optional[ComponentBlock] = None,
        start_port: Optional[Port] = None,
        end_block: Optional[ComponentBlock] = None,
        end_port: Optional[Port] = None,
    ):
        """
        Initialize a connection.

        Args:
            start_block: Source component block
            start_port: Source port
            end_block: Destination component block
            end_port: Destination port
        """
        super().__init__()

        self.start_block = start_block
        self.start_port = start_port
        self.end_block = end_block
        self.end_port = end_port
        
        # For tracking transfer indicators
        self.transfer_indicators: List[Tuple[str, QPointF]] = []

        # Set up appearance
        self.setPen(
            QPen(QColor(60, 60, 60), 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        )
        self.setZValue(-1)  # Below components
        self.setFlag(self.ItemIsSelectable, True)  # Make connection selectable

        # For tracking during creation
        self.temp_end_point: Optional[QPointF] = None

        self.update_path()

        # Set up event tracking for connected objects
        self._setup_event_tracking()
        
    def _setup_event_tracking(self):
        """Set up tracking for item changes in connected components."""
        # This function enables automatic indicator updates when components move
        # Only install filters if we have a scene and both items are in it
        if not self.scene():
            return
            
        if self.start_block and self.start_block.scene() == self.scene():
            self.start_block.installSceneEventFilter(self)
        if self.end_block and self.end_block.scene() == self.scene():
            self.end_block.installSceneEventFilter(self)
            
        # Also track parent container movements
        self._track_parent_containers()
            
    def _track_parent_containers(self):
        """Track changes in parent containers (GPU boxes, Compute boxes)."""
        # For source component parent containers
        if not self.scene():
            return
            
        if self.start_block:
            parent = self.start_block.parentItem()
            if parent and parent.scene() == self.scene():
                parent.installSceneEventFilter(self)
                # Also track grandparent (e.g., ComputeBox containing a GPUBox)
                grandparent = parent.parentItem() if hasattr(parent, 'parentItem') else None
                if grandparent and grandparent.scene() == self.scene():
                    grandparent.installSceneEventFilter(self)
                    
        # For destination component parent containers  
        if self.end_block:
            parent = self.end_block.parentItem()
            if parent and parent.scene() == self.scene():
                parent.installSceneEventFilter(self)
                # Also track grandparent (e.g., ComputeBox containing a GPUBox)
                grandparent = parent.parentItem() if hasattr(parent, 'parentItem') else None
                if grandparent and grandparent.scene() == self.scene():
                    grandparent.installSceneEventFilter(self)
        
    def sceneEventFilter(self, watched: Any, event: Any) -> bool:
        """Filter scene events for connected components and containers."""
        # Check for item change events that might affect indicators
        if event.type() in [11]:  # QEvent.GraphicsSceneMove = 11
            # Item moved - update the connection path and indicators
            self.update_path()
            # Also refresh transfer indicators
            self.update_transfer_indicators()
            return False  # Let the event propagate
            
        # Let the event propagate to other handlers
        return False
        
    def update_path(self):
        """Update the connection path between source and destination ports."""
        path = QPainterPath()

        # Get start point - use get_scene_position which handles parent-child nesting
        if self.start_port:
            start_pos = self.start_port.get_scene_position()
        else:
            # Default start point if we don't have a port yet
            start_pos = QPointF(0, 0)

        # Get end point - use get_scene_position which handles parent-child nesting
        if self.end_port:
            end_pos = self.end_port.get_scene_position()
        elif self.temp_end_point:
            # Use temporary end point for interactive creation
            end_pos = self.temp_end_point
        else:
            # Default end if we don't have an end point yet
            end_pos = start_pos + QPointF(100, 0)

        # Start the path
        path.moveTo(start_pos)

        # Calculate control points for a nice curve
        dx = end_pos.x() - start_pos.x()
        control1 = QPointF(start_pos.x() + dx * 0.5, start_pos.y())
        control2 = QPointF(end_pos.x() - dx * 0.5, end_pos.y())

        # Create a cubic bezier curve
        path.cubicTo(control1, control2, end_pos)

        # Set the path
        self.setPath(path)

        # Make the connection more prominent (thicker, brighter)
        self.setPen(QPen(QColor(0, 180, 255), 4, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))

    def update_transfer_indicators(self):
        """Update the positions of all transfer indicators when components move."""
        if self.scene():
            # Import locally to avoid circular import issues
            from .connection_manager import update_connection_indicators
            update_connection_indicators(self.scene(), self)

    def set_temp_end_point(self, point: QPointF):
        """Set a temporary end point for interactive creation."""
        self.temp_end_point = point
        self.update_path()

    def complete_connection(self, end_block: ComponentBlock, end_port: Port) -> bool:
        """
        Complete the connection to the target port.

        Args:
            end_block: Target component block
            end_port: Target port

        Returns:
            bool: True if connection was successfully completed
        """
        # Validate connection
        if not self.start_port or not self.start_block:
            return False

        # Check for valid input/output pairing
        if (
            self.start_port.port_type == PortType.INPUT
            and end_port.port_type == PortType.INPUT
        ):
            return False

        if (
            self.start_port.port_type == PortType.OUTPUT
            and end_port.port_type == PortType.OUTPUT
        ):
            return False

        # Set end points
        self.end_block = end_block
        self.end_port = end_port
        self.temp_end_point = None

        # Update the connections in both ports
        if self.start_port.port_type == PortType.OUTPUT:
            self.start_port.connected_to.append((end_block, end_port))
            end_port.connected_to.append((self.start_block, self.start_port))
        else:
            end_port.connected_to.append((self.start_block, self.start_port))
            self.start_port.connected_to.append((end_block, end_port))

        # Update the path
        self.update_path()
        
        # Set up event tracking only after both blocks are connected and in the scene
        if self.scene():
            self._setup_event_tracking()
            
            # Add transfer indicators after connection is complete
            from .connection_manager import update_connection_indicators
            update_connection_indicators(self.scene(), self)
            
        return True

    def disconnect(self):
        """Remove connection between ports."""
        # Remove any associated transfer indicators first
        if self.scene():
            # Find and remove all transfer indicators associated with this connection
            for item in self.scene().items():
                if isinstance(item, TransferIndicator) and hasattr(item, 'connection') and item.connection is self:
                    self.scene().removeItem(item)
        
        if self.start_port and self.end_port:
            # Remove from start port connections
            self.start_port.connected_to = [
                (block, port)
                for block, port in self.start_port.connected_to
                if port is not self.end_port
            ]

            # Remove from end port connections
            self.end_port.connected_to = [
                (block, port)
                for block, port in self.end_port.connected_to
                if port is not self.start_port
            ]

    def paint(self, painter, option, widget=None):
        """Custom paint method to highlight the connection if selected."""
        # Always prominent, extra highlight if selected
        if self.isSelected():
            painter.setPen(QPen(QColor(255, 80, 80), 6, Qt.SolidLine))
        else:
            painter.setPen(self.pen())

        # Optional: subtle shadow/glow
        painter.save()
        painter.setPen(QPen(QColor(0, 180, 255, 80), 10, Qt.SolidLine))
        painter.drawPath(self.path())
        painter.restore()

        painter.drawPath(self.path())
        
    def add_transfer_indicator(self, indicator_type, position):
        """Add a transfer indicator to this connection."""
        # This method will be called by PipelineScene to associate indicators with connections
        self.transfer_indicators.append((indicator_type, position))
        
    def get_path_point_at_percent(self, percent):
        """Get a point on the path at the given percentage (0-1)."""
        # For simple implementation, we'll use a linear interpolation between start and end
        # A more accurate version would follow the actual bezier curve
        if not self.start_port or (not self.end_port and not self.temp_end_point):
            return QPointF(0, 0)
            
        start_pos = self.start_port.get_scene_position()
        if self.end_port:
            end_pos = self.end_port.get_scene_position()
        else:
            end_pos = self.temp_end_point
            
        return QPointF(
            start_pos.x() + (end_pos.x() - start_pos.x()) * percent,
            start_pos.y() + (end_pos.y() - start_pos.y()) * percent
        )

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            self.setSelected(True)
            self.contextMenuEvent(event)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        # Open the transfer properties dialog on double-click
        dlg = TransferPropertiesDialog(
            parent=None,
            data_size=getattr(self, 'data_size', None),
            grouping=getattr(self, 'grouping', None)
        )
        if dlg.exec_():
            data_size, grouping = dlg.get_values()
            self.data_size = data_size
            self.grouping = grouping
            self.setToolTip(f"Data Size: {data_size} bytes\nGrouping: {grouping}")
        event.accept()

    def contextMenuEvent(self, event):
        menu = QMenu()
        set_data_action = menu.addAction("Set Data Transfer Properties")
        delete_action = menu.addAction("Delete Connection")
        action = menu.exec_(event.screenPos())
        if action == set_data_action:
            dlg = TransferPropertiesDialog(
                parent=None,
                data_size=getattr(self, 'data_size', None),
                grouping=getattr(self, 'grouping', None)
            )
            if dlg.exec_():
                data_size, grouping = dlg.get_values()
                self.data_size = data_size
                self.grouping = grouping
                self.setToolTip(f"Data Size: {data_size} bytes\nGrouping: {grouping}")
        elif action == delete_action:
            self.disconnect()
            if self.scene():
                self.scene().removeItem(self)

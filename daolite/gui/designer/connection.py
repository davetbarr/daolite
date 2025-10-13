"""
Connection classes for the daolite pipeline designer.

This module provides graphical representations of connections between components.
"""

from typing import List, Optional, Tuple

from PyQt5.QtCore import QPointF, Qt
from PyQt5.QtGui import QBrush, QColor, QFont, QPainterPath, QPen
from PyQt5.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGraphicsPathItem,
    QGraphicsRectItem,
    QGraphicsTextItem,
    QLineEdit,
    QMenu,
    QVBoxLayout,
)

from .component_block import ComponentBlock
from .port import Port, PortType
from .style_utils import set_app_style


class TransferIndicator(QGraphicsRectItem):
    """
    Visual indicator for network or PCIe transfers between compute resources.

    These indicators appear on connections crossing resource boundaries.
    """

    def __init__(self, transfer_type, parent=None):
        super().__init__(parent)
        self.transfer_type = transfer_type  # "PCIe" or "Network"
        self.setRect(0, 0, 24, 16)
        self.setZValue(10)  # Above connections, above components
        self.setCacheMode(self.DeviceCoordinateCache)
        self.setAcceptHoverEvents(True)  # Enable hover events for tooltips

        # Create label
        self.label = QGraphicsTextItem(self)
        self.label.setPlainText(transfer_type)
        self.label.setFont(QFont("Arial", 6))
        # Center text in the indicator
        self.label.setPos(2, 0)

        # Associate with a connection
        self.connection = None

    def _generate_detailed_tooltip(self) -> str:
        """Generate a detailed tooltip showing transfer type and specs."""
        if not self.connection:
            return f"{self.transfer_type} Transfer"

        # Get the connection's source and destination components
        src_comp = getattr(self.connection, "start_block", None)
        dst_comp = getattr(self.connection, "end_block", None)

        if not src_comp or not dst_comp:
            return f"{self.transfer_type} Transfer"

        # Get compute resources
        src_compute = src_comp.get_compute_resource()
        dst_compute = dst_comp.get_compute_resource()

        tooltip = f"<b>{self.transfer_type} Transfer</b><br>"
        tooltip += f"From: {src_comp.name}<br>"
        tooltip += f"To: {dst_comp.name}<br><br>"

        # Add data size information if available
        data_size = getattr(self.connection, "data_size", None)
        if data_size:
            try:
                size_value = float(data_size)
                # Format based on size
                if size_value >= 1_000_000_000:
                    tooltip += f"Data Size: {size_value/1_000_000_000:.2f} GB<br>"
                elif size_value >= 1_000_000:
                    tooltip += f"Data Size: {size_value/1_000_000:.2f} MB<br>"
                elif size_value >= 1_000:
                    tooltip += f"Data Size: {size_value/1_000:.2f} KB<br>"
                else:
                    tooltip += f"Data Size: {size_value} bytes<br>"
            except (ValueError, TypeError):
                tooltip += f"Data Size: {data_size}<br>"

        # Add grouping information if available
        grouping = getattr(self.connection, "grouping", None)
        if grouping:
            tooltip += f"Grouping: {grouping}<br><br>"

        # Add transfer-specific details
        if self.transfer_type == "PCIe":
            tooltip += "<b>PCIe Transfer Details:</b><br>"

            # Get PCIe generation if available from compute resources
            if src_compute and hasattr(src_compute, "pcie_gen"):
                tooltip += f"• PCIe Generation: {src_compute.pcie_gen}<br>"
            elif dst_compute and hasattr(dst_compute, "pcie_gen"):
                tooltip += f"• PCIe Generation: {dst_compute.pcie_gen}<br>"

            # Show bandwidth information
            if src_compute and hasattr(src_compute, "network_speed"):
                tooltip += f"• Bandwidth: {src_compute.network_speed/1e9:.2f} Gbps<br>"
            elif dst_compute and hasattr(dst_compute, "network_speed"):
                tooltip += f"• Bandwidth: {dst_compute.network_speed/1e9:.2f} Gbps<br>"

            # Show driver overhead
            if src_compute and hasattr(src_compute, "time_in_driver"):
                tooltip += f"• Driver Overhead: {src_compute.time_in_driver} μs<br>"
            elif dst_compute and hasattr(dst_compute, "time_in_driver"):
                tooltip += f"• Driver Overhead: {dst_compute.time_in_driver} μs<br>"

        elif self.transfer_type == "Network":
            tooltip += "<b>Network Transfer Details:</b><br>"

            # Show network speeds
            if src_compute and hasattr(src_compute, "network_speed"):
                tooltip += (
                    f"• Source Network: {src_compute.network_speed/1e9:.2f} Gbps<br>"
                )
            if dst_compute and hasattr(dst_compute, "network_speed"):
                tooltip += (
                    f"• Dest Network: {dst_compute.network_speed/1e9:.2f} Gbps<br>"
                )

            # Get driver overhead
            if src_compute and hasattr(src_compute, "time_in_driver"):
                tooltip += (
                    f"• Source Driver Overhead: {src_compute.time_in_driver} μs<br>"
                )
            if dst_compute and hasattr(dst_compute, "time_in_driver"):
                tooltip += (
                    f"• Dest Driver Overhead: {dst_compute.time_in_driver} μs<br>"
                )

        return tooltip

    def hoverEnterEvent(self, event):
        """Show detailed tooltip on hover."""
        self.setToolTip(self._generate_detailed_tooltip())
        super().hoverEnterEvent(event)

    def paint(self, painter, option, widget):
        """Paint the transfer indicator with appropriate styling."""
        # Different colors for different transfer types
        if self.transfer_type == "PCIe":
            brush = QBrush(QColor(255, 200, 50, 220))  # amber, more opaque
            pen = QPen(QColor(200, 130, 0), 1.5)
        else:  # Network
            brush = QBrush(QColor(100, 200, 255, 220))  # light blue, more opaque
            pen = QPen(QColor(0, 130, 200), 1.5)

        painter.setPen(pen)
        painter.setBrush(brush)
        painter.drawRoundedRect(self.rect(), 4, 4)

    def set_connection(self, connection):
        """Associate this indicator with a specific connection."""
        self.connection = connection
        if connection:
            connection.add_transfer_indicator(self.transfer_type, self.pos())


class TransferPropertiesDialog(QDialog):
    def __init__(self, parent=None, data_size=None, grouping=None):
        super().__init__(parent)
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
        self.setAcceptHoverEvents(True)  # Enable hover events for tooltips

        # For tracking during creation
        self.temp_end_point: Optional[QPointF] = None

        # Data transfer properties
        self.data_size = None
        self.grouping = None

        # Estimate initial data size based on components
        self._estimate_data_size()

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

        # Also track parent containers
        self._track_parent_containers()

    def _estimate_data_size(self):
        """Estimate data size based on connected components if not explicitly set."""
        if self.data_size is not None:
            return

        if not self.start_block or not self.end_block:
            return

        try:
            # Import locally to avoid circular import issues
            from .data_transfer import estimate_data_size

            estimated_size = estimate_data_size(self.start_block, self.end_block)

            if estimated_size > 0:
                # Convert from bits to bytes
                self.data_size = str(int(estimated_size / 8))
        except Exception as e:
            # Just log the error and continue - estimation is optional
            print(f"Error estimating data size: {e}")

    def _generate_detailed_tooltip(self) -> str:
        """Generate a detailed tooltip with connection information."""
        if not self.start_block or not self.end_block:
            return "Connection"

        tooltip = "<b>Connection</b><br>"
        tooltip += f"From: {self.start_block.name}<br>"
        tooltip += f"To: {self.end_block.name}<br><br>"

        # Get component types for additional context
        src_type = (
            self.start_block.component_type.name
            if hasattr(self.start_block, "component_type")
            else "?"
        )
        dst_type = (
            self.end_block.component_type.name
            if hasattr(self.end_block, "component_type")
            else "?"
        )
        tooltip += f"Source Type: {src_type}<br>"
        tooltip += f"Destination Type: {dst_type}<br><br>"

        # Add data size information if available
        if self.data_size:
            try:
                size_value = float(self.data_size)
                # Format based on size
                if size_value >= 1_000_000_000:
                    tooltip += (
                        f"<b>Data Size:</b> {size_value/1_000_000_000:.2f} GB<br>"
                    )
                elif size_value >= 1_000_000:
                    tooltip += f"<b>Data Size:</b> {size_value/1_000_000:.2f} MB<br>"
                elif size_value >= 1_000:
                    tooltip += f"<b>Data Size:</b> {size_value/1_000:.2f} KB<br>"
                else:
                    tooltip += f"<b>Data Size:</b> {size_value} bytes<br>"
            except (ValueError, TypeError):
                tooltip += f"<b>Data Size:</b> {self.data_size}<br>"

        # Add grouping information if available
        if self.grouping:
            tooltip += f"<b>Grouping:</b> {self.grouping}<br>"

        # Add transfer indicators info if available
        if self.transfer_indicators:
            tooltip += "<br><b>Transfer Types:</b> "
            types = set(indicator[0] for indicator in self.transfer_indicators)
            tooltip += ", ".join(types)

        # Get compute resources for additional info
        src_compute = self.start_block.get_compute_resource()
        dst_compute = self.end_block.get_compute_resource()

        if (
            src_compute != dst_compute
            and src_compute is not None
            and dst_compute is not None
        ):
            tooltip += "<br><br><b>Transfer Between Different Resources:</b>"

            # Source resource info
            src_name = getattr(src_compute, "name", "") or "Source"
            src_type = getattr(src_compute, "hardware", "CPU")
            tooltip += f"<br>• {src_name} ({src_type})"

            if hasattr(src_compute, "network_speed"):
                tooltip += f" - {src_compute.network_speed/1e9:.1f} Gbps"

            # Destination resource info
            dst_name = getattr(dst_compute, "name", "") or "Destination"
            dst_type = getattr(dst_compute, "hardware", "CPU")
            tooltip += f"<br>• {dst_name} ({dst_type})"

            if hasattr(dst_compute, "network_speed"):
                tooltip += f" - {dst_compute.network_speed/1e9:.1f} Gbps"

        return tooltip

    def hoverEnterEvent(self, event):
        """Show detailed tooltip on hover."""
        self.setToolTip(self._generate_detailed_tooltip())
        super().hoverEnterEvent(event)

    def update_tooltip(self):
        """Update the tooltip with current connection data."""
        self.setToolTip(self._generate_detailed_tooltip())

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
        self.setPen(
            QPen(QColor(0, 180, 255), 4, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        )

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
            # Handle parameter inheritance: Source -> Destination
            self._handle_parameter_inheritance(self.start_block, end_block)
        else:
            end_port.connected_to.append((self.start_block, self.start_port))
            self.start_port.connected_to.append((end_block, end_port))
            # Handle parameter inheritance: Destination -> Source
            self._handle_parameter_inheritance(end_block, self.start_block)

        # Update the path
        self.update_path()

        # Set up event tracking only after both blocks are connected and in the scene
        if self.scene():
            self._setup_event_tracking()

            # Add transfer indicators after connection is complete
            from .connection_manager import update_connection_indicators

            update_connection_indicators(self.scene(), self)

        return True

    def _handle_parameter_inheritance(self, source_block, target_block):
        """Handle parameter inheritance between components when connected."""
        if not hasattr(source_block, "params") or not source_block.params:
            return  # No parameters to inherit

        # Import locally to avoid circular imports
        from .dialogs.parameter_inheritance_dialog import ParameterInheritanceDialog
        from .parameter_inheritance import get_inheritable_parameters

        # Check for inheritable parameters
        inheritable_params = get_inheritable_parameters(source_block, target_block)
        if not inheritable_params:
            return  # No inheritable parameters

        # Show inheritance dialog
        if self.scene() and self.scene().parent():
            app = self.scene().parent()
            dlg = ParameterInheritanceDialog(
                target_block.component_type,
                inheritable_params,
                [source_block.name],
                app,
            )

            if dlg.exec_():
                # Get selected parameters
                selected_params = dlg.get_selected_parameters()
                if selected_params:
                    # Update target component parameters
                    if not hasattr(target_block, "params"):
                        target_block.params = {}
                    target_block.params.update(selected_params)

    def disconnect(self):
        """Remove connection between ports."""
        # Remove any associated transfer indicators first
        if self.scene():
            # Find and remove all transfer indicators associated with this connection
            for item in self.scene().items():
                if (
                    isinstance(item, TransferIndicator)
                    and hasattr(item, "connection")
                    and item.connection is self
                ):
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

    def connect(self, start_block, start_port, end_block, end_port):
        """
        Re-establish a connection between ports (used for undo operations).

        Args:
            start_block: Source component block
            start_port: Source port
            end_block: Destination component block
            end_port: Destination port

        Returns:
            bool: True if connection was successfully re-established
        """
        # Set connection endpoints
        self.start_block = start_block
        self.start_port = start_port
        self.end_block = end_block
        self.end_port = end_port
        self.temp_end_point = None

        # Update the connections in both ports
        if start_port.port_type == PortType.OUTPUT:
            start_port.connected_to.append((end_block, end_port))
            end_port.connected_to.append((start_block, start_port))
        else:
            end_port.connected_to.append((start_block, start_port))
            start_port.connected_to.append((end_block, end_port))

        # Update the path
        self.update_path()

        # Make connection visible again
        self.setVisible(True)

        # Re-establish event tracking
        if self.scene():
            self._setup_event_tracking()

            # Recreate transfer indicators
            from .connection_manager import update_connection_indicators

            update_connection_indicators(self.scene(), self)

        return True

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
            start_pos.y() + (end_pos.y() - start_pos.y()) * percent,
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
            data_size=getattr(self, "data_size", None),
            grouping=getattr(self, "grouping", None),
        )
        if dlg.exec_():
            data_size, grouping = dlg.get_values()
            self.data_size = data_size
            self.grouping = grouping
            # Update tooltip with new values
            self.update_tooltip()
        event.accept()

    def contextMenuEvent(self, event):
        menu = QMenu()
        set_data_action = menu.addAction("Set Data Transfer Properties")
        delete_action = menu.addAction("Delete Connection")
        action = menu.exec_(event.screenPos())
        if action == set_data_action:
            dlg = TransferPropertiesDialog(
                parent=None,
                data_size=getattr(self, "data_size", None),
                grouping=getattr(self, "grouping", None),
            )
            if dlg.exec_():
                data_size, grouping = dlg.get_values()
                self.data_size = data_size
                self.grouping = grouping
                # Update tooltip with new values
                self.update_tooltip()
        elif action == delete_action:
            self.disconnect()
            if self.scene():
                self.scene().removeItem(self)

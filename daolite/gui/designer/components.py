"""
Component classes for the DaoLITE pipeline designer.

This module provides classes for representing AO pipeline components visually.
"""

from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from PyQt5.QtWidgets import (
    QGraphicsItem,
    QGraphicsSceneContextMenuEvent,
    QMenu,
    QAction,
    QInputDialog,
)
from PyQt5.QtCore import Qt, QRectF, QPointF
from PyQt5.QtGui import QPen, QBrush, QColor, QPainter, QFont

from daolite.common import ComponentType
from daolite.compute import ComputeResources


class PortType(Enum):
    """Type of connection port."""

    INPUT = 0
    OUTPUT = 1


class Port:
    """
    Represents an input or output port on a component.

    Attributes:
        port_type: INPUT or OUTPUT port type
        position: Relative position within the parent component
        connected_to: List of connected ports
        label: Text label for the port
        parent: Reference to parent component
    """

    def __init__(self, port_type: PortType, position: QPointF, label: str = ""):
        self.port_type = port_type
        self.position = position  # Relative to parent component
        self.connected_to: List[Tuple["ComponentBlock", "Port"]] = []
        self.label = label
        self.parent: Optional["ComponentBlock"] = None
        self.rect = QRectF(-6, -6, 12, 12)  # Small rectangle for port

    def get_scene_position(self) -> QPointF:
        """Get the position in scene coordinates."""
        if self.parent:
            return self.parent.pos() + self.position
        return self.position

    def contains_point(self, point: QPointF) -> bool:
        """Check if a point is inside this port."""
        scene_pos = self.get_scene_position()
        return self.rect.translated(scene_pos).contains(point)


class ComponentBlock(QGraphicsItem):
    """
    A visual component block in the pipeline designer.

    Represents one pipeline component (camera, centroider, etc.) with
    input/output ports and configurable properties.
    """

    def __init__(self, component_type: ComponentType, name: str):
        super().__init__()
        self.component_type = component_type
        self.name = name
        self.compute: Optional[ComputeResources] = None
        self.params: Dict[str, Any] = {}
        self.size = QRectF(0, 0, 180, 80)

        # Create ports
        self.input_ports: List[Port] = []
        self.output_ports: List[Port] = []

        self._initialize_ports()

        # Set flags
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemIsSelectable)
        self.setFlag(QGraphicsItem.ItemSendsScenePositionChanges)

    def _initialize_ports(self):
        """Initialize default ports based on component type."""
        if self.component_type == ComponentType.CAMERA:
            # Camera has no inputs, one output
            output = Port(PortType.OUTPUT, QPointF(180, 40), "data")
            output.parent = self
            self.output_ports.append(output)

        elif self.component_type == ComponentType.NETWORK:
            # Network has one input, one output
            input_port = Port(PortType.INPUT, QPointF(0, 40), "data in")
            output_port = Port(PortType.OUTPUT, QPointF(180, 40), "data out")
            input_port.parent = self
            output_port.parent = self
            self.input_ports.append(input_port)
            self.output_ports.append(output_port)

        elif self.component_type == ComponentType.CONTROL:
            # Control typically has one input, no output
            input_port = Port(PortType.INPUT, QPointF(0, 40), "commands")
            input_port.parent = self
            self.input_ports.append(input_port)

        else:
            # Default for other components: one input, one output
            input_port = Port(PortType.INPUT, QPointF(0, 40), "in")
            output_port = Port(PortType.OUTPUT, QPointF(180, 40), "out")
            input_port.parent = self
            output_port.parent = self
            self.input_ports.append(input_port)
            self.output_ports.append(output_port)

    def boundingRect(self) -> QRectF:
        """Define the bounding rectangle for the component."""
        return self.size

    def paint(self, painter: QPainter, option, widget):
        """
        Paint the component block and its ports.

        Args:
            painter: QPainter to use for drawing
            option: Style options
            widget: Widget being painted on
        """
        # Draw the main component block
        pen = QPen(Qt.black, 2)
        if self.isSelected():
            pen.setColor(Qt.blue)
            pen.setWidth(3)

        brush = QBrush(self._get_color_for_component())

        painter.setPen(pen)
        painter.setBrush(brush)
        painter.drawRoundedRect(self.size, 10, 10)

        # Draw title bar
        title_rect = QRectF(0, 0, self.size.width(), 25)
        painter.setBrush(QBrush(self._get_title_color()))
        painter.drawRoundedRect(title_rect, 10, 10)

        # Draw component name
        painter.setPen(Qt.black)
        font = QFont("Arial", 9, QFont.Bold)
        painter.setFont(font)
        painter.drawText(title_rect, Qt.AlignCenter, self.name)

        # Draw component type
        font = QFont("Arial", 8)
        painter.setFont(font)
        type_rect = QRectF(5, 30, self.size.width() - 10, 20)
        painter.drawText(
            type_rect, Qt.AlignCenter, f"Type: {self.component_type.value}"
        )

        # Draw compute resource if assigned
        if self.compute:
            compute_name = self.compute.__class__.__name__
            if hasattr(self.compute, "name"):
                compute_name = self.compute.name
            compute_rect = QRectF(5, 50, self.size.width() - 10, 20)
            painter.drawText(compute_rect, Qt.AlignCenter, f"Compute: {compute_name}")

        # Draw a short description for the component
        desc_rect = QRectF(5, 65, self.size.width() - 10, 15)
        painter.setFont(QFont("Arial", 7, QFont.StyleItalic))
        painter.setPen(QColor(80, 80, 80))
        painter.drawText(desc_rect, Qt.AlignLeft, self._get_description())

        # Draw ports
        self._draw_ports(painter)

    def _draw_ports(self, painter: QPainter):
        """Draw input and output ports."""
        # Draw input ports
        painter.setPen(QPen(Qt.black, 1))
        for port in self.input_ports:
            # Draw port circle
            painter.setBrush(QBrush(QColor(50, 150, 250)))  # Blue for input

            # Fix: Use QRectF to create a rectangle for the ellipse
            port_rect = QRectF(port.position.x() - 6, port.position.y() - 6, 12, 12)
            painter.drawEllipse(port_rect)

            # Draw port label (cast coordinates to int)
            painter.drawText(
                int(port.position.x()) + 5, int(port.position.y()) - 10, port.label
            )

        # Draw output ports
        for port in self.output_ports:
            # Draw port circle
            painter.setBrush(QBrush(QColor(50, 200, 50)))  # Green for output

            # Fix: Use QRectF to create a rectangle for the ellipse
            port_rect = QRectF(port.position.x() - 6, port.position.y() - 6, 12, 12)
            painter.drawEllipse(port_rect)

            # Draw port label
            painter.drawText(
                int(port.position.x()) - 40, int(port.position.y()) - 10, port.label
            )

    def _get_color_for_component(self) -> QColor:
        """Return appropriate color based on component type."""
        colors = {
            ComponentType.CAMERA: QColor(240, 240, 255),  # Light blue
            ComponentType.CENTROIDER: QColor(240, 255, 240),  # Light green
            ComponentType.RECONSTRUCTION: QColor(255, 240, 240),  # Light red
            ComponentType.CONTROL: QColor(255, 255, 240),  # Light yellow
            ComponentType.NETWORK: QColor(255, 240, 255),  # Light purple
            ComponentType.CALIBRATION: QColor(240, 255, 255),  # Light cyan
        }
        return colors.get(self.component_type, QColor(245, 245, 245))

    def _get_title_color(self) -> QColor:
        """Return darker color for the title bar."""
        base_color = self._get_color_for_component()
        return base_color.darker(120)

    def _get_description(self) -> str:
        """Return a short description for the component type."""
        descs = {
            ComponentType.CAMERA: "Image sensor input",
            ComponentType.CENTROIDER: "Wavefront slope extraction",
            ComponentType.RECONSTRUCTION: "Wavefront phase estimation",
            ComponentType.CONTROL: "DM/actuator control",
            ComponentType.NETWORK: "PCIe/network transfer",
            ComponentType.CALIBRATION: "Pixel/offset calibration",
        }
        return descs.get(self.component_type, "AO pipeline component")

    def itemChange(self, change, value):
        """Handle changes to the item, particularly position changes."""
        if change == QGraphicsItem.ItemPositionChange and self.scene():
            # Update connected lines when this component moves
            for port in self.input_ports + self.output_ports:
                for comp, port2 in port.connected_to:
                    # Find the connection object in the scene
                    for item in self.scene().items():
                        from .connection import Connection
                        if isinstance(item, Connection):
                            if ((item.start_block == self or item.end_block == self) and
                                (item.start_port == port or item.end_port == port)):
                                item.update_path()
            self.scene().update()

        return super().itemChange(change, value)

    def contextMenuEvent(self, event: QGraphicsSceneContextMenuEvent):
        """Show context menu on right-click."""
        menu = QMenu()

        # Add action to rename component
        rename_action = QAction("Rename", menu)
        rename_action.triggered.connect(self._on_rename)
        menu.addAction(rename_action)

        # Add action to configure compute resource
        configure_action = QAction("Configure Compute Resource", menu)
        configure_action.triggered.connect(self._on_configure)
        menu.addAction(configure_action)

        # Add action to configure parameters
        params_action = QAction("Configure Parameters", menu)
        params_action.triggered.connect(self._on_params)
        menu.addAction(params_action)

        # Add action to delete component
        delete_action = QAction("Delete", menu)
        delete_action.triggered.connect(self._on_delete)
        menu.addAction(delete_action)

        menu.exec_(event.screenPos())

    def _on_rename(self):
        """Handle component rename action."""
        # Show dialog to rename component
        name, ok = QInputDialog.getText(
            None, "Rename Component", "Enter new name:", text=self.name
        )

        if ok and name:
            self.name = name
            if self.scene():
                self.scene().update()

    def _on_configure(self):
        """Handle compute resource configuration action."""
        # Delegate to the main application through the scene's parent
        if self.scene() and self.scene().parent():
            app = self.scene().parent()
            if hasattr(app, "_get_compute_resource"):
                app._get_compute_resource(self)

    def _on_params(self):
        """Handle parameters configuration action."""
        # Delegate to the main application through the scene's parent
        if self.scene() and self.scene().parent():
            app = self.scene().parent()

            # Store the currently selected component
            prev_selected = None
            if hasattr(app, "selected_component"):
                prev_selected = app.selected_component

            # Temporarily set this component as selected
            if hasattr(app, "selected_component"):
                app.selected_component = self

            # Call the parameter configuration method
            if hasattr(app, "_configure_params"):
                app._configure_params()

            # Restore the previously selected component
            if hasattr(app, "selected_component"):
                app.selected_component = prev_selected

    def _on_delete(self):
        """Handle component deletion action."""
        if self.scene():
            # Remove connections associated with this component
            for connection in list(self.scene().connections):
                if connection.start_block == self or connection.end_block == self:
                    connection.disconnect()
                    self.scene().connections.remove(connection)
                    self.scene().removeItem(connection)

            # Remove the component itself
            self.scene().removeItem(self)

    def find_port_at_point(self, point: QPointF) -> Optional[Port]:
        """Find a port that contains the given point."""
        # Check input ports
        for port in self.input_ports:
            if port.contains_point(point):
                return port

        # Check output ports
        for port in self.output_ports:
            if port.contains_point(point):
                return port

        return None

    def get_dependencies(self) -> List[str]:
        """Get list of component names this component depends on."""
        dependencies = []
        for port in self.input_ports:
            for comp, _ in port.connected_to:
                dependencies.append(comp.name)
        return dependencies

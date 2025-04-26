"""
Connection classes for the DaoLITE pipeline designer.

This module provides graphical representations of connections between components.
"""

from typing import Optional
from PyQt5.QtWidgets import QGraphicsPathItem
from PyQt5.QtCore import Qt, QPointF
from PyQt5.QtGui import QPen, QPainterPath, QColor

from .components import Port, ComponentBlock, PortType


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

        # Set up appearance
        self.setPen(
            QPen(QColor(60, 60, 60), 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        )
        self.setZValue(-1)  # Below components
        self.setFlag(self.ItemIsSelectable, True)  # Make connection selectable

        # For tracking during creation
        self.temp_end_point: Optional[QPointF] = None

        self.update_path()

    def update_path(self):
        """Update the connection path between source and destination ports."""
        path = QPainterPath()

        # Get start point
        if self.start_port:
            start_pos = self.start_port.get_scene_position()
        else:
            # Default start point if we don't have a port yet
            start_pos = QPointF(0, 0)

        # Get end point
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
        return True

    def disconnect(self):
        """Remove connection between ports."""
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

"""
Port and PortType classes for the daolite pipeline designer.
"""

from enum import Enum
from typing import TYPE_CHECKING, List, Optional, Tuple

from PyQt5.QtCore import QPointF, QRectF

if TYPE_CHECKING:
    from .component_block import ComponentBlock


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
        self.rect = QRectF(-9, -9, 18, 18)  # Larger clickable area for port

    def get_scene_position(self) -> QPointF:
        """Get the position in scene coordinates."""
        if self.parent:
            if self.parent.scene():
                return self.parent.mapToScene(self.position)
            return self.parent.pos() + self.position
        return self.position

    def contains_point(self, point: QPointF) -> bool:
        """Check if a point is inside this port."""
        scene_pos = self.get_scene_position()
        debug_rect = QRectF(self.rect)
        debug_rect.adjust(-3, -3, 3, 3)
        hit = debug_rect.translated(scene_pos).contains(point)
        if hit:
            print(
                f"[DEBUG] Port '{self.label}' clicked at {point}, rect center {scene_pos}, rect {debug_rect}"
            )
        return hit

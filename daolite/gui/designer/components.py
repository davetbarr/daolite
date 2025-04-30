"""
Component classes for the daolite pipeline designer.

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
    QColorDialog,
)
from PyQt5.QtCore import Qt, QRectF, QPointF
from PyQt5.QtGui import QPen, QBrush, QColor, QPainter, QFont, QPainterPath

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
        self.rect = QRectF(-9, -9, 18, 18)  # Larger clickable area for port

    def get_scene_position(self) -> QPointF:
        """Get the position in scene coordinates."""
        if self.parent:
            # Use mapToScene to correctly get position in scene coordinates,
            # this handles components inside a ComputeBox properly
            if self.parent.scene():
                return self.parent.mapToScene(self.position)
            return self.parent.pos() + self.position
        return self.position

    def contains_point(self, point: QPointF) -> bool:
        """Check if a point is inside this port. Debug print for click testing."""
        scene_pos = self.get_scene_position()
        # Expand clickable area for debug
        debug_rect = QRectF(self.rect)
        debug_rect.adjust(-3, -3, 3, 3)  # Add 3px margin all around
        hit = debug_rect.translated(scene_pos).contains(point)
        if hit:
            print(f"[DEBUG] Port '{self.label}' clicked at {point}, rect center {scene_pos}, rect {debug_rect}")
        return hit


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

            # Larger ellipse for port
            port_rect = QRectF(port.position.x() - 9, port.position.y() - 9, 18, 18)
            painter.drawEllipse(port_rect)

            # Draw port label (cast coordinates to int)
            painter.drawText(
                int(port.position.x()) + 5, int(port.position.y()) - 10, port.label
            )

        # Draw output ports
        for port in self.output_ports:
            # Draw port circle
            painter.setBrush(QBrush(QColor(50, 200, 50)))  # Green for output

            # Larger ellipse for port
            port_rect = QRectF(port.position.x() - 9, port.position.y() - 9, 18, 18)
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
        """Handle changes to the item, particularly position changes and parent assignment for drag-and-drop."""
        if change == QGraphicsItem.ItemPositionChange and self.scene():
            # Only update connections and scene
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
        elif change == QGraphicsItem.ItemScenePositionHasChanged and self.scene():
            # Also update connections when scene position changes (happens when parent changes)
            for port in self.input_ports + self.output_ports:
                for comp, port2 in port.connected_to:
                    for item in self.scene().items():
                        from .connection import Connection
                        if isinstance(item, Connection):
                            if ((item.start_block == self or item.end_block == self) and
                                (item.start_port == port or item.end_port == port)):
                                item.update_path()
            self.scene().update()
        elif change == QGraphicsItem.ItemParentChange and self.scene():
            # Update connections when parent changes (moved in/out of ComputeBox or GPUBox)
            # Need to defer actual connection update to after parent is set
            from .connection import Connection
            self.scene().update()
        elif change == QGraphicsItem.ItemParentHasChanged and self.scene():
            # Parent has changed, update all connections
            for port in self.input_ports + self.output_ports:
                for comp, port2 in port.connected_to:
                    for item in self.scene().items():
                        from .connection import Connection
                        if isinstance(item, Connection):
                            if ((item.start_block == self or item.end_block == self) and
                                (item.start_port == port or item.end_port == port)):
                                item.update_path()
            self.scene().update()
        elif change == QGraphicsItem.ItemSelectedChange and self.scene():
            # Remove highlight from all boxes when selection changes
            for item in self.scene().items():
                if hasattr(item, 'set_highlight'):
                    item.set_highlight(False)

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


class ComputeBox(QGraphicsItem):
    """
    A visual container for grouping components that share the same compute resource (e.g., a computer node).
    Can contain ComponentBlock and GPUBox items as children.
    """
    def __init__(self, name: str, compute: Optional[ComputeResources] = None):
        super().__init__()
        self.name = name
        self.compute = compute
        self.child_items: List[QGraphicsItem] = []
        self.size = QRectF(0, 0, 320, 220)
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemIsSelectable)
        self.setZValue(-10)  # Draw behind components
        self._highlight = False  # Visual indicator for drag-over
        self.box_color = QColor(70, 120, 220)  # Default blue
        self.fill_color = QColor(200, 220, 255, 60)
        self._resizing = False
        self._resize_handle_size = 16
        self.setAcceptHoverEvents(True)

    def set_highlight(self, value: bool):
        self._highlight = value
        self.update()

    def contextMenuEvent(self, event):
        menu = QMenu()
        color_action = QAction("Set Color", menu)
        color_action.triggered.connect(self._on_set_color)
        menu.addAction(color_action)
        configure_action = QAction("Configure Compute", menu)
        configure_action.triggered.connect(self._on_configure)
        menu.addAction(configure_action)
        delete_action = QAction("Delete", menu)
        delete_action.triggered.connect(self._on_delete)
        menu.addAction(delete_action)
        menu.exec_(event.screenPos())

    def _on_set_color(self):
        color = QColorDialog.getColor(self.box_color)
        if color.isValid():
            self.box_color = color
            self.update()

    def _on_configure(self):
        # Show compute resource dialog via main app if possible
        if self.scene() and self.scene().parent():
            app = self.scene().parent()
            if hasattr(app, '_get_compute_resource'):
                app._get_compute_resource(self)

    def _on_delete(self):
        if self.scene():
            # Remove all children
            for child in list(self.childItems()):
                self.scene().removeItem(child)
            self.scene().removeItem(self)

    def boundingRect(self) -> QRectF:
        # Add space for resize handle
        r = self.size.adjusted(0, 0, self._resize_handle_size, self._resize_handle_size)
        return r

    def paint(self, painter: QPainter, option, widget):
        pen = QPen(self.box_color, 2)
        if self._highlight:
            pen.setWidth(8)
        elif self.isSelected():
            pen.setWidth(4)
        brush = QBrush(self.fill_color)
        painter.setPen(pen)
        painter.setBrush(brush)
        painter.drawRoundedRect(self.size, 16, 16)
        # Draw title
        title_rect = QRectF(0, 0, self.size.width(), 28)
        painter.setBrush(QBrush(self.box_color.lighter(180)))
        painter.drawRoundedRect(title_rect, 12, 12)
        painter.setPen(Qt.black)
        font = QFont("Arial", 10, QFont.Bold)
        painter.setFont(font)
        painter.drawText(title_rect, Qt.AlignCenter, self.name)
        # Draw compute resource name
        if self.compute:
            compute_name = getattr(self.compute, "name", str(type(self.compute).__name__))
            painter.setFont(QFont("Arial", 8))
            painter.drawText(10, 45, f"Compute: {compute_name}")
        # Draw resize handle
        handle_rect = QRectF(self.size.width(), self.size.height(), self._resize_handle_size, self._resize_handle_size)
        painter.setBrush(QBrush(Qt.gray))
        painter.setPen(QPen(Qt.darkGray, 1))
        painter.drawRect(handle_rect)
        painter.setPen(QPen(Qt.black, 1))
        painter.drawText(handle_rect, Qt.AlignCenter, "⇲")

    def mousePressEvent(self, event):
        # Check if clicking on resize handle
        handle_rect = QRectF(self.size.width(), self.size.height(), self._resize_handle_size, self._resize_handle_size)
        if handle_rect.contains(event.pos()):
            self._resizing = True
            self._resize_start = event.pos()
            self._orig_size = self.size.size()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if getattr(self, '_resizing', False):
            delta = event.pos() - self._resize_start
            new_width = max(120, self._orig_size.width() + delta.x())
            new_height = max(80, self._orig_size.height() + delta.y())
            self.size = QRectF(0, 0, new_width, new_height)
            self.prepareGeometryChange()
            self.update()
            self.auto_arrange_children()
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if getattr(self, '_resizing', False):
            self._resizing = False
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def add_child(self, item: QGraphicsItem):
        item.setParentItem(self)
        self.child_items.append(item)
        if hasattr(item, "compute"):
            item.compute = self.compute
        self.auto_arrange_children()

    def auto_arrange_children(self):
        # Only move children if they are not fully inside or are overlapping
        if not self.child_items:
            return
        margin = 20
        changed = True
        max_iter = 30
        iter_count = 0
        # Sort children by (y, x) so top-left is first
        def child_key(child):
            c_rect = child.mapToParent(child.boundingRect()).boundingRect()
            return (c_rect.top(), c_rect.left())
        while changed and iter_count < max_iter:
            changed = False
            # Sort children for deterministic order
            sorted_children = sorted(self.child_items, key=child_key)
            child_rects = [child.mapToParent(child.boundingRect()).boundingRect() for child in sorted_children]
            for i, rect1 in enumerate(child_rects):
                for j, rect2 in enumerate(child_rects):
                    if i == j:
                        continue
                    if rect1.intersects(rect2):
                        # Only move the one further from top-left
                        if child_key(sorted_children[j]) > child_key(sorted_children[i]):
                            # Move j out of i
                            dx = rect1.right() - rect2.left() + 10
                            dy = rect1.bottom() - rect2.top() + 10
                            # Prefer the direction with the smallest move to resolve overlap
                            move_right = rect2.left() + dx <= self.size.width() - margin
                            move_down = rect2.top() + dy <= self.size.height() - margin
                            if move_right and (not move_down or dx <= dy):
                                sorted_children[j].setPos(sorted_children[j].x() + dx, sorted_children[j].y())
                            elif move_down:
                                sorted_children[j].setPos(sorted_children[j].x(), sorted_children[j].y() + dy)
                            else:
                                # If can't move right or down, move diagonally
                                sorted_children[j].setPos(sorted_children[j].x() + dx, sorted_children[j].y() + dy)
                            changed = True
                            break  # Recompute rects after any move
                if changed:
                    break
            iter_count += 1
        # Ensure all are fully inside
        for child in self.child_items:
            c_rect = child.mapToParent(child.boundingRect()).boundingRect()
            dx = dy = 0
            if c_rect.left() < 0:
                dx = -c_rect.left() + 10
            elif c_rect.right() > self.size.width():
                dx = self.size.width() - c_rect.right() - 10
            if c_rect.top() < 0:
                dy = -c_rect.top() + 10
            elif c_rect.bottom() > self.size.height():
                dy = self.size.height() - c_rect.bottom() - 10
            if dx != 0 or dy != 0:
                child.setPos(child.x() + dx, child.y() + dy)
        # Expand if needed
        for child in self.child_items:
            c_rect = child.mapToParent(child.boundingRect()).boundingRect()
            expand_w = c_rect.right() + margin - self.size.width()
            expand_h = c_rect.bottom() + margin - self.size.height()
            if expand_w > 0 or expand_h > 0:
                self.size = QRectF(0, 0, max(self.size.width(), c_rect.right() + margin), max(self.size.height(), c_rect.bottom() + margin))
                self.prepareGeometryChange()
                self.update()

    def snap_child_fully_inside(self, child):
        """Ensure child is fully inside the box, expand if needed.
        Only move the child if absolutely necessary."""
        # First check if the child is already fully inside
        c_rect = child.mapToParent(child.boundingRect()).boundingRect()
        changed = False
        margin = 10
        
        # Check if completely outside the container bounds
        if c_rect.right() > self.size.width():
            # Only move if significantly outside bounds
            if c_rect.right() > self.size.width() + 20:
                child.setX(self.size.width() - c_rect.width() - margin)
                changed = True
            else:
                # Just expand the container instead
                self.size.setWidth(c_rect.right() + margin)
                changed = True
        
        if c_rect.bottom() > self.size.height():
            # Only move if significantly outside bounds
            if c_rect.bottom() > self.size.height() + 20:
                child.setY(self.size.height() - c_rect.height() - margin)
                changed = True
            else:
                # Just expand the container instead
                self.size.setHeight(c_rect.bottom() + margin)
                changed = True
        
        if c_rect.left() < 0:
            child.setX(margin)
            changed = True
        
        if c_rect.top() < 0:
            child.setY(margin)
            changed = True
        
        # Second check if there are any overlaps with siblings
        overlaps = False
        for sibling in self.childItems():
            if sibling is not child and isinstance(sibling, ComponentBlock):
                sibling_rect = sibling.mapToParent(sibling.boundingRect()).boundingRect()
                if c_rect.intersects(sibling_rect):
                    overlaps = True
                    break
        
        # Only run auto-arrange if there are overlaps
        if overlaps:
            # Try to resolve overlaps by moving only this child
            for sibling in self.childItems():
                if sibling is not child and isinstance(sibling, ComponentBlock):
                    sibling_rect = sibling.mapToParent(sibling.boundingRect()).boundingRect()
                    if c_rect.intersects(sibling_rect):
                        # Calculate minimum move to resolve overlap
                        dx = sibling_rect.right() - c_rect.left() + margin
                        dy = sibling_rect.bottom() - c_rect.top() + margin
                        
                        # Choose the smallest move
                        if dx < dy:
                            child.setX(child.x() + dx)
                        else:
                            child.setY(child.y() + dy)
                        
                        # Update the rect with the new position
                        c_rect = child.mapToParent(child.boundingRect()).boundingRect()
                        changed = True
        
        if changed:
            self.prepareGeometryChange()
            self.update()

    def shape(self):
        """Return the shape of the ComputeBox for mouse interaction.
        Uses the full rectangle shape for better hit detection during drag and drop."""
        path = QPainterPath()
        # Use the entire box area as the shape for hit detection
        # This ensures components can be dropped anywhere within the box
        path.addRect(self.boundingRect())
        return path


class GPUBox(QGraphicsItem):
    """
    A visual container for grouping components that share the same GPU resource.
    Can only be placed inside a ComputeBox.
    """
    def __init__(self, name: str, gpu_resource: Optional[ComputeResources] = None):
        super().__init__()
        self.name = name
        self.gpu_resource = gpu_resource
        self.child_items: List[QGraphicsItem] = []
        self.size = QRectF(0, 0, 220, 120)
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemIsSelectable)
        self.setZValue(-5)
        self._highlight = False
        self.box_color = QColor(120, 180, 70)  # Default green
        self.fill_color = QColor(220, 255, 200, 80)

    def set_highlight(self, value: bool):
        self._highlight = value
        self.update()

    def contextMenuEvent(self, event):
        menu = QMenu()
        color_action = QAction("Set Color", menu)
        color_action.triggered.connect(self._on_set_color)
        menu.addAction(color_action)
        menu.exec_(event.screenPos())

    def _on_set_color(self):
        color = QColorDialog.getColor(self.box_color)
        if color.isValid():
            self.box_color = color
            self.update()

    def boundingRect(self) -> QRectF:
        return self.size

    def paint(self, painter: QPainter, option, widget):
        pen = QPen(self.box_color, 2)
        if self._highlight:
            pen.setWidth(8)
        elif self.isSelected():
            pen.setWidth(4)
        brush = QBrush(self.fill_color)
        painter.setPen(pen)
        painter.setBrush(brush)
        painter.drawRoundedRect(self.size, 12, 12)
        # Draw title
        title_rect = QRectF(0, 0, self.size.width(), 22)
        painter.setBrush(QBrush(self.box_color.lighter(180)))
        painter.drawRoundedRect(title_rect, 10, 10)
        painter.setPen(Qt.black)
        font = QFont("Arial", 9, QFont.Bold)
        painter.setFont(font)
        painter.drawText(title_rect, Qt.AlignCenter, self.name)
        # Draw GPU resource name
        if self.gpu_resource:
            gpu_name = getattr(self.gpu_resource, "name", str(type(self.gpu_resource).__name__))
            painter.setFont(QFont("Arial", 8))
            painter.drawText(10, 35, f"GPU: {gpu_name}")

    def add_child(self, item: QGraphicsItem):
        item.setParentItem(self)
        self.child_items.append(item)
        # If it's a ComponentBlock, assign GPU resource
        if hasattr(item, "compute"):
            item.compute = self.gpu_resource

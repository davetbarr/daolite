"""
PipelineScene for the daolite pipeline designer.
"""

import logging

from PyQt5.QtCore import QRectF, Qt
from PyQt5.QtGui import QColor, QLinearGradient, QPen
from PyQt5.QtWidgets import QGraphicsScene

from .component_block import ComponentBlock
from .component_container import ComputeBox, GPUBox
from .connection import Connection
from .connection_manager import update_connection_indicators
from .port import PortType

logger = logging.getLogger("PipelineDesigner")


class PipelineScene(QGraphicsScene):
    """
    Custom graphics scene for the pipeline designer.
    Handles interactions, connections, and component management.
    """

    def __init__(self, parent=None, theme="light"):
        super().__init__(parent)
        print(f"[DEBUG] Scene initialized with parent: {parent}")
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

        # Track moving items for undo/redo
        self.moving_items = {}  # {item: original_position}
        self.item_moved = False

    def set_theme(self, theme):
        self.theme = theme
        self.update()
        for item in self.items():
            if hasattr(item, "set_theme"):
                item.set_theme(theme)

    def dragMoveEvent(self, event):
        event.accept()

    def dropEvent(self, event):
        event.accept()

    def mousePressEvent(self, event):
        """
        Handle mouse press events for interaction with the scene.
        """
        # Store original positions of selected items for undo/redo
        self.moving_items = {}
        self.item_moved = False

        for item in self.selectedItems():
            if isinstance(item, (ComponentBlock, ComputeBox, GPUBox)):
                self.moving_items[item] = item.pos()

        # Connection creation logic
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
                        if (
                            port is not self.selected_port
                            and self.selected_port is not None
                        ):
                            # Only allow output->input or input->output
                            if self.selected_port.port_type != port.port_type:
                                # Always connect output to input
                                if self.selected_port.port_type == PortType.INPUT:
                                    src_block, src_port = item, port
                                    dst_block, dst_port = (
                                        self.selected_block,
                                        self.selected_port,
                                    )
                                else:
                                    src_block, src_port = (
                                        self.selected_block,
                                        self.selected_port,
                                    )
                                    dst_block, dst_port = item, port

                                # Create connection
                                from .connection import Connection

                                conn = Connection(src_block, src_port)
                                if conn.complete_connection(dst_block, dst_port):
                                    self.addItem(conn)
                                    self.connections.append(conn)

                                    # Log connection creation
                                    print(
                                        f"[DEBUG] Connection created from '{src_block.name}' to '{dst_block.name}'"
                                    )

                                    # Update connection indicators
                                    from .connection_manager import (
                                        update_connection_indicators,
                                    )

                                    update_connection_indicators(self, conn)

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
                        from .connection import Connection

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
        """
        Handle mouse move events for interaction with the scene.
        """
        # Update temporary connection line during drag-to-connect
        if self.current_connection:
            self.current_connection.set_temp_end_point(event.scenePos())
            return

        # Check if any tracked items have moved
        if self.moving_items:
            for item in self.moving_items.keys():
                if item.pos() != self.moving_items[item]:
                    self.item_moved = True
                    break

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
                    if (intersection.width() * intersection.height()) > 0.3 * (
                        block_rect.width() * block_rect.height()
                    ):
                        highlight_box = item
                        break

            # Highlight the potential parent container
            for item in self.items():
                if hasattr(item, "set_highlight"):
                    item.set_highlight(item is highlight_box)
        else:
            # Clear highlights if not dragging a component
            for item in self.items():
                if hasattr(item, "set_highlight"):
                    item.set_highlight(False)

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """
        Handle mouse release events for interaction with the scene.
        """
        # Handle connection completion if we're in the middle of creating one
        if self.current_connection and event.button() == Qt.LeftButton:
            pos = event.scenePos()
            item = self.itemAt(pos, self.views()[0].transform())
            if isinstance(item, ComponentBlock):
                port = item.find_port_at_point(pos)
                if port and port is not self.start_port:
                    # Complete the connection
                    if self.current_connection.complete_connection(item, port):
                        self.connections.append(self.current_connection)
                        connection = self.current_connection

                        # Get source and destination blocks and their compute resources
                        src_block = self.start_block
                        dst_block = item

                        # Log the connection creation
                        print(
                            f"[DEBUG] Connection created from '{src_block.name}' to '{dst_block.name}'"
                        )

                        # Update connection indicators
                        update_connection_indicators(self, connection)

                        self.current_connection = None
                        self.start_port = None
                        self.start_block = None
                        self.update()
                        return

            # Remove incomplete connection
            if self.current_connection:
                self.removeItem(self.current_connection)
                self.current_connection = None
                self.start_port = None
                self.start_block = None

        # Handle drag and drop of components into containers
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
                    if (intersection.width() * intersection.height()) > 0.3 * (
                        block_rect.width() * block_rect.height()
                    ):
                        highlight_box = item
                        break

            # Get the original scene position before any parent changes
            orig_scene_pos = moving_block.scenePos()

            # Find the best candidate container (computer box or GPU)
            parent_box = highlight_box

            # Only consider it a drop into container if we found a container
            if parent_box:
                # Store any existing parent for undo handling
                old_parent = moving_block.parentItem()

                # Convert position to parent coordinates
                local_pos = parent_box.mapFromScene(moving_block.scenePos())
                moving_block.setParentItem(parent_box)
                moving_block.setPos(local_pos)

                # Assign compute resource
                if hasattr(parent_box, "compute"):
                    moving_block.compute = parent_box.compute
                elif hasattr(parent_box, "gpu_resource"):
                    moving_block.compute = parent_box.gpu_resource

                # Add to parent's child_items list if applicable
                if (
                    hasattr(parent_box, "child_items")
                    and moving_block not in parent_box.child_items
                ):
                    parent_box.child_items.append(moving_block)

                # Optimize position within the new parent
                # Check if block is outside parent bounds or overlapping with siblings
                box_rect = QRectF(
                    0, 0, parent_box.size.width(), parent_box.size.height()
                )
                block_rect = moving_block.boundingRect()
                block_pos_rect = QRectF(
                    moving_block.pos().x(),
                    moving_block.pos().y(),
                    block_rect.width(),
                    block_rect.height(),
                )

                # Check if block is outside parent bounds
                is_outside = not box_rect.contains(block_pos_rect)

                # Check for overlaps with siblings
                is_overlapping = False
                for sibling in parent_box.childItems():
                    if sibling is not moving_block and isinstance(
                        sibling, ComponentBlock
                    ):
                        sibling_rect = QRectF(
                            sibling.pos().x(),
                            sibling.pos().y(),
                            sibling.boundingRect().width(),
                            sibling.boundingRect().height(),
                        )
                        if block_pos_rect.intersects(sibling_rect):
                            is_overlapping = True
                            break

                # Only adjust position if necessary
                if is_outside or is_overlapping:
                    if hasattr(parent_box, "snap_child_fully_inside"):
                        parent_box.snap_child_fully_inside(moving_block)

                # Update all connections of this block
                for connection in self.connections:
                    if (
                        connection.start_block == moving_block
                        or connection.end_block == moving_block
                    ):
                        connection.update_path()
                        connection.update_transfer_indicators()
            else:
                # We're moving to no parent (dragging out of a container)
                old_parent = moving_block.parentItem()
                if old_parent:
                    # Preserve the exact scene position
                    moving_block.setParentItem(None)
                    moving_block.setPos(orig_scene_pos)

                    # Remove from previous parent's child_items list if applicable
                    if (
                        hasattr(old_parent, "child_items")
                        and moving_block in old_parent.child_items
                    ):
                        old_parent.child_items.remove(moving_block)

                    # Update all connections
                    for connection in self.connections:
                        if (
                            connection.start_block == moving_block
                            or connection.end_block == moving_block
                        ):
                            connection.update_path()
                            connection.update_transfer_indicators()

        # If items have moved, create undo commands
        if (
            self.item_moved
            and self.moving_items
            and hasattr(self.parent(), "undo_stack")
        ):
            from .undo_stack import CompositeCommand, MoveComponentCommand

            if len(self.moving_items) == 1:
                # Single item move
                item = next(iter(self.moving_items.keys()))
                old_pos = self.moving_items[item]
                new_pos = item.pos()

                if (
                    old_pos != new_pos
                ):  # Only create command if position actually changed
                    command = MoveComponentCommand(item, old_pos, new_pos)
                    self.parent().undo_stack.push(command)
                    print(f"[DEBUG] Pushed MoveComponentCommand for {item}")
            else:
                # Multi-item move
                composite = CompositeCommand("Move Multiple Items")

                for item, old_pos in self.moving_items.items():
                    new_pos = item.pos()
                    if old_pos != new_pos:  # Only add to composite if position changed
                        command = MoveComponentCommand(item, old_pos, new_pos)
                        composite.add_command(command)

                if composite.commands:
                    self.parent().undo_stack.push(composite)
                    print(
                        f"[DEBUG] Pushed composite move command with {len(composite.commands)} items"
                    )

        # Reset tracking
        self.moving_items = {}
        self.item_moved = False

        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        """
        Handle key press events for deleting items and undo/redo.
        Zoom functionality has been moved to PipelineView.
        """
        from PyQt5.QtCore import Qt
        from PyQt5.QtGui import QKeySequence

        # Delete selected items
        if event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            from .undo_stack import (
                CompositeCommand,
                RemoveComponentCommand,
                RemoveConnectionCommand,
            )

            # Handle component and connection deletion with undo support
            if hasattr(self.parent(), "undo_stack"):
                items_to_delete = list(self.selectedItems())

                if items_to_delete:
                    # If multiple items, use composite command
                    if len(items_to_delete) > 1:
                        composite = CompositeCommand("Delete Multiple Items")

                        for item in items_to_delete:
                            if hasattr(item, "disconnect"):  # Connection
                                command = RemoveConnectionCommand(self, item)
                                composite.add_command(command)
                            elif isinstance(item, (ComponentBlock, ComputeBox, GPUBox)):
                                # Find connected connections
                                connections = []
                                for conn in self.connections:
                                    if isinstance(item, ComponentBlock) and (
                                        conn.start_block == item
                                        or conn.end_block == item
                                    ):
                                        connections.append(conn)

                                command = RemoveComponentCommand(
                                    self, item, connections
                                )
                                composite.add_command(command)

                        if composite.commands:
                            self.parent().undo_stack.push(composite)
                            print(
                                f"[DEBUG] Pushed composite delete command with {len(composite.commands)} items"
                            )
                    else:
                        # Single item deletion
                        item = items_to_delete[0]
                        if hasattr(item, "disconnect"):  # Connection
                            command = RemoveConnectionCommand(self, item)
                            self.parent().undo_stack.push(command)
                        elif isinstance(item, (ComponentBlock, ComputeBox, GPUBox)):
                            # Find connected connections
                            connections = []
                            for conn in self.connections:
                                if isinstance(item, ComponentBlock) and (
                                    conn.start_block == item or conn.end_block == item
                                ):
                                    connections.append(conn)

                            command = RemoveComponentCommand(self, item, connections)
                            self.parent().undo_stack.push(command)
                else:
                    # Old deletion logic as fallback
                    for item in self.selectedItems():
                        # Delete connections
                        if hasattr(item, "disconnect"):
                            item.disconnect()
                            if (
                                hasattr(self, "connections")
                                and item in self.connections
                            ):
                                self.connections.remove(item)
                            self.removeItem(item)
                        # Delete components/blocks/containers
                        elif hasattr(item, "_on_delete"):
                            item._on_delete()
            else:
                # Old deletion logic as fallback
                for item in self.selectedItems():
                    # Delete connections
                    if hasattr(item, "disconnect"):
                        item.disconnect()
                        if hasattr(self, "connections") and item in self.connections:
                            self.connections.remove(item)
                        self.removeItem(item)
                    # Delete components/blocks/containers
                    elif hasattr(item, "_on_delete"):
                        item._on_delete()

            self.update()
        # Undo/Redo handled by parent (main window)
        elif event.matches(QKeySequence.Undo) or (
            event.modifiers() & Qt.ControlModifier and event.key() == Qt.Key_Z
        ):
            if hasattr(self.parent(), "undo_stack"):
                self.parent().undo_stack.undo()
        elif event.matches(QKeySequence.Redo) or (
            event.modifiers() & Qt.ControlModifier and event.key() == Qt.Key_Y
        ):
            if hasattr(self.parent(), "undo_stack"):
                self.parent().undo_stack.redo()
        else:
            super().keyPressEvent(event)

    def drawForeground(self, painter, rect):
        """
        Draw the foreground of the scene, including visual feedback for click-to-connect.
        """
        # Draw port highlight when in click-to-connect mode
        if self.click_connect_mode and self.selected_port:
            painter.save()
            # Draw a prominent highlight around the selected port
            painter.setPen(QPen(QColor(255, 60, 60), 3, Qt.DashLine))
            pos = self.selected_port.get_scene_position()
            painter.drawEllipse(
                pos, 12, 12
            )  # Draw larger circle to make it more visible

            # Add a glow effect
            for i in range(3):
                glow_size = 15 + i * 3
                glow_opacity = 100 - i * 30
                glow_pen = QPen(QColor(255, 100, 100, glow_opacity), 1.5, Qt.SolidLine)
                painter.setPen(glow_pen)
                painter.drawEllipse(pos, glow_size, glow_size)

            painter.restore()

        # Continue with normal foreground drawing
        super().drawForeground(painter, rect)

    def drawBackground(self, painter, rect):
        """
        Draw the background of the scene.
        """
        theme = getattr(self, "theme", "light")
        if theme == "dark":
            grad = QLinearGradient(rect.topLeft(), rect.bottomRight())
            grad.setColorAt(0, QColor(36, 42, 56))
            grad.setColorAt(1, QColor(24, 28, 40))
            painter.fillRect(rect, grad)
        else:
            color1 = QColor(246, 248, 250)
            color2 = QColor(231, 242, 250)
            grad = QLinearGradient(rect.topLeft(), rect.bottomRight())
            grad.setColorAt(0, color1)
            grad.setColorAt(1, color2)
            painter.fillRect(rect, grad)
        # Draw subtle grid lines in both modes
        painter.save()
        grid_color = (
            QColor(50, 60, 80, 80) if theme == "dark" else QColor(180, 200, 220, 60)
        )
        painter.setPen(grid_color)
        grid_size = 32
        left = int(rect.left()) - (int(rect.left()) % grid_size)
        top = int(rect.top()) - (int(rect.top()) % grid_size)
        for x in range(left, int(rect.right()), grid_size):
            painter.drawLine(x, int(rect.top()), x, int(rect.bottom()))
        for y in range(top, int(rect.bottom()), grid_size):
            painter.drawLine(int(rect.left()), y, int(rect.right()), y)
        painter.restore()

    def load_from_json(self, data):
        """
        Load pipeline design from a JSON string.
        Clears the scene and reconstructs components and connections using the legacy logic from file_io.load_pipeline.
        """
        import os
        import tempfile

        from .file_io import load_pipeline

        # Write the JSON string to a temporary file to reuse load_pipeline logic
        with tempfile.NamedTemporaryFile(delete=False, suffix=".json", mode="w") as tmp:
            tmp.write(data)
            tmp_path = tmp.name
        # Use a dummy component_counts dict (caller can update real one if needed)
        dummy_counts = {}
        try:
            load_pipeline(self, tmp_path, dummy_counts)
        finally:
            os.remove(tmp_path)

    def create_connection(self, start_block, start_port, end_block, end_port):
        """
        Create a new connection between components with undo support.

        Args:
            start_block: The source component block
            start_port: The source port name
            end_block: The destination component block
            end_port: The destination port name

        Returns:
            The created connection
        """
        from .undo_stack import AddConnectionCommand

        connection = Connection(start_block, start_port, end_block, end_port)

        # Use undo command if available
        if hasattr(self.parent(), "undo_stack"):
            command = AddConnectionCommand(self, connection)
            self.parent().undo_stack.push(command)
            print(f"[DEBUG] Added connection with undo support: {connection}")
        else:
            # Fallback for backward compatibility
            self.addItem(connection)
            self.connections.append(connection)
            print(f"[DEBUG] Added connection without undo support: {connection}")

        return connection

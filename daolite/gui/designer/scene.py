"""
PipelineScene for the daolite pipeline designer.
"""

import logging
from PyQt5.QtCore import Qt, QRectF
from PyQt5.QtGui import QPen, QColor, QLinearGradient
from PyQt5.QtWidgets import QGraphicsScene
from .component_block import ComponentBlock
from .component_container import ComputeBox, GPUBox
from .connection import Connection, TransferIndicator
from .connection_manager import update_connection_indicators

logger = logging.getLogger('PipelineDesigner')

class PipelineScene(QGraphicsScene):
    """
    Custom graphics scene for the pipeline designer.
    Handles interactions, connections, and component management.
    """
    def __init__(self, parent=None, theme='light'):
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
        """
        Handle mouse press events for interaction with the scene.
        """
        super().mousePressEvent(event)
        # Add logic for mouse press event handling

    def mouseMoveEvent(self, event):
        """
        Handle mouse move events for interaction with the scene.
        """
        super().mouseMoveEvent(event)
        # Add logic for mouse move event handling

    def mouseReleaseEvent(self, event):
        """
        Handle mouse release events for interaction with the scene.
        """
        super().mouseReleaseEvent(event)
        # Add logic for mouse release event handling

    def keyPressEvent(self, event):
        """
        Handle key press events for deleting items and undo/redo.
        Zoom functionality has been moved to PipelineView.
        """
        from PyQt5.QtWidgets import QUndoStack
        from PyQt5.QtGui import QKeySequence
        from PyQt5.QtCore import Qt
        # Delete selected items
        if event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            for item in self.selectedItems():
                # Delete connections
                if hasattr(item, 'disconnect'):
                    item.disconnect()
                    if hasattr(self, 'connections') and item in self.connections:
                        self.connections.remove(item)
                    self.removeItem(item)
                # Delete components/blocks/containers
                elif hasattr(item, '_on_delete'):
                    item._on_delete()
            self.update()
        # Undo/Redo
        elif (event.matches(QKeySequence.Undo) or
              (event.modifiers() & Qt.ControlModifier and event.key() == Qt.Key_Z)):
            if hasattr(self.parent(), 'undo_stack'):
                self.parent().undo_stack.undo()
        elif (event.matches(QKeySequence.Redo) or
              (event.modifiers() & Qt.ControlModifier and event.key() == Qt.Key_Y)):
            if hasattr(self.parent(), 'undo_stack'):
                self.parent().undo_stack.redo()
        else:
            super().keyPressEvent(event)

    def drawForeground(self, painter, rect):
        """
        Draw the foreground of the scene.
        """
        super().drawForeground(painter, rect)
        # Add logic for drawing the foreground

    def drawBackground(self, painter, rect):
        """
        Draw the background of the scene.
        """
        theme = getattr(self, 'theme', 'light')
        if theme == 'dark':
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
        grid_color = QColor(50, 60, 80, 80) if theme == 'dark' else QColor(180, 200, 220, 60)
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
        import json
        from .file_io import load_pipeline
        import tempfile
        import os
        # Write the JSON string to a temporary file to reuse load_pipeline logic
        with tempfile.NamedTemporaryFile(delete=False, suffix='.json', mode='w') as tmp:
            tmp.write(data)
            tmp_path = tmp.name
        # Use a dummy component_counts dict (caller can update real one if needed)
        dummy_counts = {}
        try:
            load_pipeline(self, tmp_path, dummy_counts)
        finally:
            os.remove(tmp_path)

"""
PipelineView for the daolite pipeline designer.

This module provides the custom QGraphicsView subclass used to display and
interact with the pipeline scene.
"""

import logging
from PyQt5.QtWidgets import QGraphicsView, QMenu, QApplication
from PyQt5.QtCore import Qt, QPoint, QRectF
from PyQt5.QtGui import QPainter, QWheelEvent, QKeyEvent

logger = logging.getLogger('PipelineDesigner')

class PipelineView(QGraphicsView):
    """
    Custom graphics view for the pipeline designer.
    
    Handles view-specific functionality like zoom, pan, anti-aliasing,
    and context menus.
    """
    
    def __init__(self, scene=None, parent=None):
        """
        Initialize the pipeline view.
        
        Args:
            scene: The scene to display in the view
            parent: The parent widget
        """
        super().__init__(scene, parent)
        
        # View configuration
        self.setRenderHint(QPainter.Antialiasing, True)
        self.setRenderHint(QPainter.TextAntialiasing, True)
        self.setRenderHint(QPainter.SmoothPixmapTransform, True)
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setInteractive(True)
        
        # Set a reasonable initial scale
        self.setSceneRect(0, 0, 2000, 1500)
        
        # Panning variables
        self._panning = False
        self._pan_start_x = 0
        self._pan_start_y = 0
        
        # Context menu position
        self._context_pos = QPoint()
        
        # Scale factor for zoom operations
        self._zoom_factor = 1.2
        
        # Current theme
        self._theme = 'light'

    def set_theme(self, theme):
        """Set the view theme."""
        self._theme = theme
        self.viewport().update()

    def wheelEvent(self, event):
        """
        Handle mouse wheel events for zooming in and out.
        
        Args:
            event: The wheel event
        """
        # Get the current scale factor
        current_scale = self.transform().m11()
        
        # Calculate the new scale factor based on wheel direction
        if event.angleDelta().y() > 0:
            # Zoom in
            scale_factor = self._zoom_factor
        else:
            # Zoom out
            scale_factor = 1 / self._zoom_factor
        
        # Apply scaling limits
        new_scale = current_scale * scale_factor
        if new_scale < 0.1 or new_scale > 10:
            return
        
        # Apply the scale
        self.scale(scale_factor, scale_factor)
        
        # Update the view
        self.viewport().update()

    def keyPressEvent(self, event):
        """
        Handle key press events for the view.
        
        Args:
            event: The key press event
        """
        # Handle view-specific key events (Zoom in/out)
        if event.key() in (Qt.Key_Plus, Qt.Key_Equal):
            # Zoom in
            self.scale(self._zoom_factor, self._zoom_factor)
            event.accept()
        elif event.key() in (Qt.Key_Minus, Qt.Key_Underscore):
            # Zoom out
            self.scale(1/self._zoom_factor, 1/self._zoom_factor)
            event.accept()
        elif event.key() == Qt.Key_Space:
            # Reset zoom and centering
            self.resetTransform()
            self.centerOn(1000, 750)  # Center on the middle of the scene
            event.accept()
        else:
            # Pass other key events to the parent
            super().keyPressEvent(event)

    def mousePressEvent(self, event):
        """
        Handle mouse press events.
        
        Args:
            event: The mouse press event
        """
        # Middle button for panning
        if event.button() == Qt.MiddleButton:
            self._panning = True
            self._pan_start_x = event.x()
            self._pan_start_y = event.y()
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
        # Right button for context menu
        elif event.button() == Qt.RightButton:
            self._context_pos = event.pos()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """
        Handle mouse move events.
        
        Args:
            event: The mouse move event
        """
        # Handle panning when middle button is pressed
        if self._panning:
            # Calculate the difference between the current and previous positions
            dx = event.x() - self._pan_start_x
            dy = event.y() - self._pan_start_y
            
            # Update the starting point
            self._pan_start_x = event.x()
            self._pan_start_y = event.y()
            
            # Pan the view
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - dx)
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - dy)
            
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """
        Handle mouse release events.
        
        Args:
            event: The mouse release event
        """
        # End panning when middle button is released
        if event.button() == Qt.MiddleButton:
            self._panning = False
            self.setCursor(Qt.ArrowCursor)
            event.accept()
        # Show context menu on right button release
        elif event.button() == Qt.RightButton:
            # Allow the parent to create and show the context menu
            super().mouseReleaseEvent(event)
        else:
            super().mouseReleaseEvent(event)

    def contextMenuEvent(self, event):
        """
        Show a context menu on right click.
        
        Args:
            event: The context menu event
        """
        # Store the position
        self._context_pos = event.pos()
        
        # Let the parent handle the context menu
        super().contextMenuEvent(event)

    def get_scene_center_point(self):
        """
        Get the center point of the current view in scene coordinates.
        
        Returns:
            QPointF: The center point in scene coordinates
        """
        # Get the viewport center
        viewport_center = self.viewport().rect().center()
        
        # Convert to scene coordinates
        return self.mapToScene(viewport_center)

    def center_on_item(self, item):
        """
        Center the view on a specific item.
        
        Args:
            item: The item to center on
        """
        if item:
            self.centerOn(item)

    def center_on_items(self, items):
        """
        Center the view to fit all specified items.
        
        Args:
            items: List of items to fit in view
        """
        if not items:
            return
            
        # Calculate the bounding rect of all items
        rect = QRectF()
        for item in items:
            rect |= item.sceneBoundingRect()
            
        # Add some padding
        rect.adjust(-50, -50, 50, 50)
            
        # Center and fit the view on the rect
        self.fitInView(rect, Qt.KeepAspectRatio)

    def zoom_reset(self):
        """Reset the zoom level to default."""
        self.resetTransform()

    def zoom_in(self):
        """Zoom in by one step."""
        self.scale(self._zoom_factor, self._zoom_factor)

    def zoom_out(self):
        """Zoom out by one step."""
        self.scale(1/self._zoom_factor, 1/self._zoom_factor)

    def zoom_to_fit(self):
        """Zoom to fit all items in the scene."""
        # Get all items in the scene
        if self.scene():
            items = self.scene().items()
            if items:
                # Calculate the bounding rect of all items
                rect = QRectF()
                for item in items:
                    rect |= item.sceneBoundingRect()
                
                # Add some padding
                rect.adjust(-50, -50, 50, 50)
                
                # Fit the view to the rect
                self.fitInView(rect, Qt.KeepAspectRatio)
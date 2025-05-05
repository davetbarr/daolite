"""
Undo/Redo functionality for the Pipeline Designer.

This module provides custom undo commands for various operations in the pipeline designer,
allowing users to undo and redo their actions.
"""

from PyQt5.QtWidgets import QUndoCommand
from PyQt5.QtCore import QPointF
from daolite.common import ComponentType


class AddComponentCommand(QUndoCommand):
    """Command for adding a component to the scene."""
    
    def __init__(self, scene, component, description=None):
        """
        Initialize the add component command.
        
        Args:
            scene: The scene where the component will be added
            component: The component to add
            description: Optional description for the undo stack
        """
        super().__init__(description or f"Add {component.name}")
        self.scene = scene
        self.component = component
        self.added = False

    def redo(self):
        """Execute or redo adding the component to the scene."""
        if not self.added:
            self.scene.addItem(self.component)
            self.added = True
        else:
            self.component.setVisible(True)
            # Add back to scene's internal lists if needed
            if hasattr(self.scene, "_items") and self.component not in self.scene._items:
                self.scene._items.append(self.component)

    def undo(self):
        """Undo adding the component by removing it from the scene."""
        self.component.setVisible(False)
        # Remove from scene's internal lists if needed
        if hasattr(self.scene, "_items") and self.component in self.scene._items:
            self.scene._items.remove(self.component)


class RemoveComponentCommand(QUndoCommand):
    """Command for removing a component from the scene."""
    
    def __init__(self, scene, component, connections=None, description=None):
        """
        Initialize the remove component command.
        
        Args:
            scene: The scene where the component will be removed from
            component: The component to remove
            connections: List of connections associated with this component
            description: Optional description for the undo stack
        """
        super().__init__(description or f"Remove {component.name}")
        self.scene = scene
        self.component = component
        self.connections = connections or []
        self.original_pos = component.pos()
        
        # Store parent information if component has a parent
        self.parent_item = component.parentItem()
        if self.parent_item:
            self.parent_pos = self.parent_item.pos()
            
        # Store child items if this is a container (ComputeBox or GPUBox)
        self.child_items = []
        if hasattr(component, 'childItems'):
            for child in component.childItems():
                self.child_items.append({
                    'item': child,
                    'pos': child.pos()
                })

    def redo(self):
        """Execute or redo removing the component from the scene."""
        self.component.setVisible(False)
        # Remove from scene's internal lists if needed
        if hasattr(self.scene, "_items") and self.component in self.scene._items:
            self.scene._items.remove(self.component)
        
        # Hide connections
        for connection in self.connections:
            connection.setVisible(False)
            if hasattr(self.scene, "connections") and connection in self.scene.connections:
                self.scene.connections.remove(connection)
                
        # Hide child items if this is a container
        for child_data in self.child_items:
            child_data['item'].setVisible(False)

    def undo(self):
        """Undo removing the component by adding it back to the scene."""
        # Restore parent-child relationships first if needed
        if self.parent_item:
            self.component.setParentItem(self.parent_item)
            
        # Make component visible again
        self.component.setVisible(True)
        self.component.setPos(self.original_pos)
        
        # Add back to scene's internal lists if needed
        if hasattr(self.scene, "_items") and self.component not in self.scene._items:
            self.scene._items.append(self.component)
        
        # Restore connections
        for connection in self.connections:
            connection.setVisible(True)
            if hasattr(self.scene, "connections") and connection not in self.scene.connections:
                self.scene.connections.append(connection)
                
        # Make child items visible again
        for child_data in self.child_items:
            child_data['item'].setVisible(True)
            child_data['item'].setPos(child_data['pos'])


class MoveComponentCommand(QUndoCommand):
    """Command for moving a component in the scene."""
    
    def __init__(self, component, old_pos, new_pos, description=None):
        """
        Initialize the move component command.
        
        Args:
            component: The component that was moved
            old_pos: The original position
            new_pos: The new position
            description: Optional description for the undo stack
        """
        super().__init__(description or f"Move {getattr(component, 'name', 'Component')}")
        self.component = component
        self.old_pos = old_pos
        self.new_pos = new_pos
        
        # Track child items positions for container components
        self.child_positions = {}
        if hasattr(component, 'childItems'):
            for child in component.childItems():
                # Store each child's scene position (not relative to parent)
                if child.isVisible() and not child.parentItem() == component:
                    continue  # Skip items that are not direct children
                self.child_positions[child] = child.pos()

    def redo(self):
        """Execute or redo the move operation."""
        self.component.setPos(self.new_pos)
        
        # Update any connections if needed
        if hasattr(self.component, "update_connections"):
            self.component.update_connections()
        
        # Handle transfer indicators for container moves
        if hasattr(self.component, 'childItems'):
            # Update all connections for child items
            for child in self.component.childItems():
                for connection in self._get_connected_connections(child):
                    if hasattr(connection, 'update_path'):
                        connection.update_path()
                    if hasattr(connection, 'update_transfer_indicators'):
                        connection.update_transfer_indicators()

    def undo(self):
        """Undo the move operation by restoring the original position."""
        self.component.setPos(self.old_pos)
        
        # Update any connections if needed
        if hasattr(self.component, "update_connections"):
            self.component.update_connections()
        
        # Handle transfer indicators for container moves
        if hasattr(self.component, 'childItems'):
            # Update all connections for child items
            for child in self.component.childItems():
                for connection in self._get_connected_connections(child):
                    if hasattr(connection, 'update_path'):
                        connection.update_path()
                    if hasattr(connection, 'update_transfer_indicators'):
                        connection.update_transfer_indicators()
    
    def _get_connected_connections(self, component):
        """Helper method to find connections related to a component."""
        connections = []
        scene = component.scene()
        if not scene:
            return connections
            
        # Look for connections in the scene
        if hasattr(scene, 'connections'):
            for connection in scene.connections:
                if (hasattr(connection, 'start_block') and connection.start_block == component) or \
                   (hasattr(connection, 'end_block') and connection.end_block == component):
                    connections.append(connection)
        
        return connections


class RenameComponentCommand(QUndoCommand):
    """Command for renaming a component."""
    
    def __init__(self, component, old_name, new_name, description=None):
        """
        Initialize the rename component command.
        
        Args:
            component: The component to rename
            old_name: The original name
            new_name: The new name
            description: Optional description for the undo stack
        """
        super().__init__(description or f"Rename {old_name} to {new_name}")
        self.component = component
        self.old_name = old_name
        self.new_name = new_name

    def redo(self):
        """Execute or redo the rename operation."""
        self.component.name = self.new_name
        if hasattr(self.component, "update"):
            self.component.update()

    def undo(self):
        """Undo the rename operation by restoring the original name."""
        self.component.name = self.old_name
        if hasattr(self.component, "update"):
            self.component.update()


class AddConnectionCommand(QUndoCommand):
    """Command for adding a connection between components."""
    
    def __init__(self, scene, connection, description=None):
        """
        Initialize the add connection command.
        
        Args:
            scene: The scene where the connection will be added
            connection: The connection to add
            description: Optional description for the undo stack
        """
        super().__init__(description or "Add Connection")
        self.scene = scene
        self.connection = connection
        self.added = False

    def redo(self):
        """Execute or redo adding the connection to the scene."""
        if not self.added:
            self.scene.addItem(self.connection)
            self.added = True
        else:
            self.connection.setVisible(True)
        
        # Add to scene's connections list if needed
        if hasattr(self.scene, "connections") and self.connection not in self.scene.connections:
            self.scene.connections.append(self.connection)

    def undo(self):
        """Undo adding the connection by removing it from the scene."""
        self.connection.setVisible(False)
        # Remove from scene's connections list if needed
        if hasattr(self.scene, "connections") and self.connection in self.scene.connections:
            self.scene.connections.remove(self.connection)


class RemoveConnectionCommand(QUndoCommand):
    """Command for removing a connection between components."""
    
    def __init__(self, scene, connection, description=None):
        """
        Initialize the remove connection command.
        
        Args:
            scene: The scene where the connection will be removed from
            connection: The connection to remove
            description: Optional description for the undo stack
        """
        super().__init__(description or "Remove Connection")
        self.scene = scene
        self.connection = connection
        self.start_block = connection.start_block
        self.end_block = connection.end_block
        self.start_port = connection.start_port
        self.end_port = connection.end_port

    def redo(self):
        """Execute or redo removing the connection from the scene."""
        self.connection.disconnect()
        self.connection.setVisible(False)
        # Remove from scene's connections list if needed
        if hasattr(self.scene, "connections") and self.connection in self.scene.connections:
            self.scene.connections.remove(self.connection)

    def undo(self):
        """Undo removing the connection by adding it back to the scene."""
        self.connection.connect(self.start_block, self.start_port, self.end_block, self.end_port)
        self.connection.setVisible(True)
        # Add back to scene's connections list if needed
        if hasattr(self.scene, "connections") and self.connection not in self.scene.connections:
            self.scene.connections.append(self.connection)


class ChangeParameterCommand(QUndoCommand):
    """Command for changing component parameters."""
    
    def __init__(self, component, old_params, new_params, description=None):
        """
        Initialize the change parameter command.
        
        Args:
            component: The component whose parameters changed
            old_params: The original parameters
            new_params: The new parameters
            description: Optional description for the undo stack
        """
        super().__init__(description or f"Change {component.name} Parameters")
        self.component = component
        self.old_params = old_params.copy() if old_params else {}
        self.new_params = new_params.copy() if new_params else {}

    def redo(self):
        """Execute or redo the parameter change."""
        self.component.params = self.new_params.copy()
        if hasattr(self.component, "update"):
            self.component.update()

    def undo(self):
        """Undo the parameter change by restoring the original parameters."""
        self.component.params = self.old_params.copy()
        if hasattr(self.component, "update"):
            self.component.update()


class CompositeCommand(QUndoCommand):
    """A composite command that groups multiple commands together."""
    
    def __init__(self, description=None):
        """
        Initialize a composite command.
        
        Args:
            description: Optional description for the undo stack
        """
        super().__init__(description or "Composite Action")
        self.commands = []

    def add_command(self, command):
        """Add a command to the composite."""
        self.commands.append(command)

    def redo(self):
        """Execute or redo all commands in the composite."""
        for command in self.commands:
            command.redo()

    def undo(self):
        """Undo all commands in the composite in reverse order."""
        for command in reversed(self.commands):
            command.undo()
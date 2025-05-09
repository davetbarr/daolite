"""
Parameter propagation dialog for pipeline components.

This dialog appears when a parameter is updated in a component,
allowing users to propagate the change to related components.
"""

from typing import Dict, Any, List, Tuple
from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QCheckBox,
    QPushButton,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QWidget,
    QGridLayout,
    QGroupBox,
)

from daolite.common import ComponentType
from ..style_utils import set_app_style


class ParameterPropagationDialog(QDialog):
    """
    Dialog for selecting which components should receive parameter updates.
    
    Shows a list of components that share parameters with the component being edited,
    allowing the user to select which ones should receive the updated values.
    """

    def __init__(
        self,
        parameter_name: str,
        parameter_value: Any,
        affected_components: List[Tuple[Any, List[str]]],
        parent=None,
    ):
        """
        Initialize the dialog with components that might be affected by the parameter change.

        Args:
            parameter_name: Name of the parameter being updated
            parameter_value: New value of the parameter
            affected_components: List of (component, param_names) tuples where component is the 
                                affected component object and param_names are the parameter names
                                that map to the updated parameter in that component
            parent: Parent widget
        """
        super().__init__(parent)
        self.parameter_name = parameter_name
        self.parameter_value = parameter_value
        self.affected_components = affected_components
        self.selected_components = {}
        
        display_name = parameter_name.replace("_", " ").title()
        self.setWindowTitle(f"Update Shared Parameter: {display_name}")
        self.resize(500, 350)

        self._init_ui()
        
        # Apply styling after UI is created
        set_app_style(self)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        # Format display value
        if isinstance(self.parameter_value, int) and self.parameter_name in [
            "n_pixels", "n_subapertures", "n_actuators"
        ]:
            display_value = f"{self.parameter_value:,}"
        elif self.parameter_name == "bit_depth":
            display_value = f"{self.parameter_value}-bit"
        elif isinstance(self.parameter_value, float):
            display_value = f"{self.parameter_value:g}"
        elif hasattr(self.parameter_value, "shape"):
            display_value = f"Array {getattr(self.parameter_value, 'shape', '')}"
        else:
            display_value = str(self.parameter_value)
        
        # Add explanation label
        display_name = self.parameter_name.replace("_", " ").title()
        explanation = (
            f"The parameter <b>{display_name}</b> has been updated to <b>{display_value}</b>.<br>"
            f"This parameter is shared by other components in the pipeline.<br><br>"
        )
        
        if not self.affected_components:
            explanation += "<b>No components found that can receive this update.</b>"
        else:
            explanation += f"Select which components should also receive this update:"
        
        explanation_label = QLabel(explanation)
        explanation_label.setWordWrap(True)
        layout.addWidget(explanation_label)
        
        print(f"[DEBUG] Setting up dialog with {len(self.affected_components)} affected components")
        
        # Only create components group if we have affected components
        self.component_checkboxes = {}
        
        if self.affected_components:
            # Create components group
            component_group = QGroupBox("Affected Components")
            group_layout = QVBoxLayout()
            
            # Create a grid layout for our components
            component_layout = QGridLayout()
            
            # Add components with checkboxes
            row = 0
            
            for component, param_names in self.affected_components:
                # Format component name
                component_name = getattr(component, "name", str(component))
                
                # Format component type
                component_type = "Unknown"
                if hasattr(component, "component_type"):
                    component_type = component.component_type.name.replace("_", " ").title()
                
                # Format parameter names in this component
                param_display = ", ".join(name.replace("_", " ").title() for name in param_names)
                
                # Create checkbox and labels
                checkbox = QCheckBox()
                checkbox.setChecked(True)  # Default to checked
                self.component_checkboxes[component] = checkbox
                
                # Add to layout
                component_layout.addWidget(checkbox, row, 0)
                component_layout.addWidget(QLabel(f"{component_name} ({component_type})"), row, 1)
                component_layout.addWidget(QLabel(f"→ {param_display}"), row, 2)
                
                print(f"[DEBUG] Added row {row}: {component_name} ({component_type}) → {param_display}")
                row += 1
            
            # Add the grid layout to the group layout
            group_layout.addLayout(component_layout)
            component_group.setLayout(group_layout)
            
            # Create a scroll area
            scroll_area = QScrollArea()
            scroll_area.setWidgetResizable(True)
            scroll_area.setWidget(component_group)
            
            # Add scroll area to dialog layout
            layout.addWidget(scroll_area)
            
            print(f"[DEBUG] Added scroll area with {row} components")
        
        # Add buttons
        button_layout = QHBoxLayout()
        
        if self.affected_components:
            select_all_btn = QPushButton("Select All")
            select_all_btn.clicked.connect(self._select_all)
            button_layout.addWidget(select_all_btn)
            
            select_none_btn = QPushButton("Select None")
            select_none_btn.clicked.connect(self._select_none)
            button_layout.addWidget(select_none_btn)
            
            button_layout.addStretch()
            
            update_btn = QPushButton("Update Selected")
            update_btn.clicked.connect(self.accept)
            button_layout.addWidget(update_btn)
        else:
            button_layout.addStretch()
        
        cancel_btn = QPushButton("Close")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)

    def _select_all(self):
        """Select all checkboxes."""
        if not hasattr(self, 'component_checkboxes'):
            return
            
        for checkbox in self.component_checkboxes.values():
            if checkbox is not None:
                try:
                    checkbox.setChecked(True)
                except RuntimeError:
                    # Skip if the checkbox has been deleted
                    pass
            
    def _select_none(self):
        """Deselect all checkboxes."""
        if not hasattr(self, 'component_checkboxes'):
            return
            
        for checkbox in self.component_checkboxes.values():
            if checkbox is not None:
                try:
                    checkbox.setChecked(False)
                except RuntimeError:
                    # Skip if the checkbox has been deleted
                    pass
    
    def get_selected_components(self) -> Dict[Any, List[str]]:
        """
        Get the components that were selected for parameter propagation.
        
        Returns:
            Dict mapping component objects to lists of parameter names to update
        """
        selected = {}
        for component, checkbox in self.component_checkboxes.items():
            if checkbox.isChecked():
                # Find the corresponding parameter names for this component
                for comp, param_names in self.affected_components:
                    if comp is component:
                        selected[component] = param_names
                        break
        
        return selected
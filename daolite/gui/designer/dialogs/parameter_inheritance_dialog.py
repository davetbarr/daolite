"""
Parameter inheritance dialog for pipeline components.

This dialog appears when connecting components to allow inheriting parameters 
from connected components to maintain consistency across the pipeline.
"""

from typing import Dict, Any, List
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


class ParameterInheritanceDialog(QDialog):
    """
    Dialog for selecting which parameters to inherit from connected components.
    
    Shows a list of parameters that can be inherited from connected components
    with checkboxes to select which ones to apply.
    """

    def __init__(
        self,
        component_type: ComponentType,
        inheritable_params: Dict[str, Any],
        source_components: List[str],
        parent=None,
    ):
        """
        Initialize the dialog with parameters that can be inherited.

        Args:
            component_type: Type of component being configured
            inheritable_params: Dict of parameter name to value that can be inherited
            source_components: List of component names providing the parameters
            parent: Parent widget
        """
        super().__init__(parent)
        self.component_type = component_type
        self.inheritable_params = inheritable_params
        self.source_components = source_components
        self.selected_params = {}
        
        self.setWindowTitle(f"Inherit Parameters for {component_type.value}")
        self.resize(450, 320)

        self._init_ui()
        
        # Apply styling after UI is created
        set_app_style(self)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        # Add explanation label
        if len(self.source_components) == 1:
            explanation = f"The following parameters can be inherited from '{self.source_components[0]}':"
        else:
            explanation = f"The following parameters can be inherited from connected components ({', '.join(self.source_components)}):"
        
        explanation_label = QLabel(explanation)
        explanation_label.setWordWrap(True)
        layout.addWidget(explanation_label)
        
        # Create parameter group
        param_group = QGroupBox("Available Parameters")
        param_layout = QGridLayout()
        
        # Create scrollable area for parameters
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_widget.setLayout(param_layout)
        scroll_area.setWidget(scroll_widget)
        
        # Add parameters with checkboxes
        self.param_checkboxes = {}
        row = 0
        
        for name, value in self.inheritable_params.items():
            # Format display name
            display_name = name.replace("_", " ").title()
            
            # Format display value
            if hasattr(value, "shape"):
                display_value = f"Array {getattr(value, 'shape', '')}"
            elif name == "n_pixels" or name == "n_subapertures" or name == "n_actuators":
                display_value = f"{value:,}"
            elif name == "bit_depth":
                display_value = f"{value}-bit"
            elif isinstance(value, float):
                display_value = f"{value:g}"
            else:
                display_value = str(value)
            
            # Create checkbox
            checkbox = QCheckBox()
            checkbox.setChecked(True)  # Default to checked
            self.param_checkboxes[name] = checkbox
            
            # Add to layout
            param_layout.addWidget(checkbox, row, 0)
            param_layout.addWidget(QLabel(display_name), row, 1)
            param_layout.addWidget(QLabel(display_value), row, 2)
            row += 1
            
        # Add group to layout
        param_group.setLayout(param_layout)
        layout.addWidget(param_group)
        layout.addWidget(scroll_area)
        
        # Add buttons
        button_layout = QHBoxLayout()
        
        select_all_btn = QPushButton("Select All")
        select_all_btn.clicked.connect(self._select_all)
        button_layout.addWidget(select_all_btn)
        
        select_none_btn = QPushButton("Select None")
        select_none_btn.clicked.connect(self._select_none)
        button_layout.addWidget(select_none_btn)
        
        button_layout.addStretch()
        
        inherit_btn = QPushButton("Inherit Selected")
        inherit_btn.clicked.connect(self.accept)
        button_layout.addWidget(inherit_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)

    def _select_all(self):
        for checkbox in self.param_checkboxes.values():
            checkbox.setChecked(True)
            
    def _select_none(self):
        for checkbox in self.param_checkboxes.values():
            checkbox.setChecked(False)
    
    def get_selected_parameters(self) -> Dict[str, Any]:
        """
        Get the parameters that were selected for inheritance.
        
        Returns:
            Dict of parameter name to value for selected parameters
        """
        selected = {}
        for name, checkbox in self.param_checkboxes.items():
            if checkbox.isChecked():
                selected[name] = self.inheritable_params[name]
        
        return selected
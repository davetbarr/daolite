"""
Parameter configuration dialog for pipeline components.

This module provides dialog interfaces for configuring the parameters
of different pipeline component types.
"""

from typing import Dict, Any
from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QFormLayout,
    QLineEdit,
    QPushButton,
    QHBoxLayout,
    QCheckBox,
    QComboBox,
    QSpinBox,
    QLabel,
    QFileDialog,
    QMessageBox,
)

from daolite.common import ComponentType
from ..style_utils import set_app_style


class ComponentParametersDialog(QDialog):
    """
    Dialog for configuring component-specific parameters.

    Provides a customized form for each component type with appropriate
    parameters and validation.
    """

    def __init__(
        self,
        component_type: ComponentType,
        current_params: Dict[str, Any] = None,
        parent=None,
    ):
        """
        Initialize the dialog for a specific component type.

        Args:
            component_type: Type of component to configure
            current_params: Current parameter values (optional)
            parent: Parent widget
        """
        super().__init__(parent)
        self.component_type = component_type
        self.current_params = current_params or {}
        self.param_widgets = {}

        self.setWindowTitle(f"Configure {component_type.value} Parameters")
        self.resize(400, 300)

        layout = QVBoxLayout()

        # Create a form layout for parameters
        form_layout = QFormLayout()

        # Add component-specific parameters
        self._add_component_params(form_layout)

        layout.addLayout(form_layout)

        # Buttons
        button_layout = QHBoxLayout()

        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept)
        button_layout.addWidget(ok_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        layout.addLayout(button_layout)

        self.setLayout(layout)
        
        # Apply styling after all UI elements are created
        set_app_style(self)

    def _add_component_params(self, form_layout: QFormLayout):
        """
        Add component-specific parameters to the form, dynamically based on the function signature.
        """
        import inspect
        import importlib
        from daolite.common import ComponentType

        # Map component type to function import path
        func_map = {
            ComponentType.CAMERA: ("daolite.simulation.camera", "PCOCamLink"),
            ComponentType.CENTROIDER: ("daolite.pipeline.centroider", "Centroider"),
            ComponentType.RECONSTRUCTION: ("daolite.pipeline.reconstruction", "Reconstruction"),
            ComponentType.CALIBRATION: ("daolite.pipeline.calibration", "PixelCalibration"),
            ComponentType.CONTROL: ("daolite.pipeline.control", "FullFrameControl"),
            ComponentType.NETWORK: ("daolite.utils.network", "network_transfer"),
        }
        func_info = func_map.get(self.component_type)
        if not func_info:
            return  # Unknown component type
        module_name, func_name = func_info
        try:
            module = importlib.import_module(module_name)
            func = getattr(module, func_name)
        except Exception:
            return  # Could not import function
        sig = inspect.signature(func)
        # Build form fields for each parameter (skip self, debug, compute_resources, and start_times)
        for param in sig.parameters.values():
            if param.name in ("self", "debug", "compute_resources", "start_times"):  # skip
                continue
            # Special handling for agenda/centroid_agenda
            if param.name in ("agenda", "centroid_agenda"):
                agenda_layout = QHBoxLayout()
                self.agenda_lineedit = QLineEdit()
                self.agenda_lineedit.setReadOnly(True)
                if self.current_params.get("centroid_agenda_path"):
                    self.agenda_lineedit.setText(self.current_params["centroid_agenda_path"])
                agenda_btn = QPushButton("Select Centroid Agenda File")
                agenda_btn.clicked.connect(self._select_agenda_file)
                agenda_layout.addWidget(self.agenda_lineedit)
                agenda_layout.addWidget(agenda_btn)
                form_layout.addRow("Centroid Agenda:", agenda_layout)
                self.agenda_array = None
                self.agenda_path = self.current_params.get("centroid_agenda_path", None)
                if self.agenda_path:
                    self._load_agenda(self.agenda_path)
                continue
            # Checkbox for bools
            if param.annotation is bool or param.default is False or param.default is True:
                self._add_checkbox_param(form_layout, param.name, param.name.replace("_", " ").title())
            else:
                default = str(param.default) if param.default is not inspect.Parameter.empty else ""
                self._add_numeric_param(form_layout, param.name, param.name.replace("_", " ").title(), default=default)

    def _add_numeric_param(
        self,
        form_layout: QFormLayout,
        name: str,
        label: str,
        default: str = "",
        hint: str = "",
    ):
        """
        Add a numeric parameter input to the form.

        Args:
            form_layout: Form layout to add to
            name: Parameter name
            label: Display label
            default: Default value
            hint: Help text
        """
        edit = QLineEdit()

        # Set value from current params or default
        value = ""
        if name in self.current_params:
            value = str(self.current_params[name])
        elif default:
            value = default

        edit.setText(value)

        # Add tooltip if hint provided
        if hint:
            edit.setToolTip(hint)

        form_layout.addRow(f"{label}:", edit)
        self.param_widgets[name] = edit

    def _add_checkbox_param(
        self, form_layout: QFormLayout, name: str, label: str, hint: str = ""
    ):
        """
        Add a checkbox parameter to the form.

        Args:
            form_layout: Form layout to add to
            name: Parameter name
            label: Display label
            hint: Help text
        """
        checkbox = QCheckBox()

        # Set value from current params
        if name in self.current_params:
            checkbox.setChecked(bool(self.current_params[name]))

        # Add tooltip if hint provided
        if hint:
            checkbox.setToolTip(hint)

        form_layout.addRow(f"{label}:", checkbox)
        self.param_widgets[name] = checkbox

    def _select_agenda_file(self):
        """
        Open a file dialog to select a centroid agenda file.
        """
        import numpy as np
        filename, _ = QFileDialog.getOpenFileName(self, "Select Centroid Agenda File", "", "NumPy files (*.npy);;CSV files (*.csv);;All Files (*)")
        if not filename:
            return
        self.agenda_path = filename
        if hasattr(self, 'agenda_lineedit'):
            self.agenda_lineedit.setText(filename)
        self._load_agenda(filename)

    def _load_agenda(self, filename):
        """
        Load the selected centroid agenda file and display its summary.

        Args:
            filename: Path to the agenda file
        """
        import numpy as np
        try:
            if filename.endswith(".npy"):
                agenda = np.load(filename)
            elif filename.endswith(".csv"):
                agenda = np.loadtxt(filename, delimiter=",")
            else:
                agenda = np.load(filename)
            self.agenda_array = agenda
            self.agenda_path = filename
            if hasattr(self, 'agenda_lineedit'):
                self.agenda_lineedit.setText(f"Loaded: {filename.split('/')[-1]} (shape: {agenda.shape})")
            # Set group and n_valid_pixels based on loaded agenda
            group_value = agenda.shape[0] if hasattr(agenda, 'shape') and len(agenda.shape) > 0 else len(agenda)
            n_valid_subaps = int(np.sum(agenda))
            print(f"Loaded agenda with {group_value} groups and {n_valid_subaps} valid subaps.")
            # Set these values in the param widgets if present
            if 'group' in self.param_widgets:
                widget = self.param_widgets['group']
                if hasattr(widget, 'setText'):
                    widget.setText(str(group_value))
            if 'N Valid Subaps' in self.param_widgets:
                widget = self.param_widgets['N Valid Subaps']
                if hasattr(widget, 'setText'):
                    widget.setText(str(n_valid_subaps))
        except Exception as e:
            if hasattr(self, 'agenda_lineedit'):
                self.agenda_lineedit.setText("Load failed")
            QMessageBox.critical(self, "Load Error", f"Failed to load agenda: {e}")

    def get_parameters(self) -> Dict[str, Any]:
        """
        Get the configured parameters.

        Returns:
            Dict of parameter name to value
        """
        params = {}

        for name, widget in self.param_widgets.items():
            if isinstance(widget, QLineEdit):
                # Try to convert to appropriate type
                value = widget.text()
                if value:
                    try:
                        # If it contains a decimal point, convert to float
                        if "." in value:
                            params[name] = float(value)
                        # If it's a numeric expression like 80*80
                        elif "*" in value:
                            params[name] = eval(value)
                        # Otherwise convert to int
                        else:
                            params[name] = int(value)
                    except (ValueError, SyntaxError):
                        # If conversion fails, keep as string
                        params[name] = value

            elif isinstance(widget, QCheckBox):
                params[name] = widget.isChecked()

            elif isinstance(widget, QComboBox):
                params[name] = widget.currentText()

            elif isinstance(widget, QSpinBox):
                params[name] = widget.value()

        # Add agenda if present
        if hasattr(self, 'agenda_array') and self.agenda_array is not None:
            params["centroid_agenda"] = self.agenda_array
            params["centroid_agenda_path"] = self.agenda_path

        return params
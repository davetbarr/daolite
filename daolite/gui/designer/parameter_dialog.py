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

    def _add_component_params(self, form_layout: QFormLayout):
        """
        Add component-specific parameters to the form.

        Args:
            form_layout: Form layout to add parameters to
        """
        if self.component_type == ComponentType.CAMERA:
            # --- Camera simulation function dropdown ---
            from daolite.simulation import __all__ as camera_funcs

            camera_func_names = [
                f for f in camera_funcs if f.endswith("Camera") or f == "PCOCamLink"
            ]
            camera_func_combo = QComboBox()
            camera_func_combo.addItems(camera_func_names)
            # Set current value if present
            current_func = self.current_params.get("camera_function", "PCOCamLink")
            idx = camera_func_combo.findText(current_func)
            if idx >= 0:
                camera_func_combo.setCurrentIndex(idx)
            form_layout.addRow("Camera Simulation Type:", camera_func_combo)
            self.param_widgets["camera_function"] = camera_func_combo
            # --- End camera simulation function dropdown ---
            self._add_numeric_param(
                form_layout,
                "n_pixels",
                "Number of Pixels",
                hint="Total number of pixels (e.g., 1024*1024 for 1MP)",
            )
            self._add_numeric_param(
                form_layout,
                "n_subapertures",
                "Number of Subapertures",
                hint="Total subapertures (e.g., 80*80 for an 80×80 grid)",
            )
            self._add_numeric_param(
                form_layout,
                "pixels_per_subaperture",
                "Pixels per Subaperture",
                hint="Pixels per subaperture (e.g., 16*16)",
            )
            self._add_numeric_param(
                form_layout,
                "bit_depth",
                "Bit Depth",
                default="16",
                hint="Pixel bit depth",
            )
            self._add_numeric_param(
                form_layout,
                "readout_time",
                "Readout Time (μs)",
                default="500",
                hint="Camera readout time in microseconds",
            )
            self._add_numeric_param(
                form_layout,
                "group_size",
                "Group Size",
                default="50",
                hint="Number of packet groups",
            )

        elif self.component_type == ComponentType.CENTROIDER or self.component_type == ComponentType.RECONSTRUCTION:
            if self.component_type == ComponentType.CENTROIDER:
                self._add_numeric_param(
                    form_layout,
                    "n_subaps",
                    "Valid Subapertures",
                    hint="Number of valid subapertures",
                )
                self._add_numeric_param(
                    form_layout,
                    "n_pix_per_subap",
                    "Pixels per Subaperture",
                    hint="Pixels per subaperture (e.g., 16)",
                )
                self._add_checkbox_param(
                    form_layout,
                    "square_diff",
                    "Use Square Difference",
                    hint="Use square difference algorithm",
                )
                self._add_checkbox_param(
                    form_layout, "sort", "Use Sorting", hint="Apply sorting to results"
                )
                self._add_numeric_param(
                    form_layout,
                    "n_workers",
                    "Number of Workers",
                    default="4",
                    hint="Number of worker threads",
                )
                self._add_numeric_param(
                    form_layout,
                    "scale",
                    "Scale Factor",
                    default="1.0",
                    hint="Computation scale factor",
                )
            elif self.component_type == ComponentType.RECONSTRUCTION:
                self._add_numeric_param(
                    form_layout,
                    "n_slopes",
                    "Number of Slopes",
                    hint="Total number of slopes (usually 2 * valid subapertures)",
                )
                self._add_numeric_param(
                    form_layout,
                    "n_actuators",
                    "Number of Actuators",
                    hint="Total number of DM actuators",
                )
                self._add_numeric_param(
                    form_layout,
                    "scale",
                    "Scale Factor",
                    default="1.0",
                    hint="Computation scale factor",
                )
            # Add agenda file picker
            agenda_layout = QHBoxLayout()
            self.agenda_label = QLabel()
            agenda_btn = QPushButton("Select Centroid Agenda File")
            agenda_btn.clicked.connect(self._select_agenda_file)
            agenda_layout.addWidget(agenda_btn)
            agenda_layout.addWidget(self.agenda_label)
            form_layout.addRow("Centroid Agenda:", agenda_layout)
            # If already set, show summary
            self.agenda_array = None
            self.agenda_path = self.current_params.get("centroid_agenda_path", None)
            if self.agenda_path:
                self._load_agenda(self.agenda_path)

        elif self.component_type == ComponentType.CONTROL:
            self._add_numeric_param(
                form_layout,
                "n_actuators",
                "Number of Actuators",
                hint="Total number of DM actuators",
            )
            self._add_numeric_param(
                form_layout,
                "combine",
                "Number to Combine",
                default="1",
                hint="Number of frames to combine",
            )
            self._add_numeric_param(
                form_layout,
                "scale",
                "Scale Factor",
                default="1.0",
                hint="Computation scale factor",
            )

        elif self.component_type == ComponentType.CALIBRATION:
            self._add_numeric_param(
                form_layout,
                "n_pixels",
                "Number of Pixels",
                hint="Total number of pixels to calibrate",
            )
            self._add_numeric_param(
                form_layout,
                "group",
                "Group Size",
                default="50",
                hint="Number of packet groups",
            )
            self._add_numeric_param(
                form_layout,
                "scale",
                "Scale Factor",
                default="1.0",
                hint="Computation scale factor",
            )

        elif self.component_type == ComponentType.NETWORK:
            self._add_numeric_param(
                form_layout,
                "n_bits",
                "Number of Bits",
                hint="Total bits to transfer (e.g., actuators * 32)",
            )
            self._add_numeric_param(
                form_layout,
                "time_in_driver",
                "Driver Time (μs)",
                default="5",
                hint="Time spent in driver in microseconds",
            )

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
            self.agenda_label.setText(f"Loaded: {filename.split('/')[-1]} (shape: {agenda.shape})")
        except Exception as e:
            self.agenda_label.setText("Load failed")
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

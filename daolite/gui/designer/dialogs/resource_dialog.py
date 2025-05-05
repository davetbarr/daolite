from PyQt5.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QLabel, QLineEdit, QComboBox, QCheckBox, QPushButton, QDialogButtonBox, QWidget, QHBoxLayout
import inspect
import daolite.compute.hardware as hardware
from ..style_utils import set_app_style
from daolite.compute import create_compute_resources

class ResourceSelectionDialog(QDialog):
    """
    Dialog for selecting or configuring compute resources.
    Cleaned up: CPU dropdown (with custom), optional GPU (with custom),
    and only shows custom fields when needed.
    Now supports editing: pass existing_resource to pre-populate fields.
    """
    def __init__(self, parent=None, existing_resource=None):
        super().__init__(parent)
        self.setWindowTitle("Configure Computer Resource")
        self.resize(440, 420)
        self.cpu_name_string = None
        layout = QVBoxLayout()
        
        # Name field
        name_layout = QFormLayout()
        self.name_edit = QLineEdit("Computer")
        name_layout.addRow("Computer Name:", self.name_edit)
        layout.addLayout(name_layout)
        
        # --- Dynamic CPU list ---
        cpu_factories = [(name, func) for name, func in inspect.getmembers(hardware, inspect.isfunction) if name.startswith("amd_") or name.startswith("intel_")]
        self.cpu_names = []
        self.cpu_funcs = []
        for name, func in cpu_factories:
            try:
                res = func()
                label = getattr(res, "name", name.replace("_", " ").title())
            except Exception:
                label = name.replace("_", " ").title()
            self.cpu_names.append(label)
            self.cpu_funcs.append(func)
        self.cpu_names.append("Custom…")
        layout.addWidget(QLabel("CPU Model:"))
        self.cpu_combo = QComboBox()
        self.cpu_combo.addItems(self.cpu_names)
        layout.addWidget(self.cpu_combo)
        
        # Custom CPU fields (hidden by default)
        self.cpu_custom_fields = QFormLayout()
        self.cores_edit = QLineEdit("16")
        self.cpu_custom_fields.addRow("Cores:", self.cores_edit)
        self.freq_edit = QLineEdit("2.6e9")
        self.cpu_custom_fields.addRow("Core Frequency (Hz):", self.freq_edit)
        self.flops_edit = QLineEdit("32")
        self.cpu_custom_fields.addRow("FLOPS per cycle:", self.flops_edit)
        self.mem_channels_edit = QLineEdit("4")
        self.cpu_custom_fields.addRow("Memory Channels:", self.mem_channels_edit)
        self.mem_width_edit = QLineEdit("64")
        self.cpu_custom_fields.addRow("Memory Width (bits):", self.mem_width_edit)
        self.mem_freq_edit = QLineEdit("3200e6")
        self.cpu_custom_fields.addRow("Memory Frequency (Hz):", self.mem_freq_edit)
        self.network_edit = QLineEdit("100e9")
        self.cpu_custom_fields.addRow("Network Speed (bps):", self.network_edit)
        self.cpu_custom_fields_widget = QWidget()
        self.cpu_custom_fields_widget.setLayout(self.cpu_custom_fields)
        self.cpu_custom_fields_widget.setVisible(False)
        layout.addWidget(self.cpu_custom_fields_widget)
        self.cpu_name_string = self.cpu_combo.currentText()
        
        # --- Add GPU checkbox ---
        self.add_gpu_checkbox = QCheckBox("Add GPU")
        layout.addWidget(self.add_gpu_checkbox)
        
        # --- GPU dropdown (hidden by default) ---
        gpu_factories = [(name, func) for name, func in inspect.getmembers(hardware, inspect.isfunction) if name.startswith("nvidia_") or name.startswith("amd_mi")]
        self.gpu_names = []
        self.gpu_funcs = []
        for name, func in gpu_factories:
            try:
                res = func()
                label = getattr(res, "name", name.replace("_", " ").title())
            except Exception:
                label = name.replace("_", " ").title()
            self.gpu_names.append(label)
            self.gpu_funcs.append(func)
        self.gpu_names.append("Custom…")
        self.gpu_combo = QComboBox()
        self.gpu_combo.addItems(self.gpu_names)
        self.gpu_combo.setVisible(False)
        layout.addWidget(self.gpu_combo)
        
        # Custom GPU fields (hidden by default)
        self.gpu_custom_fields = QFormLayout()
        self.gpu_flops_edit = QLineEdit("1e12")
        self.gpu_custom_fields.addRow("FLOPS:", self.gpu_flops_edit)
        self.gpu_mem_bw_edit = QLineEdit("300e9")
        self.gpu_custom_fields.addRow("Memory Bandwidth (B/s):", self.gpu_mem_bw_edit)
        self.gpu_network_edit = QLineEdit("100e9")
        self.gpu_custom_fields.addRow("Network Speed (bps):", self.gpu_network_edit)
        self.gpu_time_in_driver_edit = QLineEdit("8")
        self.gpu_custom_fields.addRow("Time in Driver (us):", self.gpu_time_in_driver_edit)
        self.gpu_custom_fields_widget = QWidget()
        self.gpu_custom_fields_widget.setLayout(self.gpu_custom_fields)
        self.gpu_custom_fields_widget.setVisible(False)
        layout.addWidget(self.gpu_custom_fields_widget)
        
        # --- Button row ---
        button_layout = QHBoxLayout()
        self.add_btn = QPushButton("Add")
        self.add_btn.clicked.connect(self.accept)
        button_layout.addWidget(self.add_btn)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
        # --- Signals ---
        self.cpu_combo.currentIndexChanged.connect(self._on_cpu_changed)
        self.add_gpu_checkbox.toggled.connect(self._on_add_gpu_toggled)
        self.gpu_combo.currentIndexChanged.connect(self._on_gpu_changed)
        
        # State
        self.result_type = None
        self.result_index = None
        
        # After all widgets are created, pre-populate if editing
        if existing_resource is not None:
            # Set name
            self.name_edit.setText(getattr(existing_resource, 'name', 'Computer'))
            # Try to match CPU in dropdown
            cpu_name = getattr(existing_resource, 'name', None)
            cpu_idx = None
            for i, label in enumerate(self.cpu_names):
                if label == cpu_name:
                    cpu_idx = i
                    break
            if cpu_idx is not None:
                self.cpu_combo.setCurrentIndex(cpu_idx)
            else:
                # Custom CPU
                self.cpu_combo.setCurrentIndex(len(self.cpu_names) - 1)
                self.cpu_custom_fields_widget.setVisible(True)
                # Fill custom fields if present
                self.cores_edit.setText(str(getattr(existing_resource, 'cores', '16')))
                self.freq_edit.setText(str(getattr(existing_resource, 'core_frequency', '2.6e9')))
                self.flops_edit.setText(str(getattr(existing_resource, 'flops_per_cycle', '32')))
                self.mem_channels_edit.setText(str(getattr(existing_resource, 'memory_channels', '4')))
                self.mem_width_edit.setText(str(getattr(existing_resource, 'memory_width', '64')))
                self.mem_freq_edit.setText(str(getattr(existing_resource, 'memory_frequency', '3200e6')))
                self.network_edit.setText(str(getattr(existing_resource, 'network_speed', '100e9')))
            # GPU
            attached_gpus = getattr(existing_resource, 'attached_gpus', [])
            if attached_gpus:
                self.add_gpu_checkbox.setChecked(True)
                self.gpu_combo.setVisible(True)
                gpu = attached_gpus[0]
                gpu_name = getattr(gpu, 'name', None)
                gpu_idx = None
                for i, label in enumerate(self.gpu_names):
                    if label == gpu_name:
                        gpu_idx = i
                        break
                if gpu_idx is not None:
                    self.gpu_combo.setCurrentIndex(gpu_idx)
                else:
                    # Custom GPU
                    self.gpu_combo.setCurrentIndex(len(self.gpu_names) - 1)
                    self.gpu_custom_fields_widget.setVisible(True)
                    self.gpu_flops_edit.setText(str(getattr(gpu, 'flops', '1e12')))
                    self.gpu_mem_bw_edit.setText(str(getattr(gpu, 'memory_bandwidth', '300e9')))
                    self.gpu_network_edit.setText(str(getattr(gpu, 'network_speed', '100e9')))
                    self.gpu_time_in_driver_edit.setText(str(getattr(gpu, 'time_in_driver', '8')))
                    
        # Apply styling after all UI elements and connections are created
        set_app_style(self)

    def _on_cpu_changed(self, idx):
        self.cpu_custom_fields_widget.setVisible(idx == len(self.cpu_names) - 1)
        self.cpu_name_string = self.cpu_combo.currentText()

    def _on_add_gpu_toggled(self, checked):
        self.gpu_combo.setVisible(checked)
        self.gpu_custom_fields_widget.setVisible(checked and self.gpu_combo.currentIndex() == len(self.gpu_names) - 1)

    def _on_gpu_changed(self, idx):
        self.gpu_custom_fields_widget.setVisible(idx == len(self.gpu_names) - 1 and self.add_gpu_checkbox.isChecked())

    def get_selected_resource(self):
        # CPU
        cpu_idx = self.cpu_combo.currentIndex()
        if cpu_idx == len(self.cpu_names) - 1:
            # Custom CPU
            cpu_resource = create_compute_resources(
                cores=int(self.cores_edit.text()),
                core_frequency=float(self.freq_edit.text()),
                flops_per_cycle=int(self.flops_edit.text()),
                memory_channels=int(self.mem_channels_edit.text()),
                memory_width=int(self.mem_width_edit.text()),
                memory_frequency=float(self.mem_freq_edit.text()),
                network_speed=float(self.network_edit.text()),
                time_in_driver=5,
            )
        else:
            cpu_func = self.cpu_funcs[cpu_idx]
            cpu_resource = cpu_func()
        cpu_resource.name = self.name_edit.text().strip()
        # GPU
        attached_gpus = []
        if self.add_gpu_checkbox.isChecked():
            gpu_idx = self.gpu_combo.currentIndex()
            if gpu_idx == len(self.gpu_names) - 1:
                # Custom GPU
                from daolite.compute.base_resources import create_gpu_resource
                gpu_resource = create_gpu_resource(
                    flops=float(self.gpu_flops_edit.text()),
                    memory_bandwidth=float(self.gpu_mem_bw_edit.text()),
                    network_speed=float(self.gpu_network_edit.text()),
                    time_in_driver=float(self.gpu_time_in_driver_edit.text()),
                )
            else:
                gpu_func = self.gpu_funcs[gpu_idx]
                gpu_resource = gpu_func()
            attached_gpus.append(gpu_resource)
        # Always update attached_gpus, even if empty (removes GPU if unchecked)
        cpu_resource.attached_gpus = attached_gpus
        return cpu_resource

    def get_name(self):
        return self.name_edit.text().strip()

    def cpu_name(self):
        return self.cpu_name_string

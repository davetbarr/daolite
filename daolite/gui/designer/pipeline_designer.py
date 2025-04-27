"""
Main application for the daolite pipeline designer.

This module provides the main application window and functionality for
the visual pipeline designer, with emphasis on network and multi-compute
node configurations.
"""

import sys
from typing import List
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QGraphicsScene,
    QGraphicsView,
    QToolBar,
    QPushButton,
    QComboBox,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QAction,
    QFileDialog,
    QMessageBox,
    QInputDialog,
    QDialog,
    QFormLayout,
    QLineEdit,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter, QPen

from daolite.common import ComponentType
from daolite.compute import create_compute_resources
from daolite.compute.hardware import (
    amd_epyc_7763,
    amd_epyc_9654,
    intel_xeon_8480,
    intel_xeon_8462,
    amd_ryzen_7950x,
    nvidia_a100_80gb,
    nvidia_h100_80gb,
    nvidia_rtx_4090,
    amd_mi300x,
)
from daolite.config import SystemConfig, CameraConfig, OpticsConfig, PipelineConfig

from .components import ComponentBlock
from .connection import Connection
from .code_generator import CodeGenerator
from .parameter_dialog import ComponentParametersDialog


class PipelineScene(QGraphicsScene):
    """
    Custom graphics scene for the pipeline designer.

    Handles interactions, connections, and component management.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSceneRect(0, 0, 2000, 1500)

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

    def mousePressEvent(self, event):
        """Handle mouse press events for connection creation."""
        pos = event.scenePos()
        item = self.itemAt(pos, self.views()[0].transform())

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
                        if port is not self.selected_port and self.selected_port is not None:
                            # Only allow output->input or input->output
                            if self.selected_port.port_type != port.port_type:
                                # Always connect output to input
                                if self.selected_port.port_type == port.port_type.INPUT:
                                    src_block, src_port = item, port
                                    dst_block, dst_port = self.selected_block, self.selected_port
                                else:
                                    src_block, src_port = self.selected_block, self.selected_port
                                    dst_block, dst_port = item, port
                                # Create connection
                                conn = Connection(src_block, src_port)
                                if conn.complete_connection(dst_block, dst_port):
                                    self.connections.append(conn)
                                    self.addItem(conn)
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
        """Handle mouse move events for connection creation."""
        if self.current_connection:
            # Update the end point of the current connection
            self.current_connection.set_temp_end_point(event.scenePos())
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """Handle mouse release events for connection completion."""
        if self.current_connection and event.button() == Qt.LeftButton:
            pos = event.scenePos()
            item = self.itemAt(pos, self.views()[0].transform())
            if isinstance(item, ComponentBlock):
                port = item.find_port_at_point(pos)
                if port and port is not self.start_port:
                    # --- PCIe/Network Transfer Insertion Logic ---
                    src_block = self.start_block
                    dst_block = item
                    src_compute = getattr(src_block, "compute", None)
                    dst_compute = getattr(dst_block, "compute", None)
                    src_is_gpu = (
                        hasattr(src_compute, "is_gpu") and src_compute.is_gpu
                        if src_compute
                        else False
                    )
                    dst_is_gpu = (
                        hasattr(dst_compute, "is_gpu") and dst_compute.is_gpu
                        if dst_compute
                        else False
                    )
                    src_is_cpu = (
                        hasattr(src_compute, "is_cpu") and src_compute.is_cpu
                        if src_compute
                        else False
                    )
                    dst_is_cpu = (
                        hasattr(dst_compute, "is_cpu") and dst_compute.is_cpu
                        if dst_compute
                        else False
                    )
                    # Insert PCIe/network transfer if CPU<->GPU
                    if (src_is_cpu and dst_is_gpu) or (src_is_gpu and dst_is_cpu):
                        # Insert a network/PCIe transfer block between src and dst
                        from daolite.common import ComponentType

                        transfer_block = ComponentBlock(
                            ComponentType.NETWORK, "PCIe/Network"
                        )
                        # Place transfer block between src and dst
                        src_pos = src_block.pos()
                        dst_pos = dst_block.pos()
                        mid_pos = (src_pos + dst_pos) / 2
                        transfer_block.setPos(mid_pos)
                        self.addItem(transfer_block)
                        # Connect src -> transfer
                        out_port = (
                            src_block.output_ports[0]
                            if src_block.output_ports
                            else None
                        )
                        in_port = (
                            transfer_block.input_ports[0]
                            if transfer_block.input_ports
                            else None
                        )
                        if out_port and in_port:
                            conn1 = Connection(src_block, out_port)
                            conn1.complete_connection(transfer_block, in_port)
                            self.connections.append(conn1)
                            self.addItem(conn1)
                        # Connect transfer -> dst
                        out_port2 = (
                            transfer_block.output_ports[0]
                            if transfer_block.output_ports
                            else None
                        )
                        in_port2 = (
                            dst_block.input_ports[0] if dst_block.input_ports else None
                        )
                        if out_port2 and in_port2:
                            conn2 = Connection(transfer_block, out_port2)
                            conn2.complete_connection(dst_block, in_port2)
                            self.connections.append(conn2)
                            self.addItem(conn2)
                        # Remove the temporary connection
                        self.removeItem(self.current_connection)
                        self.current_connection = None
                        self.start_port = None
                        self.start_block = None
                        self.update()
                        return
                    # --- End PCIe/Network Transfer Logic ---
                    if self.current_connection.complete_connection(item, port):
                        self.connections.append(self.current_connection)
                        self.current_connection = None
                        self.start_port = None
                        self.start_block = None
                        self.update()
                        return
            self.removeItem(self.current_connection)
            self.current_connection = None
            self.start_port = None
            self.start_block = None
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        """Handle key press events for deleting connections."""
        if event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            for item in self.selectedItems():
                if isinstance(item, Connection):
                    item.disconnect()
                    if item in self.connections:
                        self.connections.remove(item)
                    self.removeItem(item)
            self.update()
        else:
            super().keyPressEvent(event)

    def drawForeground(self, painter, rect):
        """Draw visual feedback for click-to-connect."""
        if self.click_connect_mode and self.selected_port:
            painter.save()
            painter.setPen(QPen(Qt.red, 2, Qt.DashLine))
            pos = self.selected_port.get_scene_position()
            painter.drawEllipse(pos, 10, 10)
            painter.restore()
        super().drawForeground(painter, rect)


class ResourceSelectionDialog(QDialog):
    """
    Dialog for selecting or configuring compute resources.

    Allows users to choose from predefined resources or specify custom ones.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Compute Resource")
        self.resize(400, 300)

        layout = QVBoxLayout()

        # Predefined resources section
        layout.addWidget(QLabel("<b>Predefined Resources</b>"))

        # CPUs
        layout.addWidget(QLabel("CPUs:"))
        self.cpu_combo = QComboBox()
        self.cpu_combo.addItems(
            [
                "AMD EPYC 7763 (Milan)",
                "AMD EPYC 9654 (Genoa)",
                "Intel Xeon 8480+ (Sapphire Rapids)",
                "Intel Xeon 8462Y+ (Emerald Rapids)",
                "AMD Ryzen 9 7950X",
            ]
        )
        layout.addWidget(self.cpu_combo)

        # GPUs
        layout.addWidget(QLabel("GPUs:"))
        self.gpu_combo = QComboBox()
        self.gpu_combo.addItems(
            [
                "NVIDIA A100 80GB",
                "NVIDIA H100 80GB",
                "NVIDIA RTX 4090",
                "AMD Instinct MI300X",
            ]
        )
        layout.addWidget(self.gpu_combo)

        # Custom resource section
        layout.addWidget(QLabel("<b>Custom Resource</b>"))

        form_layout = QFormLayout()

        self.cores_edit = QLineEdit("16")
        form_layout.addRow("Cores:", self.cores_edit)

        self.freq_edit = QLineEdit("2.6e9")
        form_layout.addRow("Core Frequency (Hz):", self.freq_edit)

        self.flops_edit = QLineEdit("32")
        form_layout.addRow("FLOPS per cycle:", self.flops_edit)

        self.mem_channels_edit = QLineEdit("4")
        form_layout.addRow("Memory Channels:", self.mem_channels_edit)

        self.mem_width_edit = QLineEdit("64")
        form_layout.addRow("Memory Width (bits):", self.mem_width_edit)

        self.mem_freq_edit = QLineEdit("3200e6")
        form_layout.addRow("Memory Frequency (Hz):", self.mem_freq_edit)

        self.network_edit = QLineEdit("100e9")
        form_layout.addRow("Network Speed (bps):", self.network_edit)

        layout.addLayout(form_layout)

        # Buttons
        button_layout = QHBoxLayout()

        self.use_cpu_btn = QPushButton("Use Selected CPU")
        self.use_cpu_btn.clicked.connect(self.accept_cpu)
        button_layout.addWidget(self.use_cpu_btn)

        self.use_gpu_btn = QPushButton("Use Selected GPU")
        self.use_gpu_btn.clicked.connect(self.accept_gpu)
        button_layout.addWidget(self.use_gpu_btn)

        self.use_custom_btn = QPushButton("Use Custom Resource")
        self.use_custom_btn.clicked.connect(self.accept_custom)
        button_layout.addWidget(self.use_custom_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        layout.addLayout(button_layout)

        self.setLayout(layout)

        self.result_type = None
        self.result_index = None

    def accept_cpu(self):
        """Accept with CPU selection."""
        self.result_type = "cpu"
        self.result_index = self.cpu_combo.currentIndex()
        self.accept()

    def accept_gpu(self):
        """Accept with GPU selection."""
        self.result_type = "gpu"
        self.result_index = self.gpu_combo.currentIndex()
        self.accept()

    def accept_custom(self):
        """Accept with custom resource."""
        self.result_type = "custom"
        self.accept()

    def get_selected_resource(self):
        """
        Get the selected compute resource.

        Returns:
            ComputeResources: The selected compute resource
        """
        if self.result_type == "cpu":
            cpu_map = {
                0: amd_epyc_7763,
                1: amd_epyc_9654,
                2: intel_xeon_8480,
                3: intel_xeon_8462,
                4: amd_ryzen_7950x,
            }
            return cpu_map.get(self.result_index, amd_epyc_7763)()

        elif self.result_type == "gpu":
            gpu_map = {
                0: nvidia_a100_80gb,
                1: nvidia_h100_80gb,
                2: nvidia_rtx_4090,
                3: amd_mi300x,
            }
            return gpu_map.get(self.result_index, nvidia_rtx_4090)()

        elif self.result_type == "custom":
            # Create custom compute resource
            return create_compute_resources(
                cores=int(self.cores_edit.text()),
                core_frequency=float(self.freq_edit.text()),
                flops_per_cycle=int(self.flops_edit.text()),
                memory_channels=int(self.mem_channels_edit.text()),
                memory_width=int(self.mem_width_edit.text()),
                memory_frequency=float(self.mem_freq_edit.text()),
                network_speed=float(self.network_edit.text()),
                time_in_driver=5,
            )

        # Default
        return create_compute_resources()


class PipelineDesignerApp(QMainWindow):
    """
    Main application window for the daolite pipeline designer.

    Provides a graphical interface for designing AO pipelines with emphasis on
    network and multi-compute node configurations.
    """

    def __init__(self):
        super().__init__()

        self.setWindowTitle("daolite Pipeline Designer")
        self.resize(1200, 800)

        # Set up the scene and view
        self.scene = PipelineScene(self)
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(
            QPainter.Antialiasing
        )  # Fixed: Using QPainter.Antialiasing instead of self.view.Antialiasing
        self.view.setDragMode(self.view.RubberBandDrag)
        self.view.setViewportUpdateMode(self.view.FullViewportUpdate)
        self.setCentralWidget(self.view)

        # Track component count for naming
        self.component_counts = {
            ComponentType.CAMERA: 0,
            ComponentType.CENTROIDER: 0,
            ComponentType.RECONSTRUCTION: 0,
            ComponentType.CONTROL: 0,
            ComponentType.CALIBRATION: 0,
            ComponentType.NETWORK: 0,
        }

        self._create_toolbar()
        self._create_menu()

        # Connect context menu actions
        self.scene.selectionChanged.connect(self._update_selection)
        self.selected_component = None

    def _create_toolbar(self):
        """Create component toolbar."""
        self.toolbar = QToolBar("Components")
        self.addToolBar(Qt.LeftToolBarArea, self.toolbar)

        # Add buttons for each component type
        camera_btn = QPushButton("Camera")
        camera_btn.clicked.connect(lambda: self._add_component(ComponentType.CAMERA))
        camera_btn.setToolTip("Add a camera component to the pipeline")
        self.toolbar.addWidget(camera_btn)

        network_btn = QPushButton("Network")
        network_btn.clicked.connect(lambda: self._add_component(ComponentType.NETWORK))
        network_btn.setToolTip(
            "Add a network transfer component (emphasizes multi-node configurations)"
        )
        self.toolbar.addWidget(network_btn)

        calibration_btn = QPushButton("Calibration")
        calibration_btn.clicked.connect(
            lambda: self._add_component(ComponentType.CALIBRATION)
        )
        calibration_btn.setToolTip("Add a pixel calibration component")
        self.toolbar.addWidget(calibration_btn)

        centroider_btn = QPushButton("Centroider")
        centroider_btn.clicked.connect(
            lambda: self._add_component(ComponentType.CENTROIDER)
        )
        centroider_btn.setToolTip("Add a centroider component for wavefront sensing")
        self.toolbar.addWidget(centroider_btn)

        reconstruction_btn = QPushButton("Reconstruction")
        reconstruction_btn.clicked.connect(
            lambda: self._add_component(ComponentType.RECONSTRUCTION)
        )
        reconstruction_btn.setToolTip("Add a wavefront reconstruction component")
        self.toolbar.addWidget(reconstruction_btn)

        control_btn = QPushButton("Control")
        control_btn.clicked.connect(lambda: self._add_component(ComponentType.CONTROL))
        control_btn.setToolTip("Add a DM control component")
        self.toolbar.addWidget(control_btn)

        # Add separator
        self.toolbar.addSeparator()

        # === Add Generate Pipeline Button ===
        generate_btn = QPushButton("Generate Pipeline")
        generate_btn.setStyleSheet(
            "font-size: 16px; font-weight: bold; background: #4CAF50; color: white; padding: 8px 16px;"
        )
        generate_btn.clicked.connect(self._generate_code)
        generate_btn.setToolTip("Generate Python code for the current pipeline design")
        self.toolbar.addWidget(generate_btn)
        self.toolbar.addSeparator()

        # Add configuration buttons
        if_selected = QLabel("With selected component:")
        self.toolbar.addWidget(if_selected)

        compute_btn = QPushButton("Set Compute")
        compute_btn.clicked.connect(self._configure_compute)
        compute_btn.setToolTip("Configure compute resource for selected component")
        self.toolbar.addWidget(compute_btn)

        params_btn = QPushButton("Set Parameters")
        params_btn.clicked.connect(self._configure_params)
        params_btn.setToolTip("Configure parameters for selected component")
        self.toolbar.addWidget(params_btn)

    def _create_menu(self):
        """Create application menu."""
        menu_bar = self.menuBar()

        # File menu
        file_menu = menu_bar.addMenu("&File")

        new_action = QAction("&New Pipeline", self)
        new_action.triggered.connect(self._new_pipeline)
        file_menu.addAction(new_action)

        save_action = QAction("&Save Pipeline", self)
        save_action.triggered.connect(self._save_pipeline)
        file_menu.addAction(save_action)

        load_action = QAction("&Load Pipeline", self)
        load_action.triggered.connect(self._load_pipeline)
        file_menu.addAction(load_action)

        file_menu.addSeparator()

        generate_action = QAction("&Generate Code", self)
        generate_action.triggered.connect(self._generate_code)
        file_menu.addAction(generate_action)

        export_config_action = QAction("Export Config &YAML", self)
        export_config_action.triggered.connect(self._export_config)
        file_menu.addAction(export_config_action)

        file_menu.addSeparator()

        exit_action = QAction("E&xit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Edit menu
        edit_menu = menu_bar.addMenu("&Edit")

        rename_action = QAction("&Rename Selected", self)
        rename_action.triggered.connect(self._rename_selected)
        edit_menu.addAction(rename_action)

        delete_action = QAction("&Delete Selected", self)
        delete_action.triggered.connect(self._delete_selected)
        edit_menu.addAction(delete_action)

        # View menu
        view_menu = menu_bar.addMenu("&View")

        zoom_in_action = QAction("Zoom &In", self)
        zoom_in_action.triggered.connect(lambda: self.view.scale(1.2, 1.2))
        view_menu.addAction(zoom_in_action)

        zoom_out_action = QAction("Zoom &Out", self)
        zoom_out_action.triggered.connect(lambda: self.view.scale(0.8, 0.8))
        view_menu.addAction(zoom_out_action)

        reset_zoom_action = QAction("&Reset Zoom", self)
        reset_zoom_action.triggered.connect(lambda: self.view.resetTransform())
        view_menu.addAction(reset_zoom_action)

        # Help menu
        help_menu = menu_bar.addMenu("&Help")

        about_action = QAction("&About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _add_component(self, comp_type: ComponentType):
        """
        Add a new component to the scene.

        Args:
            comp_type: Type of component to add
        """
        # Generate a unique name
        self.component_counts[comp_type] += 1
        name = f"{comp_type.value}{self.component_counts[comp_type]}"

        # Create the component
        component = ComponentBlock(comp_type, name)

        # Position at center of view
        view_center = self.view.mapToScene(self.view.viewport().rect().center())
        component.setPos(view_center.x() - 90, view_center.y() - 40)

        # Add to scene
        self.scene.addItem(component)

        # For components needing a compute resource, prompt for it
        if comp_type != ComponentType.NETWORK:  # Network uses sources/targets compute
            component.compute = self._get_default_compute_for_type(comp_type)

    def _get_default_compute_for_type(self, comp_type: ComponentType):
        """Get a default compute resource based on component type."""
        if (
            comp_type == ComponentType.CENTROIDER
            or comp_type == ComponentType.RECONSTRUCTION
        ):
            # These typically benefit from GPU
            return nvidia_rtx_4090()
        else:
            # Others typically run on CPU
            return amd_epyc_7763()

    def _update_selection(self):
        """Update when selection changes."""
        selected_items = self.scene.selectedItems()

        if len(selected_items) == 1 and isinstance(selected_items[0], ComponentBlock):
            self.selected_component = selected_items[0]
        else:
            self.selected_component = None

    def _configure_compute(self):
        """Configure compute resource for selected component."""
        if not self.selected_component:
            QMessageBox.information(
                self, "No Selection", "Please select a component to configure."
            )
            return

        self._get_compute_resource(self.selected_component)

    def _configure_params(self):
        """Configure parameters for selected component."""
        if not self.selected_component:
            QMessageBox.information(
                self, "No Selection", "Please select a component to configure."
            )
            return

        # Show parameter dialog
        dlg = ComponentParametersDialog(
            self.selected_component.component_type, self.selected_component.params, self
        )

        if dlg.exec_():
            # Update component with new parameters
            self.selected_component.params = dlg.get_parameters()
            self.scene.update()

    def _rename_selected(self):
        """Rename the selected component."""
        if not self.selected_component:
            return

        name, ok = QInputDialog.getText(
            self,
            "Rename Component",
            "Enter new name:",
            text=self.selected_component.name,
        )

        if ok and name:
            self.selected_component.name = name
            self.scene.update()

    def _new_pipeline(self):
        """Create a new empty pipeline."""
        reply = QMessageBox.question(
            self,
            "New Pipeline",
            "Clear the current pipeline?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            self.scene.clear()
            self.scene.connections = []
            self.component_counts = {key: 0 for key in self.component_counts}

    def _delete_selected(self):
        """Delete selected items from the scene."""
        for item in self.scene.selectedItems():
            if isinstance(item, ComponentBlock):
                # Remove connections associated with this component
                for connection in list(self.scene.connections):
                    if connection.start_block == item or connection.end_block == item:
                        connection.disconnect()
                        self.scene.connections.remove(connection)
                        self.scene.removeItem(connection)

                self.scene.removeItem(item)

    def _get_compute_resource(self, component: ComponentBlock):
        """
        Show a dialog to select a compute resource.

        Args:
            component: The component to configure
        """
        dlg = ResourceSelectionDialog(self)
        if dlg.exec_():
            component.compute = dlg.get_selected_resource()
            self.scene.update()

    def _get_all_components(self) -> List[ComponentBlock]:
        """
        Get all component blocks in the scene.

        Returns:
            List of all component blocks
        """
        return [item for item in self.scene.items() if isinstance(item, ComponentBlock)]

    def _generate_code(self):
        """Generate and save pipeline code."""
        components = self._get_all_components()

        if not components:
            QMessageBox.warning(
                self, "Empty Pipeline", "No components to generate code from."
            )
            return

        # Generate code
        generator = CodeGenerator(components)

        # Get save location
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Pipeline Code", "", "Python Files (*.py);;All Files (*)"
        )

        if filename:
            generator.export_to_file(filename)
            QMessageBox.information(
                self, "Code Generation Complete", f"Pipeline code saved to {filename}"
            )

    def _save_pipeline(self):
        """Save pipeline design to a file (not the code, but the design)."""
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Pipeline Design", "", "JSON Files (*.json)"
        )
        if filename:
            import json

            data = {"components": [], "connections": []}
            for comp in self._get_all_components():
                comp_data = {
                    "type": comp.component_type.name,
                    "name": comp.name,
                    "pos": (comp.pos().x(), comp.pos().y()),
                    "params": comp.params,
                }
                if comp.compute is not None:
                    compute_dict = comp.compute.to_dict().copy()
                    if "name" in compute_dict:
                        del compute_dict["name"]
                    comp_data["compute"] = compute_dict
                data["components"].append(comp_data)
            for conn in self.scene.connections:
                data["connections"].append(
                    {
                        "start": conn.start_block.name,
                        "end": conn.end_block.name,
                    }
                )
            with open(filename, "w") as f:
                json.dump(data, f, indent=2)
            QMessageBox.information(
                self, "Pipeline Saved", f"Pipeline design saved to {filename}"
            )

    def _load_pipeline(self):
        """Load pipeline design from a file."""
        filename, _ = QFileDialog.getOpenFileName(
            self, "Load Pipeline Design", "", "JSON Files (*.json)"
        )
        if filename:
            import json

            with open(filename, "r") as f:
                data = json.load(f)
            self.scene.clear()
            self.scene.connections = []
            self.component_counts = {key: 0 for key in self.component_counts}
            name_to_block = {}
            # Recreate components
            for comp_data in data["components"]:
                comp_type = ComponentType[comp_data["type"]]
                block = ComponentBlock(comp_type, comp_data["name"])
                block.setPos(*comp_data["pos"])
                block.params = comp_data.get("params", {})
                # Restore compute resource if present
                compute_dict = comp_data.get("compute")
                if compute_dict is not None:
                    from daolite.compute.base_resources import ComputeResources
                    block.compute = ComputeResources.from_dict(compute_dict)
                self.scene.addItem(block)
                name_to_block[block.name] = block
                self.component_counts[comp_type] += 1
            # Recreate connections
            for conn_data in data["connections"]:
                start = name_to_block.get(conn_data["start"])
                end = name_to_block.get(conn_data["end"])
                if start and end:
                    out_port = start.output_ports[0] if start.output_ports else None
                    in_port = end.input_ports[0] if end.input_ports else None
                    if out_port and in_port:
                        conn = Connection(start, out_port)
                        conn.complete_connection(end, in_port)
                        self.scene.connections.append(conn)
                        self.scene.addItem(conn)
            self.scene.update()
            QMessageBox.information(
                self, "Pipeline Loaded", f"Pipeline design loaded from {filename}"
            )

    def _export_config(self):
        """Export configuration as YAML."""
        components = self._get_all_components()

        if not components:
            QMessageBox.warning(
                self, "Empty Pipeline", "No components to export configuration from."
            )
            return

        # Find camera and optics components
        camera_component = None
        actuator_count = 5000  # default

        for component in components:
            if component.component_type == ComponentType.CAMERA:
                camera_component = component
            elif component.component_type == ComponentType.CONTROL:
                if "n_actuators" in component.params:
                    actuator_count = component.params["n_actuators"]

        # Create configuration objects
        if camera_component and camera_component.params:
            # Extract parameters from camera component
            camera_params = camera_component.params
            camera_config = CameraConfig(
                n_pixels=camera_params.get("n_pixels", 1024 * 1024),
                n_subapertures=camera_params.get("n_subapertures", 80 * 80),
                pixels_per_subaperture=camera_params.get(
                    "pixels_per_subaperture", 16 * 16
                ),
                bit_depth=camera_params.get("bit_depth", 16),
                readout_time=camera_params.get("readout_time", 500.0),
            )
        else:
            # Default camera config
            camera_config = CameraConfig(
                n_pixels=1024 * 1024,
                n_subapertures=80 * 80,
                pixels_per_subaperture=16 * 16,
            )

        # Create optics config
        optics_config = OpticsConfig(n_actuators=actuator_count)

        # Create pipeline config
        use_square_diff = False
        use_sorting = False
        n_workers = 4

        for component in components:
            if component.component_type == ComponentType.CENTROIDER:
                if "square_diff" in component.params:
                    use_square_diff = component.params["square_diff"]
                if "sort" in component.params:
                    use_sorting = component.params["sort"]
                if "n_workers" in component.params:
                    n_workers = component.params["n_workers"]

        pipeline_config = PipelineConfig(
            use_square_diff=use_square_diff,
            use_sorting=use_sorting,
            n_workers=n_workers,
        )

        # Create system config
        system_config = SystemConfig(
            camera=camera_config, optics=optics_config, pipeline=pipeline_config
        )

        # Get save location
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Configuration YAML", "", "YAML Files (*.yaml);;All Files (*)"
        )

        if filename:
            system_config.to_yaml(filename)
            QMessageBox.information(
                self,
                "Configuration Export Complete",
                f"System configuration saved to {filename}",
            )

    def _show_about(self):
        """Show about dialog."""
        QMessageBox.about(
            self,
            "About daolite Pipeline Designer",
            """<b>daolite Pipeline Designer</b><br/><br/>
               A visual tool for designing AO pipelines with emphasis on 
               network and multi-compute node configurations.<br/><br/>
               Part of the daolite package for estimating latency in 
               Adaptive Optics Real-time Control Systems.""",
        )

    @staticmethod
    def run():
        """Run the pipeline designer application."""
        app = QApplication(sys.argv)
        window = PipelineDesignerApp()
        window.show()
        sys.exit(app.exec_())

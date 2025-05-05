from PyQt5.QtWidgets import QMainWindow, QComboBox, QUndoStack, QWidget, QMessageBox, QApplication, QFileDialog, QUndoView, QDockWidget
from PyQt5.QtGui import QFont, QPainter, QKeySequence
from PyQt5.QtCore import Qt
from .scene import PipelineScene
from .view import PipelineView
from .dialogs.misc_dialogs import ShortcutHelpDialog, StyledTextInputDialog
from .dialogs.resource_dialog import ResourceSelectionDialog
from .dialogs.parameter_dialog import ComponentParametersDialog
from .toolbar import create_toolbar
from .menu import create_menu
from .component_block import ComponentBlock
from .component_container import ComputeBox, GPUBox
from .code_generator import CodeGenerator
from .style_utils import set_app_style, get_saved_theme, save_theme
from .undo_stack import (
    AddComponentCommand, RemoveComponentCommand, MoveComponentCommand, 
    RenameComponentCommand, AddConnectionCommand, RemoveConnectionCommand, 
    ChangeParameterCommand, CompositeCommand
)
from daolite.common import ComponentType
from daolite.compute.hardware import nvidia_rtx_4090, amd_epyc_7763

class PipelineDesignerApp(QMainWindow):
    """
    Main application window for the daolite pipeline designer.
    Provides a graphical interface for designing AO pipelines with emphasis on
    network and multi-compute node configurations.
    """
    def __init__(self, json_path=None):
        print("[DEBUG] PipelineDesignerApp.__init__ called")
        self.theme = get_saved_theme()
        self.pipeline_title = "AO Pipeline"  # Ensure pipeline_title is always initialized
        self.component_counts = {
            ComponentType.CAMERA: 0,
            ComponentType.CALIBRATION: 0,
            ComponentType.CENTROIDER: 0,
            ComponentType.RECONSTRUCTION: 0,
            ComponentType.CONTROL: 0,
            ComponentType.NETWORK: 0,
        }
        super().__init__()
        self.setWindowTitle("Pipeline Designer")
        self.setGeometry(100, 100, 800, 600)
        self.scene = PipelineScene(self)  # Explicitly set parent to self
        print(f"[DEBUG] Scene created with parent: {self.scene.parent()}")
        # Use our custom PipelineView instead of QGraphicsView
        self.view = PipelineView(self.scene, self)
        self.setCentralWidget(self.view)
        self.undo_stack = QUndoStack(self)
        self.execution_method = QComboBox()
        self.execution_method.addItems(["Python", "JSON"])
        self.execution_method.setCurrentText("Python")
        self.init_ui()
        print(f"[DEBUG] json_path: {json_path}")
        if json_path:
            self.load_pipeline(json_path)
        
        # Initialize selected_component attribute
        self.selected_component = None

    def init_ui(self):
        print("[DEBUG] PipelineDesignerApp.init_ui called")
        # Set up undo/redo actions before creating the menu that references them
        self._setup_undo_redo_actions()
        self._create_toolbar()
        self.create_menu()
        self._create_undo_view()
        self.statusBar().showMessage("Ready")
        self.set_theme(get_saved_theme())
        
    def _create_undo_view(self):
        """Create a dock widget with an undo history view."""
        print("[DEBUG] PipelineDesignerApp._create_undo_view called")
        undo_view = QUndoView(self.undo_stack)
        dock = QDockWidget("History", self)
        dock.setWidget(undo_view)
        dock.setObjectName("UndoHistoryDock")
        self.addDockWidget(Qt.RightDockWidgetArea, dock)
        # Hide by default, can be shown from menu
        dock.setVisible(False)
        self.undo_history_dock = dock
        
    def _setup_undo_redo_actions(self):
        """Set up actions for undo/redo with keyboard shortcuts."""
        print("[DEBUG] PipelineDesignerApp._setup_undo_redo_actions called")
        # Create undo action with Ctrl+Z shortcut
        self.undo_action = self.undo_stack.createUndoAction(self, "Undo")
        self.undo_action.setShortcut(QKeySequence.Undo)
        
        # Create redo action with Ctrl+Shift+Z shortcut
        self.redo_action = self.undo_stack.createRedoAction(self, "Redo")
        self.redo_action.setShortcut(QKeySequence.Redo)
        
        # Add actions to the window so shortcuts work globally
        self.addAction(self.undo_action)
        self.addAction(self.redo_action)
        
        # Connect undo stack's clean state to application state if needed
        self.undo_stack.cleanChanged.connect(self._handle_clean_state_changed)

    def _create_toolbar(self):
        print("[DEBUG] PipelineDesignerApp._create_toolbar called")
        toolbar = create_toolbar(self)
        self.addToolBar(toolbar)

    def create_menu(self):
        print("[DEBUG] PipelineDesignerApp.create_menu called")
        create_menu(self)

    def set_theme(self, theme_name):
        print(f"[DEBUG] PipelineDesignerApp.set_theme called with theme_name={theme_name}")
        set_app_style(self, theme_name)  # Pass self as the widget parameter
        save_theme(theme_name)

    def show_shortcut_help(self):
        print("[DEBUG] PipelineDesignerApp.show_shortcut_help called")
        dialog = ShortcutHelpDialog(self)
        dialog.exec_()

    def add_component(self, component_type):
        print(f"[DEBUG] PipelineDesignerApp.add_component called with component_type={component_type}")
        if component_type == ComponentType.COMPUTE:
            component = ComputeBox()
        elif component_type == ComponentType.GPU:
            component = GPUBox()
        else:
            component = ComponentBlock()
        command = AddComponentCommand(self.scene, component)
        self.undo_stack.push(command)
        print(f"[DEBUG] Added component: {component}")

    def generate_code(self):
        print("[DEBUG] PipelineDesignerApp.generate_code called")
        generator = CodeGenerator(self.scene)
        code = generator.generate()
        dialog = StyledTextInputDialog("Generated Code", code, self)
        dialog.exec_()

    def select_resource(self):
        print("[DEBUG] PipelineDesignerApp.select_resource called")
        dialog = ResourceSelectionDialog(self)
        if dialog.exec_() == QMessageBox.Accepted:
            resource = dialog.get_selected_resource()
            print(f"[DEBUG] Selected resource: {resource}")

    def _add_compute_box(self):
        print("[DEBUG] PipelineDesignerApp._add_compute_box called")
        dlg = ResourceSelectionDialog(self)
        if dlg.exec_():
            cpu = dlg.cpu_name()
            compute_resource = dlg.get_selected_resource()
            cpu_name = getattr(compute_resource, "name", "Computer")
            compute_box = ComputeBox(cpu_name, compute=compute_resource, cpu_resource=cpu)
            view_center = self.view.mapToScene(self.view.viewport().rect().center())
            compute_box.setPos(view_center.x() - 160, view_center.y() - 110)
            command = AddComponentCommand(self.scene, compute_box)
            self.undo_stack.push(command)
            print(f"[DEBUG] Added compute_box: {compute_box}")
            if hasattr(compute_resource, 'attached_gpus'):
                for idx, gpu_resource in enumerate(compute_resource.attached_gpus):
                    gpu_name = getattr(gpu_resource, 'name', f"GPU{idx+1}")
                    gpu_box = GPUBox(gpu_name, gpu_resource=gpu_resource)
                    gpu_box.setPos(30, 60 + 40 * idx)
                    compute_box.add_child(gpu_box)
                    command = AddComponentCommand(self.scene, gpu_box)
                    self.undo_stack.push(command)
                    print(f"[DEBUG] Added gpu_box: {gpu_box}")

    def _add_gpu_box(self):
        print("[DEBUG] PipelineDesignerApp._add_gpu_box called")
        # Find selected ComputeBox
        selected = self.scene.selectedItems()
        compute_box = None
        for item in selected:
            if isinstance(item, ComputeBox):
                compute_box = item
                break
        if not compute_box:
            QMessageBox.information(self, "No Computer Selected", "Please select a computer box to add a GPU to.")
            return
        dlg = StyledTextInputDialog("Add GPU", "Enter GPU name:", "GPU", self)
        if not dlg.exec_():
            print("[DEBUG] Add GPU cancelled by user")
            return
        name = dlg.getText()
        # Prompt for GPU resource
        dlg = ResourceSelectionDialog(self)
        gpu_resource = None
        if dlg.exec_():
            gpu_resource = dlg.get_selected_resource()
        gpu_box = GPUBox(name, gpu_resource=gpu_resource)
        # Place GPUBox at a default offset inside the ComputeBox
        gpu_box.setPos(30, 60 + 40 * len(getattr(compute_box, 'child_items', [])))
        if hasattr(compute_box, 'add_child'):
            compute_box.add_child(gpu_box)
        command = AddComponentCommand(self.scene, gpu_box)
        self.undo_stack.push(command)
        print(f"[DEBUG] Added gpu_box: {gpu_box}")

    def load_pipeline(self, json_path):
        print(f"[DEBUG] PipelineDesignerApp.load_pipeline called with json_path={json_path}")
        try:
            with open(json_path, 'r') as file:
                data = file.read()
                self.scene.load_from_json(data)
                self.statusBar().showMessage(f"Loaded pipeline from {json_path}")
                print(f"[DEBUG] Loaded pipeline from {json_path}")
        except Exception as e:
            print(f"[DEBUG] Failed to load pipeline: {e}")
            QMessageBox.critical(self, "Error", f"Failed to load pipeline: {e}")

    @staticmethod
    def run(json_path=None):
        print(f"[DEBUG] PipelineDesignerApp.run called with json_path={json_path}")
        import sys
        from PyQt5.QtWidgets import QApplication
        app = QApplication(sys.argv)
        window = PipelineDesignerApp(json_path=json_path)
        window.show()
        sys.exit(app.exec_())

    def _new_pipeline(self):
        print("[DEBUG] PipelineDesignerApp._new_pipeline called")
        reply = QMessageBox.question(
            self,
            "New Pipeline",
            "Clear the current pipeline?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            print("[DEBUG] Clearing scene and resetting component counts")
            self.scene.clear()
            self.scene.connections = []
            self.component_counts = {key: 0 for key in self.component_counts}

    def _save_pipeline(self):
        print("[DEBUG] PipelineDesignerApp._save_pipeline called")
        dlg = StyledTextInputDialog("Set Pipeline Title", "Enter pipeline title:", self.pipeline_title, self)
        if not dlg.exec_():
            print("[DEBUG] Save pipeline cancelled by user")
            return
        self.pipeline_title = dlg.getText()
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Pipeline Design", "", "JSON Files (*.json)"
        )
        print(f"[DEBUG] Save pipeline filename: {filename}")
        if filename:
            from .file_io import save_pipeline_to_file
            success = save_pipeline_to_file(
                self.scene,
                self._get_all_components(),
                self.scene.connections,
                filename
            )
            print(f"[DEBUG] Save pipeline success: {success}")
            if success:
                QMessageBox.information(
                    self, "Pipeline Saved", f"Pipeline design saved to {filename}"
                )
            else:
                QMessageBox.warning(
                    self, "Save Error", f"Failed to save pipeline to {filename}"
                )

    def _load_pipeline(self):
        print("[DEBUG] PipelineDesignerApp._load_pipeline called")
        from .file_io import load_pipeline
        filename, _ = QFileDialog.getOpenFileName(
            self, "Load Pipeline Design", "", "JSON Files (*.json);;All Files (*)"
        )
        print(f"[DEBUG] Load pipeline filename: {filename}")
        if filename:
            success = load_pipeline(
                self.scene,
                filename,
                self.component_counts
            )
            print(f"[DEBUG] Load pipeline success: {success}")
            if success:
                QMessageBox.information(
                    self, "Pipeline Loaded", f"Pipeline design loaded from {filename}"
                )
            else:
                QMessageBox.critical(
                    self, "Load Error", f"Failed to load pipeline from {filename}"
                )

    def _rename_selected(self):
        print("[DEBUG] PipelineDesignerApp._rename_selected called")
        if not self.selected_component:
            print("[DEBUG] No selected component to rename")
            return
        dlg = StyledTextInputDialog("Rename Component", "Enter new name:", self.selected_component.name, self)
        if dlg.exec_():
            old_name = self.selected_component.name
            new_name = dlg.getText()
            print(f"[DEBUG] Renaming component {self.selected_component} from {old_name} to {new_name}")
            
            # Create and push the rename command
            command = RenameComponentCommand(self.selected_component, old_name, new_name)
            self.undo_stack.push(command)
            
            # Update the scene
            self.scene.update()

    def _delete_selected(self):
        print("[DEBUG] PipelineDesignerApp._delete_selected called")
        for item in self.scene.selectedItems():
            print(f"[DEBUG] Considering item for deletion: {item}")
            if isinstance(item, ComponentBlock):
                for connection in list(self.scene.connections):
                    if connection.start_block == item or connection.end_block == item:
                        print(f"[DEBUG] About to disconnect connection: {connection}")
                        connection.disconnect()
                        print(f"[DEBUG] Disconnected connection: {connection}")
                        self.scene.connections.remove(connection)
                        print(f"[DEBUG] Removed connection from scene.connections: {connection}")
                        self.scene.removeItem(connection)
                        print(f"[DEBUG] Removed connection from scene: {connection}")
                command = RemoveComponentCommand(self.scene, item)
                self.undo_stack.push(command)
                print(f"[DEBUG] Removed item: {item}")

    def _get_default_compute_for_type(self, comp_type: ComponentType):
        print(f"[DEBUG] PipelineDesignerApp._get_default_compute_for_type called with comp_type={comp_type}")
        if comp_type in (ComponentType.CENTROIDER, ComponentType.RECONSTRUCTION):
            return nvidia_rtx_4090()
        else:
            return amd_epyc_7763()

    def _update_selection(self):
        print("[DEBUG] PipelineDesignerApp._update_selection called")
        selected_items = self.scene.selectedItems()
        print(f"[DEBUG] Selected items: {selected_items}")
        if len(selected_items) == 1 and isinstance(selected_items[0], ComponentBlock):
            self.selected_component = selected_items[0]
            for item in self.scene.items():
                if hasattr(item, 'set_highlight'):
                    item.set_highlight(False)
                if hasattr(item, 'highlight_connection'):
                    item.highlight_connection(False)
            for conn in getattr(self.scene, 'connections', []):
                if conn.start_block == self.selected_component or conn.end_block == self.selected_component:
                    if hasattr(conn, 'highlight_connection'):
                        conn.highlight_connection(True)
        else:
            self.selected_component = None
            for item in self.scene.items():
                if hasattr(item, 'set_highlight'):
                    item.set_highlight(False)
                if hasattr(item, 'highlight_connection'):
                    item.highlight_connection(False)

    def _generate_code(self):
        print("[DEBUG] PipelineDesignerApp._generate_code called")
        components = self._get_all_components()
        print(f"[DEBUG] Components for code generation: {components}")
        if not components:
            QMessageBox.warning(
                self, "Empty Pipeline", "No components to generate code from."
            )
            return
        generator = CodeGenerator(components)
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Pipeline Code", "", "Python Files (*.py);;All Files (*)"
        )
        print(f"[DEBUG] Code generation filename: {filename}")
        if filename:
            generator.export_to_file(filename)
            QMessageBox.information(
                self, "Code Generation Complete", f"Pipeline code saved to {filename}"
            )

    def _set_theme(self, theme):
        print(f"[DEBUG] PipelineDesignerApp._set_theme called with theme={theme}")
        self.theme = theme
        save_theme(theme)
        set_app_style(self, theme)
        self.scene.set_theme(theme)
        self._create_toolbar()
        self.update()
        for widget in self.findChildren(QWidget):
            set_app_style(widget, theme)
        if hasattr(self, '_theme_actions'):
            for act in self._theme_actions:
                act.setChecked(act.text().lower().startswith(theme))

    def _show_about(self):
        print("[DEBUG] PipelineDesignerApp._show_about called")
        from .dialogs import AboutDialog
        dlg = AboutDialog(self)
        dlg.exec_()

    def _show_shortcuts(self):
        print("[DEBUG] PipelineDesignerApp._show_shortcuts called")
        dlg = ShortcutHelpDialog(self)
        dlg.exec_()

    def _add_component(self, comp_type: ComponentType):
        print(f"[DEBUG] PipelineDesignerApp._add_component called with comp_type={comp_type}")
        self.component_counts[comp_type] += 1
        name = f"{comp_type.value}{self.component_counts[comp_type]}"
        component = ComponentBlock(comp_type, name)
        view_center = self.view.mapToScene(self.view.viewport().rect().center())
        component.setPos(view_center.x() - 90, view_center.y() - 40)
        command = AddComponentCommand(self.scene, component)
        self.undo_stack.push(command)
        print(f"[DEBUG] Added component: {component}")
        if comp_type != ComponentType.NETWORK:
            component.compute = self._get_default_compute_for_type(comp_type)

    def _configure_compute(self):
        print("[DEBUG] PipelineDesignerApp._configure_compute called")
        if not self.selected_component:
            print("[DEBUG] No selected component to configure compute")
            QMessageBox.information(
                self, "No Selection", "Please select a component to configure."
            )
            return
        self._get_compute_resource(self.selected_component)

    def _configure_params(self):
        print("[DEBUG] PipelineDesignerApp._configure_params called")
        if not self.selected_component:
            print("[DEBUG] No selected component to configure params")
            QMessageBox.information(
                self, "No Selection", "Please select a component to configure."
            )
            return
        
        # Store the original parameters
        old_params = self.selected_component.params.copy() if self.selected_component.params else {}
        
        # Show dialog
        dlg = ComponentParametersDialog(
            self.selected_component.component_type, self.selected_component.params, self
        )
        if dlg.exec_():
            # Get new parameters
            new_params = dlg.get_parameters()
            
            # Create and push command
            command = ChangeParameterCommand(self.selected_component, old_params, new_params)
            self.undo_stack.push(command)
            
            self.scene.update()
            print(f"[DEBUG] Updated params for component: {self.selected_component}")

    def _quick_save_pipeline(self):
        print("[DEBUG] PipelineDesignerApp._quick_save_pipeline called")
        import os
        default_path = os.path.expanduser("~/daolite_quicksave.json")
        from .file_io import save_pipeline_to_file
        save_pipeline_to_file(
            self.scene,
            self._get_all_components(),
            self.scene.connections,
            default_path
        )
        self.statusBar().showMessage(f"Pipeline quick-saved to {default_path}", 3000)
        print(f"[DEBUG] Pipeline quick-saved to {default_path}")

    def _get_compute_resource(self, item):
        print(f"[DEBUG] PipelineDesignerApp._get_compute_resource called for item: {item}")
        existing_resource = item.compute if hasattr(item, 'compute') else None
        dlg = ResourceSelectionDialog(self, existing_resource=existing_resource)
        if dlg.exec_():
            new_resource = dlg.get_selected_resource()
            print(f"[DEBUG] New resource selected: {new_resource}")
            if isinstance(item, ComputeBox):
                item.compute = new_resource
                for child in list(item.childItems()):
                    if isinstance(child, GPUBox):
                        item.childItems().remove(child)
                        self.scene.removeItem(child)
                        print(f"[DEBUG] Removed GPUBox child: {child}")
                if hasattr(new_resource, 'attached_gpus') and new_resource.attached_gpus:
                    for idx, gpu_resource in enumerate(new_resource.attached_gpus):
                        gpu_name = getattr(gpu_resource, 'name', f"GPU{idx+1}")
                        gpu_box = GPUBox(gpu_name, gpu_resource=gpu_resource)
                        gpu_box.setPos(30, 60 + 40 * idx)
                        item.add_child(gpu_box)
                        command = AddComponentCommand(self.scene, gpu_box)
                        self.undo_stack.push(command)
                        print(f"[DEBUG] Added GPUBox: {gpu_box}")
                for child in item.childItems():
                    if isinstance(child, ComponentBlock):
                        child.update()
            elif isinstance(item, GPUBox):
                item.compute = new_resource
                for child in item.childItems():
                    if isinstance(child, ComponentBlock):
                        child.update()
            else:
                parent = item.parentItem()
                if parent and isinstance(parent, (ComputeBox, GPUBox)):
                    parent.compute = new_resource
                    item.update()
                else:
                    print("[DEBUG] No container for compute resource")
                    QMessageBox.warning(
                        self, 
                        "No Container", 
                        "This component is not in a compute container. Please add it to a CPU or GPU container first."
                    )
            self.scene.update()
            print(f"[DEBUG] Finished updating compute resource for item: {item}")

    def _get_all_components(self):
        components = [item for item in self.scene.items() if isinstance(item, ComponentBlock)]
        print(f"[DEBUG] _get_all_components found: {components}")
        return components

    def _export_config(self):
        print("[DEBUG] PipelineDesignerApp._export_config called")
        components = self._get_all_components()
        if not components:
            print("[DEBUG] No components to export config from")
            QMessageBox.warning(
                self, "Empty Pipeline", "No components to export configuration from."
            )
            return
        camera_component = None
        actuator_count = 5000
        for component in components:
            if component.component_type == ComponentType.CAMERA:
                camera_component = component
            elif component.component_type == ComponentType.CONTROL:
                if "n_actuators" in component.params:
                    actuator_count = component.params["n_actuators"]
        if camera_component and camera_component.params:
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
            camera_config = CameraConfig(
                n_pixels=1024 * 1024,
                n_subapertures=80 * 80,
                pixels_per_subaperture=16 * 16,
            )
        optics_config = OpticsConfig(n_actuators=actuator_count)
        use_square_diff = False
        use_sorting = False
        n_workers = 4
        filename, _ = QFileDialog.getOpenFileName(
            self, "Load Pipeline Design", "", "JSON Files (*.json);;All Files (*)"
        )
        print(f"[DEBUG] Export config filename: {filename}")
        if not filename:
            print("[DEBUG] Export config cancelled by user")
            return
        from .file_io import load_pipeline
        success = load_pipeline(
            self.scene,
            filename,
            self.component_counts
        )
        print(f"[DEBUG] Export config load_pipeline success: {success}")
        if success:
            QMessageBox.information(
                self, "Pipeline Loaded", f"Pipeline design loaded from {filename}"
            )
        else:
            QMessageBox.critical(
                self, "Load Error", f"Failed to load pipeline from {filename}"
            )

    def _run_pipeline(self):
        print("[DEBUG] PipelineDesignerApp._run_pipeline called")
        from .pipeline_executor import run_pipeline
        components = self._get_all_components()
        execution_method = self.execution_method.currentText()
        print(f"[DEBUG] Running pipeline with execution_method={execution_method}")
        run_pipeline(self, components, self.scene, execution_method)

    def _set_pipeline_title(self):
        print("[DEBUG] PipelineDesignerApp._set_pipeline_title called")
        dlg = StyledTextInputDialog("Set Pipeline Title", "Enter pipeline title:", getattr(self, 'pipeline_title', "AO Pipeline"), self)
        if dlg.exec_():
            self.pipeline_title = dlg.getText()
            self.statusBar().showMessage(f"Pipeline title set to: {self.pipeline_title}", 3000)

    def _handle_clean_state_changed(self, is_clean):
        """Handle changes in the undo stack's clean state."""
        print(f"[DEBUG] PipelineDesignerApp._handle_clean_state_changed called with is_clean={is_clean}")
        # Update window title to indicate if there are unsaved changes
        title = "Pipeline Designer"
        if not is_clean:
            title += " *"
        self.setWindowTitle(title)
        
    def toggle_history_view(self):
        """Toggle visibility of the undo history dock."""
        print("[DEBUG] PipelineDesignerApp.toggle_history_view called")
        if hasattr(self, 'undo_history_dock'):
            self.undo_history_dock.setVisible(not self.undo_history_dock.isVisible())

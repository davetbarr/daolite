"""
ComponentBlock class for the daolite pipeline designer.
"""

from typing import Dict, List, Optional, Any
from PyQt5.QtCore import Qt, QRectF, QPointF
from PyQt5.QtGui import QPen, QBrush, QColor, QPainter, QFont, QLinearGradient
from PyQt5.QtWidgets import QGraphicsItem, QGraphicsSceneContextMenuEvent, QMenu, QAction, QStyle
from daolite.common import ComponentType
from daolite.compute import ComputeResources
from .dialogs.misc_dialogs import StyledTextInputDialog
from .port import Port, PortType

class ComponentBlock(QGraphicsItem):
    """
    A visual component block in the pipeline designer.
    Represents one pipeline component (camera, centroider, etc.) with
    input/output ports and configurable properties.
    """
    def __init__(self, component_type: ComponentType, name: str = None, instance_number: int = None):
        super().__init__()
        self.component_type = component_type
        # Assign a default name if not provided
        if name is None:
            base = component_type.name.capitalize().replace('_', ' ')
            if instance_number is not None:
                self.name = f"{base}({instance_number})"
            else:
                self.name = base
        else:
            self.name = name
        self.params: Dict[str, Any] = {}
        self.size = QRectF(0, 0, 190, 90)
        # Create ports
        self.input_ports: List[Port] = []
        self.output_ports: List[Port] = []
        self._initialize_ports()
        # Set flags
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemIsSelectable)
        self.setFlag(QGraphicsItem.ItemSendsScenePositionChanges)
        self.setAcceptedMouseButtons(Qt.LeftButton)

    def set_theme(self, theme):
        self.theme = theme
        self.update()

    def get_compute_resource(self) -> Optional[ComputeResources]:
        parent = self.parentItem()
        if parent and hasattr(parent, "compute") and parent.compute is not None:
            return parent.compute
        return None

    def _initialize_ports(self):
        if self.component_type == ComponentType.CAMERA:
            output = Port(PortType.OUTPUT, QPointF(190, 40), "data")
            output.parent = self
            self.output_ports.append(output)
        elif self.component_type == ComponentType.NETWORK:
            input_port = Port(PortType.INPUT, QPointF(0, 40), "data in")
            output_port = Port(PortType.OUTPUT, QPointF(190, 40), "data out")
            input_port.parent = self
            output_port.parent = self
            self.input_ports.append(input_port)
            self.output_ports.append(output_port)
        elif self.component_type == ComponentType.CONTROL:
            input_port = Port(PortType.INPUT, QPointF(0, 40), "commands")
            input_port.parent = self
            self.input_ports.append(input_port)
        else:
            input_port = Port(PortType.INPUT, QPointF(0, 40), "in")
            output_port = Port(PortType.OUTPUT, QPointF(190, 40), "out")
            input_port.parent = self
            output_port.parent = self
            self.input_ports.append(input_port)
            self.output_ports.append(output_port)

    def boundingRect(self) -> QRectF:
        return self.size

    def paint(self, painter: QPainter, option, widget):
        theme = getattr(self, 'theme', getattr(self.scene(), 'theme', 'light'))
        is_dark = theme == 'dark'
        shadow_color = QColor(0, 0, 0, 100 if is_dark else 60)
        shadow_rect = self.size.adjusted(3, 3, 3, 3)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(shadow_color))
        painter.drawRoundedRect(shadow_rect, 16, 16)
        grad = QLinearGradient(self.size.topLeft(), self.size.bottomRight())
        base_color = self._get_color_for_component()
        if is_dark:
            grad.setColorAt(0, base_color.darker(180))
            grad.setColorAt(1, base_color.darker(220))
        else:
            grad.setColorAt(0, base_color.lighter(110))
            grad.setColorAt(1, base_color.darker(105))
        painter.setBrush(QBrush(grad))
        pen = QPen(QColor('#8ecfff') if is_dark else Qt.black, 2)
        if self.isSelected():
            pen.setColor(QColor(0, 180, 255) if is_dark else QColor(0, 120, 255))
            pen.setWidth(4)
        elif option.state & QStyle.State_MouseOver:
            pen.setColor(QColor(80, 180, 255))
            pen.setWidth(3)
        painter.setPen(pen)
        painter.drawRoundedRect(self.size, 14, 14)
        title_rect = QRectF(0, 0, self.size.width(), 28)
        title_grad = QLinearGradient(title_rect.topLeft(), title_rect.bottomLeft())
        if is_dark:
            title_grad.setColorAt(0, QColor(40, 60, 80))
            title_grad.setColorAt(1, QColor(30, 40, 60))
        else:
            title_grad.setColorAt(0, self._get_title_color().lighter(120))
            title_grad.setColorAt(1, self._get_title_color().darker(110))
        painter.setBrush(QBrush(title_grad))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(title_rect, 12, 12)
        painter.setPen(Qt.black if not is_dark else QColor('#e0e6ef'))
        font = QFont("Segoe UI", 11, QFont.Bold)
        painter.setFont(font)
        painter.drawText(title_rect, Qt.AlignCenter, self.name)
        type_rect = QRectF(0, 30, self.size.width(), 18)
        font = QFont("Segoe UI", 9, QFont.Normal)
        painter.setFont(font)
        painter.setPen(QColor(60, 60, 120) if not is_dark else QColor('#b3e1ff'))
        painter.drawText(type_rect, Qt.AlignCenter, self.component_type.name.title())
        desc = self._get_description()
        desc_rect = QRectF(0, 48, self.size.width(), 16)
        font = QFont("Segoe UI", 8, QFont.StyleItalic)
        painter.setFont(font)
        painter.setPen(QColor(90, 90, 90) if not is_dark else QColor('#e0e6ef'))
        painter.drawText(desc_rect, Qt.AlignCenter, desc)
        compute = self.get_compute_resource()
        if compute:
            compute_name = getattr(compute, "name", "")
            compute_rect = QRectF(5, 68, self.size.width() - 10, 16)
            resource_type = ""
            parent = self.parentItem()
            if parent:
                if hasattr(parent, 'gpu_resource'):
                    resource_type = "GPU: "
                elif hasattr(parent, 'cpu_resource'):
                    resource_type = "CPU: "
            if resource_type:
                font = QFont("Segoe UI", 7)
                painter.setFont(font)
                painter.setPen(QColor(60, 120, 60) if not is_dark else QColor('#b3e1ff'))
                painter.drawText(compute_rect, Qt.AlignCenter, f"{resource_type}{compute_name}")
        self._draw_ports(painter)

    def _draw_ports(self, painter: QPainter):
        theme = getattr(self, 'theme', getattr(self.scene(), 'theme', 'light'))
        is_dark = theme == 'dark'
        for port in self.input_ports:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(0, 0, 0, 100 if is_dark else 60))
            shadow_rect = QRectF(port.position.x() - 8, port.position.y() - 7, 18, 18)
            painter.drawEllipse(shadow_rect)
            painter.setPen(QPen(QColor(30, 120, 220), 2))
            painter.setBrush(QBrush(QColor(80, 180, 255)))
            port_rect = QRectF(port.position.x() - 9, port.position.y() - 9, 18, 18)
            painter.drawEllipse(port_rect)
            painter.setFont(QFont("Segoe UI", 7))
            painter.setPen(QColor(30, 120, 220))
            painter.drawText(int(port.position.x()) + 7, int(port.position.y()) + 2, port.label)
            if hasattr(port, 'label'):
                self.setToolTip(f"{self.name} - {port.label}")
            if port.connected_to:
                connected_comp = port.connected_to[0][0]
                painter.setFont(QFont("Segoe UI", 7, QFont.StyleItalic))
                painter.setPen(QColor(80, 80, 180))
                painter.drawText(int(port.position.x()) + 7, int(port.position.y()) + 12, f"← {connected_comp.name}")
        for port in self.output_ports:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(0, 0, 0, 100 if is_dark else 60))
            shadow_rect = QRectF(port.position.x() - 8, port.position.y() - 7, 18, 18)
            painter.drawEllipse(shadow_rect)
            painter.setPen(QPen(QColor(40, 180, 60), 2))
            painter.setBrush(QBrush(QColor(100, 220, 100)))
            port_rect = QRectF(port.position.x() - 9, port.position.y() - 9, 18, 18)
            painter.drawEllipse(port_rect)
            painter.setFont(QFont("Segoe UI", 7))
            painter.setPen(QColor(40, 180, 60))
            painter.drawText(int(port.position.x()) - 55, int(port.position.y()) + 2, port.label)
            if hasattr(port, 'label'):
                self.setToolTip(f"{self.name} - {port.label}")
            if port.connected_to:
                connected_comps = [comp[0].name for comp in port.connected_to]
                if connected_comps:
                    painter.setFont(QFont("Segoe UI", 7, QFont.StyleItalic))
                    painter.setPen(QColor(80, 150, 80))
                    if len(connected_comps) > 1:
                        display_text = f"{connected_comps[0]} +{len(connected_comps)-1} →"
                    else:
                        display_text = f"{connected_comps[0]} →"
                    painter.drawText(int(port.position.x()) - 55, int(port.position.y()) + 12, display_text)

    def _get_color_for_component(self) -> QColor:
        colors = {
            ComponentType.CAMERA: QColor(240, 240, 255),
            ComponentType.CENTROIDER: QColor(240, 255, 240),
            ComponentType.RECONSTRUCTION: QColor(255, 240, 240),
            ComponentType.CONTROL: QColor(255, 255, 240),
            ComponentType.NETWORK: QColor(255, 240, 255),
            ComponentType.CALIBRATION: QColor(240, 255, 255),
        }
        return colors.get(self.component_type, QColor(245, 245, 245))

    def _get_title_color(self) -> QColor:
        base_color = self._get_color_for_component()
        return base_color.darker(120)

    def _get_description(self) -> str:
        descs = {
            ComponentType.CAMERA: "Image sensor input",
            ComponentType.CENTROIDER: "Wavefront slope extraction",
            ComponentType.RECONSTRUCTION: "Wavefront phase estimation",
            ComponentType.CONTROL: "DM/actuator control",
            ComponentType.NETWORK: "PCIe/network transfer",
            ComponentType.CALIBRATION: "Pixel/offset calibration",
        }
        return descs.get(self.component_type, "AO pipeline component")

    def _update_all_transfer_indicators(self):
        if not self.scene():
            return
        from .connection import Connection
        for item in self.scene().items():
            if isinstance(item, Connection):
                if item.start_block == self or item.end_block == self:
                    item.update_transfer_indicators()

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange and self.scene():
            for port in self.input_ports + self.output_ports:
                for comp, port2 in port.connected_to:
                    for item in self.scene().items():
                        from .connection import Connection
                        if isinstance(item, Connection):
                            if ((item.start_block == self or item.end_block == self) and
                                (item.start_port == port or item.end_port == port)):
                                item.update_path()
            self.scene().update()
            self._update_all_transfer_indicators()
        elif change == QGraphicsItem.ItemScenePositionHasChanged and self.scene():
            for port in self.input_ports + self.output_ports:
                for comp, port2 in port.connected_to:
                    for item in self.scene().items():
                        from .connection import Connection
                        if isinstance(item, Connection):
                            if ((item.start_block == self or item.end_block == self) and
                                (item.start_port == port or item.end_port == port)):
                                item.update_path()
            self.scene().update()
            self._update_all_transfer_indicators()
        elif change == QGraphicsItem.ItemParentChange and self.scene():
            from .connection import Connection
            self.scene().update()
            self._update_all_transfer_indicators()
        elif change == QGraphicsItem.ItemParentHasChanged and self.scene():
            for port in self.input_ports + self.output_ports:
                for comp, port2 in port.connected_to:
                    for item in self.scene().items():
                        from .connection import Connection
                        if isinstance(item, Connection):
                            if ((item.start_block == self or item.end_block == self) and
                                (item.start_port == port or item.end_port == port)):
                                item.update_path()
            self.scene().update()
            self._update_all_transfer_indicators()
        elif change == QGraphicsItem.ItemSelectedChange and self.scene():
            for item in self.scene().items():
                if hasattr(item, 'set_highlight'):
                    item.set_highlight(False)
        return super().itemChange(change, value)

    def contextMenuEvent(self, event: QGraphicsSceneContextMenuEvent):
        menu = QMenu()
        rename_action = QAction("Rename", menu)
        rename_action.triggered.connect(self._on_rename)
        menu.addAction(rename_action)
        if type(self).__name__ in ("ComputeBox", "GPUBox"):
            configure_action = QAction("Configure Compute Resource", menu)
            configure_action.triggered.connect(self._on_configure)
            menu.addAction(configure_action)
        params_action = QAction("Configure Parameters", menu)
        params_action.triggered.connect(self._on_params)
        menu.addAction(params_action)
        delete_action = QAction("Delete", menu)
        delete_action.triggered.connect(self._on_delete)
        menu.addAction(delete_action)
        menu.exec_(event.screenPos())

    def _on_rename(self):
        print("[DEBUG] _on_rename called")
        dlg = StyledTextInputDialog("Rename Component", "Enter new name:", self.name, None)
        print(f"[DEBUG] Created StyledTextInputDialog: {dlg}")
        if dlg.exec_():
            name = dlg.getText()
            self.name = name
            if self.scene():
                self.scene().update()

    def _on_configure(self):
        print("[DEBUG] _on_configure called")
        if self.scene():
            print(f"[DEBUG] Scene: {self.scene()}")
            app = self.scene().parent()
            print(f"[DEBUG] App (scene parent): {app}")
            if hasattr(app, "_get_compute_resource"):
                print(f"[DEBUG] App has _get_compute_resource method")
                app._get_compute_resource(self)
            else:
                print(f"[DEBUG] App does NOT have _get_compute_resource method")
                print(f"[DEBUG] Available methods: {[m for m in dir(app) if not m.startswith('__')]}")

    def _on_params(self):
        print("[DEBUG] _on_params called")
        if self.scene():
            print(f"[DEBUG] Scene: {self.scene()}")
            app = self.scene().parent()
            print(f"[DEBUG] App (scene parent): {app}")
            prev_selected = None
            if hasattr(app, "selected_component"):
                print(f"[DEBUG] App has selected_component: {app.selected_component}")
                prev_selected = app.selected_component
                app.selected_component = self
            else:
                print(f"[DEBUG] App does NOT have selected_component attribute")
            if hasattr(app, "_configure_params"):
                print(f"[DEBUG] App has _configure_params method")
                app._configure_params()
            else:
                print(f"[DEBUG] App does NOT have _configure_params method")
                print(f"[DEBUG] Available methods: {[m for m in dir(app) if not m.startswith('__')]}")
            if hasattr(app, "selected_component"):
                app.selected_component = prev_selected

    def _on_delete(self):
        if self.scene():
            for connection in list(self.scene().connections):
                if connection.start_block == self or connection.end_block == self:
                    connection.disconnect()
                    self.scene().connections.remove(connection)
            self.scene().removeItem(self)

    def find_port_at_point(self, point: QPointF) -> Optional[Port]:
        for port in self.input_ports:
            if port.contains_point(point):
                return port
        for port in self.output_ports:
            if port.contains_point(point):
                return port
        return None

    def get_dependencies(self) -> List[str]:
        dependencies = []
        for port in self.input_ports:
            for comp, _ in port.connected_to:
                dependencies.append(comp.name)
        return dependencies

    def mouseDoubleClickEvent(self, event):
        print(f"[DEBUG] Mouse double-click at position: {event.pos()}")
        # Check if the click is in the title area (top ~28 pixels of the component)
        if event.pos().y() < 28:
            print("[DEBUG] Double-click in title area - showing rename dialog")
            self._on_rename()
            event.accept()
            return
        
        # For clicks elsewhere on the component, show parameter configuration
        if self.scene() and self.scene().parent():
            app = self.scene().parent()
            prev_selected = None
            if hasattr(app, "selected_component"):
                prev_selected = app.selected_component
                app.selected_component = self
            if hasattr(app, "_configure_params"):
                app._configure_params()
            if hasattr(app, "selected_component"):
                app.selected_component = prev_selected
            event.accept()
            return
        super().mouseDoubleClickEvent(event)
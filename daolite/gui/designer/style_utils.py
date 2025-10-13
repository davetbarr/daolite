import os

from PyQt5.QtCore import QSettings
from PyQt5.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)


def get_style_path(theme=None):
    here = os.path.dirname(os.path.abspath(__file__))
    if theme == "dark":
        return os.path.join(here, "style_dark.qss")
    elif theme == "light":
        return os.path.join(here, "style_light.qss")
    else:
        return os.path.join(here, "style_light.qss")  # fallback


def detect_system_theme():
    # Simple macOS/dark mode detection, can be expanded for other OS
    import platform

    if platform.system() == "Darwin":
        try:
            from subprocess import check_output

            mode = (
                check_output(["defaults", "read", "-g", "AppleInterfaceStyle"])
                .decode()
                .strip()
            )
            if mode.lower() == "dark":
                return "dark"
        except Exception:
            pass
    # Default to light
    return "light"


def set_app_style(widget: QWidget, theme=None):
    """
    Apply the shared QSS style to a widget/dialog, with theme support.

    Args:
        widget: The widget or dialog to style
        theme: 'light', 'dark', or 'system' (default: None, uses saved theme or system theme)
    """
    # If no theme specified, use the saved theme preference
    if theme is None:
        theme = get_saved_theme()

    # If theme is 'system' or invalid, detect from system
    if theme == "system":
        theme = detect_system_theme()

    style_path = get_style_path(theme)
    if os.path.exists(style_path):
        with open(style_path, "r") as f:
            style_content = f.read()
            widget.setStyleSheet(style_content)

            # Also apply the style to all existing child widgets
            # This ensures even dynamically created widgets get proper styling
            for child in widget.findChildren(QWidget):
                child.setStyleSheet(style_content)


class StyledTextInputDialog(QDialog):
    def __init__(self, title, label, default_text="", parent=None, theme=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(label))
        self.line_edit = QLineEdit(default_text)
        layout.addWidget(self.line_edit)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        # Apply styling after all widgets are created
        set_app_style(self, theme)

    def getText(self):
        return self.line_edit.text()


def get_saved_theme():
    settings = QSettings("daolite", "PipelineDesigner")
    return settings.value("theme", "system")


def save_theme(theme):
    settings = QSettings("daolite", "PipelineDesigner")
    settings.setValue("theme", theme)

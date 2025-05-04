import os
from PyQt5.QtWidgets import QWidget, QDialog, QVBoxLayout, QLineEdit, QLabel, QDialogButtonBox
from PyQt5.QtCore import QSettings

def get_style_path(theme=None):
    here = os.path.dirname(os.path.abspath(__file__))
    if theme == 'dark':
        return os.path.join(here, "style_dark.qss")
    elif theme == 'light':
        return os.path.join(here, "style_light.qss")
    else:
        return os.path.join(here, "style_light.qss")  # fallback

def detect_system_theme():
    # Simple macOS/dark mode detection, can be expanded for other OS
    import platform
    if platform.system() == 'Darwin':
        try:
            from subprocess import check_output
            mode = check_output([
                'defaults', 'read', '-g', 'AppleInterfaceStyle'
            ]).decode().strip()
            if mode.lower() == 'dark':
                return 'dark'
        except Exception:
            pass
    # Default to light
    return 'light'

def set_app_style(widget: QWidget, theme=None):
    """Apply the shared QSS style to a widget/dialog, with theme support."""
    if theme is None or theme == 'system':
        theme = detect_system_theme()
    style_path = get_style_path(theme)
    if os.path.exists(style_path):
        with open(style_path, "r") as f:
            widget.setStyleSheet(f.read())

class StyledTextInputDialog(QDialog):
    def __init__(self, title, label, default_text="", parent=None, theme=None):
        super().__init__(parent)
        set_app_style(self, theme)
        self.setWindowTitle(title)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(label))
        self.line_edit = QLineEdit(default_text)
        layout.addWidget(self.line_edit)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    def getText(self):
        return self.line_edit.text()

def get_saved_theme():
    settings = QSettings('daolite', 'PipelineDesigner')
    return settings.value('theme', 'system')

def save_theme(theme):
    settings = QSettings('daolite', 'PipelineDesigner')
    settings.setValue('theme', theme)

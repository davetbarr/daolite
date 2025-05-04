import os
from PyQt5.QtWidgets import QWidget, QDialog, QVBoxLayout, QLineEdit, QLabel, QDialogButtonBox

def get_style_path():
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(here, "style.qss")

def set_app_style(widget: QWidget):
    """Apply the shared QSS style to a widget/dialog."""
    style_path = get_style_path()
    if os.path.exists(style_path):
        with open(style_path, "r") as f:
            widget.setStyleSheet(f.read())

class StyledTextInputDialog(QDialog):
    def __init__(self, title, label, default_text="", parent=None):
        super().__init__(parent)
        set_app_style(self)
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

import os
from PyQt5.QtWidgets import QWidget

def get_style_path():
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(here, "style.qss")

def set_app_style(widget: QWidget):
    """Apply the shared QSS style to a widget/dialog."""
    style_path = get_style_path()
    if os.path.exists(style_path):
        with open(style_path, "r") as f:
            widget.setStyleSheet(f.read())

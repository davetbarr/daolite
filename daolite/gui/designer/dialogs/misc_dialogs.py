from PyQt5.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from ..style_utils import set_app_style


class ShortcutHelpDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Keyboard Shortcuts")
        layout = QVBoxLayout(self)
        text = QTextEdit()
        text.setReadOnly(True)
        text.setPlainText(
            """
            Keyboard Shortcuts:
            ------------------
            ⌘N / Ctrl+N: New Pipeline
            ⌘O / Ctrl+O: Open Pipeline
            ⌘S / Ctrl+S: Save Pipeline
            ⌘Z / Ctrl+Z: Undo
            ⌘Y / Ctrl+Y: Redo
            Delete/Backspace: Delete Selected
            ⌘Q / Ctrl+Q: Quit
            ⌘G / Ctrl+G: Generate Code
            ⌘R / Ctrl+R: Run Pipeline
            ⌘E / Ctrl+E: Export Config
            ⌘H / Ctrl+H: Show Shortcuts
            ⌘+: Zoom In
            ⌘-: Zoom Out
            ⌘0: Reset Zoom
            """
        )
        layout.addWidget(text)
        btn = QPushButton("Close")
        btn.clicked.connect(self.accept)
        layout.addWidget(btn)

        # Apply styling after all UI elements are created
        set_app_style(self)


class StyledTextInputDialog(QDialog):
    def __init__(self, title, label, default_text="", parent=None):
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

        # Apply styling after all UI elements are created
        set_app_style(self)

    def getText(self):
        return self.line_edit.text()

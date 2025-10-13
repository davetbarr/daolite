import logging
import sys
import tempfile

from daolite.gui.designer.main_window import PipelineDesignerApp

# Set up logging with proper configuration
logfile = tempfile.NamedTemporaryFile(prefix="daolite_", suffix=".log", delete=False)
logging.basicConfig(filename=logfile.name, level=logging.INFO, filemode="w")
print(f"Logging to {logfile.name}")


def main():
    from PyQt5.QtWidgets import QApplication, QMessageBox

    # Show experimental warning
    print("\n" + "=" * 70)
    print("WARNING: Pipeline Designer GUI is in EXPERIMENTAL phase")
    print("=" * 70)
    print("This GUI tool is under active development and may:")
    print("  - Crash unexpectedly")
    print("  - Have incomplete features")
    print("  - Change significantly in future releases")
    print("\nFor production use, please use the Python API or JSON runner.")
    print("=" * 70 + "\n")

    # Get json_path from command line arguments if provided
    json_path = sys.argv[1] if len(sys.argv) > 1 else None

    # Create the application
    app = QApplication(sys.argv)

    # Show GUI warning dialog
    msg = QMessageBox()
    msg.setIcon(QMessageBox.Warning)
    msg.setWindowTitle("Experimental Feature")
    msg.setText("Pipeline Designer GUI - Experimental Phase")
    msg.setInformativeText(
        "This GUI is in experimental development and may crash or have incomplete features.\n\n"
        "For production use, please use the Python API or JSON configuration files.\n\n"
        "Continue anyway?"
    )
    msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
    msg.setDefaultButton(QMessageBox.No)

    if msg.exec_() != QMessageBox.Yes:
        return 0

    # Create and show the main window
    window = PipelineDesignerApp(json_path=json_path)
    window.show()

    # Start the application event loop
    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())

from daolite.gui.designer.main_window import PipelineDesignerApp
import sys
import tempfile
import logging

# Set up logging with proper configuration
logfile = tempfile.NamedTemporaryFile(prefix="daolite_", suffix=".log", delete=False)
logging.basicConfig(filename=logfile.name, level=logging.INFO, filemode='w')
print(f"Logging to {logfile.name}")

def main():
    from PyQt5.QtWidgets import QApplication
    
    # Get json_path from command line arguments if provided
    json_path = sys.argv[1] if len(sys.argv) > 1 else None
    
    # Create the application
    app = QApplication(sys.argv)
    
    # Create and show the main window
    window = PipelineDesignerApp(json_path=json_path)
    window.show()
    
    # Start the application event loop
    return app.exec_()

if __name__ == "__main__":
    sys.exit(main())
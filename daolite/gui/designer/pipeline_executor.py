"""
Pipeline execution utilities for the pipeline designer.

This module provides functions to execute pipelines designed in the GUI
using either Python code generation or direct JSON execution.
"""

import os
import sys
import tempfile
import subprocess
import logging
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QDialogButtonBox, QMessageBox, QApplication

from .code_generator import CodeGenerator
from .file_io import save_pipeline_to_file
from .visualization_utils import show_visualization

# Set up logging
logger = logging.getLogger('PipelineExecutor')

def run_pipeline(parent, components, scene, execution_method="Python"):
    """
    Run the pipeline and display visualization in a popup window.
    
    Args:
        parent: Parent widget
        components: List of component blocks
        scene: The QGraphicsScene containing the pipeline
        execution_method: Either "Python" or "JSON"
        
    Returns:
        bool: True if execution was successful, False otherwise
    """
    if not components:
        QMessageBox.warning(parent, "Empty Pipeline", "No components to run.")
        return False
    
    # Create a temporary directory for pipeline execution
    with tempfile.TemporaryDirectory() as temp_dir:
        # For either method, we need to save the pipeline design in JSON format
        json_path = os.path.join(temp_dir, "temp_pipeline.json")
        save_pipeline_to_file(scene, components, scene.connections, json_path)
        
        # For Python method, also create a Python script
        if execution_method == "Python":
            py_path = os.path.join(temp_dir, "temp_pipeline.py")
            generator = CodeGenerator(components)
            try:
                generator.export_to_file(py_path)
                # Add visualization code to the Python file
                with open(py_path, 'a') as f:
                    f.write("\n\n# Visualize pipeline\n")
                    f.write("fig, ax, latency = pipeline.visualize('Pipeline Timing')\n")
                    
                    # Save the figure to a file instead of showing it
                    vis_path = os.path.join(temp_dir, "visualization.png")
                    f.write(f"fig.savefig('{vis_path}', dpi=300, bbox_inches='tight')\n")
                    f.write(f"print('\\nVisualization saved to: {vis_path}')\n")
                    f.write("print(f'Total pipeline latency: {latency:.2f} μs')\n")
                    # Don't call plt.show() - instead, just save the figure
            except Exception as e:
                QMessageBox.critical(parent, "Code Generation Error", f"Failed to generate Python code: {str(e)}")
                return False
        
        # Determine the visualization image path
        vis_path = os.path.join(temp_dir, "visualization.png")
        
        # Create a dialog to show execution progress
        progress_dialog = QDialog(parent)
        progress_dialog.setWindowTitle("Running Pipeline")
        progress_dialog.resize(500, 300)
        
        layout = QVBoxLayout()
        status_label = QLabel("Executing pipeline, please wait...")
        layout.addWidget(status_label)
        
        button_box = QDialogButtonBox(QDialogButtonBox.Cancel)
        button_box.rejected.connect(progress_dialog.reject)
        layout.addWidget(button_box)
        
        progress_dialog.setLayout(layout)
        progress_dialog.show()
        
        # Construct the command based on execution method
        if execution_method == "Python":
            # Set environment variable to force matplotlib to use Agg backend (non-interactive)
            my_env = os.environ.copy()
            my_env["MPLBACKEND"] = "Agg"  # Force non-interactive matplotlib backend
            cmd = [sys.executable, py_path]
        else:  # JSON
            my_env = os.environ.copy()
            my_env["MPLBACKEND"] = "Agg"  # Force non-interactive matplotlib backend
            cmd = [sys.executable, "-m", "daolite.pipeline.json_runner", json_path, "--save", vis_path, "--no-show"]
        
        # Run the command
        try:
            process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.STDOUT,
                text=True,
                cwd=temp_dir,
                env=my_env
            )
            
            # Update status with output from the process
            output = []
            while True:
                line = process.stdout.readline()
                if not line and process.poll() is not None:
                    break
                if line:
                    output.append(line.strip())
                    status_label.setText("\n".join(output[-10:]))  # Show last 10 lines
                    QApplication.processEvents()  # Update UI
            
            return_code = process.wait()
            
            # Check if execution was successful
            if return_code != 0:
                # Show error dialog with full output
                progress_dialog.close()
                error_msg = "\n".join(output)
                QMessageBox.critical(
                    parent, 
                    "Pipeline Execution Failed", 
                    f"Pipeline execution returned code {return_code}.\n\nOutput:\n{error_msg}"
                )
                return False
            
            # Close progress dialog
            progress_dialog.close()
            
            # Check if visualization file was created
            if not os.path.exists(vis_path):
                QMessageBox.warning(
                    parent, 
                    "Visualization Not Found", 
                    "Pipeline executed successfully, but no visualization was generated."
                )
                return True
            
            # Show visualization in a new dialog
            show_visualization(parent, vis_path, "\n".join(output))
            return True
            
        except Exception as e:
            progress_dialog.close()
            QMessageBox.critical(parent, "Execution Error", f"Failed to execute pipeline: {str(e)}")
            return False
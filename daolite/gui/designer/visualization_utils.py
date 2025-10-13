"""
Visualization utilities for the pipeline designer.

This module provides functions for displaying and saving pipeline visualizations.
"""

import logging

import matplotlib
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

logging.getLogger("matplotlib").setLevel(logging.WARNING)

# Set up logging
logger = logging.getLogger("VisualizationUtils")


def show_visualization(parent, image_path, output_text):
    """
    Show the visualization image in a dialog with embedded matplotlib figure.

    Args:
        parent: Parent widget
        image_path: Path to the visualization image
        output_text: Text output from pipeline execution
    """
    try:
        # Import matplotlib for visualization
        matplotlib.use("Qt5Agg")
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
        from matplotlib.figure import Figure

        dialog = QDialog(parent)
        dialog.setWindowTitle("Pipeline Visualization")
        dialog.resize(1000, 700)

        # Main layout
        main_layout = QVBoxLayout(dialog)

        # Create a splitter to allow resizing between visualization and text
        splitter = QSplitter(Qt.Vertical)
        splitter.setChildrenCollapsible(True)  # Allow sections to be collapsed

        # Top widget for visualization
        viz_widget = QWidget()
        viz_layout = QVBoxLayout(viz_widget)

        # Try to display the figure directly if possible, otherwise use the saved image
        try:
            # Load the image as a matplotlib figure
            img = plt.imread(image_path)
            fig = Figure(figsize=(10, 6))
            ax = fig.add_subplot(111)
            ax.imshow(img)
            ax.axis("off")  # Hide axes

            # Create a canvas to display the figure
            canvas = FigureCanvasQTAgg(fig)
            viz_layout.addWidget(canvas)
        except Exception as e:
            # Fallback to QPixmap if matplotlib embedding fails
            logger.error(f"Error embedding matplotlib figure: {str(e)}")
            scroll_area = QScrollArea()
            scroll_area.setWidgetResizable(True)

            image_label = QLabel()
            pixmap = QPixmap(image_path)
            image_label.setPixmap(pixmap)
            image_label.setAlignment(Qt.AlignCenter)

            scroll_area.setWidget(image_label)
            viz_layout.addWidget(scroll_area)

        # Add the visualization widget to the splitter
        splitter.addWidget(viz_widget)

        # Bottom widget for text output
        text_widget = QWidget()
        text_layout = QVBoxLayout(text_widget)

        # Add a header with toggle button for the text section
        text_header = QWidget()
        header_layout = QHBoxLayout(text_header)
        header_layout.setContentsMargins(0, 0, 0, 0)

        header_label = QLabel("<b>Pipeline Execution Output</b>")
        header_layout.addWidget(header_label)

        toggle_button = QPushButton("▼")  # Down arrow to indicate collapsible
        toggle_button.setMaximumWidth(30)
        toggle_button.setToolTip("Toggle output visibility")
        header_layout.addWidget(toggle_button)

        text_layout.addWidget(text_header)

        # Add the output text widget
        output_edit = QTextEdit()
        output_edit.setReadOnly(True)
        output_edit.setText(output_text)
        output_edit.setLineWrapMode(QTextEdit.NoWrap)  # Preserve formatting
        output_edit.setMinimumHeight(100)
        text_layout.addWidget(output_edit)

        # Add the text widget to the splitter
        splitter.addWidget(text_widget)

        # Set the initial sizes of the splitter (visualization larger than text)
        splitter.setSizes([700, 300])

        # Connect toggle button to hide/show text section
        def toggle_text_visibility():
            current_sizes = splitter.sizes()
            if current_sizes[1] == 0:  # If text is hidden
                # Show text (roughly 1/3 of the space)
                total_height = sum(current_sizes)
                splitter.setSizes([int(total_height * 0.7), int(total_height * 0.3)])
                toggle_button.setText("▼")  # Down arrow
            else:  # If text is visible
                # Hide text (save current proportions first)
                splitter.setSizes([current_sizes[0] + current_sizes[1], 0])
                toggle_button.setText("▲")  # Up arrow

        toggle_button.clicked.connect(toggle_text_visibility)

        # Add the splitter to the main layout
        main_layout.addWidget(splitter)

        # Add buttons
        button_box = QDialogButtonBox()

        # Add a save button
        save_button = button_box.addButton("Save Image", QDialogButtonBox.ActionRole)
        save_button.clicked.connect(
            lambda: save_visualization_image(parent, image_path)
        )

        # Add close button
        close_button = button_box.addButton(QDialogButtonBox.Close)
        close_button.clicked.connect(dialog.accept)

        main_layout.addWidget(button_box)

        dialog.exec_()

    except Exception as e:
        logger.error(f"Error showing visualization: {str(e)}")
        # Show a simple error message dialog if visualization fails
        QDialog(parent, f"Error showing visualization: {str(e)}")


def save_visualization_image(parent, source_path):
    """
    Save the visualization image to a user-selected location.

    Args:
        parent: Parent widget
        source_path: Path to the source image file
    """
    filename, _ = QFileDialog.getSaveFileName(
        parent, "Save Visualization", "", "PNG Files (*.png);;All Files (*)"
    )

    if filename:
        from shutil import copyfile

        try:
            copyfile(source_path, filename)
            from PyQt5.QtWidgets import QMessageBox

            QMessageBox.information(
                parent, "Image Saved", f"Visualization saved to {filename}"
            )
        except Exception as e:
            from PyQt5.QtWidgets import QMessageBox

            QMessageBox.critical(parent, "Save Error", f"Error saving image: {str(e)}")

"""
About dialog for the daolite pipeline designer.

This module provides a styled about dialog with information about the application.
"""

from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QTextBrowser, QTabWidget, QWidget
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QPixmap, QFont, QDesktopServices
from ..style_utils import set_app_style
import os
import sys
import importlib.metadata


class AboutDialog(QDialog):
    """
    A dialog displaying information about the daolite Pipeline Designer application.
    
    This dialog shows the application name, version, description, author info,
    documentation links, and citation information in a styled format that matches
    the rest of the application.
    """
    
    def __init__(self, parent=None):
        """
        Initialize the about dialog.
        
        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.setWindowTitle("About daolite Pipeline Designer")
        self.resize(600, 450)
        self.setup_ui()
        
        # Apply styling after all UI elements are created
        set_app_style(self)
        
    def setup_ui(self):
        """Set up the user interface for the about dialog."""
        layout = QVBoxLayout(self)
        
        # Create tab widget for organizing information
        tab_widget = QTabWidget(self)
        
        # About tab
        about_widget = QWidget()
        about_layout = QVBoxLayout(about_widget)
        
        # Title
        title_label = QLabel("<h1>daolite Pipeline Designer</h1>")
        title_label.setAlignment(Qt.AlignCenter)
        title_font = title_label.font()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        about_layout.addWidget(title_label)
        
        # Version - dynamically get from package metadata
        try:
            # Try to get version from importlib.metadata (Python 3.8+)
            version = importlib.metadata.version("daolite")
        except:
            # Fallback to pkg_resources or hardcoded version
            try:
                import pkg_resources
                version = pkg_resources.get_distribution("daolite").version
            except:
                # Get version from setup.py
                version = self._get_setup_attribute("version", "0.1.0")
        
        version_label = QLabel(f"<p><b>Version:</b> {version}</p>")
        version_label.setAlignment(Qt.AlignCenter)
        about_layout.addWidget(version_label)
        
        # Description
        description = QTextBrowser()
        description.setReadOnly(True)
        description.setOpenExternalLinks(True)
        description.setHtml("""
            <p>A visual tool for designing Adaptive Optics pipelines with emphasis on 
            network and multi-compute node configurations.</p>
            
            <p>Part of the daolite package for estimating latency in 
            Adaptive Optics Real-time Control Systems.</p>
            
            <p><b>Features:</b></p>
            <ul>
                <li>Visual pipeline design</li>
                <li>Component parameter configuration</li>
                <li>CPU and GPU resource management</li>
                <li>Latency estimation</li>
                <li>Code generation</li>
                <li>JSON import/export</li>
            </ul>
        """)
        about_layout.addWidget(description)
        
        tab_widget.addTab(about_widget, "About")
        
        # Author tab
        author_widget = QWidget()
        author_layout = QVBoxLayout(author_widget)
        
        # Get author information from setup.py
        author_name = self._get_setup_attribute("author", "David Barr")
        author_email = self._get_setup_attribute("author_email", "dave@davetbarr.com")
        github_url = self._get_setup_attribute("url", "https://github.com/davetbarr/daolite")
        
        author_info = QTextBrowser()
        author_info.setReadOnly(True)
        author_info.setOpenExternalLinks(True)
        author_info.setHtml(f"""
            <h2>Author</h2>
            <p><b>Name:</b> {author_name}</p>
            <p><b>Email:</b> <a href="mailto:{author_email}">{author_email}</a></p>
            <p><b>GitHub:</b> <a href="{github_url}">{github_url}</a></p>
            
            <h2>Contributors</h2>
            <p>The daolite package is open to contributions from the community.</p>
            <p>See the GitHub repository for a list of contributors.</p>
        """)
        author_layout.addWidget(author_info)
        
        tab_widget.addTab(author_widget, "Author")
        
        # Documentation tab
        doc_widget = QWidget()
        doc_layout = QVBoxLayout(doc_widget)
        
        doc_links = QTextBrowser()
        doc_links.setReadOnly(True)
        doc_links.setOpenExternalLinks(True)
        doc_links.setHtml("""
            <h2>Documentation</h2>
            
            <p><b>Online Documentation:</b> 
            <a href="https://daolite.readthedocs.io">https://daolite.readthedocs.io</a></p>
            
            <p><b>GitHub Wiki:</b>
            <a href="https://github.com/davetbarr/daolite/wiki">https://github.com/davetbarr/daolite/wiki</a></p>
            
            <h3>Local Documentation</h3>
            <p>You can generate local documentation by running:</p>
            <pre>cd docs && make html</pre>
            <p>Then open <code>docs/build/html/index.html</code> in your browser.</p>
        """)
        doc_layout.addWidget(doc_links)
        
        tab_widget.addTab(doc_widget, "Documentation")
        
        # Citation tab
        citation_widget = QWidget()
        citation_layout = QVBoxLayout(citation_widget)
        
        citation_text = QTextBrowser()
        citation_text.setReadOnly(True)
        citation_text.setHtml("""
            <h2>How to Cite</h2>
            
            <p>If you use daolite in your research, please cite it as follows:</p>
            
            <pre>
Barr, D. (2023). daolite: A Python package for estimating latency 
in Adaptive Optics Real-time Control Systems. 
GitHub: https://github.com/davetbarr/daolite
            </pre>
            
            <h3>BibTeX</h3>
            <pre>
@software{daolite,
  author = {Barr, David},
  title = {daolite: A Python package for estimating latency in Adaptive Optics Real-time Control Systems},
  year = {2023},
  url = {https://github.com/davetbarr/daolite}
}
            </pre>
        """)
        citation_layout.addWidget(citation_text)
        
        tab_widget.addTab(citation_widget, "Citation")
        
        # License tab
        license_widget = QWidget()
        license_layout = QVBoxLayout(license_widget)
        
        license_text = QTextBrowser()
        license_text.setReadOnly(True)
        
        # Try to read LICENSE file
        license_content = "Please see the LICENSE file in the repository."
        try:
            # Attempt to find the LICENSE file
            script_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
            license_path = os.path.join(script_dir, "LICENSE")
            
            if os.path.exists(license_path):
                with open(license_path, 'r') as f:
                    license_content = f.read()
        except Exception:
            pass
            
        license_text.setPlainText(license_content)
        license_layout.addWidget(license_text)
        
        tab_widget.addTab(license_widget, "License")
        
        layout.addWidget(tab_widget)
        
        # Close button
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)
        
        self.setLayout(layout)
        
    def _get_setup_attribute(self, attr_name, default_value=""):
        """
        Extract an attribute from setup.py if possible.
        
        Args:
            attr_name: The name of the attribute to extract
            default_value: Default value to return if extraction fails
            
        Returns:
            The extracted attribute value or the default value
        """
        try:
            # Try to find setup.py in parent directories
            script_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
            setup_path = os.path.join(script_dir, "setup.py")
            
            if os.path.exists(setup_path):
                with open(setup_path, 'r') as f:
                    setup_content = f.read()
                    
                # Simple regex-free parser for setup attributes
                for line in setup_content.split('\n'):
                    line = line.strip()
                    if line.startswith(f"{attr_name}=") or f"{attr_name} =" in line:
                        value = line.split('=', 1)[1].strip()
                        # Remove quotes and commas
                        value = value.strip('"\'').rstrip(',').strip('"\'')
                        return value
                        
        except Exception:
            pass
            
        return default_value
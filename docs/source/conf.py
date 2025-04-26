# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------
# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here.
import os
import sys
sys.path.insert(0, os.path.abspath('../..'))
sys.path.insert(0, os.path.abspath('.'))  # Include the current directory for docs

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'daolite'
copyright = '2024, David Barr'
author = 'David Barr'
release = '0.1'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.duration',
    'sphinx.ext.doctest',
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary',
    'sphinx.ext.intersphinx',
    'sphinx.ext.napoleon',  # Support for NumPy and Google style docstrings
    'sphinx.ext.viewcode',  # Add links to view source code
    'sphinx.ext.coverage',  # Check documentation coverage
]

# Napoleon settings
napoleon_google_docstring = False
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = True
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = False
napoleon_use_admonition_for_notes = False
napoleon_use_admonition_for_references = False
napoleon_use_ivar = False
napoleon_use_param = True
napoleon_use_rtype = True
napoleon_use_keyword = True

templates_path = ['_templates']
exclude_patterns = []

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']

# Intersphinx mapping to other documentation
intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'numpy': ('https://numpy.org/doc/stable', None),
    'matplotlib': ('https://matplotlib.org/stable', None),
    'scipy': ('https://docs.scipy.org/doc/scipy', None),
}

# Suppress specific warning types
suppress_warnings = [
    'misc.highlighting_failure',
    'toc.circular',
    'app.add_node',
    'app.add_directive',
    'app.add_role',
    'toc.not_readable',
    'toc.secnum',
    'autodoc.import_object'  # Suppress specific import errors when mocking
]

# Setup event handlers to handle complex imports
def setup(app):
    """Set up event handlers for Sphinx build."""
    app.connect('autodoc-skip-member', skip_member)
    
    # Add special CSS for better rendering
    app.add_css_file('custom.css')

def skip_member(app, what, name, obj, skip, options):
    """Skip internal members and special methods unless specifically included."""
    # Skip internal methods but not __init__
    if skip:
        return True
    if name.startswith('_') and name != '__init__':
        return True
    return skip

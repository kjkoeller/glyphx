# Configuration file for the Sphinx documentation builder.

import datetime
from configparser import ConfigParser
from importlib.metadata import version as get_version
from unittest.mock import MagicMock
import os
import sys

# Mock optional dependencies that are not needed to build docs
# and may not be installable in the ReadTheDocs environment
MOCK_MODULES = [
    'anthropic',
    'cairosvg',
    'cairocffi',
    'pptx',
    'python_pptx',
    'ipywidgets',
    'jupyterlab_widgets',
    'widgetsnbextension',
]

for mod_name in MOCK_MODULES:
    sys.modules[mod_name] = MagicMock()

# Get configuration information from setup.cfg
conf = ConfigParser()
conf.read([os.path.join(os.path.dirname(__file__), '..', 'setup.cfg')])
setup_cfg = dict(conf.items('metadata'))

# By default, highlight as Python 3.
highlight_language = 'python3'

# -- Project information
project = setup_cfg['name']
author = setup_cfg['author']
copyright = '{0}, {1}'.format(datetime.datetime.now().year, author)

try:
    release = get_version("glyphx")
except Exception:
    release = "unknown"
version = '.'.join(release.split('.')[:2])

html_title = '{0} v{1}'.format(project, release)

# -- General configuration
root_doc = 'index'

man_pages = [('index', project.lower(), project + u' Documentation',
              [author], 1)]

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.duration',
    'sphinx.ext.doctest',
    'sphinx.ext.intersphinx',
    'sphinx.ext.napoleon',
    'sphinx.ext.viewcode',
]

intersphinx_mapping = {
    'python': ('https://docs.python.org/3/', None),
    'sphinx': ('https://www.sphinx-doc.org/en/master/', None),
}

autodoc_default_options = {
    'members':          True,
    'undoc-members':    False,
    'show-inheritance': True,
}

nitpicky = False

suppress_warnings = [
    'ref.python',
    'autodoc.import_error',
]

templates_path = ['_templates']

# -- Options for HTML output
html_theme = 'furo'

# -- Static files / images
# Sphinx copies everything from html_static_path into the _static directory.
# Images referenced via .. image:: are found relative to the docs/ source dir,
# so docs/examples/*.svg are found automatically without html_static_path.
# However, to ensure image directories are copied to the build output:
html_static_path = []

# Images referenced as 'examples/foo.svg' are found by Sphinx relative to docs/
# No additional configuration needed for .. image:: directives.

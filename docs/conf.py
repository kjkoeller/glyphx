import os
import sys
sys.path.insert(0, os.path.abspath(’..’))

project = ‘glyphx’
author  = ‘Kyle Koeller’

extensions = [
‘sphinx.ext.autodoc’,
‘sphinx.ext.napoleon’,
‘sphinx.ext.viewcode’,
‘sphinx.ext.todo’,
‘sphinx.ext.githubpages’,
‘sphinx.ext.intersphinx’,
]

intersphinx_mapping = {
‘python’: (‘https://docs.python.org/3’, None),
‘numpy’:  (‘https://numpy.org/doc/stable’, None),
‘pandas’: (‘https://pandas.pydata.org/docs’, None),
}

autodoc_default_options = {
‘members’:         True,
‘undoc-members’:   False,
‘show-inheritance’: True,
}

templates_path   = [’_templates’]
exclude_patterns = [’_build’]

html_theme = ‘sphinx_rtd_theme’
html_static_path = [’_static’]
html_theme_options = {
‘navigation_depth’: 4,
‘titles_only’:      False,
}
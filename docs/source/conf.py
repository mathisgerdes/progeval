# Configuration file for the Sphinx documentation builder.

# -- Project information
from progeval import __version__

project = 'progeval'
copyright = '2022, Mathis Gerdes'

release = __version__
version = '.'.join(release.split('.')[:2])

# -- General configuration

extensions = [
    'sphinx.ext.duration',
    'sphinx.ext.doctest',
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary',
    'sphinx.ext.intersphinx',
    'sphinx.ext.napoleon',
    'sphinx.ext.autosectionlabel',
    'sphinx_autodoc_typehints',
    'sphinx_copybutton',
    'myst_nb',
]

templates_path = ['_templates']

source_suffix = ['.rst', '.ipynb', '.md']

autosummary_generate = True
napolean_use_rtype = False
autosectionlabel_prefix_document = True
myst_heading_anchors = 3

# -- Options for HTML output

html_theme = 'pydata_sphinx_theme'
html_title = "Progressive Evaluation"
html_favicon = '_static/favicon.ico'

html_theme_options = {
    'use_edit_page_button': False,
    'show_toc_level': 2,
    'github_url': 'https://github.com/mathisgerdes/progeval',
    'icon_links': [
            {
                'name': 'PyPI',
                'url': 'https://pypi.org/project/progeval/',
                'icon': 'fa-solid fa-box',
            },
        ],
}

html_sidebars = {
  "**": []
}

# myst options
nb_merge_streams = True
nb_execution_timeout = 100

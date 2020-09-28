"""
Configuration file for the Sphinx documentation builder.

For a full list of options see the documentation:
https://www.sphinx-doc.org/en/master/usage/configuration.html
"""

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.realpath to make it absolute, like shown here.
#

import logging
import os
import shutil
import sys
from typing import *

from sphinx.application import Sphinx

logging.basicConfig(level=logging.INFO)
_log = logging.getLogger(name=__name__)

# this is the directory that contains all required repos
_conf_base_dir = os.path.dirname(os.path.realpath(__file__))
_root_dir = os.path.normpath(
    os.path.join(_conf_base_dir, os.pardir, os.pardir, os.pardir)
)

# noinspection PyShadowingNames
def set_config(
    *, project: str, modules: Iterable[str], html_logo: Optional[str] = None
) -> None:
    """
    Add required modules to the python path, and set custom configuration options
    """

    _set_globals(project_=project, html_logo_=html_logo)

    modules = set(modules) | {"pytools"}
    for module in modules:
        module_path = os.path.normpath(os.path.join(_root_dir, module, "src"))
        if module_path not in sys.path:
            # noinspection PyUnboundLocalVariable
            sys.path.insert(0, module_path)
            _log.info(f"added `{module_path}` to python paths")


def _set_globals(project_: str, html_logo_: Optional[str]) -> None:
    """
    Set global configuration parameters
    """
    global project, html_logo

    project = project_
    html_logo = latex_logo = html_logo_


_log.info(f"sys.path = {sys.path}")

# -- Project information -----------------------------------------------------

project = "pytools"
copyright = "2020, The Boston Consulting Group (BCG)"
author = "FACET Team"

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "nbsphinx",
    "sphinx.ext.autodoc",
    "sphinx.ext.imgmath",
    "sphinx.ext.intersphinx",
    "sphinx.ext.viewcode",
    "sphinx_autodoc_typehints",
]

# -- Options for autodoc / autosummary -------------------------------------------------

# generate autosummary even if no references
autosummary_generate = True

# always overwrite generated auto summaries with newly generated versions
autosummary_generate_overwrite = True

autodoc_default_options = {
    "no-ignore-module-all": True,
    "inherited-members": True,
    "imported-members": True,
    "no-show-inheritance": True,
    "member-order": "groupwise",
}

nbsphinx_allow_errors = True
nbsphinx_timeout = 60 * 15  # 15 minutes due to tutorial/model notebook

# add intersphinx mapping
intersphinx_mapping = {
    "pandas": ("https://pandas.pydata.org/pandas-docs/stable", None),
    "matplotlib": ("https://matplotlib.org", None),
    "numpy": ("https://numpy.org/doc/stable", None),
    "python": ("https://docs.python.org/3.6", None),
    "scipy": ("https://docs.scipy.org/doc/scipy/reference", None),
    "sklearn": ("https://scikit-learn.org/stable", None),
    "shap": ("https://shap.readthedocs.io/en/latest", None),
    "joblib": ("https://joblib.readthedocs.io/en/latest", None),
    "sphinx": ("https://www.sphinx-doc.org/en/master", None),
    "pytools": ("", None),
    "sklearndf": ("", None),
    "facet": ("", None),
    "flow": ("", None),
}

intersphinx_collapsible_submodules = {
    "pandas.core.frame": "pandas",
    "pandas.core.series": "pandas",
    "pandas.core.indexes.base": "pandas",
    "pandas.core.indexes.multi": "pandas",
}

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

source_suffix = [".rst", ".md", ".ipynb"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ["*/.ipynb_checkpoints/*"]

# -- Options for sphinx_autodoc_typehints ----------------------------------------------
set_type_checking_flag = False
typehints_fully_qualified = False
always_document_param_types = False

# -- Options for Math output -----------------------------------------------------------

imgmath_image_format = "svg"
imgmath_use_preview = True

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "pydata_sphinx_theme"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]
html_logo = "_static/gamma_logo.jpg"

# Class documentation to include docstrings both global to the class, and from __init__
autoclass_content = "both"

# -- End of options section ------------------------------------------------------------


def setup(app: Sphinx) -> None:
    """
    Add event handlers to the Sphinx application object
    :param app: the Sphinx application object
    """

    from pytools.sphinx import AddInheritance, CollapseModulePaths

    AddInheritance(collapsible_submodules=intersphinx_collapsible_submodules).connect(
        app=app
    )

    CollapseModulePaths(
        collapsible_submodules=intersphinx_collapsible_submodules
    ).connect(app=app, priority=100000)

    _add_custom_css_and_js(app=app)


def _add_custom_css_and_js(app: Sphinx):
    # add custom css and js files, and copy them to the build/html/_static folder

    css_rel_path = os.path.join("css", "gamma.css")
    js_rel_path = os.path.join("js", "gamma.js")
    app.add_css_file(filename=css_rel_path)
    app.add_js_file(filename=js_rel_path)
    src_root = os.path.join(_conf_base_dir, "_static_base")
    dst_root = os.path.join(os.path.abspath(os.getcwd()), "build", "html", "_static")
    for rel_path in [css_rel_path, js_rel_path]:
        dst_dir = os.path.join(dst_root, os.path.dirname(rel_path))
        os.makedirs(dst_dir, exist_ok=True)
        shutil.copy(src=os.path.join(src_root, rel_path), dst=dst_dir)

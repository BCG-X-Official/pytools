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
from typing import Any, Dict, Iterable, Optional

from sphinx.application import Sphinx

from pytools.sphinx import Replace3rdPartyDoc

logging.basicConfig(level=logging.INFO)
_log = logging.getLogger(name=__name__)

# this is the directory that contains all required repos
_dir_conf_base = os.path.dirname(os.path.realpath(__file__))
_dir_repo_root = os.path.normpath(
    os.path.join(_dir_conf_base, os.pardir, os.pardir, os.pardir)
)
_dir_sphinx = os.path.abspath(os.getcwd())


# noinspection PyShadowingNames
def set_config(
    globals_: Dict[str, Any],
    *,
    project: str,
    modules: Iterable[str],
    html_logo: Optional[str] = None,
) -> None:
    """
    Add required modules to the python path, and set custom configuration options
    """

    globals_["project"] = project

    if html_logo:
        globals_["html_logo"] = html_logo
        globals_["latex_logo"] = html_logo

    modules = set(modules) | {"pytools"}
    for module in modules:
        module_path = os.path.normpath(os.path.join(_dir_repo_root, module, "src"))
        if module_path not in sys.path:
            # noinspection PyUnboundLocalVariable
            sys.path.insert(0, module_path)
            _log.info(f"added `{module_path}` to python paths")

    # Update global variables
    globals_.update(
        (k, v) for k, v in globals().items() if not (k.startswith("_") or k in globals_)
    )

    globals_.update(
        (k, v) for k, v in globals().items() if not (k.startswith("_") or k in globals_)
    )


_log.info(f"sys.path = {sys.path}")

# -- Project information -----------------------------------------------------

project = "pytools"
copyright = "2021, Boston Consulting Group (BCG)"
author = "FACET Team"

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "nbsphinx",
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.mathjax",
    "sphinx.ext.intersphinx",
    "sphinx.ext.viewcode",
    "sphinx_autodoc_typehints",
]

# -- Options for autodoc / autosummary -------------------------------------------------

# prevent numpydoc from interfering with autosummary
numpydoc_show_class_members = False

# generate autosummary even if no references
autosummary_generate = False

# always overwrite generated auto summaries with newly generated versions
autosummary_generate_overwrite = True

autosummary_imported_members = True

autodoc_default_options = {
    "ignore-module-all": False,
    "inherited-members": True,
    "imported-members": False,
    "show-inheritance": False,
    "member-order": "groupwise",
}

nbsphinx_allow_errors = True

# add intersphinx mapping
intersphinx_mapping = {
    "pandas": ("https://pandas.pydata.org/pandas-docs/stable", None),
    "pd": ("https://pandas.pydata.org/pandas-docs/stable", None),
    "matplotlib": ("https://matplotlib.org", None),
    "numpy": ("https://numpy.org/doc/stable", None),
    "np": ("https://numpy.org/doc/stable", None),
    "python": ("https://docs.python.org/3.6", None),
    "scipy": ("https://docs.scipy.org/doc/scipy/reference", None),
    "sklearn": ("https://scikit-learn.org/stable", None),
    "shap": ("https://shap.readthedocs.io/en/stable", None),
    "joblib": ("https://joblib.readthedocs.io/en/latest", None),
    "sphinx": ("https://www.sphinx-doc.org/en/master", None),
    "lightgbm": ("https://lightgbm.readthedocs.io/en/latest/", None),
    "pytools": ("https://bcg-gamma.github.io/pytools/", None),
    "sklearndf": ("https://bcg-gamma.github.io/sklearndf/", None),
    "facet": ("https://bcg-gamma.github.io/facet/", None),
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


def _get_package_version() -> str:
    """
    Get the package version for the project being built.
    :return: string with Python package version
    """
    # NOTE: sphinx-make changes the CWD into sphinx/source
    #       while FACET's make_base expects a CWD <project>/src
    #       hence: save current CWD, navigate to <project>/src, then go back
    cwd = os.getcwd()
    os.chdir(os.path.join(cwd, os.pardir, os.pardir, "src"))
    import make_base

    version_ = str(make_base.get_package_version())
    os.chdir(cwd)
    return version_


version = _get_package_version()
# -- End of options section ------------------------------------------------------------


def setup(app: Sphinx) -> None:
    """
    Add event handlers to the Sphinx application object
    :param app: the Sphinx application object
    """

    from pytools.sphinx import (
        AddInheritance,
        CollapseModulePathsInDocstring,
        CollapseModulePathsInSignature,
        SkipIndirectImports,
    )

    AddInheritance(collapsible_submodules=intersphinx_collapsible_submodules).connect(
        app=app
    )

    CollapseModulePathsInDocstring(
        collapsible_submodules=intersphinx_collapsible_submodules
    ).connect(app=app, priority=100000)

    CollapseModulePathsInSignature(
        collapsible_submodules=intersphinx_collapsible_submodules
    ).connect(app=app, priority=100000)

    SkipIndirectImports().connect(app=app)

    Replace3rdPartyDoc().connect(app=app)

    _add_custom_css_and_js(app=app)


def _add_custom_css_and_js(app: Sphinx):
    # add custom css and js files, and copy them to the build/html/_static folder
    css_rel_paths = (os.path.join("css", "gamma.css"),)
    js_rel_paths = (os.path.join("js", "gamma.js"), os.path.join("js", "versions.js"))

    for css in css_rel_paths:
        app.add_css_file(filename=css)

    for js in js_rel_paths:
        app.add_js_file(filename=js)

    src_root = os.path.normpath(
        os.path.join(_dir_conf_base, os.pardir, "source", "_static_base")
    )
    dst_html = os.path.normpath(
        os.path.join(_dir_sphinx, os.pardir, "build", "html", "_static")
    )
    for rel_path in css_rel_paths + js_rel_paths:
        dst_dir = os.path.join(dst_html, os.path.dirname(rel_path))
        os.makedirs(dst_dir, exist_ok=True)
        src_file = os.path.join(src_root, rel_path)
        print(f"copying {src_file} to {dst_dir}")
        shutil.copy(src=src_file, dst=dst_dir)

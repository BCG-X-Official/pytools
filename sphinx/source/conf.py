# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#

import itertools
import logging
import re
import sys
from typing import *

import typing_inspect
from sphinx.application import Sphinx

log = logging.getLogger(name=__name__)
log.setLevel(logging.INFO)


# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
def _set_paths() -> None:
    import sys
    import os

    module_paths = ["pytools"]

    if "cwd" not in globals():
        # noinspection PyGlobalUndefined
        global cwd
        cwd = os.path.join(os.getcwd(), os.pardir, os.pardir)
    print(f"working dir is '{os.getcwd()}'")
    for module_path in module_paths:
        if module_path not in sys.path:
            # noinspection PyUnboundLocalVariable
            sys.path.insert(0, os.path.abspath(f"{cwd}/{os.pardir}/{module_path}/src"))
            print(f"added `{sys.path[0]}` to python paths")


_set_paths()

log.info(f"sys.path = {sys.path}")


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

# always overwrite generated autosummaries with newly generated versions
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
    "joblib": ("https://joblib.readthedocs.io/en/latest", None),
}

intersphinx_collapsible_submodules = {
    "pandas.core.frame": "pandas",
    "pandas.core.series": "pandas",
    "pandas.core.panel": "pandas",
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
always_document_param_types = True

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
latex_logo = html_logo

# Class documentation to include docstrings both global to the class, and from __init__
autoclass_content = "both"

# -- End of options section ------------------------------------------------------------


_classes_visited: Set[type] = set()


# noinspection PyUnusedLocal
def add_inheritance(
    app: Sphinx, what: str, name: str, obj: object, options: object, lines: List[str]
) -> None:
    """
    Add list of base classes as the first line of the docstring. Ignore builtin
    classes and classes that were already visited once
    :param app: the Sphinx application object
    :param what: the type of the object which the docstring belongs to (one of \
        "module", "class", "exception", "function", "method", "attribute")
    :param name: the fully qualified name of the object
    :param obj: the object itself
    :param options: the options given to the directive: an object with attributes \
        inherited_members, undoc_members, show_inheritance and noindex that are true \
        if the flag option of same name was given to the auto directive
    :param lines: the lines of the docstring
    """

    if what == "class" and obj not in _classes_visited:
        # visit each class only once (this method will be called twice if there are
        # docstrings both for the class, and for __init__)

        _classes_visited.add(cast(type, obj))

        # add bases and generics documentation to class

        # generate the RST for bases and generics
        class_ = cast(type, obj)

        bases = [
            (base, typing_inspect.get_origin(base) or base)
            for base in set(_get_bases(class_))
        ]
        bases = [
            base
            for base, origin in bases
            if not any(
                origin is not other and issubclass(other, origin) for _, other in bases
            )
        ]

        bases_lines = [""]
        if bases:
            base_names = (_class_name_with_generics(base) for base in bases)
            bases_lines.append(f':Bases: {", ".join(base_names)}')
            bases_lines.append("")

        generics = _get_generics(class_)
        if len(generics) > 0:
            generic_type_variables = f':Generic Types: {", ".join(generics)}'
            bases_lines.append(generic_type_variables)
            bases_lines.append("")

        # insert this after the intro text, and before class parameters

        def _insert_position() -> int:
            for n, line in enumerate(lines):
                if re.match(r"\s*:param\s*\w+:", line):
                    return n
            return -1

        if len(bases_lines) > 0:
            pos = _insert_position()
            lines[pos:pos] = bases_lines


_intersphinx_collapsible_prefixes: List[Tuple[re.Pattern, str]] = [
    *[
        (re.compile(r"(`~?)" + old.replace(".", r"\.")), f"\\1{new}")
        for old, new in intersphinx_collapsible_submodules.items()
    ],
    (re.compile(r"(`~?(?:(?!_)\w+\.)+)(_\w*\.)+"), r"\1"),
]

# noinspection PyUnusedLocal
def collapse_module_paths(
    app: Sphinx, what: str, name: str, obj: object, options: object, lines: List[str]
) -> None:
    for expanded, collapsed in _intersphinx_collapsible_prefixes:
        for i, line in enumerate(lines):
            lines[i] = expanded.sub(collapsed, line)


def _class_attr(cls: type, attr: str, default: Callable[[], str]) -> str:
    def _get_attr(_cls: type) -> str:
        try:
            # we try to get the class name
            return getattr(_cls, attr)
        except AttributeError:
            # if the name is not defined, this class is likely to have generic
            # arguments, so we re-try recursively with the origin (unless the origin
            # is the class itself to avoid infinite recursion)
            cls_origin = typing_inspect.get_origin(cls)
            if cls_origin != _cls:
                return _get_attr(_cls=cls_origin)
            else:
                # as a last resort, we convert the class to a string
                return default()

    return _get_attr(_cls=cls)


def _class_name(cls: type) -> str:
    return _class_attr(cls=cls, attr="__qualname__", default=lambda: str(cls))


def _class_module(cls: type) -> str:
    module_name = _class_attr(cls=cls, attr="__module__", default=lambda: "")

    collapsed_module = intersphinx_collapsible_submodules.get(module_name, None)
    if collapsed_module:
        return collapsed_module

    # remove private submodules
    module_path = module_name.split(".")
    for i, submodule in enumerate(module_path):
        if submodule.startswith("_"):
            return ".".join(module_path[:i])

    # return the unchanged module name
    return module_name


def _full_name(cls: type) -> str:
    # get the full name of the class, including the module prefix
    return f"{_class_module(cls=cls)}.{_class_name(cls=cls)}"


def _class_name_with_generics(cls: type) -> str:
    if not hasattr(cls, "__module__"):
        return str(cls)

    if cls.__module__ in ("__builtin__", "builtins"):
        return f":class:`{cls.__name__}`"

    else:
        generic_args = [
            _class_name_with_generics(arg)
            for arg in typing_inspect.get_args(cls, evaluate=True)
        ]

        generic_arg_str = f'[{", ".join(generic_args)}]' if generic_args else ""

        return f":class:`~{_full_name(cls)}` {generic_arg_str}"


def _get_bases(child_class: type) -> Generator[type, None, None]:
    # get the names of the immediate base classes of arg child_class

    # ensure we have the non-generic origin class
    child_class = typing_inspect.get_origin(child_class) or child_class

    # get the base classes, try generic bases first then fall back to "regular" bases
    base_classes = get_generic_bases(child_class) or child_class.__bases__

    # get the names of all base classes; go up the class hierarchy in case of hidden
    # classes
    for base in base_classes:

        # exclude object and Generic types
        if base is object or typing_inspect.get_origin(base) is Generic:
            continue

        # exclude protected classes
        elif _class_name(base).startswith("_"):
            yield from _get_bases(base)

        # all other classes will be listed as bases
        else:
            yield base


def get_generic_bases(cls: type) -> Tuple[type, ...]:
    bases = typing_inspect.get_generic_bases(cls)
    if any(bases is typing_inspect.get_generic_bases(base) for base in cls.__bases__):
        return ()
    else:
        return bases


def _get_generics(child_class: type) -> List[str]:
    return list(
        itertools.chain.from_iterable(
            (
                [
                    _class_name_with_generics(arg)
                    for arg in typing_inspect.get_args(base, evaluate=True)
                ]
                for base in get_generic_bases(child_class)
                if typing_inspect.get_origin(base) is Generic
            )
        )
    )


def setup(app: Sphinx) -> None:
    """
    Add event handlers to the Sphinx application object
    :param app: the Sphinx application object
    """
    app.connect("autodoc-process-docstring", add_inheritance)
    app.connect("autodoc-process-docstring", collapse_module_paths, priority=100000)

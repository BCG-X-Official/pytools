"""
Implementation of ``validate__all__declarations``.
"""

import logging
import os
from collections.abc import Iterator
from importlib import import_module
from types import ModuleType
from typing import ParamSpec, TypeVar

log = logging.getLogger(__name__)

__all__ = [
    "validate__all__declarations",
]


def validate__all__declarations(root_module: ModuleType) -> None:  # pragma: no cover
    """
    Validate that the ``__all__`` declarations include all publicly defined functions
    and classes in the given module and its submodules.

    :param root_module: the root module to validate
    """

    # get the path to the root module in the file system; check that it is not None
    root_file = root_module.__file__
    if root_file is None:
        raise ValueError(f"root module {root_module} does not have a file path")

    # get the path to the root module in the file system
    root_dir = os.path.dirname(root_file)

    # recursively get all Python files in the root directory
    log.debug(f"scanning .py files in path: {root_dir}")
    module_names = _iter_module_names(root_dir)

    # validate the __all__ declaration for each module
    for module_name in module_names:
        # import the module
        module: ModuleType = import_module(module_name)

        # get the public declarations in the module
        public_declarations = set(_get_public_declarations(module))

        # get the public constants in the module, these are optional in __all__
        public_constants = set(_get_public_constants(module))

        # get the __all__ declaration in the module; empty set if not defined
        all_ = set(getattr(module, "__all__", {})) - public_constants

        if public_declarations != all_:
            # declarations do not match, determine the differences
            symbols_not_in_all = public_declarations - all_
            symbols_only_in_all = all_ - public_declarations

            # raise an error with the differences
            error_message = f"__all__ does not match public symbols in {module}: "
            if symbols_not_in_all:
                error_message += f"\n  missing from __all__: {symbols_not_in_all}"
            if symbols_only_in_all:
                error_message += f"\n  only in __all__: {symbols_only_in_all}"
            raise ValueError(error_message)


#
# Private auxiliary functions
#


def _get_public_declarations(module: ModuleType) -> Iterator[str]:  # pragma: no cover

    # get all public declarations in the module

    module_name = module.__name__
    for name, value in vars(module).items():
        if (
            # ignore private declarations
            not name.startswith("_")
            # ignore TypeVars and imported modules
            and not isinstance(value, (TypeVar, ParamSpec, ModuleType))
            # ignore objects from other modules, or objects lacking a module ascription
            and getattr(value, "__module__", None) == module_name
        ):
            yield name


def _get_public_constants(module: ModuleType) -> Iterator[str]:  # pragma: no cover

    # get all public constants in the module

    for name, value in vars(module).items():
        if (
            # ignore private declarations
            not name.startswith("_")
            # ignore objects with a module ascription
            and getattr(value, "__module__", None) is None
        ):
            yield name


def _iter_module_names(root_dir: str) -> Iterator[str]:  # pragma: no cover

    # recursively get all module names in the root directory, including
    # private modules and submodules

    for dir_path, dir_names, filenames in os.walk(root_dir):
        # iterate over the filenames in the current directory
        for filename in filenames:
            # check if the file is a Python file
            if filename.endswith(".py"):
                # yield the file path that's relative to the root directory
                yield (
                    os.path.relpath(
                        path=(
                            dir_path
                            if filename == "__init__.py"
                            else os.path.join(dir_path, filename[:-3])
                        ),
                        start=os.path.dirname(root_dir),
                    )
                    # replace the file separator with a dot to get the module name
                    .replace(os.sep, ".")
                )

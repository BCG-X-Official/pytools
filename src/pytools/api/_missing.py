"""
Implementation of ``MissingClassMeta``.
"""

import logging
from collections.abc import Callable
from typing import Any, NoReturn

log = logging.getLogger(__name__)

__all__ = ["MissingClassMeta", "missing_function"]


def missing_function(name: str, module: str) -> Callable[..., NoReturn]:
    """
    Create a placeholder function for a function that could not be imported from an
    optional dependency.

    The placeholder function raises an ImportError when called, stating that the given
    function is missing, and the module that defines it needs to be installed.

    :param name: the name of the missing function
    :param module: the name of the module that defines the function
    :return: a callable that raises an ImportError when called
    """

    def _missing(*_args: Any, **_kwargs: Any) -> NoReturn:
        raise ImportError(
            f"Module {module!r} needs to be installed to use the {name!r} function"
        )

    return _missing


class MissingClassMeta(type):
    """
    A metaclass that creates a placeholder for a class that could not be imported
    from an optional dependency.

    The placeholder class raises an ImportError when instantiated, stating that the
    given class is missing, and the module that defines it needs to be installed.

    Usage:

    .. code-block:: python

        try:
            from some_module import SomeClass
        except ImportError:
            class SomeClass(metaclass=MissingClassMeta, module="some_module"):
                \"""Placeholder class for the missing ``SomeClass``.\"""
    """

    def __init__(
        cls,
        name: str,
        base: tuple[type, ...],
        namespace: dict[str, Any],
        *,
        module: str,
    ) -> None:
        """
        :param name: the name of the missing class
        :param base: the base classes of the missing class
        :param namespace: the namespace of the missing class
        :param module: the name of the package dependency that is missing
        """
        super().__init__(name, base, namespace)
        # set the module of the missing class to the package name
        cls.__module__ = module

    def __new__(
        cls,
        name: str,
        base: tuple[type, ...],
        namespace: dict[str, Any],
        *,
        module: str,
    ) -> Any:
        return super().__new__(cls, name, (), {})

    def __call__(cls, *args: Any, **kwargs: Any) -> None:
        raise ImportError(
            f"Module {cls.__module__!r} needs to be installed to use the "
            f"{cls.__name__!r} class"
        )

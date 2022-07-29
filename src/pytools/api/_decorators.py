"""
Core implementation of decorators in :mod:`pytools.api`.
"""

import logging
import re
from typing import Any, Callable, Optional, Type, TypeVar

from pytools.api._alltracker import AllTracker

log = logging.getLogger(__name__)


#
# Type variables
#

T = TypeVar("T")
T_Type = TypeVar("T_Type", bound=Type[Any])


__all__ = ["inheritdoc", "subsdoc"]


#
# The AllTracker, used to check that __all__ includes all publicly defined symbols
#
__tracker = AllTracker(globals())


def inheritdoc(*, match: str) -> Callable[[T_Type], T_Type]:
    """
    Class decorator to inherit docstrings of overridden methods.

    Usage:

    .. code-block:: python

      class A:
          def my_function(self) -> None:
          \"""Some documentation\"""
          # …

      @inheritdoc(match="[see superclass]")
      class B(A):
          def my_function(self) -> None:
          \"""[see superclass]\"""
          # …

          def my_other_function(self) -> None:
          \"""This docstring will not be replaced\"""
          # …

    In this example, the docstring of ``my_function`` will be replaced with the
    docstring of the overridden function of the same name, or with ``None`` if no
    overridden function exists, or if that function has no docstring.

    :param match: the parent docstring will be inherited if the current docstring
        is equal to match
    :return: the parameterized decorator
    """

    def _inheritdoc_inner(_cls: T_Type) -> T_Type:
        if not type(_cls):
            raise TypeError(
                f"@{inheritdoc.__name__} can only decorate classes, "
                f"not a {type(_cls).__name__}"
            )

        match_found = False

        if _cls.__doc__ == match:
            _cls.__doc__ = _cls.mro()[1].__doc__
            match_found = True

        for name, member in vars(_cls).items():
            doc = _get_docstring(member)
            if doc == match:
                _set_docstring(member, _get_inherited_docstring(_cls, name))
                match_found = True

        if not match_found:
            log.warning(
                f"{inheritdoc.__name__}:"
                f"no match found for docstring {repr(match)} in class {_cls.__name__}"
            )

        return _cls

    return _inheritdoc_inner


def subsdoc(
    *, pattern: str, replacement: str, using: Optional[Any] = None
) -> Callable[[T], T]:
    """
    Decorator for substituting parts of an object's docstring.

    Matches the given pattern in the docstring, and substitutes it with the given
    replacement string (analogous to :func:`re.sub`).

    :param pattern: a regular expression for the pattern to match
    :param replacement: the replacement for substrings matching the pattern
    :param using: get the docstring from the given object as the basis for the
        substitution
    :return: the parameterized decorator
    """

    def _decorate(_obj: T) -> T:
        origin = _obj if using is None else using
        docstring_original = _get_docstring(origin)
        if not isinstance(docstring_original, str):
            raise ValueError(
                f"docstring of {origin!r} is not a string: {docstring_original!r}"
            )
        docstring_substituted, n = re.subn(pattern, replacement, docstring_original)
        if not n:
            raise ValueError(
                f"subsdoc: pattern {pattern!r} "
                f"not found in docstring {docstring_original!r}"
            )
        _set_docstring(_obj, docstring_substituted)
        return _obj

    if not (isinstance(pattern, str)):
        raise ValueError("arg pattern must be a string")
    if not (isinstance(replacement, str)):
        raise ValueError("arg replacement must be a string")
    return _decorate


__tracker.validate()


def _get_docstring(obj: Any) -> str:
    # get the docstring of the given object

    docstring: str

    try:
        docstring = obj.__func__.__doc__
    except AttributeError:
        docstring = obj.__doc__

    return docstring


def _set_docstring(obj: Any, docstring: Optional[str]) -> None:
    # set the docstring of the given object

    try:
        obj.__func__.__doc__ = docstring
    except AttributeError:
        obj.__doc__ = docstring


def _get_inherited_docstring(child_class: type, attr_name: str) -> Optional[str]:
    # get the docstring for a given attribute from the base class of the given class

    return _get_docstring(getattr(super(child_class, child_class), attr_name, None))

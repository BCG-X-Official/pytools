"""
Core implementation of decorators in :mod:`pytools.api`.
"""

import logging
import re
import textwrap
from collections.abc import Callable
from typing import Any, TypeVar

from pytools.api._alltracker import AllTracker

log = logging.getLogger(__name__)


#
# Type variables
#

T = TypeVar("T")
T_Type = TypeVar("T_Type", bound=type[Any])
T_Method = TypeVar("T_Method", bound=Callable[..., Any])


__all__ = [
    "appenddoc",
    "inheritdoc",
    "subsdoc",
]


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

      @inheritdoc(match=\"""[see superclass]\""")
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

    :param match: the exact text a docstring has to match in order to be replaced
        by the parent's docstring
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
    *, pattern: str, replacement: str, using: Any | None = None
) -> Callable[[T], T]:
    """
    Decorator for substituting parts of an object's docstring.

    Matches the given pattern in the docstring, and substitutes it with the given
    replacement string (analogous to :func:`re.sub`).

    Prior to matching, the docstring is *de-dented*, i.e. the indentation of the
    first line is removed from all lines. This ensures that docstrings that are
    indented to align with the opening triple quotes are matched correctly, regardless
    of the indentation level.

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
        docstring_dedented = textwrap.dedent(docstring_original)
        docstring_substituted, n = re.subn(pattern, replacement, docstring_dedented)
        if not n:
            raise ValueError(
                f"subsdoc: pattern {pattern!r} "
                f"not found in docstring {docstring_dedented!r}"
            )
        _set_docstring(_obj, docstring_substituted)
        return _obj

    if not (isinstance(pattern, str)):
        raise ValueError("arg pattern must be a string")
    if not (isinstance(replacement, str)):
        raise ValueError("arg replacement must be a string")
    return _decorate


def appenddoc(
    *, to: Callable[..., Any], prepend: bool = False
) -> Callable[[T_Method], T_Method]:
    """
    A decorator that appends the docstring of the decorated method to the docstring of
    another method.

    Useful especially if an ``__init__`` method is defined in a base class, and the
    docstring of the derived class's ``__init__`` method defines additional parameters.

    :param to: the other method to append the docstring to
    :param prepend: if True, prepend the docstring of the decorated method to the
        docstring of the other method, otherwise append it
    :return: the actual decorating function
    """

    # the actual decorator
    def _decorator(method: T_Method) -> T_Method:
        # update the method's docstring, then returns the function itself

        # get the docstring of the other method
        other_doc = to.__doc__

        # do not change the docstring if the other method has no docstring
        if not other_doc:
            log.warning(
                f"@appenddoc: {to.__qualname__} has no docstring, nothing to append to "
                f"{method.__qualname__}"
            )
            return method

        # get the docstring of the parent class
        other_doc = textwrap.dedent(other_doc).rstrip()

        # get the docstring of the decorated method
        method_doc = textwrap.dedent(method.__doc__ or "").rstrip()

        # append the parent docstring to the method docstring
        if prepend:
            method.__doc__ = f"{method_doc}\n{other_doc}"
        else:
            method.__doc__ = f"{other_doc}\n{method_doc}"

        return method

    return _decorator


__tracker.validate()

#
# Auxiliary functions
#


def _get_docstring(obj: Any) -> str:
    # get the docstring of the given object

    docstring: str

    try:
        docstring = obj.__func__.__doc__
    except AttributeError:
        docstring = obj.__doc__

    return docstring


def _set_docstring(obj: Any, docstring: str | None) -> None:
    # set the docstring of the given object

    try:
        obj.__func__.__doc__ = docstring
    except AttributeError:
        obj.__doc__ = docstring


def _get_inherited_docstring(child_class: type, attr_name: str) -> str | None:
    # get the docstring for a given attribute from the base class of the given class

    return _get_docstring(getattr(super(child_class, child_class), attr_name, None))

"""
Core implementation of :mod:`pytools.api`.
"""

import logging
import warnings
from collections.abc import Callable, Collection, Iterable
from functools import wraps
from typing import Any, TypeVar, cast, overload

import numpy as np
import pandas as pd

from ._alltracker import AllTracker
from ._decorators import subsdoc

log = logging.getLogger(__name__)

__all__ = [
    "deprecated",
    "deprecation_warning",
    "is_list_like",
    "as_collection",
    "as_list",
    "as_set",
    "as_tuple",
    "validate_element_types",
    "validate_type",
]


#
# Type variables
#

T = TypeVar("T")
T_Collection = TypeVar("T_Collection", list[Any], set[Any], tuple[Any, ...])
T_Iterable = TypeVar("T_Iterable", bound=Iterable[Any])
T_Type = TypeVar("T_Type", bound=type[Any])
T_Callable = TypeVar("T_Callable", bound=Callable[..., Any])

#
# Ensure all symbols introduced below are included in __all__
#

__tracker = AllTracker(globals())


#
# Functions
#


def is_list_like(obj: Any) -> bool:
    """
    Check if the object is list-like.

    Objects that are considered list-like when they implement methods ``len`` and
    ``__getitem__``. These include, for example, lists, tuples, sets, NumPy arrays, and
    Pandas series and indices.

    As an exception, the following types are not considered list-like:

    - :class:`str`
    - :class:`bytes`
    - :class:`~pandas.DataFrame`: inconsistent behaviour of the sequence interface;
      iterating a data frame yields the values of the column index, while the length
      of a data frame is its number of rows
    - :class:`numpy.ndarray` instances with 0 dimensions

    :param obj: The object to check
    :return: ``True`` if ``obj`` has list-like properties, ``False`` otherwise
    """

    return (
        hasattr(obj, "__len__")
        and hasattr(obj, "__getitem__")
        and not isinstance(obj, (str, bytes))
        and not isinstance(obj, pd.DataFrame)
        # exclude zero-dimensional numpy arrays, effectively scalars
        and not (isinstance(obj, np.ndarray) and obj.ndim == 0)
    )


@overload
def as_tuple(
    values: Iterable[T],
    *,
    element_type: type[T] | tuple[type[T], ...] | None = None,
    optional: bool = False,
    arg_name: str | None = None,
) -> tuple[T, ...]:
    """see below for implementation"""
    pass


@overload
def as_tuple(
    values: T | None,
    *,
    element_type: type[T] | tuple[type[T], ...] | None = None,
    optional: bool = False,
    arg_name: str | None = None,
) -> tuple[T, ...]:
    """see below for implementation"""
    pass


def as_tuple(
    values: Iterable[T] | T | None,
    *,
    element_type: type[T] | tuple[type[T], ...] | None = None,
    optional: bool = False,
    arg_name: str | None = None,
) -> tuple[T, ...]:
    """
    Return the given values as a tuple:

    - If arg `values` is a tuple, return arg `values` unchanged.
    - If arg `values` is an iterable other than a tuple, return a tuple of its elements.
    - If arg `values` is not an iterable, return a tuple with the value as its only
      element.

    :param values: one or more elements to return as a tuple
    :param element_type: expected type of the values, or a tuple of alternative types
        of which each value must match at least one
    :param optional: if ``True``, return an empty tuple when ``None`` is passed as
        arg ``values``; otherwise, return a tuple with ``None`` as its only element
        unless this conflicts with arg ``element_type``
    :param arg_name: name of the argument as which the values were passed to a function
        or method; used when composing the :class:`TypeError` message
    :return: the values as a tuple
    :raise TypeError: one or more values did not match the expected type(s)
    """

    return _as_collection(
        values=values,
        collection_type=tuple,
        new_collection_type=tuple,
        element_type=element_type,
        optional=optional,
        arg_name=arg_name,
    )


@overload
def as_list(
    values: Iterable[T],
    *,
    element_type: type[T] | tuple[type[T], ...] | None = None,
    optional: bool = False,
    arg_name: str | None = None,
) -> list[T]:
    """see below for implementation"""
    pass


@overload
def as_list(
    values: T | None,
    *,
    element_type: type[T] | tuple[type[T], ...] | None = None,
    optional: bool = False,
    arg_name: str | None = None,
) -> list[T]:
    """see below for implementation"""
    pass


@subsdoc(pattern="tuple", replacement="list", using=as_tuple)
def as_list(
    values: Iterable[T] | T | None,
    *,
    element_type: type[T] | tuple[type[T], ...] | None = None,
    optional: bool = False,
    arg_name: str | None = None,
) -> list[T]:
    """[will be substituted]"""

    return _as_collection(
        values=values,
        collection_type=list,
        new_collection_type=list,
        element_type=element_type,
        optional=optional,
        arg_name=arg_name,
    )


@overload
def as_set(
    values: Iterable[T],
    *,
    element_type: type[T] | tuple[type[T], ...] | None = None,
    optional: bool = False,
    arg_name: str | None = None,
) -> set[T]:
    """see below for implementation"""
    pass


@overload
def as_set(
    values: T | None,
    *,
    element_type: type[T] | tuple[type[T], ...] | None = None,
    optional: bool = False,
    arg_name: str | None = None,
) -> set[T]:
    """see below for implementation"""
    pass


@subsdoc(pattern="tuple", replacement="set", using=as_tuple)
def as_set(
    values: Iterable[T] | T | None,
    *,
    element_type: type[T] | tuple[type[T], ...] | None = None,
    optional: bool = False,
    arg_name: str | None = None,
) -> set[T]:
    """[will be substituted]"""

    return _as_collection(
        values=values,
        collection_type=set,
        new_collection_type=set,
        element_type=element_type,
        optional=optional,
        arg_name=arg_name,
    )


@overload
def as_collection(
    values: Iterable[T],
    *,
    element_type: type[T] | tuple[type[T], ...] | None = None,
    optional: bool = False,
    arg_name: str | None = None,
) -> Collection[T]:
    """see below for implementation"""
    pass


@overload
def as_collection(
    values: T | None,
    *,
    element_type: type[T] | tuple[type[T], ...] | None = None,
    optional: bool = False,
    arg_name: str | None = None,
) -> Collection[T]:
    """see below for implementation"""
    pass


@subsdoc(pattern="iterable other than a collection", replacement="iterable")
@subsdoc(pattern="return (a|an empty) collection", replacement=r"return \1 tuple")
@subsdoc(
    pattern=r"(given values as a collection)",
    replacement=r"\1, i.e., an iterable container",
)
@subsdoc(pattern="tuple", replacement="collection", using=as_tuple)
def as_collection(
    values: Iterable[T] | T | None,
    *,
    element_type: type[T] | tuple[type[T], ...] | None = None,
    optional: bool = False,
    arg_name: str | None = None,
) -> Collection[T]:
    """[will be substituted]"""
    return _as_collection(
        values=values,
        collection_type=None,
        new_collection_type=cast(type[tuple[Any, ...]], tuple),
        element_type=element_type,
        optional=optional,
        arg_name=arg_name,
    )


def _as_collection(
    values: Iterable[T] | T | None,
    *,
    collection_type: type[Collection[Any]] | None,
    new_collection_type: type[T_Collection],
    element_type: type[T] | tuple[type[T], ...] | None = None,
    optional: bool,
    arg_name: str | None,
) -> T_Collection:
    elements: T_Collection

    if optional and values is None:
        return new_collection_type()
    elif (
        isinstance(values, Iterable)
        and not isinstance(values, str)
        and not isinstance(values, bytes)
    ):
        if isinstance(values, collection_type or Collection):
            # no change needed, values already is the collection we need
            elements = cast(T_Collection, values)
        elif element_type and isinstance(values, element_type):
            # create a single-element collection
            elements = new_collection_type((values,))
        else:
            elements = new_collection_type(values)
    else:
        # create a single-element collection
        elements = new_collection_type((values,))

    if element_type:
        validate_element_types(
            elements,
            expected_type=element_type,
            name=f"arg {arg_name}" if arg_name else None,
        )

    return elements


def validate_type(
    value: T,
    *,
    expected_type: type[T] | tuple[type[T], ...],
    optional: bool = False,
    name: str | None = None,
) -> T:
    """
    Validate that a value implements the expected type.

    :param value: an arbitrary object
    :param expected_type: expected type of the values, or a tuple of alternative types
        of which the value must match at least one
    :param optional: if ``True``, accept ``None`` as a valid value (default: ``False``)
    :param name: optional name of the argument or callable with/to which the value
        was passed; use ``"arg …"`` for arguments, or the name of a callable if
        verifying positional arguments
    :return: the value passed as arg `value`
    :raise TypeError: one or more values did not match the expected type(s)
    """
    if expected_type is object:
        return value

    if optional and value is None:
        return None

    if not isinstance(value, expected_type):
        _raise_type_mismatch(
            name=name,
            expected_type=_as_optional_type(expected_type, is_optional=optional),
            mismatched_type=type(value),
            is_single=True,
        )

    return value


def validate_element_types(
    iterable: T_Iterable,
    *,
    expected_type: type | tuple[type, ...],
    optional: bool = False,
    name: str | None = None,
) -> T_Iterable:
    """
    Validate that all elements in the given iterable implement the expected type.

    :param iterable: an iterable
    :param expected_type: the type to check for
    :param optional: if ``True``, accept ``None`` as valid elements (default: ``False``)
    :param name: optional name of the argument or callable with/to which the elements
        were passed; use ``"arg …"`` for arguments, or the name of a callable if
        verifying positional arguments
    :return: the iterable passed as arg `iterable`
    :raise TypeException: one or more elements of the iterable did not match the
        expected type
    """
    if isinstance(iterable, (str, bytes)):
        raise TypeError(
            f"{name} must not be a string or bytes instance"
            if name
            else "expected an iterable other than a string or bytes instance"
        )

    if expected_type is not object:
        expected_type = _as_optional_type(type_=expected_type, is_optional=optional)

        for element in iterable:
            if not isinstance(element, expected_type):
                _raise_type_mismatch(
                    name=name,
                    expected_type=expected_type,
                    mismatched_type=type(element),
                    is_single=False,
                )

    return iterable


def _as_optional_type(
    type_: type | tuple[type, ...], *, is_optional: bool
) -> type | tuple[type, ...]:
    # if is_optional is True, return a tuple comprising the original (types) and None
    if is_optional:
        if isinstance(type_, tuple):
            return (*type_, type(None))
        else:
            return (type_, type(None))
    else:
        return type_


def _raise_type_mismatch(
    *,
    name: str | None,
    expected_type: type | tuple[type, ...],
    mismatched_type: type,
    is_single: bool,
) -> None:
    if name:
        message_head = f"{name} requires"
    else:
        message_head = "expected"

    if isinstance(expected_type, type):
        expected_type_str = expected_type.__name__
    else:
        expected_type_str = f"one of {{{', '.join(t.__name__ for t in expected_type)}}}"

    instance = "an instance" if is_single else "instances"

    raise TypeError(
        f"{message_head} {instance} of {expected_type_str} "
        f"but got: {mismatched_type.__name__}"
    )


#
# Decorators
#


@overload
def deprecated(function: T_Callable) -> T_Callable:
    """[overload]"""
    pass


@overload
def deprecated(*, message: str) -> Callable[[T_Callable], T_Callable]:
    """[overload]"""
    pass


def deprecated(
    function: T_Callable | None = None, *, message: str | None = None
) -> T_Callable | Callable[[T_Callable], T_Callable]:
    """
    Decorator to mark a function as deprecated.

    Issues a warning when the decorated function is called.

    Usage:

    .. code-block:: python

        @deprecated(message=\
"function f is deprecated and will be removed in the next minor release")
        def f() -> None:
            # ...

    To deprecate classes, apply this decorator to the ``__init__`` method, not to the
    class itself.

    :param function: the function to be decorated (optional)
    :param message: custom message to include when logging the warning (optional)
    :return: the decorated function if arg function was provided; else a decorator
        function that will accept a function as its parameter, and will return the
        decorated function
    """

    def _validate_function(func: T_Callable) -> None:
        if not callable(func):
            raise ValueError("Deprecated object must be callable")

    def _deprecated_inner(func: T_Callable) -> T_Callable:
        _validate_function(func)

        @wraps(func)
        def new_func(*args: Any, **kwargs: Any) -> Any:
            """
            Function wrapper
            """
            message_header = (
                f"Call to deprecated {type(func).__name__} {func.__qualname__}"
            )
            if message is None:
                warnings.warn(message_header, FutureWarning, stacklevel=2)
            else:
                warnings.warn(
                    f"{message_header}: {message}", FutureWarning, stacklevel=2
                )
            return func(*args, **kwargs)

        return cast(T_Callable, new_func)

    if function is None:
        return _deprecated_inner
    elif isinstance(function, str):
        raise ValueError(
            "Deprecation message not provided as a keyword argument. "
            f'Usage: @{deprecated.__name__}(message="...")'
        )
    else:
        _validate_function(function)
        return _deprecated_inner(function)


def deprecation_warning(message: str, stacklevel: int = 1) -> None:
    """
    Issue a deprecation warning.

    :param message: the warning message
    :param stacklevel: stack level relative to caller for emitting the context of the
        warning (default: 1)
    """
    if stacklevel < 1:
        raise ValueError(f"arg stacklevel={stacklevel} must be a positive integer")
    warnings.warn(message, FutureWarning, stacklevel=stacklevel + 1)


__tracker.validate()

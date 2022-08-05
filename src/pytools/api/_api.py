"""
Core implementation of :mod:`pytools.api`.
"""

import logging
import warnings
from functools import wraps
from typing import (
    Any,
    Callable,
    Collection,
    Iterable,
    List,
    Optional,
    Set,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
    overload,
)

import numpy as np
import pandas as pd
import typing_inspect

from ._alltracker import AllTracker
from ._decorators import subsdoc

log = logging.getLogger(__name__)

__all__ = [
    "deprecated",
    "deprecation_warning",
    "get_generic_bases",
    "is_list_like",
    "to_collection",
    "to_list",
    "to_set",
    "to_tuple",
    "validate_element_types",
    "validate_type",
]


#
# Type variables
#

T = TypeVar("T")
T_Collection = TypeVar("T_Collection", List[Any], Set[Any], Tuple[Any, ...])
T_Iterable = TypeVar("T_Iterable", bound=Iterable[Any])
T_Type = TypeVar("T_Type", bound=Type[Any])
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
        # pandas data objects with more than 1 dimension, e.g., data frames
        and not (isinstance(obj, pd.NDFrame) and obj.ndim != 1)
        # exclude zero-dimensional numpy arrays, effectively scalars
        and not (isinstance(obj, np.ndarray) and obj.ndim == 0)
    )


@overload
def to_tuple(
    values: Iterable[T],
    *,
    element_type: Optional[Union[Type[T], Tuple[Type[T], ...]]] = None,
    optional: bool = False,
    arg_name: Optional[str] = None,
) -> Tuple[T, ...]:
    """see below for implementation"""
    pass


@overload
def to_tuple(
    values: Optional[T],
    *,
    element_type: Optional[Union[Type[T], Tuple[Type[T], ...]]] = None,
    optional: bool = False,
    arg_name: Optional[str] = None,
) -> Tuple[T, ...]:
    """see below for implementation"""
    pass


def to_tuple(
    values: Union[Iterable[T], T, None],
    *,
    element_type: Optional[Union[Type[T], Tuple[Type[T], ...]]] = None,
    optional: bool = False,
    arg_name: Optional[str] = None,
) -> Tuple[T, ...]:
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

    return _to_collection(
        values=values,
        collection_type=tuple,
        new_collection_type=tuple,
        element_type=element_type,
        optional=optional,
        arg_name=arg_name,
    )


@overload
def to_list(
    values: Iterable[T],
    *,
    element_type: Optional[Union[Type[T], Tuple[Type[T], ...]]] = None,
    optional: bool = False,
    arg_name: Optional[str] = None,
) -> List[T]:
    """see below for implementation"""
    pass


@overload
def to_list(
    values: Optional[T],
    *,
    element_type: Optional[Union[Type[T], Tuple[Type[T], ...]]] = None,
    optional: bool = False,
    arg_name: Optional[str] = None,
) -> List[T]:
    """see below for implementation"""
    pass


@subsdoc(pattern="tuple", replacement="list", using=to_tuple)
def to_list(
    values: Union[Iterable[T], T, None],
    *,
    element_type: Optional[Union[Type[T], Tuple[Type[T], ...]]] = None,
    optional: bool = False,
    arg_name: Optional[str] = None,
) -> List[T]:
    """[will be substituted]"""

    return _to_collection(
        values=values,
        collection_type=list,
        new_collection_type=list,
        element_type=element_type,
        optional=optional,
        arg_name=arg_name,
    )


@overload
def to_set(
    values: Iterable[T],
    *,
    element_type: Optional[Union[Type[T], Tuple[Type[T], ...]]] = None,
    optional: bool = False,
    arg_name: Optional[str] = None,
) -> Set[T]:
    """see below for implementation"""
    pass


@overload
def to_set(
    values: Optional[T],
    *,
    element_type: Optional[Union[Type[T], Tuple[Type[T], ...]]] = None,
    optional: bool = False,
    arg_name: Optional[str] = None,
) -> Set[T]:
    """see below for implementation"""
    pass


@subsdoc(pattern="tuple", replacement="set", using=to_tuple)
def to_set(
    values: Union[Iterable[T], T, None],
    *,
    element_type: Optional[Union[Type[T], Tuple[Type[T], ...]]] = None,
    optional: bool = False,
    arg_name: Optional[str] = None,
) -> Set[T]:
    """[will be substituted]"""

    return _to_collection(
        values=values,
        collection_type=set,
        new_collection_type=set,
        element_type=element_type,
        optional=optional,
        arg_name=arg_name,
    )


@overload
def to_collection(
    values: Iterable[T],
    *,
    element_type: Optional[Union[Type[T], Tuple[Type[T], ...]]] = None,
    optional: bool = False,
    arg_name: Optional[str] = None,
) -> Collection[T]:
    """see below for implementation"""
    pass


@overload
def to_collection(
    values: Optional[T],
    *,
    element_type: Optional[Union[Type[T], Tuple[Type[T], ...]]] = None,
    optional: bool = False,
    arg_name: Optional[str] = None,
) -> Collection[T]:
    """see below for implementation"""
    pass


@subsdoc(pattern="iterable other than a collection", replacement="iterable")
@subsdoc(pattern="return (a|an empty) collection", replacement=r"return \1 tuple")
@subsdoc(
    pattern=r"(given values as a collection)",
    replacement=r"\1, i.e., an iterable container",
)
@subsdoc(pattern="tuple", replacement="collection", using=to_tuple)
def to_collection(
    values: Union[Iterable[T], T, None],
    *,
    element_type: Optional[Union[Type[T], Tuple[Type[T], ...]]] = None,
    optional: bool = False,
    arg_name: Optional[str] = None,
) -> Collection[T]:
    """[will be substituted]"""
    return _to_collection(
        values=values,
        collection_type=None,
        new_collection_type=cast(Type[Tuple[Any, ...]], tuple),
        element_type=element_type,
        optional=optional,
        arg_name=arg_name,
    )


def _to_collection(
    values: Union[Iterable[T], T, None],
    *,
    collection_type: Optional[Type[Collection[Any]]],
    new_collection_type: Type[T_Collection],
    element_type: Optional[Union[Type[T], Tuple[Type[T], ...]]] = None,
    optional: bool,
    arg_name: Optional[str],
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
    expected_type: Union[Type[T], Tuple[Type[T], ...]],
    optional: bool = False,
    name: Optional[str] = None,
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
    expected_type: Union[type, Tuple[type, ...]],
    optional: bool = False,
    name: Optional[str] = None,
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
    type_: Union[type, Tuple[type, ...]], *, is_optional: bool
) -> Union[type, Tuple[type, ...]]:
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
    name: Optional[str],
    expected_type: Union[type, Tuple[type, ...]],
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


def get_generic_bases(class_: type) -> Tuple[type, ...]:
    """
    Bugfix version of :func:`typing_inspect.get_generic_bases`.

    Prevents getting the generic bases of the parent class if not defined for the given
    class.

    :param class_: class to get the generic bases for
    :return: the generic base classes of the given class
    """
    bases: Tuple[type, ...] = typing_inspect.get_generic_bases(class_)
    if bases is typing_inspect.get_generic_bases(super(class_, class_)):
        return ()
    else:
        return bases


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
    function: Optional[T_Callable] = None, *, message: Optional[str] = None
) -> Union[T_Callable, Callable[[T_Callable], T_Callable]]:
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

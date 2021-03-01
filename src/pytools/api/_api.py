"""
Core implementation of :mod:`pytools.api`.
"""

import logging
import re
import warnings
from functools import wraps
from types import FunctionType
from typing import (
    Any,
    Callable,
    Collection,
    Dict,
    Iterable,
    List,
    Mapping,
    Optional,
    Set,
    Tuple,
    Type,
    TypeVar,
    Union,
)

import numpy as np
import pandas as pd
import typing_inspect

log = logging.getLogger(__name__)

__all__ = [
    "AllTracker",
    "deprecated",
    "deprecation_warning",
    "get_generic_bases",
    "inheritdoc",
    "is_list_like",
    "public_module_prefix",
    "to_list",
    "to_set",
    "to_tuple",
    "update_forward_references",
    "validate_element_types",
    "validate_type",
]

T = TypeVar("T")
T_Collection = TypeVar("T_Collection", bound=Collection)
T_Callable = TypeVar("T_Callable", bound=Callable)
T_Any_Callable = TypeVar("T_Any_Callable", bound=Callable)


class AllTracker:
    """
    Track global, public items defined in a module and validate that all eligible items
    have been included in the ``__all__`` variable.

    Items will be tracked if:

    - their name does not start with an underscore character
    - they are defined after the :class:`.AllTracker` instance has been created

    The underlying idea (and widely used pattern in GAMMA packages) is to define all
    items in one or more private submodules, export all public items using the
    ``__all__`` keyword, and import them into a public package one level up
    (usually the package's ``__init__.py``).

    This ensures a clean namespace in the public package, uncluttered by any imports
    used in the private module.
    """

    def __init__(
        self,
        globals_: Dict[str, Any],
        *,
        public_module: Optional[str] = None,
        update_forward_references: Optional[bool] = True,
    ) -> None:
        """
        :param globals_: the dictionary of global variables returned by calling
            :meth:`._globals` in the current module scope
        :param public_module: full name of the public module that will export the items
            managed by this tracker
        :param update_forward_references: if ``True``, automatically replace all forward
            type references in function annotations with the referenced classes; see
            :func:`.update_forward_references`
            (default: ``True``)

        """
        self._globals = globals_
        self._imported = set(globals_.keys())

        if public_module:
            self.public_module = public_module
        else:
            try:
                module = globals_["__name__"]
            except KeyError:
                raise ValueError(
                    "cannot infer public module: "
                    "arg globals_ does not define module name in __name__"
                )

            self.public_module = public_module_prefix(module)

        self.update_forward_references = update_forward_references

    #: Full name of the public module that will export the items managed by this
    #: tracker.
    public_module: str

    def validate(self) -> None:
        """
        Validate that all eligible items that were defined since the creation of this
        tracker are listed in the ``__all__`` variable.

        :raise RuntimeError: if ``__all__`` is not as expected
        """
        all_expected = self.get_tracked()

        globals_ = self._globals

        if set(globals_.get("__all__", [])) != set(all_expected):
            raise RuntimeError(
                "missing or unexpected all declaration, "
                f"expected:\n__all__ = {all_expected}"
            )

        public_module = self.public_module

        for name in all_expected:
            obj = globals_[name]

            # set public module field
            obj.__publicmodule__ = public_module

            if self.update_forward_references:
                # update forward references in annotations
                update_forward_references(obj, globals_=globals_)

    def get_tracked(self) -> List[str]:
        """
        List the names of all locally tracked, public items.

        :return: the list of object names, sorted alphabetically
        """
        return sorted(filter(self._is_eligible, self._globals))

    def is_tracked(self, name: str, item: Any) -> bool:
        """
        Check if the given item is tracked by this tracker under the given name.

        :param name: the name of the item in the tracker's global namespace
        :param item: the item referred to by the name
        :return: ``True`` if the given item is tracked by this tracker under the given
            name; ``False`` otherwise
        """
        try:
            return self._globals[name] is item and self._is_eligible(name)
        except KeyError:
            return False

    def _is_eligible(self, name: str) -> bool:
        # check if the given item is eligible for tracking by this tracker
        return not (name.startswith("_") or name in self._imported)

    def __getitem__(self, name: str) -> Any:
        # get a tracked item by name

        item = self._globals[name]
        if self._is_eligible(name=name):
            return item
        else:
            raise KeyError(name)


# regular expression to extract the public prefix of a private module
# this is the module path up to the first submodule with a leading underscore
__RE_PUBLIC_MODULE = re.compile(
    # start of match group for the public part of the module path
    r"("
    # first module component must not start with '_')
    r"(?:[a-zA-Z]\w+)"
    # then as many path components as can be matched non-greedily …)
    r"(?:\.\w+)*?"
    # but when we hit the first private path component, we stop matching the
    # public part of the path …
    r")"
    # … and match the rest as the private path
    r"(?:\._\w*(?:\.\w+)*)?"
)


def public_module_prefix(module_name: str) -> str:
    """
    Get the public prefix of the given module name.

    A module name is composed of one or more identifiers, separated by ``.`` operators.
    The public prefix is the module name including all identifiers up to, and excluding,
    the first identifier starting with an underscore character (``_``) .
    If there is no such identifier, then the public prefix is the same as the full
    module name.
    If the first identifier starts with a ``_``, then the public prefix is not defined.

    For example:

    - the public module prefix of ``a.b._c.d._e`` is ``a.b``
    - the public module prefix of ``a.b`` is ``a.b``
    - the public module prefix of ``_a.b.c`` is undefined

    :param module_name: the module name for which to get the public prefix
    :return: the public prefix
    :raise ValueError: the public prefix is undefined
    """
    match = __RE_PUBLIC_MODULE.fullmatch(module_name)
    if not match:
        raise ValueError(f"cannot infer public module path from module {module_name}")
    return match[1]


#
# Ensure all symbols introduced below are included in __all__
#

__tracker = AllTracker(globals())
# we forget that class AllTracker itself is already defined, because we want to include
# it in the __all__ statement
# noinspection PyProtectedMember
__tracker._imported.remove(AllTracker.__name__)
# noinspection PyProtectedMember
__tracker._imported.remove(public_module_prefix.__name__)

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
    - :class:`pandas.DataFrame`: inconsistent behaviour of the sequence interface;
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


def to_tuple(
    values: Union[Iterable[T], T],
    *,
    element_type: Optional[Type[T]] = None,
    arg_name: Optional[str] = None,
) -> Tuple[T, ...]:
    """
    Return the given values as a tuple.

    - if arg `values` is a tuple, return arg `values` unchanged
    - if arg `values` is an iterable other than a tuple, return a list of its elements
    - if arg `values` is not an iterable, return a tuple with the value as its only
      element

    :param values: one or more elements to return as a tuple
    :param element_type: expected type of the values; raise a ``TypeException`` if one
        or more values do not implement this type
    :param arg_name: name of the argument as which the values were passed to a function
        or method; used when composing the ``TypeException`` message
    :return: the values as a tuple
    :raise TypeException: one or more values did not match the expected type
    """

    return _to_collection(
        values=values,
        collection_type=tuple,
        element_type=element_type,
        arg_name=arg_name,
    )


def to_list(
    values: Union[Iterable[T], T],
    *,
    element_type: Optional[Type[T]] = None,
    arg_name: Optional[str] = None,
) -> List[T]:
    """
    Return the given values as a list.

    - if arg `values` is a list, return arg `values` unchanged
    - if arg `values` is an iterable other than a list, return a list of its elements
    - if arg `values` is not an iterable, return a list with the value as its only
      element

    :param values: one or more elements to return as a list
    :param element_type: expected type of the values; raise a ``TypeException`` if one
        or more values do not implement this type
    :param arg_name: name of the argument as which the values were passed to a function
        or method; used when composing the ``TypeException`` message
    :return: the values as a list
    :raise TypeException: one or more values did not match the expected type
    """

    return _to_collection(
        values=values,
        collection_type=list,
        element_type=element_type,
        arg_name=arg_name,
    )


def to_set(
    values: Union[Iterable[T], T],
    *,
    element_type: Optional[Type[T]] = None,
    arg_name: Optional[str] = None,
) -> Set[T]:
    """
    Return the given values as a set.

    - if arg `values` is a set, return arg `values` unchanged
    - if arg `values` is an iterable other than a set, return a set of its elements
    - if arg `values` is not an iterable, return a list with the value as its only
      element

    :param values: one or more elements to return as a set
    :param element_type: expected type of the values; raise a ``TypeException`` if one
        or more values do not implement this type
    :param arg_name: name of the argument as which the values were passed to a function
        or method; used when composing the ``TypeException`` message
    :return: the values as a set
    :raise TypeException: one or more values did not match the expected type
    """

    return _to_collection(
        values=values, collection_type=set, element_type=element_type, arg_name=arg_name
    )


def _to_collection(
    values: Union[T, Iterable[T]],
    *,
    collection_type: Type[T_Collection],
    element_type: Optional[Type[T]],
    arg_name: Optional[str] = None,
) -> T_Collection:

    elements: T_Collection

    if (
        isinstance(values, Iterable)
        and not isinstance(values, str)
        and not isinstance(values, bytes)
    ):
        if isinstance(values, collection_type):
            # no change needed, values already is the collection we need
            elements = values
        elif element_type and isinstance(values, element_type):
            # create a single-element collection
            elements = collection_type((values,))
        else:
            elements = collection_type(values)
    else:
        # create a single-element collection
        elements = collection_type((values,))

    if element_type:
        validate_element_types(
            elements, expected_type=element_type, name=f"arg {arg_name}"
        )

    return elements


def validate_type(
    value: T,
    *,
    expected_type: Type[T],
    optional: bool = False,
    name: Optional[str] = None,
) -> None:
    """
    Validate that a value implements the expected type.

    :param value: an arbitrary object
    :param expected_type: the type to check for
    :param optional: if ``True``, accept ``None`` as a valid value (default: ``False``)
    :param name: optional name of the argument or callable with/to which the value
        was passed; use ``"arg …"`` for arguments, or the name of a callable if
        verifying positional arguments
    :raise TypeException: the value did not match the expected type
    """
    if expected_type == object:
        return

    if optional and value is None:
        return

    if not isinstance(value, expected_type):
        if name:
            message_head = f"{name} requires"
        else:
            message_head = "expected"
        raise TypeError(
            f"{message_head} instance of {expected_type.__name__} "
            f"but got a {type(value).__name__}"
        )


def validate_element_types(
    iterable: Iterable[T], *, expected_type: Type[T], name: Optional[str] = None
) -> None:
    """
    Validate that all elements in the given iterable implement the expected type.

    :param iterable: an iterable
    :param expected_type: the type to check for
    :param name: optional name of the argument or callable with/to which the elements
        were passed; use ``"arg …"`` for arguments, or the name of a callable if
        verifying positional arguments
    :raise TypeException: one or more elements of the iterable did not match the
        expected type
    """
    if expected_type == object:
        return

    for element in iterable:
        if not isinstance(element, expected_type):
            if name:
                message_head = f"{name} requires"
            else:
                message_head = "expected"
            raise TypeError(
                f"{message_head} instances of {expected_type.__name__} "
                f"but got a {type(element).__name__}"
            )


def get_generic_bases(class_: type) -> Tuple[type, ...]:
    """
    Bugfix version of :func:`typing_inspect.get_generic_bases`.

    Prevents getting the generic bases of the parent class if not defined for the given
    class.

    :param class_: class to get the generic bases for
    :return: the generic base classes of the given class
    """
    bases = typing_inspect.get_generic_bases(class_)
    if bases is typing_inspect.get_generic_bases(super(class_, class_)):
        return ()
    else:
        return bases


#
# Decorators
#


def deprecated(
    function: Optional[T_Callable] = None, *, message: Optional[str] = None
) -> Union[T_Callable, Callable[[T_Any_Callable], T_Any_Callable]]:
    """
    Decorator to mark a function as deprecated.

    Logs a warning when the decorated function is called.

    Usage:

    .. codeblock: python

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

    def _deprecated_inner(func: T_Callable) -> T_Callable:
        @wraps(func)
        def new_func(*args, **kwargs: Any) -> Any:
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

        return new_func

    if function is None:
        return _deprecated_inner
    elif callable(function):
        return _deprecated_inner(function)
    elif isinstance(function, str):
        raise ValueError(
            "Deprecation message not provided as a keyword argument. "
            f'Usage: @{deprecated.__name__}(message="...")'
        )
    else:
        raise ValueError("Deprecated object must be callable")


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


# noinspection PyIncorrectDocstring
def inheritdoc(
    class_: type = None, *, match: str
) -> Union[type, Callable[[type], type]]:
    """
    Decorator to inherit docstrings of overridden methods.

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

    In this example, the docstring of the ``my_function`` will be replaced with the
    docstring of the overridden function of the same name, or with ``None`` if no
    overridden function exists, or if that function has no docstring.

    :param class_: the decorated class
    :param match: the parent docstring will be inherited if the current docstring
        is equal to match
    :return: the decorated class, or the parameterized decorator if arg ``class_``
        has not been provided
    """

    def _inheritdoc_inner(_cls: type) -> type:
        if not type(_cls):
            _raise_type_error(_cls)

        match_found = False

        def _get_docstring(m: Any) -> str:
            try:
                return m.__func__.__doc__
            except AttributeError:
                return m.__doc__

        def _set_docstring(m: Any, d: str) -> None:
            try:
                m.__func__.__doc__ = d
            except AttributeError:
                m.__doc__ = d

        for name, member in vars(_cls).items():
            doc = _get_docstring(m=member)
            if doc == match:
                _set_docstring(
                    m=member,
                    d=_get_docstring(m=getattr(super(_cls, _cls), name, None)),
                )
                match_found = True

        if not match_found:
            log.warning(
                f"{inheritdoc.__name__}:"
                f"no match found for docstring {repr(match)} in class {_cls.__name__}"
            )

        return _cls

    def _raise_type_error(_cls: type) -> None:
        raise TypeError(
            f"@{inheritdoc.__name__} can only decorate classes, "
            f"not a {type(_cls).__name__}"
        )

    if class_ is None:
        return _inheritdoc_inner
    elif type(class_):
        return _inheritdoc_inner(class_)
    elif isinstance(class_, str):
        raise ValueError(
            "arg match not provided as a keyword argument. "
            f'Usage: @{inheritdoc.__name__}(match="...")'
        )
    else:
        _raise_type_error(class_)


def update_forward_references(
    obj: Union[type, FunctionType], *, globals_: Mapping[str, Any]
) -> None:
    """
    Replace all forward references with their referenced classes.

    :param obj: a function or class
    :param globals_: a global namespace to search the referenced classes in
    """

    def _update(obj: Any) -> None:
        if isinstance(obj, type):
            for member in vars(obj).values():
                _update(member)
        elif isinstance(obj, FunctionType):
            annotations = obj.__annotations__
            if annotations:
                for arg, cls in annotations.items():
                    if isinstance(cls, str):
                        real_cls = globals_[cls]
                        if isinstance(real_cls, type):
                            annotations[arg] = real_cls

    _update(obj)


__tracker.validate()

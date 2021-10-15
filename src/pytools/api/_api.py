"""
Core implementation of :mod:`pytools.api`.
"""

import logging
import re
import warnings
from collections import deque
from functools import wraps
from types import FunctionType
from typing import (
    Any,
    Callable,
    Collection,
    Deque,
    Dict,
    Iterable,
    List,
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
    "subsdoc",
    "to_collection",
    "to_list",
    "to_set",
    "to_tuple",
    "update_forward_references",
    "validate_element_types",
    "validate_type",
]


#
# Type variables
#

T = TypeVar("T")
T_Collection = TypeVar("T_Collection", bound=Collection)
T_Callable = TypeVar("T_Callable", bound=Callable)
T_Iterable = TypeVar("T_Iterable", bound=Iterable)
T_Type = TypeVar("T_Type", bound=type)


#
# The AllTracker, used to check that __all__ includes all publicly defined symbols
#


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

    The tracker also performs additional checks to validate the eligibility of
    definitions for being exported:

    - constant definitions should not be exported, as this will pose difficulties
      with Sphinx documentation and - from a design perspective - provides less context
      than defining constants inside classes
    - definitions exported from other modules should not be re-exported by the importing
      module

    These validation checks can be overridden if required in special cases.
    """

    #: if ``True``, automatically replace all forward
    #: type references in function annotations with the referenced classes;
    #: see :func:`.update_forward_references`
    update_forward_references: bool

    #: if ``True``, allow exporting public global constants in ``__all__``;
    #: these typically have no ``__module__`` or ``__doc__`` attributes and will
    #: not be properly rendered in generated documentation
    allow_global_constants: bool

    #: if ``True``, allow exporting definitions in ``__all__`` even if they have been
    #: imported from another module
    allow_imported_definitions: bool

    # noinspection PyShadowingNames
    def __init__(
        self,
        globals_: Dict[str, Any],
        *,
        public_module: Optional[str] = None,
        update_forward_references: bool = True,
        allow_global_constants: bool = False,
        allow_imported_definitions: bool = False,
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
        :param allow_global_constants: if ``True``, allow exporting public global
            constants in ``__all__``;
            these typically have no ``__module__`` or ``__doc__`` attributes and will
            not be properly rendered in generated documentation (default: ``False``)
        :param allow_imported_definitions: if ``True``, allow exporting definitions in
            ``__all__`` even if they have been imported from another module
            (default: ``False``)
        """
        self._globals = globals_
        self._imported = set(globals_.keys())

        try:
            self._module = module = globals_["__name__"]
        except KeyError:
            raise ValueError("arg globals_ does not define module name in __name__")

        if not public_module:
            public_module = public_module_prefix(module)

        self.public_module = globals_["__publicmodule__"] = public_module

        self.update_forward_references = update_forward_references
        self.allow_global_constants = allow_global_constants
        self.allow_imported_definitions = allow_imported_definitions

    #: Full name of the public module that will export the items managed by this
    #: tracker.
    public_module: str

    def validate(self) -> None:
        """
        Validate that all eligible items that were defined since the creation of this
        tracker are listed in the ``__all__`` variable.

        :raise AssertionError: if ``__all__`` is not as expected, or if one or more
            definitions do not meet the required criteria to be exported (
        """
        all_expected = self.get_tracked()

        globals_ = self._globals

        if set(globals_.get("__all__", [])) != set(all_expected):
            raise AssertionError(
                "missing or unexpected all declaration, "
                f"expected:\n__all__ = {all_expected}"
            )

        def _qualname(_obj: Any) -> str:
            try:
                return _obj.__qualname__
            except AttributeError:
                try:
                    return _obj.__name__
                except AttributeError:
                    return repr(_obj)

        module = self._module
        public_module = self.public_module
        allow_global_constants = self.allow_global_constants
        forbid_imported_definitions = not self.allow_imported_definitions

        for name in all_expected:
            obj = globals_[name]

            # check that the object was defined locally
            try:
                obj_module = obj.__module__
            except AttributeError:
                if allow_global_constants:
                    obj_module = None
                else:
                    raise AssertionError(
                        f"exporting a global constant is not permitted: {obj!r}"
                    )

            if forbid_imported_definitions and obj_module and obj_module != module:
                raise AttributeError(
                    f"{_qualname(obj)} is exported by module {module} "
                    f"but defined in module {obj_module}"
                )

            # set public module field
            try:
                obj.__publicmodule__ = public_module
            except AttributeError:
                # objects without a __dict__ will not permit setting the public module
                pass

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
# noinspection RegExpUnnecessaryNonCapturingGroup
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
    element_type: Optional[Union[Type[T], Tuple[Type, ...]]] = None,
    arg_name: Optional[str] = None,
) -> Tuple[T, ...]:
    """
    Return the given values as a tuple.

    - if arg `values` is a tuple, return arg `values` unchanged
    - if arg `values` is an iterable other than a tuple, return a list of its elements
    - if arg `values` is not an iterable, return a tuple with the value as its only
      element

    :param values: one or more elements to return as a tuple
    :param element_type: expected type of the values, or a tuple of alternative types
        of which each value must match at least one
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
        arg_name=arg_name,
    )


def to_list(
    values: Union[Iterable[T], T],
    *,
    element_type: Optional[Union[Type[T], Tuple[Type, ...]]] = None,
    arg_name: Optional[str] = None,
) -> List[T]:
    """
    Return the given values as a list.

    - if arg `values` is a list, return arg `values` unchanged
    - if arg `values` is an iterable other than a list, return a list of its elements
    - if arg `values` is not an iterable, return a list with the value as its only
      element

    :param values: one or more elements to return as a list
    :param element_type: expected type of the values, or a tuple of alternative types
        of which each value must match at least one
    :param arg_name: name of the argument as which the values were passed to a function
        or method; used when composing the :class:`TypeError` message
    :return: the values as a list
    :raise TypeError: one or more values did not match the expected type(s)
    """

    return _to_collection(
        values=values,
        collection_type=list,
        new_collection_type=list,
        element_type=element_type,
        arg_name=arg_name,
    )


def to_set(
    values: Union[Iterable[T], T],
    *,
    element_type: Optional[Union[Type[T], Tuple[Type, ...]]] = None,
    arg_name: Optional[str] = None,
) -> Set[T]:
    """
    Return the given values as a set.

    - if arg `values` is a set, return arg `values` unchanged
    - if arg `values` is an iterable other than a set, return a set of its elements
    - if arg `values` is not an iterable, return a set with the value as its only
      element

    :param values: one or more elements to return as a set
    :param element_type: expected type of the values, or a tuple of alternative types
        of which each value must match at least one
    :param arg_name: name of the argument as which the values were passed to a function
        or method; used when composing the :class:`TypeError` message
    :return: the values as a set
    :raise TypeError: one or more values did not match the expected type(s)
    """

    return _to_collection(
        values=values,
        collection_type=set,
        new_collection_type=set,
        element_type=element_type,
        arg_name=arg_name,
    )


def to_collection(
    values: Union[Iterable[T], T],
    *,
    element_type: Optional[Union[Type[T], Tuple[Type, ...]]] = None,
    arg_name: Optional[str] = None,
) -> Collection[T]:
    """
    Return the given values as a collection, i.e., an iterable container.

    - if arg `values` is a collection, return arg `values` unchanged
    - if arg `values` is an iterator, return a tuple with its elements
    - if arg `values` is not an iterable, return a tuple with the value as its only
      element

    :param values: one or more elements to return as a collection
    :param element_type: expected type of the values, or a tuple of alternative types
        of which each value must match at least one
    :param arg_name: name of the argument as which the values were passed to a function
        or method; used when composing the :class:`TypeError` message
    :return: the values as a collection
    :raise TypeError: one or more values did not match the expected type(s)
    """
    return _to_collection(
        values=values,
        collection_type=None,
        new_collection_type=tuple,
        element_type=element_type,
        arg_name=arg_name,
    )


def _to_collection(
    values: Union[T, Iterable[T]],
    *,
    collection_type: Optional[Type[Collection]],
    new_collection_type: Type[T_Collection],
    element_type: Optional[Union[Type[T], Tuple[Type, ...]]],
    arg_name: Optional[str],
) -> T_Collection:

    elements: T_Collection

    if (
        isinstance(values, Iterable)
        and not isinstance(values, str)
        and not isinstance(values, bytes)
    ):
        if isinstance(values, collection_type or Collection):
            # no change needed, values already is the collection we need
            elements = values
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
            elements, expected_type=element_type, name=f"arg {arg_name}"
        )

    return elements


def validate_type(
    value: T,
    *,
    expected_type: Union[Type[T], Tuple[Type, ...]],
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

    if isinstance(value, expected_type):
        return value
    else:
        if name:
            message_head = f"{name} requires"
        else:
            message_head = "expected"

        if not isinstance(expected_type, tuple):
            expected_type = (expected_type,)
        if optional:
            expected_type = (*expected_type, type(None))
        expected_type_str = " or ".join(t.__name__ for t in expected_type)

        observed_type = type(value).__name__

        # noinspection SpellCheckingInspection
        det = "an" if observed_type[0] in "aeiou" else "a"

        raise TypeError(
            f"{message_head} an instance of {expected_type_str} "
            f"but got {det} {observed_type}"
        )


def validate_element_types(
    iterable: T_Iterable,
    *,
    expected_type: Union[Type, Tuple[Type, ...]],
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
    if expected_type is not object:
        if optional:
            expected_type = (
                (*expected_type, type(None))
                if isinstance(expected_type, tuple)
                else (expected_type, type(None))
            )
        for element in iterable:
            if not isinstance(element, expected_type):
                if name:
                    message_head = f"{name} requires"
                else:
                    message_head = "expected"

                if isinstance(expected_type, type):
                    expected_type_str = expected_type.__name__
                else:
                    expected_type_str = (
                        f"one of {{{', '.join(t.__name__ for t in expected_type)}}}"
                    )
                raise TypeError(
                    f"{message_head} instances of {expected_type_str} "
                    f"but got a {type(element).__name__}"
                )

    return iterable


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
) -> Union[T_Callable, Callable[[T_Callable], T_Callable]]:
    """
    Decorator to mark a function as deprecated.

    Logs a warning when the decorated function is called.

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

    def _validate_function(func: Callable):
        if not callable(func):
            raise ValueError("Deprecated object must be callable")

    def _deprecated_inner(func: T_Callable) -> T_Callable:
        _validate_function(func)

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


def inheritdoc(*, match: str) -> Callable[[T_Type], T_Type]:
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

    :param match: the parent docstring will be inherited if the current docstring
        is equal to match
    :return: the parameterized decorator
    """

    def _inheritdoc_inner(_cls: type) -> type:
        if not type(_cls):
            raise TypeError(
                f"@{inheritdoc.__name__} can only decorate classes, "
                f"not a {type(_cls).__name__}"
            )

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

        if _cls.__doc__ == match:
            _cls.__doc__ = _cls.mro()[1].__doc__
            match_found = True

        for name, member in vars(_cls).items():
            doc = _get_docstring(member)
            if doc == match:
                _set_docstring(
                    member,
                    _get_docstring(getattr(super(_cls, _cls), name, None)),
                )
                match_found = True

        if not match_found:
            log.warning(
                f"{inheritdoc.__name__}:"
                f"no match found for docstring {repr(match)} in class {_cls.__name__}"
            )

        return _cls

    return _inheritdoc_inner


def subsdoc(*, pattern: str, replacement: str) -> Callable[[T], T]:
    """
    Decorator that matches a given pattern in the decorated object's docstring, and
    substitutes it with the given replacement string (see :func:`re.sub`)

    :param pattern: a regular expression for the pattern to match
    :param replacement: the replacement for substrings matching the pattern
    :return: the parameterized decorator
    """

    def _decorate(_obj: T) -> T:
        if not isinstance(_obj.__doc__, str):
            raise ValueError(f"docstring of {_obj!r} is not a string: {_obj.__doc__!r}")
        _obj.__doc__, n = re.subn(pattern, replacement, _obj.__doc__)
        if not n:
            raise ValueError(
                f"subsdoc: pattern {pattern!r} not found in docstring {_obj.__doc__!r}"
            )
        return _obj

    if not (isinstance(pattern, str)):
        raise ValueError("arg pattern must be a string")
    if not (isinstance(replacement, str)):
        raise ValueError("arg replacement must be a string")
    return _decorate


def update_forward_references(
    obj: Union[type, FunctionType], *, globals_: Dict[str, Any]
) -> None:
    """
    Replace all forward references with their referenced classes.

    :param obj: a function or class
    :param globals_: a global namespace to search the referenced classes in
    """

    def _parse_cls_with_generic_arguments(cls: str) -> type:
        def _parse(cls_tokens: Deque[str]) -> type:
            real_cls = eval(cls_tokens.popleft(), globals_)
            if cls_tokens and cls_tokens[0] not in ",]":
                real_args: List[type] = list()
                sep = cls_tokens.popleft()
                if sep != "[":
                    raise TypeError(
                        f"invalid separator for generic type arguments: {sep}"
                    )
                while True:
                    real_args.append(_parse(cls_tokens))
                    sep = cls_tokens.popleft()
                    if sep == "]":
                        break
                    elif sep != ",":
                        raise TypeError(
                            f"invalid separator for generic type arguments: {sep}"
                        )
                return real_cls.__getitem__(tuple(real_args))
            else:
                return real_cls

        try:
            return _parse(deque(map(str.strip, re.split(r"([,\[\]])", cls))))
        except TypeError as e:
            raise TypeError(f"invalid type syntax in forward reference: {cls}") from e

    # keep track of classes we already visited to prevent infinite recursion
    visited: Set[type] = set()

    def _update(_obj: Any) -> None:
        if isinstance(_obj, type):
            if _obj not in visited:
                visited.add(_obj)
                for member in vars(_obj).values():
                    _update(member)
                _update_annotations(getattr(_obj, "__annotations__", None))

        elif isinstance(_obj, FunctionType):
            _update_annotations(_obj.__annotations__)

    def _update_annotations(annotations: Optional[Dict[str, Any]]):
        if annotations:
            for arg, cls in annotations.items():
                if isinstance(cls, str):
                    annotations[arg] = _parse_cls_with_generic_arguments(cls)

    _update(obj)


__tracker.validate()

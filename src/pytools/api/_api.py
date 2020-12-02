"""
Core implementation of :mod:`pytools.api`
"""

import inspect
import logging
import operator
import warnings
from abc import ABCMeta, abstractmethod
from functools import reduce, wraps
from typing import (
    Any,
    Callable,
    Collection,
    Dict,
    Iterable,
    Iterator,
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
    "is_list_like",
    "to_tuple",
    "to_list",
    "to_set",
    "validate_type",
    "validate_element_types",
    "get_generic_bases",
    "deprecated",
    "deprecation_warning",
    "inheritdoc",
    "ImportGroup",
]

T = TypeVar("T")
T_Collection = TypeVar("T_Collection", bound=Collection)


class AllTracker:
    """
    Track global, public items defined in a module and validate that all eligible items
    have been included in the ``__all__`` variable.

    Items will be tracked if:

    - their name does not start with an underscore character
    - they are defined after the :class:`.AllTracker` instance has been created
    - they are not an :class:`.ImportGroup` instance

    The underlying idea (and widely used pattern in GAMMA packages) is to define all
    items in a private module, export all public items using the ``__all__`` keyword,
    and import them from a public package (usually the package's ``__init__.py``).

    This ensures a clean namespace in the public package, uncluttered by any imports
    used in the private module.

    It can make sense to expose the items of one private module across several public
    modules.
    To this end, tracked items can be assigned to different import groups using a group
    decorator, and each group can be used to validate that the correct subset of items
    has been imported by the respective public modules (see :meth:`.add_group`)
    """

    def __init__(self, globals_: Dict[str, Any]):
        """
        :param globals_: the dictionary of global variables returned by calling
            :meth:`._globals` in the current module scope
        """
        self._globals = globals_
        self._imported = set(globals_.keys())
        self._groups: List["ImportGroup"] = []
        self._default_group: Optional[_DefaultGroup] = None

    @property
    def default_group(self) -> "ImportGroup":
        """
        The default group containing all ungrouped items managed by this tracker
        """
        # we must create the default group here because it is not yet defined
        # by the time we instantiate the AllTracker further down in this module
        if not self._default_group:
            self._default_group = _DefaultGroup(tracker=self)
        return self._default_group

    @property
    def groups(self) -> Iterator["ImportGroup"]:
        """
        The import groups managed by this tracker
        """
        return iter(self._groups)

    def validate(self) -> None:
        """
        Validate that all eligible items that were defined since the creation of this
        tracker are listed in the ``__all__`` variable.

        :raise RuntimeError: if ``__all__`` is not as expected
        """
        all_expected = self.get_tracked()

        if set(self._globals.get("__all__", [])) != set(all_expected):
            raise RuntimeError(
                f"unexpected all declaration, expected:\n__all__ = {all_expected}"
            )

    def add_group(self) -> "ImportGroup":
        """
        Add a new import group to this tracker.

        Import group objects can be used as decorators to add items to the group
        (usually classes or functions).
        See :class:`ImportGroup` for more details.

        Import group objects are excluded from tracking, even if they are assigned
        after creating the tracker.

        Therefore it is perfectly fine to write

        .. code:: python
            __tracker = AllTracker()
            base = __tracker.add_group()

        without adding ``base`` to ``__all__``.

        :return: the newly added import group
        """
        group = _ImportGroupDecorator(tracker=self)
        self._groups.append(group)
        return group

    def get_tracked(self) -> List[str]:
        """
        List the names of all locally tracked, public items.

        :return: the list of object names
        """

        return [
            name
            for name, item in self._globals.items()
            if self._is_eligible(name=name, item=item)
        ]

    def is_tracked(self, name: str, item: Any) -> bool:
        """
        Check if the given item is tracked by this tracker under the given name.

        :param name: the name of the item in the tracker's global namespace
        :param item: the item referred to by the name
        """
        try:
            return self._globals[name] is item and self._is_eligible(name, item)
        except KeyError:
            return False

    def _is_eligible(self, name: str, item: Any) -> bool:
        # check if the given item is eligible for tracking by this tracker
        return not (
            name.startswith("_")
            or name in self._imported
            or isinstance(item, ImportGroup)
        )

    def __getitem__(self, name: str) -> Any:
        # get a tracked item by name

        item = self._globals[name]
        if self._is_eligible(name=name, item=item):
            return item
        else:
            raise KeyError(name)


#
# Ensure all symbols introduced below are included in __all__
#

__tracker = AllTracker(globals())
# we forget that class AllTracker itself is already defined, because we want to include
# it in the __all__ statement
# noinspection PyProtectedMember
__tracker._imported.remove(AllTracker.__name__)

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
    - :class:`pandas.DataFrame`: inconsistent behaviour of the sequence interface; \
        iterating a data frame yields the values of the column index, while the length \
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
            f"but got a {expected_type(value).__name__}"
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


def get_generic_bases(cls: type) -> Tuple[type, ...]:
    """
    Bugfix version of :func:`typing_inspect.get_generic_bases`.

    Prevents getting the generic bases of the parent class if not defined for the given
    class.

    :param cls: class to get the generic bases for
    :return: the generic base classes of the given class
    """
    bases = typing_inspect.get_generic_bases(cls)
    if bases is typing_inspect.get_generic_bases(super(cls, cls)):
        return ()
    else:
        return bases


#
# Decorators
#


def deprecated(function: Callable = None, *, message: Optional[str] = None):
    """
    Decorator to mark a function as deprecated.

    Logs a warning when the decorated function is called.

    To deprecate classes, apply this decorator to the ``__init__`` method, not to the
    class itself.

    :param function: the function to be decorated
    :param message: custom message to include when logging the warning (optional)
    """

    def _deprecated_inner(func: callable) -> callable:
        @wraps(func)
        def new_func(*args, **kwargs) -> Any:
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
    :return:
    """
    if stacklevel < 1:
        raise ValueError(f"arg stacklevel={stacklevel} must be a positive integer")
    warnings.warn(message, FutureWarning, stacklevel=stacklevel + 1)


# noinspection PyIncorrectDocstring
def inheritdoc(cls: type = None, *, match: str) -> Union[type, Callable[[type], type]]:
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

    :param match: the parent docstring will be inherited if the current docstring \
        is equal to match
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
                parents = inspect.getmro(_cls)[1:]
                _set_docstring(
                    m=member,
                    d=(
                        _get_docstring(m=getattr(parents[0], name, None))
                        if parents
                        else None
                    ),
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

    if cls is None:
        return _inheritdoc_inner
    elif type(cls):
        return _inheritdoc_inner(cls)
    elif isinstance(cls, str):
        raise ValueError(
            "arg match not provided as a keyword argument. "
            f'Usage: @{inheritdoc.__name__}(match="...")'
        )
    else:
        _raise_type_error(cls)


#
# Import group decorator
#


class ImportGroup(metaclass=ABCMeta):
    """
    A group of definitions designated to be jointly imported from their original module.

    The :class:`ImportGroup` object can be used as a decorator (usually for classes or
    functions) to include newly defined items in the group.

    Supports the ``in`` operator to check if an arbitraty object is contained in this
    group.
    """

    @property
    @abstractmethod
    def tracker(self) -> AllTracker:
        """
        The tracker managing the namespace associated with the items in this group
        """
        pass

    @abstractmethod
    def get_members(self) -> Dict[int, Any]:
        """
        Get all members of this group as a mapping of hash ids to the actual items.

        :return: the items in this group
        """

    def validate_imported(self, globals_: Mapping[str, Any]) -> None:
        """
        Check that all items in this group have been imported to the caller's
        global namespace, and that no other item has been imported from the module
        associated with this group.

        :param globals_: the dictionary returned by ``globals()`` in the caller's
            namespace
        :raises ImportError: if not all members of this group are present in the
           given _globals dictionary
        """
        imported_objects: Dict[int, Any] = {
            id(item): item
            for name, item in globals_.items()
            if self.tracker.is_tracked(name=name, item=item)
        }
        expected_objects: Dict[int, Any] = self.get_members()

        def _check_overlap(
            minimal_set: Dict[int, Any], comparison_set: Dict[int, Any], message: str
        ) -> None:
            # ensure that the comparison set includes all elements of the minimal set
            deviation = minimal_set.keys() - comparison_set.keys()
            if deviation:
                names = (minimal_set[id_].__name__ for id_ in deviation)
                raise ImportError(f'{message}: {", ".join(names)}')

        _check_overlap(
            minimal_set=expected_objects,
            comparison_set=imported_objects,
            message="not all group members were imported",
        )

        _check_overlap(
            minimal_set=imported_objects,
            comparison_set=expected_objects,
            message="some imported items are not part of the group",
        )

    @abstractmethod
    def __call__(self, item: T) -> T:
        """
        Add the given item to this group.

        :param item: the item to add to this group
        :return: the unchanged item
        """
        pass

    @abstractmethod
    def __contains__(self, item: Any) -> bool:
        # check if the given item is a member of this group
        pass


class _BaseImportGroup(ImportGroup, metaclass=ABCMeta):
    """
    Abstract base implementation of import groups, implementing the :attr:`.tracker`
    property.

    We don't include this in the :class:`.ImportGroup` base class because we want users
    to instantiate groups via the :class:`.AllTracker`, and not by instantiating
    :class:`.ImportGroup`.
    """

    def __init__(self, tracker: AllTracker) -> None:
        """
        :param tracker: the tracker that created this group
        """
        self.__tracker = tracker

    @property
    def tracker(self) -> AllTracker:
        """[see superclass]"""
        return self.__tracker


@inheritdoc(match="[see superclass]")
class _ImportGroupDecorator(_BaseImportGroup):
    """
    A decorator flagging classes or other objects as a member of an import group.

    Useful for validating selective imports from a private module.
    """

    __members: Dict[int, Any]

    def __init__(self, tracker: AllTracker):
        """[see superclass]"""
        super().__init__(tracker=tracker)
        self.__members = {}

    def get_members(self) -> Dict[int, Any]:
        """[see superclass]"""
        return self.__members

    def __call__(self, item: T) -> T:
        """[see superclass]"""
        if not hasattr(item, "__name__"):
            raise TypeError("only named objects can be decorated with an import group")

        if any(item in group for group in self.tracker.groups):
            raise ValueError(f"{item.__name__} has already been assigned to a group")

        self.__members[id(item)] = item

        return item

    def __contains__(self, item: Any) -> bool:
        return id(item) in self.__members


@inheritdoc(match="[see superclass]")
class _DefaultGroup(_BaseImportGroup):
    """
    Group of definitions that have not explicitly been assigned to any import group.
    """

    def get_members(self) -> Dict[int, Any]:
        """[see superclass]"""
        tracker = self.tracker

        all_ids: Dict[int, Any] = {
            id(obj): obj for obj in (tracker[name] for name in tracker.get_tracked())
        }

        default_ids = reduce(
            operator.sub,
            (group.get_members().keys() for group in tracker.groups),
            all_ids,
        )

        return {id_: all_ids[id_] for id_ in default_ids}

    def __call__(self, item: T) -> T:
        """
        Raises a :class:`.NotImplementedError`.

        Items are in this group by default.
        Attempts to explicitly add them to this group will raise an exception.

        :raises NotImplementedError: objects cannot be added to the default group
        """
        raise NotImplementedError("objects cannot be added to the default group")

    def __contains__(self, item: Any) -> bool:
        tracker = self.tracker
        return item in tracker and all(item not in group for group in tracker.groups)


__tracker.validate()

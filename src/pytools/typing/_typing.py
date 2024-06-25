"""
Implementation of unions.
"""

from __future__ import annotations

import itertools
import logging
import sys
import typing
from collections.abc import (
    AsyncGenerator,
    AsyncIterable,
    AsyncIterator,
    Awaitable,
    ByteString,
    Collection,
    Container,
    Generator,
    ItemsView,
    Iterable,
    Iterator,
    KeysView,
    Mapping,
    Reversible,
    Sequence,
    ValuesView,
)
from types import GenericAlias
from typing import (
    AbstractSet,
    Any,
    Generic,
    TypeAlias,
    TypeVar,
    cast,
    get_args,
    get_origin,
)

import typing_inspect as ti
from typing_extensions import Never

from pytools.api import subsdoc

if sys.version_info >= (3, 11):

    class SpecialForm:
        """
        Placeholder for the SpecialForm class, which is required up to Python 3.10.
        """

        pass

else:
    from typing import _SpecialForm as SpecialForm


log = logging.getLogger(__name__)

__all__ = [
    "get_common_generic_base",
    "get_common_generic_subclass",
    "get_generic_bases",
    "get_generic_instance",
    "get_type_arguments",
    "isinstance_generic",
    "issubclass_generic",
]


#
# Type aliases
#

EllipsisType: TypeAlias = type(Ellipsis)  # type: ignore[valid-type]


#
# Type variables
#
# Naming convention used here:
# _ret for covariant type variables used in return positions
# _arg for contravariant type variables used in argument positions

T = TypeVar("T")


#
# Constants
#

_SPECIAL_GENERIC_BASES: dict[type, type] = {
    Iterator: Iterable,
    AsyncIterator: AsyncIterable,
}


_IMMUTABLE_GENERIC_ALIASES = {
    AbstractSet,
    AsyncGenerator,
    AsyncIterable,
    AsyncIterator,
    Awaitable,
    ByteString,
    Collection,
    Container,
    getattr(typing, "FrozenSet"),
    Generator,
    ItemsView,
    Iterable,
    Iterator,
    KeysView,
    Reversible,
    Sequence,
    ValuesView,
}


#
# Classes
#


def get_common_generic_base(classes: Iterable[type[T]]) -> type[T]:
    """
    Get the most specific common type of the given objects.

    :param classes: the objects to get the common type of
    :return: the most specific common type
    """
    # Get the unique classes
    classes_unique = set(classes)

    # Iterate over the unique origin classes
    iter_classes = iter({get_origin(cls) or cls for cls in classes_unique})

    common_type: type[T] = next(iter_classes)
    for cls in iter_classes:
        cls_mro: list[type] = cls.mro()
        # find the first common base class
        for base in common_type.mro():
            if base in cls_mro:
                common_type = base
                break

    if not ti.is_generic_type(common_type):
        return common_type

    # For each generic class, get the generic instance of the common origin class
    common_type_generic = set(
        itertools.chain.from_iterable(
            get_generic_instance(cls, common_type) for cls in classes_unique
        )
    )

    if len(common_type_generic) > 1:
        raise TypeError(
            f"Cannot find a common generic base class; the common base origin class "
            f"{common_type.__name__} has multiple generic instances: "
            + ", ".join(map(str, common_type_generic))
        )

    return common_type_generic.pop()


def get_common_generic_subclass(classes: Iterable[type[T]]) -> type[T]:
    """
    Get the most general common subclass of the given classes.

    Selects the class from the given classes that is a subclass of all other classes.

    :param classes: the classes to get the common subclass of
    :return: the most general common subclass
    :raises TypeError: if the classes have no common subclass
    """
    # iterate over the classes, excluding duplicates
    iter_classes = iter(set(classes))

    # start with the first class
    try:
        common_class = next(iter_classes)
    except StopIteration:
        raise TypeError(
            "get_common_generic_subclass() requires at least one class, but got none"
        )

    for cls in iter_classes:
        if issubclass_generic(cls, common_class):
            common_class = cls
        elif not issubclass_generic(common_class, cls):
            raise TypeError(
                f"Classes {common_class.__name__} and {cls.__name__} have no common "
                "subclass"
            )
    return common_class


def get_generic_instance(subclass: type, base: type) -> list[type]:
    # noinspection GrazieInspection
    """
    Given a subclass and a generic base class, get the generic instances of the
    base class, substituting all type arguments along the class hierarchy.

    In most cases this will return a single generic instance, but in the case of
    multiple inheritance with different type arguments, it may return more than one.

    As an example, consider this generic class and its instance:

    .. code-block:: python

            class MyClass(Generic[T]):

                def __init__(self, value: T):
                    self.value = value

            class MySubclass(MyClass[int]):

                def __init__(self, value: int):
                    super().__init__(value)

    Calling ``get_generic_base_arguments(MyClass[float], MyClass)`` will yield
    ``MyClass[float]``.
    Calling ``get_generic_base_arguments(MySubclass, MyClass)`` will yield
    ``MyClass[int]``.

    :param subclass: the subclass for which to get the type arguments of the base class
    :param base: the base class for which to get the type arguments
    :return: the generic instances of the base class
    :raises TypeError: if arg base is not a generic class, or if arg subclass is not a
        subclass of arg base
    """

    def _walk_bases(subclass_: type, bindings: dict[TypeVar, type]) -> Iterator[type]:

        def _apply_bindings(tp: TypeVar | type) -> type:
            if isinstance(tp, TypeVar):
                # We have a type variable, apply bindings
                bound_type = bindings.get(tp, None)
                if bound_type is None:
                    # If the type variable is not bound, try to derive the type from
                    # constraints or bounds
                    return _infer_type_var(tp)
                else:
                    return bound_type
            elif ti.is_generic_type(tp):
                # Recursively apply bindings to unbound parameters of the type argument
                bound_args: tuple[type, ...] = tuple(
                    _apply_bindings(arg_) for arg_ in ti.get_parameters(tp)
                )
                return (
                    cast(
                        type,
                        tp[bound_args],  # type: ignore[index]
                    )
                    if bound_args
                    else tp
                )
            else:
                # We have a concrete type, no need to apply bindings
                return tp

        # infer types for unbound type variables
        for param in ti.get_parameters(subclass_):
            if param not in bindings:
                bindings[param] = _infer_type_var(param)

        # Substitute parameter values
        args_subs = tuple(bindings[param] for param in ti.get_parameters(subclass_))

        origin = get_origin(subclass_) or subclass_

        if origin is base:
            # We have found the generic base
            yield (
                subclass_[args_subs] if args_subs else subclass_  # type: ignore[index]
            )
        else:
            # Map bases to original bases
            base_to_orig = {
                get_origin(base_): base_
                for base_ in get_generic_bases(generic_instance=subclass_)
            }
            # Get substitutions
            base_bindings = {
                param: _apply_bindings(arg)
                for param, arg in zip(ti.get_parameters(origin), get_args(subclass_))
            }
            # Get bases, substituting original bases where available
            for base_ in origin.__bases__:
                if base_ is Generic:
                    continue
                yield from _walk_bases(
                    subclass_=base_to_orig.get(base_, base_),
                    bindings=base_bindings,
                )

    if ti.get_origin(base) is not None and get_args(base):
        raise TypeError(f"arg base must not be a generic instance, but got {base}")

    if not issubclass(get_origin(subclass) or subclass, base):
        raise TypeError(
            f"Class {subclass.__name__} is not a subclass of {base.__name__}"
        )

    base = _replace_deprecated_type(base)

    return list(
        # eliminate duplicates by converting to a set, then convert to a list
        set(_walk_bases(_replace_deprecated_type(subclass), bindings={}))
    )


def get_generic_bases(*, generic_instance: type) -> tuple[type, ...]:
    """
    Extended version of typing_inspect.get_generic_bases that covers some special cases
    for generic instances of generic aliases.

    Must be called with a generic instance, rather than a generic alias.

    - If the origin is a :class:`.Iterator`, return a generic instance of its base
      class, :class:`.Iterable`
    - If the origin is a :class:`.AsyncIterator`, return a generic instance of its base
      class, :class:`.AsyncIterable`

    :param generic_instance: the generic instance to get the generic bases of (note that
        this is not a non-generic type, as in the original function in
        :mod:`typing_inspect`)
    :return: the generic bases of the generic instance
    """

    generic_instance = _replace_deprecated_type(generic_instance)
    origin = get_origin(generic_instance) or generic_instance
    generic_bases: tuple[type, ...] = ti.get_generic_bases(origin)

    if generic_bases:
        # The typing_inspect implementation returned generic bases; return these
        return generic_bases

    special_generic_base: type | None = _SPECIAL_GENERIC_BASES.get(origin, None)
    if special_generic_base is not None:
        # Inherit generic arguments from the generic base for an identified special case
        assert origin.__bases__ == (special_generic_base,), (
            f"The base classes {origin.__bases__} of {origin!r} should be "
            f"{special_generic_base!r}"
        )

        return (
            special_generic_base[ti.get_args(generic_instance)],  # type: ignore[index]
        )

    # The origin is not a generic alias
    return ()


@subsdoc(pattern="Given a subclass", replacement="Given an object")
@subsdoc(pattern="generic instances", replacement="type arguments")
@subsdoc(
    pattern="single generic instance", replacement="single tuple of type arguments"
)
@subsdoc(pattern=r"\[float\]", replacement="(3.0)")
@subsdoc(pattern=r"MySubclass, MyClass", replacement="MySubclass(), MyClass")
@subsdoc(pattern=r":param subclass: the subclass", replacement=":param obj: the object")
@subsdoc(
    pattern=r":return: the generic instances of the base class",
    replacement=(
        ":return: the type arguments of the base class, each as a tuple of types"
    ),
    using=get_generic_instance,
)
def get_type_arguments(obj: Any, base: type) -> list[tuple[type, ...]]:
    """[see above]"""
    return list(map(get_args, get_generic_instance(ti.get_generic_type(obj), base)))


def issubclass_generic(subclass: type | Never, base: type | Never) -> bool:
    """
    Check if a class is a subclass of a generic instance, i.e., it is a subclass of the
    generic class, and has compatible type arguments.

    :param subclass: the class to check
    :param base: the generic class to check against
    :return: ``True`` if the class is a subclass of the generic instance, ``False``
        otherwise
    """

    # As a special case, type `Any` is a superclass of anything
    if base is Any:
        return True
    elif subclass is Any:
        return False

    # As a special case, type `Never` is a subclass of anything
    if subclass is Never:
        return True
    elif base is Never:
        return False

    subclass = _replace_deprecated_type(subclass)
    base = _replace_deprecated_type(base)

    # Get the non-generic origin of the base class
    base_origin = get_origin(base) or base

    # If the non-generic origin of the subclass is not a subclass of the non-generic
    # origin of the base class, the subclass cannot be a subclass of the base class
    subclass_origin = get_origin(subclass) or subclass
    if not issubclass(subclass_origin, base_origin):
        return False

    # If the base class is not a generic class, there are no type arguments to check
    if not ti.is_generic_type(base):
        if isinstance(base, GenericAlias):
            raise TypeError(f"Unsupported type construct: {base!r}")
        return True

    subclass = _infer_generic_types(subclass)
    base = _infer_generic_types(base)

    # Get the type arguments at the level of the base class
    for base_generic in get_generic_instance(subclass, base_origin):
        args: tuple[type, ...] = get_args(base_generic)
        # Get the type parameters of the base class
        base_params: tuple[TypeVar | EllipsisType, ...] = _get_origin_parameters(base)
        # Get the type arguments of given base class
        base_args: tuple[type, ...] = get_args(base)
        # For each parameter and argument, check compatibility depending on the
        # variance of the parameter
        assert len(args) == len(base_params) == len(base_args), (
            f"Expected the number of type arguments of {base_generic.__name__} to "
            f"match the number of type parameters of {base.__name__} and the number of "
            f"type arguments of {base_origin.__name__} itself, but got "
            f"{args}, {base_params} and {base_args}, respectively"
        )
        arg: type
        base_param: TypeVar | EllipsisType
        base_arg: type
        for arg, base_param, base_arg in zip(args, base_params, base_args):
            if isinstance(base_param, EllipsisType):  # pragma: no cover
                raise TypeError(
                    f"Unexpected Ellipsis type parameter in base class: {base}"
                )
            if base_param.__covariant__:
                if not issubclass_generic(arg, base_arg):
                    return False
            elif base_param.__contravariant__:
                if not issubclass_generic(base_arg, arg):
                    return False
            elif arg != base_arg:
                return False
    return True


def isinstance_generic(obj: Any, base: type) -> bool:
    """
    Check if an object is an instance of a generic instance, i.e., it is a subclass of
    the generic class, and has compatible type arguments.

    :param obj: the object to check
    :param base: the generic class to check against
    :return: ``True`` if the object is an instance of the generic instance, ``False``
        otherwise
    """
    return issubclass_generic(ti.get_generic_type(obj), base)


#
# Auxiliary functions
#


def _infer_type_var(tp: TypeVar) -> type:
    # Derive the most specific type argument from a type variable based on its
    # constraints or bounds

    # First try to get the bound
    bound: type = ti.get_bound(tp)
    if bound is not None:
        return bound

    # Alternatively, try to get the constraints
    constraints = ti.get_constraints(tp)
    if len(constraints) > 1:
        raise TypeError(
            f"Type variable {tp} has multiple constraints "
            f"{constraints}; cannot determine unique type argument"
        )
    elif len(constraints) == 1:
        return constraints[0]

    # If no bound or constraints are available, return Any
    return Any


def _infer_generic_types(cls: type) -> type:
    """
    Ensure that a class has no unbound type variables.

    :param cls: the class to check
    """
    unbound_parameters: tuple[TypeVar, ...] = ti.get_parameters(cls)
    if unbound_parameters:
        return cast(
            type,
            cls[tuple(map(_infer_type_var, unbound_parameters))],  # type: ignore[index]
        )
    else:
        return cls


def _get_origin_parameters(
    generic_instance: type,
) -> tuple[TypeVar | EllipsisType, ...]:
    """
    Get the type parameters of a generic instance, handling special cases for generic
    aliases.

    :param generic_instance: the class to get the type parameters of
    :return: the type parameters of the class
    """

    from typing import Optional, Union

    # We do not support union types
    origin = get_origin(generic_instance)
    if origin in {Union, Optional}:
        raise TypeError(f"Union types are not supported: {generic_instance}")

    parameters: tuple[TypeVar | EllipsisType, ...] = ti.get_parameters(origin)

    # If parameters are defined, or we do not have a generic alias, return the
    # parameters
    if parameters or not isinstance(generic_instance, GenericAlias):
        return parameters

    # We have a generic alias; derive the type parameters from its arguments
    args = get_args(generic_instance)

    # We only support generic types, types, type variables, and Ellipsis as arguments;
    # raise an error if we encounter anything else
    if not all(
        ti.is_generic_type(arg)
        or isinstance(arg, (type, TypeVar, SpecialForm))
        or arg is Ellipsis
        for arg in args
    ):
        raise TypeError(
            f"Generic alias {generic_instance} has unsupported arguments: {args}"
        )

    # Derive type variables from the arguments

    # Type variables are covariant for iteration types, red-only containers,
    # and tuples, unless they contain an Ellipsis
    if origin in _IMMUTABLE_GENERIC_ALIASES or origin is tuple and Ellipsis not in args:
        # noinspection PyTypeHints
        return tuple(TypeVar(f"T{i}", covariant=True) for i, arg in enumerate(args))
    elif origin is Mapping:
        # Mapping is only covariant in the value type
        # noinspection PyTypeHints
        return TypeVar("KT"), TypeVar("VT", covariant=True)
    else:
        # noinspection PyTypeHints
        return tuple(
            Ellipsis if arg is Ellipsis else TypeVar(f"T{i}")
            for i, arg in enumerate(args)
        )


def _replace_deprecated_type(tp: type) -> type:
    """
    Replace deprecated types in :mod:`typing` with their canonical replacements in
    :mod:`collections.abc`.

    :param tp: the type to check and possibly replace
    :return: the original type, or the replacement type if the original type is
        deprecated
    """

    if tp.__module__ == "typing":
        # Check if the same type is defined in collections.abc
        origin: type | None = get_origin(tp)
        if origin is not None and origin.__module__ == "collections.abc":
            log.warning(
                f"Type typing.{tp.__name__} is deprecated; "
                f"please use {origin.__module__}.{origin.__name__} instead"
            )
            args: tuple[type, ...] = get_args(tp)
            if args:
                # If the type has arguments, apply the same arguments to the replacement
                return cast(type, origin[args])  # type: ignore[index]
            else:
                return origin
    return tp

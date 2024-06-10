"""
Implementation of ``DictRepresentation``.
"""

from __future__ import annotations

import logging
from abc import ABCMeta
from collections.abc import Iterable, Mapping
from importlib import import_module
from typing import Any, TypeVar, final

from ..api import get_init_params, inheritdoc
from ..expression import Expression, HasExpressionRepr
from ..expression.atomic import Id

log = logging.getLogger(__name__)

__all__ = [
    "HasDictRepr",
]

#
# Type variables
#


T_Class = TypeVar("T_Class", bound="HasDictRepr")


#
# Constants
#

KEY_CLASS = "cls"
KEY_PARAMS = "params"
KEY_DICT = "dict"


@inheritdoc(match="""[see superclass]""")
class HasDictRepr(HasExpressionRepr, metaclass=ABCMeta):
    """
    A class that can be represented as a JSON-serializable dictionary.
    """

    @final
    def to_dict(self) -> dict[str, Any]:
        """
        Convert this object to a dictionary that can be serialized to JSON.

        Calls private method :meth:`._get_params` to get the parameters that were
        used to initialize this object. By default, this uses class introspection to
        determine the class initializer parameters and access attributes of the same
        name. Subclasses can override this method to provide a custom implementation.

        Creates a dictionary with keys ``{KEY_CLASS}`` and ``{KEY_PARAMS}``,
        with the class name and a dictionary of parameters, respectively.

        Parameter values are recursively converted to JSON-serializable forms using the
        following rules:

        - If the value is a string, bytes, int, float, or bool, leave it as is
        - If the value is an instance of :class:`HasDictRepresentation`, call its
          :meth:`to_dict` method and use the result
        - If the value is a mapping, recursively convert its keys and values,
          collate the result into a dictionary and wrap it in a dictionary with a
          single key ``{KEY_DICT}`` to distinguish it from dictionary representations
          of classes
        - If the value is an iterable, recursively convert its elements and collate the
          result into a list
        - Otherwise, convert the value to a string using :func:`repr`.

        :return: the dictionary representation of the object
        """

        # iterate over args of __init__; these must correspond to matching fields
        # in the class

        return {
            KEY_CLASS: f"{self.__module__}.{type(self).__qualname__}",
            KEY_PARAMS: {
                # recursively convert all parameter values to JSON-serializable forms
                name: _to_json_like(value)
                for name, value in self._get_params().items()
            },
        }

    to_dict.__doc__ = str(to_dict.__doc__).format(
        KEY_CLASS=KEY_CLASS, KEY_PARAMS=KEY_PARAMS, KEY_DICT=KEY_DICT
    )

    @classmethod
    @final
    def from_dict(
        cls: type[T_Class], data: Mapping[str, Any], **kwargs: Any
    ) -> T_Class:
        """
        Create a new instance of this class from a dictionary.

        This method is the inverse of :meth:`to_dict`. It creates an instance of the
        class from a dictionary representation.

        :param data: the dictionary representation of the object
        :param kwargs: additional keyword arguments for pre-processing the parameters
        :return: the new object
        :raises TypeError: if the class of the object in the dictionary representation
            is not a subclass of this class
        """

        # the dict should only have the keys we expect
        unexpected_keys: set[str] = data.keys() - [KEY_CLASS, KEY_PARAMS]
        if unexpected_keys:
            raise ValueError(
                f"Unexpected keys in object representation: {unexpected_keys}"
            )

        # get the class name and parameters from the dictionary
        try:
            class_full_name: str = data[KEY_CLASS]
            params: dict[str, Any] = data[KEY_PARAMS]
        except KeyError as e:
            raise ValueError(
                f"Expected keys {KEY_CLASS!r} and {KEY_PARAMS!r} in object "
                f"representation but got: {data!r}"
            ) from e

        # get the class from the name
        module_name, _, class_name = class_full_name.rpartition(".")
        cls_target: type[T_Class] = getattr(import_module(module_name), class_name)

        if not issubclass(cls_target, cls):
            raise TypeError(f"Expected a subclass of {cls}, but got {cls_target}")

        # create an instance of the class with the parameters
        return cls_target(**cls_target._params_from_dict(params, **kwargs))

    def _get_params(self) -> dict[str, Any]:
        """
        Get the parameters that were used to initialize this object.
        """
        return get_init_params(self)

    @classmethod
    def _params_from_dict(
        cls, params: Mapping[str, Any], **kwargs: Any
    ) -> dict[str, Any]:
        """
        Process the parameters from a dict representation prior to creating a new
        object.

        This method is called by :meth:`to_dict`. By default, this method recursively
        de-serializes dictionary representations into instances of their original
        classes, and returns built-in data structures and data types as-is.

        Subclasses can override this method to provide a custom implementation.

        :param params: the parameters to process
        :return: the processed parameters
        """
        return {
            name: _from_json_like(value, **kwargs) for name, value in params.items()
        }

    def to_expression(self) -> Expression:
        """[see superclass]"""
        return Id(type(self))(**self._get_params())


def _to_json_like(obj: Any) -> Any:
    # helper function to convert an object to a JSON-serializable form
    if obj is None or isinstance(obj, (str, bytes, int, float, bool)):
        return obj
    elif isinstance(obj, Mapping):
        return {KEY_DICT: {_to_json_like(k): _to_json_like(v) for k, v in obj.items()}}
    elif isinstance(obj, Iterable):
        return list(map(_to_json_like, iter(obj)))
    elif isinstance(obj, HasDictRepr):
        return obj.to_dict()
    else:
        raise ValueError(f"Object does not implement {HasDictRepr.__name__}: {obj!r}")


def _from_json_like(obj: Any, **kwargs: Any) -> Any:
    # helper function to convert a JSON-serializable object representation to
    # the original object
    if obj is None or isinstance(obj, (str, bytes, int, float, bool)):
        return obj
    elif isinstance(obj, Mapping):
        if len(obj) == 1:
            try:
                dict_ = obj[KEY_DICT]
            except KeyError:
                raise ValueError(
                    f"Expected key {KEY_DICT!r} in object representation but got: "
                    f"{obj!r}"
                )
            return {_from_json_like(k): _from_json_like(v) for k, v in dict_.items()}
        elif len(obj) == 2:
            return HasDictRepr.from_dict(obj, **kwargs)
        else:
            raise ValueError(f"Invalid  object representation: {obj}")
    elif isinstance(obj, Iterable):
        return list(map(_from_json_like, iter(obj)))
    else:
        raise ValueError(f"Invalid object representation: {obj}")

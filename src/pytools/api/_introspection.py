"""
Implementation of introspection functions.
"""

import inspect
import logging
from collections.abc import Iterable
from typing import Any

log = logging.getLogger(__name__)

__all__ = [
    "get_init_params",
]


def get_init_params(
    obj: Any, ignore_default: bool = True, ignore_missing: bool = False
) -> dict[str, Any]:
    """
    Get the attribute values for parameters of the ``__init__`` method of a class.
    Requires the class to define attributes matching the names of the ``__init__``
    parameters.

    :param obj: the object to get the parameters from
    :param ignore_default: if True, ignore parameters whose value is the default value
    :param ignore_missing: if True, ignore parameters for which no matching attribute
        exists
    :return: the parameters and their values
    :raises AttributeError: if a parameter has no matching attribute and
        ``ignore_missing`` is False
    """
    # get the signature of the __init__ method
    init = getattr(obj, "__init__")
    # if this is the init method of object, skip it
    if init.__qualname__ == "object.__init__":
        return {}
    parameters: Iterable[inspect.Parameter] = inspect.signature(
        init
    ).parameters.values()

    # sentinel value for missing attributes
    _missing = object()

    # the dictionary to store the parameters and their values
    params: dict[str, Any] = {}

    # return the names and values of the remaining parameters
    for p in parameters:
        value = getattr(obj, p.name, _missing)
        if value is _missing:
            if ignore_missing:
                continue
            else:
                raise AttributeError(
                    # We use the native __repr__ method to avoid infinite recursion
                    # in case the object has overridden __repr__ and it calls
                    # get_init_params
                    f"Object {object.__repr__(obj)} has no attribute matching "
                    f"parameter {p.name}"
                )
        # we skip the parameter if ignore_default is True and its attribute value is
        # equal to the default value
        if not (ignore_default and p.default == value):
            params[p.name] = value

    return params

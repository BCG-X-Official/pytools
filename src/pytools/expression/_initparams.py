"""
Implementation of introspection functions.
"""

import logging
from collections.abc import Collection
from typing import Any

from ..api import get_init_params
from pytools.expression import Expression
from pytools.expression.atomic import Id

log = logging.getLogger(__name__)

__all__ = [
    "expression_from_init_params",
]


def expression_from_init_params(
    obj: Any,
    *,
    ignore_null: bool = False,
    ignore_empty: bool = False,
    args: str | None = None,
    kwargs: str | None = None,
) -> Expression:
    """
    Create an expression from the ``__init__`` parameters of the given object.
    Requires the object to have attributes with the same name as the parameters of its
    ``__init__`` method.

    :param obj: the object to create the expression from
    :param ignore_null: if True, ignore attributes with value ``None``
    :param ignore_empty: if True, ignore attributes whose value is an empty collection
    :param args: the name of the attribute that stores variable positional arguments
        as an iterable (optional)
    :param kwargs: the name of the attribute that stores variable keyword arguments
        as a name/value mapping (optional)
    :return: the expression
    """
    # create the expression
    init_params = get_init_params(obj, ignore_missing=True)
    positional_args = [] if args is None else init_params.pop(args)
    keyword_args = {} if kwargs is None else init_params.pop(kwargs)
    return Id(type(obj))(
        *positional_args,
        **{
            # get the attributes corresponding to the parameters of the __init__ method
            param: value
            for param, value in (
                # get the names and values of the attributes corresponding to the
                # parameters of the __init__ method
                init_params.items()
            )
            if not (
                # if ignore_null is True, ignore attributes with value None
                (ignore_null and value is None)
                # if ignore_empty is True, ignore attributes whose value is an empty
                # collection
                or (ignore_empty and isinstance(value, Collection) and not value)
            )
        },
        **keyword_args,
    )

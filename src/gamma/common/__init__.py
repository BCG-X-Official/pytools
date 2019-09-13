#
# NOT FOR CLIENT USE!
#
# This is a pre-release library under development. Handling of IP rights is still
# being investigated. To avoid causing any potential IP disputes or issues, DO NOT USE
# ANY OF THIS CODE ON A CLIENT PROJECT, not even in modified form.
#
# Please direct any queries to any of:
# - Jan Ittner
# - Jörg Schneider
# - Florent Martin
#

"""
Global definitions of basic types and functions for use across all gamma libraries
"""

import logging
import warnings
from functools import wraps
from typing import *

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)

# noinspection PyShadowingBuiltins
_T = TypeVar("_T")
ListLike = Union[np.ndarray, pd.Series, pd.Index, Iterable[_T]]


def is_list_like(obj: Any) -> bool:
    """
    Check if the object is list-like.

    Objects that are considered list-like are for example Python
    lists, tuples, sets, NumPy arrays, and Pandas Series.

    Strings and datetime objects, however, are not considered list-like.

    :param obj The object to check
    :return `True` if `obj` has list-like properties
    """

    return (
        isinstance(obj, Iterable)
        # we do not count strings/unicode/bytes as list-like
        # also exclude Pandas data frames and panels, as iterating them will yield the
        # column index
        and not isinstance(obj, (str, bytes, pd.DataFrame, pd.Panel))
        # exclude zero-dimensional numpy arrays, effectively scalars
        and not (isinstance(obj, np.ndarray) and obj.ndim == 0)
    )


def deprecated(function: Callable = None, *, message: str = None):
    """
    Decorator to mark functions as deprecated.

    It will result in a warning being logged when the function is used.
    """

    def _deprecated_inner(func: callable) -> callable:
        @wraps(func)
        def new_func(*args, **kwargs) -> Any:
            """
            Function wrapper
            """
            message_header = f"Call to deprecated function {func.__name__}"
            if message is None:
                warnings.warn(message_header, DeprecationWarning)
            else:
                warnings.warn(f"{message_header}: {message}", DeprecationWarning)

            return func(*args, **kwargs)

        return new_func

    if function is None:
        return _deprecated_inner
    else:
        return _deprecated_inner(function)

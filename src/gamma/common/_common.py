"""
Core implementation of :mod:`gamma.common`
"""

import logging
import warnings
from functools import wraps
from typing import *

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)


def is_list_like(obj: Any) -> bool:
    """
    Check if the object is list-like.

    Objects that are considered list-like when they implement methods `len` and
    `__getitem__`. These include, for example, lists, tuples, sets, NumPy arrays, and
    Pandas series and indices.

    As an exception, the following types are not considered list-like despite
    implementing the methods above:

    - `str`
    - `bytes`
    - :class:`pandas.DataFrame`: inconsistent behaviour of the sequence interface; \
        iterating a data frame yields the values of the column index, while numeric \
        indices access columns as series
    - :class:`pandas.Panel`: similar behaviour as for data frames
    - :class:`numpy.ndarray` instances with 0 dimensions


    :param obj The object to check
    :return `True` if `obj` has list-like properties
    """

    return (
        hasattr(obj, "__len__")
        and hasattr(obj, "__getitem__")
        and not isinstance(obj, (str, bytes, pd.DataFrame, pd.Panel))
        # exclude zero-dimensional numpy arrays, effectively scalars
        and not (isinstance(obj, np.ndarray) and obj.ndim == 0)
    )


def deprecated(function: Callable = None, *, message: str = None):
    """
    Decorator to mark functions as deprecated.

    It will result in a warning being logged when the function is used.

    To deprecate classes, apply this decorator to the `__init__` method, not to the
    class itself.
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
    else:
        return _deprecated_inner(function)

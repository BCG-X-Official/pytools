"""
Core implementation of :mod:`pytools.fit`
"""
import logging
from abc import ABCMeta, abstractmethod
from typing import Generic, TypeVar

from ..api import AllTracker

log = logging.getLogger(__name__)

#
# Exported names
#

__all__ = ["FittableMixin"]


#
# Type variables
#

T = TypeVar("T")
T_Data = TypeVar("T_Data")


#
# Ensure all symbols introduced below are included in __all__
#

__tracker = AllTracker(globals())


#
# Classes
#


class FittableMixin(Generic[T_Data], metaclass=ABCMeta):
    """
    Mix-in class that supports fitting the object to data.
    """

    @abstractmethod
    def fit(self: T, _x: T_Data, **fit_params) -> T:
        """
        Fit this object to the given data
        :param _x: the data to fit this object to
        :param fit_params: optional fitting parameters
        :return: self
        """
        pass

    @property
    @abstractmethod
    def is_fitted(self) -> bool:
        """``True`` if this object is fitted, ``False`` otherwise."""
        pass

    def _ensure_fitted(self) -> None:
        # raise a runtime exception if this object is not fitted
        if not self.is_fitted:
            raise RuntimeError(f"{type(self).__name__} is not fitted")


__tracker.validate()

"""
Core implementation of :mod:`gamma.common.fit`
"""
import logging
from abc import ABC, abstractmethod
from typing import *

log = logging.getLogger(__name__)


#
# exported names
#

__all__ = ["FittableMixin"]


#
# type variables
#


T_Self = TypeVar("T_Self")
T_Data = TypeVar("T_Data")

#
# class definitions
#


class FittableMixin(ABC, Generic[T_Data]):
    """
    Mix-in class that supports fitting the object to data.
    """

    @abstractmethod
    def fit(self: T_Self, _x: T_Data, **fit_params) -> T_Self:
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
        """`True` if this object is fitted, else `False`"""
        pass

    def _ensure_fitted(self) -> None:
        # raise a runtime exception if this object is not fitted
        if not self.is_fitted:
            raise RuntimeError(f"{type(self).__name__} is not fitted")

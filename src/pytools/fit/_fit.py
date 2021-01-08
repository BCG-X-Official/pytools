"""
Core implementation of :mod:`pytools.fit`.
"""
import logging
from abc import ABCMeta, abstractmethod
from typing import Generic, TypeVar

from ..api import AllTracker

log = logging.getLogger(__name__)

#
# Exported names
#

__all__ = ["NotFittedError", "FittableMixin"]


#
# Type variables
#

T_Self = TypeVar("T_Self")
T_Data = TypeVar("T_Data")


#
# Ensure all symbols introduced below are included in __all__
#

__tracker = AllTracker(globals())


#
# Classes
#


class NotFittedError(Exception):
    """
    Raised when a fittable object was expected to be fitted but was not fitted.
    """


class FittableMixin(Generic[T_Data], metaclass=ABCMeta):
    """
    Mix-in class that supports fitting the object to data.
    """

    @abstractmethod
    def fit(self: T_Self, _x: T_Data, **fit_params) -> T_Self:
        """
        Fit this object to the given data.

        :param _x: the data to fit this object to
        :param fit_params: optional fitting parameters
        :return: self
        """
        pass

    @property
    @abstractmethod
    def is_fitted(self) -> bool:
        """
        ``True`` if this object is fitted, ``False`` otherwise.
        """
        pass

    def _ensure_fitted(self) -> None:
        """
        Raise a :class:`.NotFittedError` if this object is not fitted.

        :meta public:
        :raise NotFittedError: this object is not fitted
        """
        if not self.is_fitted:
            raise NotFittedError(f"{type(self).__name__} is not fitted")


__tracker.validate()

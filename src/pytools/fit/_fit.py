"""
Core implementation of :mod:`pytools.fit`.
"""

import functools
import logging
from abc import ABCMeta, abstractmethod
from collections.abc import Callable
from typing import Any, Generic, TypeVar, cast, overload

from ..api import AllTracker

log = logging.getLogger(__name__)

#
# Exported names
#

__all__ = [
    "NotFittedError",
    "FittableMixin",
    "fitted_only",
]


#
# Type variables
#

T_Self = TypeVar("T_Self")
T_Data = TypeVar("T_Data")
T_Callable = TypeVar("T_Callable", bound=Callable[..., Any])


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

    See also :class:`FittableMixin` and the :obj:`fitted_only` decorator.
    """


class FittableMixin(Generic[T_Data], metaclass=ABCMeta):
    # noinspection GrazieInspection
    """
    Mix-in class that supports fitting the object to data.

    See also the :obj:`fitted_only` decorator.

    Usage:

    .. code-block:: python

        class MyFittable(FittableMixin[MyData]):
            def fit(self, data: MyData) -> "MyFittable":
                # fit object to data
                ...

                return self

            def is_fitted(self) -> bool:
                # Return True if the object is fitted, False otherwise
                ...

            @fitted_only
            def some_method(self, ...) -> ...:
                # This method may only be called if the object is fitted
                ...

    .. note::
        This class is not meant to be instantiated directly. Instead, it is
        meant to be used as a mix-in class for other classes.
    """

    @abstractmethod
    def fit(self: T_Self, __x: T_Data, **fit_params: Any) -> T_Self:
        """
        Fit this object to the given data.

        :param __x: the data to fit this object to
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


@overload
def fitted_only(__method: T_Callable) -> T_Callable:
    """[overloaded]"""


@overload
def fitted_only(
    *,
    not_fitted_error: type[Exception] = NotFittedError,
) -> Callable[[T_Callable], T_Callable]:
    """[overloaded]"""


def fitted_only(
    __method: T_Callable | None = None,
    *,
    not_fitted_error: type[Exception] = NotFittedError,
) -> T_Callable | Callable[[T_Callable], T_Callable]:
    # noinspection GrazieInspection
    """
    Decorator that ensures that the decorated method is only called if the object is
    fitted.

    The decorated method must be a method of a class that inherits from
    :class:`FittableMixin`, or implements a boolean property ``is_fitted``.

    Usage:

    .. code-block:: python

      class MyFittable(FittableMixin):
          def __init__(self) -> None:
              self._is_fitted = False

          @fitted_only
          def my_method(self) -> None:
              # this method may only be called if the object is fitted
              ...

          @property
          def is_fitted(self) -> bool:
              return self._is_fitted

    :param __method: the method to decorate
    :param not_fitted_error: the type of exception to raise if the object is not fitted;
        defaults to :class:`.NotFittedError`
    :return: the decorated method
    """
    if __method is None:
        return functools.partial(fitted_only, not_fitted_error=not_fitted_error)
    method: T_Callable = __method

    @functools.wraps(method)
    def _wrapper(self: FittableMixin[Any], *args: Any, **kwargs: Any) -> Any:
        if not self.is_fitted:
            raise not_fitted_error(f"{type(self).__name__} is not fitted")
        return method(self, *args, **kwargs)

    return cast(T_Callable, _wrapper)


__tracker.validate()

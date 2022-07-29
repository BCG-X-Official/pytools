"""
Core implementation of :mod:`pytools.meta`.
"""
from __future__ import annotations

import logging
from abc import ABCMeta
from typing import Any, Optional
from weakref import ReferenceType

from ..api import AllTracker

log = logging.getLogger(__name__)


#
# Exported names
#

__all__ = [
    "SingletonABCMeta",
    "SingletonMeta",
]


#
# Ensure all symbols introduced below are included in __all__
#

__tracker = AllTracker(globals())


#
# Classes
#


class SingletonMeta(type):
    """
    Metaclass for singleton classes.

    Subsequent instantiations of a singleton class return the identical object.
    Singleton classes must not accept any parameters upon instantiation.
    """

    __instance_ref: "Optional[ReferenceType[Any]]"

    def __init__(cls: SingletonMeta, *args: Any, **kwargs: Any) -> None:
        """
        :param args: arguments to be passed on to the initializer of the base metaclass
        :param kwargs: keyword arguments to be passed on to the initializer of the
            base metaclass
        """
        super().__init__(*args, **kwargs)
        cls.__instance_ref = None

    def __call__(cls: SingletonMeta, *args: Any, **kwargs: Any) -> Any:
        """
        Return the existing singleton instance, or create a new one if none exists yet.

        Behind the scenes, uses a weak reference so the singleton instance can be
        garbage collected when no longer in use.

        Singletons must be instantiated without any parameters.

        :return: the singleton instance
        :raises ValueError: if called with parameters
        """
        if args or kwargs:
            raise ValueError("singleton classes may not take any arguments")

        if cls.__instance_ref:
            obj: Optional[Any] = cls.__instance_ref()
            if obj is not None:
                return obj

        instance: Any = super(SingletonMeta, cls).__call__()
        cls.__instance_ref = ReferenceType(instance)
        return instance


class SingletonABCMeta(SingletonMeta, ABCMeta):
    """
    Convenience metaclass combining :class:`.SingletonMeta` and :class:`~abc.ABCMeta`.
    """


__tracker.validate()

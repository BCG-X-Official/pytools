"""
Core implementation of :mod:`pytools.meta`.
"""
import logging
from typing import Optional, Type, TypeVar
from weakref import ref

from ..api import AllTracker

log = logging.getLogger(__name__)


#
# Exported names
#

__all__ = ["SingletonMeta", "compose_meta"]


#
# Type variables
#

T = TypeVar("T")


#
# Ensure all symbols introduced below are included in __all__
#

__tracker = AllTracker(globals())


#
# Classes
#


class SingletonMeta(type):
    """
    Meta-class for singleton classes.

    Subsequent instantiations of a singleton class return the identical object.
    Singleton classes may not accept any parameters upon instantiation.
    """

    def __init__(cls, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        cls.__instance_ref: Optional[ref] = None

    def __call__(cls: Type[T], *args, **kwargs) -> T:
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

        cls: SingletonMeta

        if cls.__instance_ref:
            obj = cls.__instance_ref()
            if obj is not None:
                return obj

        instance = super(SingletonMeta, cls).__call__()
        cls.__instance_ref = ref(instance)
        return instance


#
# Functions
#


def compose_meta(*metaclasses: type) -> type:
    """
    Compose multiple metaclasses.

    :param metaclasses: one or more metaclasses
    """
    metaclasses = tuple(
        mcs
        for i, mcs in enumerate(metaclasses)
        if mcs is not type and mcs not in metaclasses[:i]
    )
    return type("_" + "_".join(mcs.__name__ for mcs in metaclasses), metaclasses, {})


__tracker.validate()

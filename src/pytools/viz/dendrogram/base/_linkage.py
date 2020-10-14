"""
Supporting classes for linkage trees
"""

import logging
from abc import ABCMeta, abstractmethod
from typing import Optional

from pytools.api import AllTracker

log = logging.getLogger(__name__)

#
# exported names
#

__all__ = ["BaseNode", "LeafNode", "LinkageNode"]


#
# Ensure all symbols introduced below are included in __all__
#

__tracker = AllTracker(globals())


class BaseNode(metaclass=ABCMeta):
    """
    Base class for nodes of a :class:`LinkageTree`.
    """

    __slots__ = ["_index"]

    def __init__(self, index: int) -> None:
        self._index = index

    @property
    def index(self) -> int:
        """The index of the node."""
        return self._index

    @property
    @abstractmethod
    def children_distance(self) -> float:
        """Distance from the node to its children."""
        pass

    @property
    @abstractmethod
    def weight(self) -> float:
        """Weight of the node."""
        pass

    @property
    @abstractmethod
    def label(self) -> str:
        """Label of the node."""
        pass

    @property
    @abstractmethod
    def is_leaf(self) -> bool:
        """True if the node is a leaf, False otherwise."""
        pass

    def _type_error(self, property_name: str) -> TypeError:
        return TypeError(f"{property_name} is not defined for a {type(self).__name__}")

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}_{self._index}"


class LinkageNode(BaseNode):
    """
    Internal node in a :class:`LinkageTree`.

    :param children_distance: distance from the node to its children
    """

    __slots__ = ["_children_distance"]

    def __init__(self, index: int, children_distance: Optional[float]) -> None:
        super().__init__(index=index)
        self._children_distance = children_distance

    @property
    def children_distance(self) -> float:
        """Distance to the children."""
        return self._children_distance

    @property
    def weight(self) -> float:
        """Undefined, should not be called."""
        raise self._type_error("weight")

    @property
    def label(self) -> str:
        """Undefined, should not be called."""
        raise self._type_error("label")

    @property
    def is_leaf(self) -> bool:
        """``True`` if the node is a leaf, ``False`` otherwise."""
        return False

    def __repr__(self) -> str:
        return f"{super().__repr__()}[dist={self.children_distance * 100:.0f}%]"


class LeafNode(BaseNode):
    """
    Leaf in a linkage tree.

    :param index: the leaf index
    :param label: the leaf label
    :param weight: the leaf weight
    """

    __slots__ = ["_weight", "_label"]

    def __init__(self, index: int, label: str, weight: float) -> None:
        super().__init__(index=index)
        self._label = label
        self._weight = weight

    @property
    def children_distance(self) -> float:
        """Distance to the children."""
        raise self._type_error("children_distance")

    @property
    def label(self) -> str:
        """Label of the node."""
        return self._label

    @property
    def weight(self) -> float:
        """Importance of the node."""
        return self._weight

    @property
    def is_leaf(self) -> bool:
        """True."""
        return True

    def __repr__(self) -> str:
        return f"{super().__repr__()}[label={self.label}, weight={self.weight}]"


__tracker.validate()

"""
Supporting classes for linkage trees
"""

import logging
from abc import ABCMeta, abstractmethod
from typing import Optional

from pytools.api import AllTracker, inheritdoc

log = logging.getLogger(__name__)

#
# exported names
#

__all__ = ["Node", "LeafNode", "LinkageNode"]


#
# Ensure all symbols introduced below are included in __all__
#

__tracker = AllTracker(globals())


#
# Classes
#


class Node(metaclass=ABCMeta):
    """
    Base class for nodes of a :class:`.LinkageTree`.
    """

    def __init__(self, index: int) -> None:
        """
        :param index: the index of this node in the linkage tree
        """
        self._index = index

    @property
    def index(self) -> int:
        """The index of the node."""
        return self._index

    @property
    @abstractmethod
    def children_distance(self) -> float:
        """
        Distance of this node from its children.
        """
        pass

    @property
    @abstractmethod
    def weight(self) -> float:
        """
        Weight of this node.
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Name of this node.
        """
        pass

    @property
    @abstractmethod
    def is_leaf(self) -> bool:
        """``True`` if the node is a leaf, ``False`` otherwise."""
        pass

    def _type_error(self, property_name: str) -> TypeError:
        return TypeError(f"{property_name} is not defined for a {type(self).__name__}")

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}_{self._index}"


@inheritdoc(match="[see superclass]")
class LinkageNode(Node):
    """
    Inner node in a :class:`.LinkageTree`.
    """

    def __init__(self, index: int, children_distance: Optional[float]) -> None:
        """
        :param children_distance: the distance between this node and its children
        """
        super().__init__(index=index)
        self._children_distance = children_distance

    __init__.__doc__ = Node.__init__.__doc__ + __init__.__doc__

    @property
    def children_distance(self) -> float:
        """[see superclass]"""
        return self._children_distance

    @property
    def weight(self) -> float:
        """
        Undefined, raises :class:`TypeError`.
        """
        raise self._type_error("weight")

    @property
    def name(self) -> str:
        """
        Undefined, raises :class:`TypeError`.
        """
        raise self._type_error("name")

    @property
    def is_leaf(self) -> bool:
        """``False``"""
        return False

    def __repr__(self) -> str:
        return f"{super().__repr__()}[dist={self.children_distance * 100:.0f}%]"


@inheritdoc(match="[see superclass]")
class LeafNode(Node):
    """
    A leaf in a linkage tree.
    """

    def __init__(self, index: int, name: str, weight: float) -> None:
        """
        :param name: the name of the leaf
        :param weight: the weight of the leaf
        """
        super().__init__(index=index)
        self._name = name
        self._weight = weight

    __init__.__doc__ = Node.__init__.__doc__ + __init__.__doc__

    @property
    def children_distance(self) -> float:
        """
        Undefined, raises :class:`TypeError`.
        """
        raise self._type_error("children_distance")

    @property
    def name(self) -> str:
        """[see superclass]"""
        return self._name

    @property
    def weight(self) -> float:
        """[see superclass]"""
        return self._weight

    @property
    def is_leaf(self) -> bool:
        """``True``"""
        return True

    def __repr__(self) -> str:
        return f"{super().__repr__()}[name={self.name}, weight={self.weight}]"


__tracker.validate()

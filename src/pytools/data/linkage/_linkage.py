"""
Supporting classes for linkage trees.
"""

import logging
from abc import ABCMeta, abstractmethod
from typing import cast

from pytools.api import AllTracker, inheritdoc
from pytools.expression import Expression, HasExpressionRepr
from pytools.expression.atomic import Id

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


class Node(HasExpressionRepr, metaclass=ABCMeta):
    """
    Base class for nodes of a :class:`.LinkageTree`.
    """

    def __init__(self, index: int) -> None:
        """
        :param index: the numerical index of this node in the linkage tree
        """
        self._index = index

    @property
    def index(self) -> int:
        """
        The numerical index of this node in the linkage tree.
        """
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
        The weight of this node.
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """
        The name of this node.
        """
        pass

    @property
    @abstractmethod
    def is_leaf(self) -> bool:
        """
        ``True`` if the node is a leaf; ``False`` otherwise.
        """
        pass

    def _type_error(self, property_name: str) -> TypeError:
        return TypeError(f"{property_name} is not defined for a {type(self).__name__}")


@inheritdoc(match="""[see superclass]""")
class LinkageNode(Node):
    """
    An inner node in a :class:`.LinkageTree`.
    """

    def __init__(self, index: int, children_distance: float) -> None:
        """
        :param children_distance: the distance between this node and its children
        """
        super().__init__(index=index)
        self._children_distance = children_distance

    __init__.__doc__ = cast(str, Node.__init__.__doc__) + cast(str, __init__.__doc__)

    @property
    def children_distance(self) -> float:
        """[see superclass]"""
        return self._children_distance

    @property
    def weight(self) -> float:
        """
        Undefined for inner nodes; raises :class:`TypeError`.
        """
        raise self._type_error("weight")

    @property
    def name(self) -> str:
        """
        Undefined for inner nodes; raises :class:`TypeError`.
        """
        raise self._type_error("name")

    @property
    def is_leaf(self) -> bool:
        """``False``"""
        return False

    def to_expression(self) -> Expression:
        """[see superclass]"""
        return Id(type(self))(self.index, children_distance=self.children_distance)


@inheritdoc(match="""[see superclass]""")
class LeafNode(Node):
    """
    A leaf in a :class:`.LinkageTree`.
    """

    def __init__(self, index: int, name: str, weight: float) -> None:
        """
        :param name: the name of the leaf
        :param weight: the weight of the leaf
        """
        super().__init__(index=index)
        self._name = name
        self._weight = weight

    __init__.__doc__ = cast(str, Node.__init__.__doc__) + cast(str, __init__.__doc__)

    @property
    def children_distance(self) -> float:
        """
        Undefined for leaf nodes; raises :class:`TypeError`.
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

    def to_expression(self) -> Expression:
        """[see superclass]"""
        return Id(type(self))(self.index, name=self.name, weight=self.weight)


__tracker.validate()

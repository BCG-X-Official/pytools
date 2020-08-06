"""
Linkage Tree.

:class:`LinkageTree` is the internal representation of dendrograms.

:class:`LinkageNode` and :class:`LeafNode` are the building blocks of
:class:`LinkageTree`. Both these classes inherit from :class:`BaseNode`.
"""

from abc import ABCMeta, abstractmethod
from typing import *

import numpy as np

__all__ = ["BaseNode", "LinkageNode", "LeafNode", "LinkageTree"]


class BaseNode(metaclass=ABCMeta):
    """
    BaseNode of a :class:`LinkageTree`.

    Implementations must define ``children_distance``, ``weight``, ``label``, ``is_leaf``.
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


class LinkageTree:
    """
    A traversable tree derived from a SciPy linkage matrix.

    :param scipy_linkage_matrix: linkage matrix from SciPy
    :param leaf_labels: labels of the leaves
    :param leaf_weights: weight of the leaves (all values must range between 0.0 and \
        1.0; should add up to 1.0)
    """

    F_CHILD_LEFT = 0
    F_CHILD_RIGHT = 1
    F_CHILDREN_DISTANCE = 2
    F_N_DESCENDANTS = 3

    def __init__(
        self,
        scipy_linkage_matrix: np.ndarray,
        leaf_labels: Iterable[str],
        leaf_weights: Iterable[float],
        max_distance: Optional[float] = None,
    ) -> None:
        # one row of the linkage matrix is a quadruple:
        # (
        #    <index of left child>,
        #    <index of right child>,
        #    <distance between children>,
        #    <number of descendant nodes, from direct children down to leaf nodes>
        # )

        n_branches = len(scipy_linkage_matrix)
        n_leaves = n_branches + 1

        def _validate_leafs(var: Sequence[Any], var_name: str):
            if len(var) != n_branches + 1:
                raise ValueError(
                    f"expected {n_branches + 1} values " f"for arg {var_name}"
                )

        self._linkage_matrix = scipy_linkage_matrix

        leaf_labels = list(leaf_labels)
        leaf_weights = list(leaf_weights)

        _validate_leafs(leaf_labels, "leaf_labels")
        _validate_leafs(leaf_weights, "leaf_weights")

        if any(not (0.0 <= weight <= 1.0) for weight in leaf_weights):
            raise ValueError(
                "all values in arg leaf_weights are required to be in the range "
                "from 0.0 to 1.0"
            )

        self._nodes: List[BaseNode] = [
            *[
                LeafNode(index=index, label=label, weight=weight)
                for index, (label, weight) in enumerate(zip(leaf_labels, leaf_weights))
            ],
            *[
                LinkageNode(
                    index=index + n_leaves,
                    children_distance=scipy_linkage_matrix[index][
                        LinkageTree.F_CHILDREN_DISTANCE
                    ],
                )
                for index in range(n_branches)
            ],
        ]

        root_children_distance = self._nodes[-1].children_distance
        if max_distance is None:
            max_distance = root_children_distance
        elif max_distance < root_children_distance:
            raise ValueError(
                f"arg max_distance={max_distance} must be equal to or greater than "
                f"the maximum distance (= {root_children_distance}) in the linkage tree"
            )
        self._max_distance = max_distance

    @property
    def root(self) -> BaseNode:
        """
        The root node of the linkage tree.

        It is the cluster containing all other clusters.
        """
        return self._nodes[-1]

    @property
    def max_distance(self) -> float:
        """
        The maximum possible distance in the linkage tree; this determines the height of
        the tree to be drawn
        """
        return self._max_distance

    def children(self, node: BaseNode) -> Optional[Tuple[BaseNode, BaseNode]]:
        """Return the children of the node.

        :return: ``None`` if the node is a leaf, otherwise the pair of children
        """
        if node.is_leaf:
            return None
        else:
            # noinspection PyProtectedMember
            node_linkage = self._linkage_matrix[node._index - self.n_leaves]
            ix_c1, ix_c2 = node_linkage[
                [LinkageTree.F_CHILD_LEFT, LinkageTree.F_CHILD_RIGHT]
            ].astype(int)
            return self._nodes[ix_c1], self._nodes[ix_c2]

    @property
    def n_leaves(self) -> int:
        """The number of leaves."""
        return len(self) - len(self._linkage_matrix)

    def __len__(self) -> int:
        return len(self._nodes)

    def __getitem__(self, item: int) -> BaseNode:
        return self._nodes[item]

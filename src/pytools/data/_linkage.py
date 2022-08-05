"""
Linkage Tree.

:class:`LinkageTree` is the internal representation of dendrograms.

:class:`LinkageNode` and :class:`LeafNode` are the building blocks of
:class:`LinkageTree`. Both these classes inherit from :class:`BaseNode`.
"""
from __future__ import annotations

from copy import copy
from typing import Any, Iterable, Iterator, List, Optional, Sequence, Tuple

import numpy as np
import numpy.typing as npt

from ..api import AllTracker, inheritdoc
from ..expression import Expression, HasExpressionRepr
from ..expression.atomic import Id
from .linkage import LeafNode, LinkageNode, Node

#
# Exported names
#

__all__ = ["LinkageTree"]


#
# Type variables
#

LinkageMatrix = npt.NDArray[np.float_]


#
# Constants
#

ASSERTION_CURRENT_NODE_NOT_A_LEAF = "current node must not be a leaf"


#
# Ensure all symbols introduced below are included in __all__
#

__tracker = AllTracker(globals())


#
# Class definitions
#


@inheritdoc(match="[see superclass]")
class LinkageTree(HasExpressionRepr):
    """
    A traversable tree derived from a SciPy linkage matrix.

    Supports :func:`len`, numerical indexing, and node iteration.
    """

    __F_CHILD_LEFT = 0
    __F_CHILD_RIGHT = 1
    __F_CHILDREN_DISTANCE = 2

    #: The original linkage matrix created by :func:`scipy.cluster.hierarchy.linkage`.
    #:
    #: One row of the scipy linkage matrix is a quadruple:
    #: `(<index of left child>,
    #: <index of right child>,
    #: <distance between children>,
    #: <number of descendant nodes>)`,
    #: where the descendant nodes include the nodes from the entire sub-tree,
    #: from direct children down to leaf nodes.
    scipy_linkage_matrix: LinkageMatrix

    #: The maximum possible distance in the linkage tree; this determines the height of
    #: the tree to be drawn.
    max_distance: float

    #: A label describing the type/unit of distances
    #: passed in arg `scipy_linkage_matrix` (optional).
    distance_label: Optional[str]

    #: A label describing the type of names
    #: passed in arg `leaf_names` (optional).
    leaf_label: Optional[str]

    #: A label describing the type/unit of weights
    #: passed in arg `leaf_weights` (optional).
    weight_label: Optional[str]

    def __init__(
        self,
        *,
        scipy_linkage_matrix: LinkageMatrix,
        leaf_names: Iterable[str],
        leaf_weights: Iterable[float],
        max_distance: Optional[float] = None,
        distance_label: Optional[str] = None,
        leaf_label: Optional[str] = None,
        weight_label: Optional[str] = None,
    ) -> None:
        """
        :param scipy_linkage_matrix: linkage matrix calculated by function
            :func:`scipy.cluster.hierarchy.linkage`
        :param leaf_names: labels of the leaves
        :param leaf_weights: weight of the leaves; all values must range between `0.0`
            and `1.0`, and should add up to `1.0`
        :param max_distance: maximum theoretical distance value; this must be equal
            to, or greater than the maximum distance in arg `scipy_linkage_matrix`
            (optional)
        :param distance_label: a label describing the type and/or unit of distances
            passed in arg `scipy_linkage_matrix` (optional)
        :param leaf_label: a label describing the type of names
            passed in arg `leaf_names` (optional)
        :param weight_label: a label describing the type and/or unit of weights
            passed in arg `leaf_weights` (optional)
        """

        n_branches = len(scipy_linkage_matrix)
        n_leaves = n_branches + 1

        def _validate_leaves(var: Sequence[Any], var_name: str) -> None:
            if len(var) != n_leaves:
                raise ValueError(f"expected {n_leaves} values for arg {var_name}")

        self.scipy_linkage_matrix = scipy_linkage_matrix

        leaf_names = [str(name) for name in leaf_names]
        leaf_weights = [float(weight) for weight in leaf_weights]

        _validate_leaves(leaf_names, "leaf_labels")
        _validate_leaves(leaf_weights, "leaf_weights")

        if any(not (0.0 <= weight <= 1.0) for weight in leaf_weights):
            raise ValueError(
                "all values in arg leaf_weights are required to be in the range "
                "from 0.0 to 1.0"
            )

        self._nodes: List[Node] = [
            *[
                LeafNode(index=index, name=label, weight=weight)
                for index, (label, weight) in enumerate(zip(leaf_names, leaf_weights))
            ],
            *[
                LinkageNode(
                    index=index + n_leaves,
                    children_distance=scipy_linkage_matrix[index][
                        LinkageTree.__F_CHILDREN_DISTANCE
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

        self.max_distance = max_distance
        self.leaf_label = leaf_label
        self.weight_label = weight_label
        self.distance_label = distance_label

    @property
    def root(self) -> Node:
        """
        The root node of the linkage tree.
        """
        return self._nodes[-1]

    def children(self, node: Node) -> Optional[Tuple[Node, Node]]:
        """
        Get the children of the given node.

        :param node: the node for which to get the children
        :return: ``None`` if the node is a leaf, otherwise the pair of children
        """

        node_index = node.index
        nodes = self._nodes

        # check that the node is included in this tree
        if node_index >= len(nodes) or node is not nodes[node_index]:
            raise ValueError("arg node is not a node in this linkage tree")

        if node.is_leaf:
            return None
        else:
            # noinspection PyProtectedMember
            node_linkage = self.scipy_linkage_matrix[node_index - self.n_leaves]
            ix_c1, ix_c2 = node_linkage[
                [LinkageTree.__F_CHILD_LEFT, LinkageTree.__F_CHILD_RIGHT]
            ].astype(int)
            return nodes[ix_c1], nodes[ix_c2]

    @property
    def n_leaves(self) -> int:
        """
        The number of leave nodes in this linkage tree.
        """
        return len(self) - len(self.scipy_linkage_matrix)

    def sort_by_weight(self) -> LinkageTree:
        """
        Create a copy of this linkage trees, switching the left and right nodes of
        branches such that the mean leaf weight or any left node is always greater
        than the mean leaf weight in the right node.

        :return: a copy of this linkage tree with sorting applied
        """

        linkage: LinkageMatrix = self.scipy_linkage_matrix.copy()

        def _sort_node(n: Node) -> Tuple[float, int]:
            # sort a linkage node and return its total weight and leaf count

            if n.is_leaf:
                return n.weight, 1

            children = self.children(n)
            assert children is not None, ASSERTION_CURRENT_NODE_NOT_A_LEAF
            l, r = children

            weight_left, leaves_left = _sort_node(l)
            weight_right, leaves_right = _sort_node(r)

            if weight_left / leaves_left < weight_right / leaves_right:
                # swap nodes if the right node has the higher weight
                n_linkage = linkage[n.index - self.n_leaves]
                n_linkage[
                    [LinkageTree.__F_CHILD_RIGHT, LinkageTree.__F_CHILD_LEFT]
                ] = n_linkage[[LinkageTree.__F_CHILD_LEFT, LinkageTree.__F_CHILD_RIGHT]]

            return weight_left + weight_right, leaves_left + leaves_right

        _sort_node(self.root)

        linkage_sorted = copy(self)
        linkage_sorted.scipy_linkage_matrix = linkage
        return linkage_sorted

    def iter_nodes(self, inner: bool = True) -> Iterator[Node]:
        """
        Traverse this linkage tree depth-first and return all nodes.

        :param inner: if ``True``, iterate inner nodes; if ``False``, iterate
           leaf nodes only
        :return: an iterator for all nodes
        """

        def _iter(n: Node) -> Iterator[Node]:
            if n.is_leaf:
                yield n
            else:
                if inner:
                    yield n
                children = self.children(n)
                assert children is not None, ASSERTION_CURRENT_NODE_NOT_A_LEAF
                l, r = children
                yield from _iter(l)
                yield from _iter(r)

        yield from _iter(self.root)

    def __len__(self) -> int:
        return len(self._nodes)

    def __getitem__(self, item: int) -> Node:
        return self._nodes[item]

    def to_expression(self) -> Expression:
        """[see superclass]"""

        def _expr(n: Node) -> Expression:
            if n.is_leaf:
                return n.to_expression()
            else:
                children = self.children(n)
                assert children is not None, ASSERTION_CURRENT_NODE_NOT_A_LEAF
                l, r = children
                return n.to_expression()[_expr(l), _expr(r)]

        return Id(type(self))(
            _expr(self.root),
            max_distance=self.max_distance,
            leaf_label=self.leaf_label,
            weight_label=self.weight_label,
            distance_label=self.distance_label,
        )


__tracker.validate()

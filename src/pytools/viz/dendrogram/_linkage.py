"""
Linkage Tree.

:class:`LinkageTree` is the internal representation of dendrograms.

:class:`LinkageNode` and :class:`LeafNode` are the building blocks of
:class:`LinkageTree`. Both these classes inherit from :class:`BaseNode`.
"""

from typing import Any, Iterable, List, Optional, Sequence, Tuple

import numpy as np

from pytools.api import AllTracker, to_tuple
from pytools.viz.dendrogram.base import LeafNode, LinkageNode, Node

#
# Exported names
#

__all__ = ["LinkageTree"]


#
# Ensure all symbols introduced below are included in __all__
#

__tracker = AllTracker(globals())


#
# Class definitions
#


class LinkageTree:
    """
    A traversable tree derived from a SciPy linkage matrix.

    Supports :func:`len`, and numerical indexing and iteration of nodes.
    """

    __F_CHILD_LEFT = 0
    __F_CHILD_RIGHT = 1
    __F_CHILDREN_DISTANCE = 2
    __F_N_DESCENDANTS = 3

    #: The original linkage matrix created by :func:`scipy.cluster.hierarchy.linkage`.
    #:
    #: One row of the scipy linkage matrix is a quadruple:
    #: `(<index of left child>,
    #: <index of right child>,
    #: <distance between children>,
    #: <number of descendant nodes>)`,
    #: where the descendant nodes include the nodes from the entire sub-tree,
    #: from direct children down to leaf nodes.
    scipy_linkage_matrix: np.ndarray

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
        scipy_linkage_matrix: np.ndarray,
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

        def _validate_leaves(var: Sequence[Any], var_name: str):
            if len(var) != n_leaves:
                raise ValueError(f"expected {n_leaves} values " f"for arg {var_name}")

        self.scipy_linkage_matrix = scipy_linkage_matrix

        leaf_names: Tuple[str, ...] = to_tuple(
            leaf_names, element_type=str, arg_name="leaf_names"
        )
        leaf_weights: Tuple[float, ...] = to_tuple(
            leaf_weights, element_type=float, arg_name="leaf_weights"
        )

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

    def __len__(self) -> int:
        return len(self._nodes)

    def __getitem__(self, item: int) -> Node:
        return self._nodes[item]


__tracker.validate()

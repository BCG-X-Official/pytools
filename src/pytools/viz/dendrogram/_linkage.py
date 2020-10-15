"""
Linkage Tree.

:class:`LinkageTree` is the internal representation of dendrograms.

:class:`LinkageNode` and :class:`LeafNode` are the building blocks of
:class:`LinkageTree`. Both these classes inherit from :class:`BaseNode`.
"""

from typing import Any, Iterable, List, Optional, Sequence, Tuple

import numpy as np

from pytools.api import AllTracker
from pytools.viz.dendrogram.base import BaseNode, LeafNode, LinkageNode

#
# exported names
#

__all__ = ["LinkageTree"]

#
# Ensure all symbols introduced below are included in __all__
#

__tracker = AllTracker(globals())


#
# class definitions
#


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


__tracker.validate()

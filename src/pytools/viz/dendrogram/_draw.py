"""
Drawing dendrograms.
"""

import logging
from typing import Any, Dict, Iterable, List, NamedTuple, Optional, Type, Union

import numpy as np

from .. import Drawer
from ._linkage import LinkageTree
from ._style import DendrogramHeatmapStyle, DendrogramLineStyle, DendrogramReportStyle
from .base import DendrogramStyle, Node
from pytools.api import AllTracker, inheritdoc

log = logging.getLogger(__name__)


#
# Exported names
#

__all__ = ["DendrogramDrawer"]


#
# Ensure all symbols introduced below are included in __all__
#

__tracker = AllTracker(globals())


#
# Classes
#


class _SubtreeInfo(NamedTuple):
    names: List[str]
    weights: List[float]
    weight_total: float


@inheritdoc(match="[see superclass]")
class DendrogramDrawer(Drawer[LinkageTree, DendrogramStyle]):
    """
    Draws dendrogram representations of :class:`.LinkageTree` objects.
    """

    def __init__(self, style: Optional[Union[DendrogramStyle, str]] = None) -> None:
        """[see superclass]"""
        super().__init__(style=style)

    @classmethod
    def get_style_classes(cls) -> Iterable[Type[DendrogramStyle]]:
        """[see superclass]"""
        return [
            DendrogramHeatmapStyle,
            DendrogramLineStyle,
            DendrogramReportStyle,
        ]

    def _get_style_kwargs(self, data: LinkageTree) -> Dict[str, Any]:
        return dict(
            leaf_label=data.leaf_label,
            distance_label=data.distance_label,
            weight_label=data.weight_label,
            max_distance=data.max_distance,
            n_leaves=data.n_leaves,
            **super()._get_style_kwargs(data=data),
        )

    def _draw(self, data: LinkageTree) -> None:
        # draw the linkage tree

        mean_leaf_weight = np.zeros(len(data), float)

        def _calculate_weights(n: Node) -> (float, int):
            # calculate the weight of a node and number of leaves below
            if n.is_leaf:
                weight = n.weight
                n_leaves = 1
            else:
                l, r = data.children(n)
                lw, ln = _calculate_weights(l)
                rw, rn = _calculate_weights(r)
                weight = lw + rw
                n_leaves = ln + rn
            mean_leaf_weight[n.index] = weight / n_leaves
            return weight, n_leaves

        def _draw_node(
            node: Node, node_idx: int, weight_cumulative: float, width: float
        ) -> _SubtreeInfo:
            # Recursively draw the part of the dendrogram under a node.
            #
            # Arguments:
            #   node:     the node to be drawn
            #   node_idx: an integer determining the position of the node with respect
            #             to the leaves of the tree
            #   weight_cumulative:
            #             the cumulative weight of all nodes with a lower position
            #   width:    width difference in the tree covered by the node
            #
            # Returns:
            #   _SubtreeInfo instance with labels and weights

            if node.is_leaf:
                self.style.draw_link_leg(
                    bottom=0.0,
                    top=width,
                    leaf=node_idx,
                    weight=node.weight,
                    weight_cumulative=weight_cumulative,
                    tree_height=data.max_distance,
                )

                return _SubtreeInfo(
                    names=[node.name], weights=[node.weight], weight_total=node.weight
                )

            else:
                child_left, child_right = data.children(node=node)
                if (
                    mean_leaf_weight[child_left.index]
                    > mean_leaf_weight[child_right.index]
                ):
                    child_left, child_right = child_right, child_left

                subtree_left_info = _draw_node(
                    node=child_left,
                    node_idx=node_idx,
                    weight_cumulative=weight_cumulative,
                    width=node.children_distance,
                )
                subtree_right_info = _draw_node(
                    node=child_right,
                    node_idx=node_idx + len(subtree_left_info.names),
                    weight_cumulative=weight_cumulative
                    + subtree_left_info.weight_total,
                    width=node.children_distance,
                )

                parent_info = _SubtreeInfo(
                    names=subtree_left_info.names + subtree_right_info.names,
                    weights=subtree_left_info.weights + subtree_right_info.weights,
                    weight_total=(
                        subtree_left_info.weight_total + subtree_right_info.weight_total
                    ),
                )

                self.style.draw_link_connector(
                    bottom=node.children_distance,
                    top=width,
                    first_leaf=node_idx,
                    n_leaves_left=len(subtree_left_info.names),
                    n_leaves_right=len(subtree_right_info.names),
                    weight=parent_info.weight_total,
                    weight_cumulative=weight_cumulative,
                    tree_height=data.max_distance,
                )

                return parent_info

        _calculate_weights(data.root)

        tree_info = _draw_node(
            node=data.root, node_idx=0, weight_cumulative=0.0, width=data.max_distance
        )
        self.style.draw_leaf_labels(names=tree_info.names, weights=tree_info.weights)


__tracker.validate()

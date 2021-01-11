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
    weight: float


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
            **super()._get_style_kwargs(data=data),
        )

    def _draw(self, data: LinkageTree) -> None:
        # draw the linkage tree

        node_weight = np.zeros(len(data), float)

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
            node_weight[n.index] = weight / n_leaves
            return weight, n_leaves

        def _draw_node(node: Node, y: int, width: float) -> _SubtreeInfo:
            # Recursively draw the part of the dendrogram under a node.
            #
            # Arguments:
            # - node:  the node to be drawn
            # - y:     the value determining the position of the node with respect to
            #          the leaves of the tree
            # - width: width difference in the tree covered by the node
            #
            # Returns: _SubtreeInfo instance with labels and weights

            if node.is_leaf:
                self.style.draw_link_leg(
                    bottom=0.0,
                    top=width,
                    leaf=y,
                    weight=node.weight,
                    tree_height=data.max_distance,
                )

                return _SubtreeInfo(names=[node.name], weight=node.weight)

            else:
                child_left, child_right = data.children(node=node)
                if node_weight[child_left.index] > node_weight[child_right.index]:
                    child_left, child_right = child_right, child_left

                info_left = _draw_node(
                    node=child_left, y=y, width=node.children_distance
                )
                info_right = _draw_node(
                    node=child_right,
                    y=y + len(info_left.names),
                    width=node.children_distance,
                )

                info = _SubtreeInfo(
                    names=info_left.names + info_right.names,
                    weight=info_left.weight + info_right.weight,
                )

                self.style.draw_link_connector(
                    bottom=node.children_distance,
                    top=width,
                    first_leaf=y,
                    n_leaves_left=len(info_left.names),
                    n_leaves_right=len(info_right.names),
                    weight=info.weight,
                    tree_height=data.max_distance,
                )

                return info

        _calculate_weights(data.root)

        tree_info = _draw_node(node=data.root, y=0, width=data.max_distance)
        self.style.draw_leaf_names(names=tree_info.names)


__tracker.validate()

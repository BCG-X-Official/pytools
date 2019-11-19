"""
Drawing dendrograms
"""

import logging
from typing import *

import numpy as np

from gamma.viz import Drawer
from gamma.viz.dendrogram._linkage import BaseNode, LinkageTree
from gamma.viz.dendrogram._style import (
    DendrogramHeatmapStyle,
    DendrogramReportStyle,
    DendrogramStyle,
)

log = logging.getLogger(__name__)

__all__ = ["DendrogramDrawer"]


class _SubtreeInfo(NamedTuple):
    labels: List[str]
    weight: float


class DendrogramDrawer(Drawer[LinkageTree, DendrogramStyle]):
    """
    Class to draw a `LinkageTree` as a dendrogram.

    The class has a public method :meth:`~.draw` which draws the dendrogram.
    """

    _STYLES = {"matplot": DendrogramHeatmapStyle, "text": DendrogramReportStyle}

    @classmethod
    def _get_style_dict(cls) -> Mapping[str, Type[DendrogramStyle]]:
        return DendrogramDrawer._STYLES

    def _draw(self, data: LinkageTree) -> None:
        # draw the linkage tree

        node_weight = np.zeros(len(data), float)

        def _calculate_weights(n: BaseNode) -> (float, int):
            """calculate the weight of a node and number of leaves under it"""
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

        def _draw_node(node: BaseNode, y: int, width: float) -> _SubtreeInfo:
            """
            Recursively draw the part of the dendrogram under a node.

            :param node: the node to be drawn
            :param y: the value determining the position of the node with respect to the
              leaves of the tree
            :param width: width difference in the tree covered by the node
            :return info: `_SubtreeInfo` which contains weights and labels
            """
            if node.is_leaf:
                self.style.draw_link_leg(
                    bottom=0.0,
                    top=width,
                    leaf=y,
                    weight=node.weight,
                    tree_height=data.max_distance,
                )

                return _SubtreeInfo(labels=[node.label], weight=node.weight)

            else:
                child_left, child_right = data.children(node=node)
                if node_weight[child_left.index] > node_weight[child_right.index]:
                    child_left, child_right = child_right, child_left

                info_left = _draw_node(
                    node=child_left, y=y, width=node.children_distance
                )
                info_right = _draw_node(
                    node=child_right,
                    y=y + len(info_left.labels),
                    width=node.children_distance,
                )

                info = _SubtreeInfo(
                    labels=info_left.labels + info_right.labels,
                    weight=info_left.weight + info_right.weight,
                )

                self.style.draw_link_connector(
                    bottom=node.children_distance,
                    top=width,
                    first_leaf=y,
                    n_leaves_left=len(info_left.labels),
                    n_leaves_right=len(info_right.labels),
                    weight=info.weight,
                    tree_height=data.max_distance,
                )

                return info

        _calculate_weights(data.root)

        tree_info = _draw_node(node=data.root, y=0, width=data.max_distance)
        self.style.draw_leaf_labels(tree_info.labels)

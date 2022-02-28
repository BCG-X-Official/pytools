"""
Base classes for dendrogram styles.
"""

import logging
from abc import ABCMeta, abstractmethod
from typing import Any, List, Optional, Sequence

from pytools.api import AllTracker
from pytools.viz import DrawingStyle

log = logging.getLogger(__name__)

#
# Exported names
#

__all__ = ["DendrogramStyle"]


#
# Ensure all symbols introduced below are included in __all__
#

__tracker = AllTracker(globals())


#
# Classes
#


class DendrogramStyle(DrawingStyle, metaclass=ABCMeta):
    """
    Base class for dendrogram drawing styles.
    """

    def start_drawing(
        self,
        *,
        title: str,
        leaf_label: Optional[str] = None,
        distance_label: Optional[str] = None,
        weight_label: Optional[str] = None,
        max_distance: Optional[float] = None,
        leaf_names: Optional[Sequence[str]] = None,
        **kwargs: Any,
    ) -> None:
        """
        Prepare a new dendrogram for drawing, using the given title.

        :param title: the title of the chart
        :param leaf_label: the label for the leaf axis
        :param distance_label: the label for the distance axis
        :param weight_label: the label for the weight scale
        :param max_distance: the height (= maximum possible distance) of the dendrogram
        :param leaf_names: the names of the dendrogram leaf nodes
        :param kwargs: additional drawer-specific arguments
        """

        none_args: List[str] = [
            arg
            for arg, value in {
                "leaf_label": leaf_label,
                "distance_label": distance_label,
                "weight_label": weight_label,
                "max_distance": max_distance,
                "leaf_names": leaf_names,
            }.items()
            if value is None
        ]
        if none_args:
            raise ValueError(
                "keyword arguments must not be None: " + ", ".join(none_args)
            )

        super().start_drawing(title=title, **kwargs)

    def finalize_drawing(
        self,
        *,
        leaf_label: Optional[str] = None,
        distance_label: Optional[str] = None,
        weight_label: Optional[str] = None,
        max_distance: Optional[float] = None,
        leaf_names: Optional[Sequence[str]] = None,
        **kwargs: Any,
    ) -> None:
        """
        Finalize the dendrogram, adding labels to the axes.

        :param leaf_label: the label for the leaf axis
        :param distance_label: the label for the distance axis
        :param weight_label: the label for the weight scale
        :param max_distance: the height (= maximum possible distance) of the dendrogram
        :param leaf_names: the names of the dendrogram leaf nodes
        :param kwargs: additional drawer-specific arguments
        """
        super().finalize_drawing(**kwargs)

    @abstractmethod
    def draw_leaf_labels(
        self, *, names: Sequence[str], weights: Sequence[float]
    ) -> None:
        """
        Render the labels for all leaves.

        :param names: the names of all leaves
        :param weights: the weights of all leaves
        """
        pass

    @abstractmethod
    def draw_link_leg(
        self,
        *,
        bottom: float,
        top: float,
        leaf: float,
        weight: float,
        weight_cumulative: float,
        tree_height: float,
    ) -> None:
        """
        Draw a "leg" connecting two levels of the linkage tree hierarchy.

        :param bottom: the height of the child node in the linkage tree
        :param top: the height of the parent node in the linkage tree
        :param leaf: the index of the leaf where the link leg should be drawn (may be
            a ``float``, indicating a position in between two leaves)
        :param weight: the weight of the child node
        :param weight_cumulative: the cumulative weight of all nodes with a lower
            position index than the current one
        :param tree_height: the total height of the linkage tree
        """
        pass

    @abstractmethod
    def draw_link_connector(
        self,
        *,
        bottom: float,
        top: float,
        first_leaf: int,
        n_leaves_left: int,
        n_leaves_right: int,
        weight: float,
        weight_cumulative: float,
        tree_height: float,
    ) -> None:
        """
        Draw a connector between two sub-trees and their parent node.

        :param bottom: the height (i.e. cluster distance) of the sub-trees
        :param top: the height of the parent node
        :param first_leaf: the index of the first leaf in the left sub-tree
        :param n_leaves_left: the number of leaves in the left sub-tree
        :param n_leaves_right: the number of leaves in the right sub-tree
        :param weight: the weight of the parent node
        :param weight_cumulative: the cumulative weight of all nodes with a lower
            position index than the current one
        :param tree_height: the total height of the linkage tree
        """
        pass


__tracker.validate()

"""
Base classes for dendrogram styles.
"""

import logging
from abc import ABCMeta, abstractmethod
from typing import Optional, Sequence, Union

from matplotlib.axes import Axes
from matplotlib.colors import Colormap, LogNorm

from pytools.api import AllTracker
from pytools.viz import (
    ColorbarMatplotStyle,
    DrawStyle,
    MatplotStyle,
    PercentageFormatter,
)

log = logging.getLogger(__name__)

#
# exported names
#

__all__ = ["DendrogramStyle", "DendrogramMatplotStyle"]


#
# Ensure all symbols introduced below are included in __all__
#

__tracker = AllTracker(globals())


class DendrogramStyle(DrawStyle, metaclass=ABCMeta):
    """
    Base class for dendrogram drawing styles.
    """

    @abstractmethod
    def draw_leaf_labels(self, labels: Sequence[str]) -> None:
        """Render the labels for all leaves.

        :param labels: labels of the leaves
        """
        pass

    @abstractmethod
    def draw_link_leg(
        self, bottom: float, top: float, leaf: float, weight: float, tree_height: float
    ) -> None:
        """
        Draw a leaf of the linkage tree.

        :param tree_height:
        :param bottom: the x coordinate of the child node
        :param top: the x coordinate of the parent node
        :param leaf: the index of the leaf where the link leg should be drawn (may be a
            float, indicating a position in between two leaves)
        :param weight: the weight of the child node
        """
        pass

    @abstractmethod
    def draw_link_connector(
        self,
        bottom: float,
        top: float,
        first_leaf: int,
        n_leaves_left: int,
        n_leaves_right: int,
        weight: float,
        tree_height: float,
    ) -> None:
        """
        Draw a connector between two child nodes and their parent node.

        :param bottom: the clustering level (i.e. similarity) of the child nodes
        :param top: the clustering level (i.e. similarity) of the parent node
        :param first_leaf: the index of the first leaf in the left sub-tree
        :param n_leaves_left: the number of leaves in the left sub-tree
        :param n_leaves_right: the number of leaves in the right sub-tree
        :param weight: the weight of the parent node
        :param tree_height: the total height of the tree
        """
        pass


class DendrogramMatplotStyle(DendrogramStyle, ColorbarMatplotStyle, metaclass=ABCMeta):
    """
    Base class for Matplotlib styles for dendrogram.

    Provide basic support for plotting a color legend for feature importance,
    and providing the ``Axes`` object for plotting the actual dendrogram including
    tick marks for the feature distance axis.
    """

    _PERCENTAGE_FORMATTER = PercentageFormatter()

    def __init__(
        self,
        *,
        ax: Optional[Axes] = None,
        min_weight: float = 0.01,
        colormap: Optional[Union[str, Colormap]] = None,
    ) -> None:
        """
        :param min_weight: the min weight on the feature importance color scale; must \
            be greater than 0 and smaller than 1 (default: 0.01)
        """
        if min_weight >= 1.0 or min_weight <= 0.0:
            raise ValueError("arg min_weight must be > 0.0 and < 1.0")

        super().__init__(
            ax=ax,
            colormap=colormap,
            colormap_normalize=LogNorm(min_weight, 1),
            colorbar_label="feature importance",
            colorbar_major_formatter=DendrogramMatplotStyle._PERCENTAGE_FORMATTER,
            colorbar_minor_formatter=DendrogramMatplotStyle._PERCENTAGE_FORMATTER,
        )

    __init__.__doc__ = MatplotStyle.__init__.__doc__ + __init__.__doc__

    def _drawing_finalize(self) -> None:
        super()._drawing_finalize()

        # configure the axes
        ax = self.ax
        ax.set_xlabel("feature distance")
        ax.set_ylabel("feature")
        ax.ticklabel_format(axis="x", scilimits=(-3, 3))

    def draw_leaf_labels(self, labels: Sequence[str]) -> None:
        """Draw leaf labels on the dendrogram."""
        y_axis = self.ax.yaxis
        y_axis.set_ticks(ticks=range(len(labels)))
        y_axis.set_ticklabels(ticklabels=labels)


__tracker.validate()

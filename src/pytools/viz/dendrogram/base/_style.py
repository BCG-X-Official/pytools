"""
Base classes for dendrogram styles.
"""

import logging
from abc import ABCMeta, abstractmethod
from typing import Optional, Sequence

from matplotlib.axes import Axes
from matplotlib.colors import LogNorm

from pytools.api import AllTracker, inheritdoc
from pytools.viz import ColorbarMatplotStyle, DrawingStyle, MatplotStyle
from pytools.viz.color import ColorScheme
from pytools.viz.util import PercentageFormatter

log = logging.getLogger(__name__)

#
# Exported names
#

__all__ = ["DendrogramStyle", "DendrogramMatplotStyle"]


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

    @abstractmethod
    def draw_leaf_names(
        self,
        *,
        names: Sequence[str],
    ) -> None:
        """
        Render the names for all leaves.

        :param names: the names of all leaves
        """
        pass

    @abstractmethod
    def draw_link_leg(
        self, bottom: float, top: float, leaf: float, weight: float, tree_height: float
    ) -> None:
        """
        Draw a "leg" connecting two levels of the linkage tree hierarchy.

        :param bottom: the height of the child node in the linkage tree
        :param top: the height of the parent node in the linkage tree
        :param leaf: the index of the leaf where the link leg should be drawn (may be
            a ``float``, indicating a position in between two leaves)
        :param weight: the weight of the child node
        :param tree_height: the total height of the linkage tree
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
        Draw a connector between two sub-trees and their parent node.

        :param bottom: the height (i.e. cluster distance) of the sub-trees
        :param top: the height of the parent node
        :param first_leaf: the index of the first leaf in the left sub-tree
        :param n_leaves_left: the number of leaves in the left sub-tree
        :param n_leaves_right: the number of leaves in the right sub-tree
        :param weight: the weight of the parent node
        :param tree_height: the total height of the linkage tree
        """
        pass


@inheritdoc(match="[see superclass]")
class DendrogramMatplotStyle(DendrogramStyle, ColorbarMatplotStyle, metaclass=ABCMeta):
    """
    Base class for `matplotlib` styles for dendrograms.

    Supports color maps to indicate feature importance on a logarithmic scale,
    and renders a color bar as a legend.
    """

    def __init__(
        self,
        *,
        ax: Optional[Axes] = None,
        colors: Optional[ColorScheme] = None,
        min_weight: float = 0.01,
    ) -> None:
        """
        :param min_weight: the minimum weight on the logarithmic feature importance
            color scale; must be greater than `0` and smaller than `1`
            (default: `0.01`, i.e., 1%)
        """
        if min_weight >= 1.0 or min_weight <= 0.0:
            raise ValueError("arg min_weight must be > 0.0 and < 1.0")

        percentage_formatter = PercentageFormatter()
        super().__init__(
            ax=ax,
            colors=colors,
            colormap_normalize=LogNorm(min_weight, 1),
            colorbar_major_formatter=percentage_formatter,
            colorbar_minor_formatter=percentage_formatter,
        )

    __init__.__doc__ = MatplotStyle.__init__.__doc__ + __init__.__doc__

    def draw_leaf_names(self, *, names: Sequence[str]) -> None:
        """[see superclass]"""
        ax = self.ax
        y_axis = ax.yaxis
        y_axis.set_ticks(ticks=range(len(names)))
        y_axis.set_ticklabels(ticklabels=names)

    def finalize_drawing(
        self,
        *,
        leaf_label: Optional[str] = None,
        distance_label: Optional[str] = None,
        weight_label: Optional[str] = None,
        **kwargs,
    ) -> None:
        """
        Add labels to the axes of this drawing.

        :param leaf_label: the label for the leaf axis
        :param distance_label: the label for the distance axis
        :param weight_label: the label for the color bar, indicating weights
        """
        super().finalize_drawing(colorbar_label=weight_label, **kwargs)

        ax = self.ax

        # configure the axes
        ax.ticklabel_format(axis="x", scilimits=(-3, 3))
        if distance_label:
            ax.set_xlabel(distance_label)
        if leaf_label:
            ax.set_ylabel(leaf_label)


__tracker.validate()

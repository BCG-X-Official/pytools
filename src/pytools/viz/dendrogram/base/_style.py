"""
Base classes for dendrogram styles.
"""

import logging
from abc import ABCMeta, abstractmethod
from typing import Optional, Sequence, Union

from matplotlib.axes import Axes
from matplotlib.colors import Colormap, LogNorm

from pytools.api import AllTracker, inheritdoc
from pytools.viz import ColorbarMatplotStyle, DrawingStyle, MatplotStyle
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
        :param leaf: the index of the leaf where the link leg should be drawn (may be \
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
    Base class for Matplotlib styles for dendrograms.

    Includes support for plotting a color legend for feature importance.
    """

    _PERCENTAGE_FORMATTER = PercentageFormatter()

    def __init__(
        self,
        *,
        ax: Optional[Axes] = None,
        colormap: Optional[Union[str, Colormap]] = None,
        min_weight: float = 0.01,
    ) -> None:
        """
        :param min_weight: the min weight on the logarithmic feature importance color \
            scale; must be greater than 0 and smaller than 1 (default: 0.01)
        """
        if min_weight >= 1.0 or min_weight <= 0.0:
            raise ValueError("arg min_weight must be > 0.0 and < 1.0")

        super().__init__(
            ax=ax,
            colormap=colormap,
            colormap_normalize=LogNorm(min_weight, 1),
            colorbar_major_formatter=DendrogramMatplotStyle._PERCENTAGE_FORMATTER,
            colorbar_minor_formatter=DendrogramMatplotStyle._PERCENTAGE_FORMATTER,
        )

    __init__.__doc__ = MatplotStyle.__init__.__doc__ + __init__.__doc__

    def draw_leaf_names(self, *, names: Sequence[str]) -> None:
        """[see superclass]"""
        ax = self.ax
        y_axis = ax.yaxis
        y_axis.set_ticks(ticks=range(len(names)))
        y_axis.set_ticklabels(ticklabels=names)

    def _drawing_finalize(
        self,
        *,
        labels_name: Optional[str] = None,
        distance_name: Optional[str] = None,
        weights_name: Optional[str] = None,
        **kwargs,
    ) -> None:
        super()._drawing_finalize(colorbar_label=weights_name, **kwargs)

        ax = self.ax

        # configure the axes
        ax.ticklabel_format(axis="x", scilimits=(-3, 3))
        if distance_name:
            ax.set_xlabel(distance_name)
        if labels_name:
            ax.set_ylabel(labels_name)


__tracker.validate()

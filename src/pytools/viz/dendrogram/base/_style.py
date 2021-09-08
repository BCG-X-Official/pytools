"""
Base classes for dendrogram styles.
"""

import logging
import math
from abc import ABCMeta, abstractmethod
from typing import Any, Iterable, Optional, Sequence, Union

from matplotlib.axes import Axes
from matplotlib.colors import LogNorm

from pytools.api import AllTracker, inheritdoc
from pytools.viz import ColorbarMatplotStyle, DrawingStyle, MatplotStyle
from pytools.viz.color import ColorScheme, text_contrast_color
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

    def start_drawing(
        self,
        *,
        title: str,
        leaf_label: Optional[str] = None,
        distance_label: Optional[str] = None,
        weight_label: Optional[str] = None,
        max_distance: Optional[float] = None,
        n_leaves: Optional[int] = None,
        **kwargs: Any,
    ) -> None:
        """
        Prepare a new dendrogram for drawing, using the given title.

        :param title: the title of the chart
        :param leaf_label: the label for the leaf axis
        :param distance_label: the label for the distance axis
        :param weight_label: the label for the weight scale
        :param max_distance: the height (= maximum possible distance) of the dendrogram
        :param n_leaves: the number of leaves in the dendrogram
        :param kwargs: additional drawer-specific arguments
        """
        super().start_drawing(title=title, **kwargs)

    def finalize_drawing(
        self,
        *,
        leaf_label: Optional[str] = None,
        distance_label: Optional[str] = None,
        weight_label: Optional[str] = None,
        max_distance: Optional[float] = None,
        n_leaves: Optional[int] = None,
        **kwargs: Any,
    ) -> None:
        """
        Finalize the dendrogram, adding labels to the axes.

        :param leaf_label: the label for the leaf axis
        :param distance_label: the label for the distance axis
        :param weight_label: the label for the weight scale
        :param max_distance: the height (= maximum possible distance) of the dendrogram
        :param n_leaves: the number of leaves in the dendrogram
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
        :param n_leaves_right: the number of leaves in the left sub-tree
        :param weight: the weight of the parent node
        :param weight_cumulative: the cumulative weight of all nodes with a lower
            position index than the current one
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

    def draw_leaf_labels(
        self, *, names: Sequence[str], weights: Sequence[float]
    ) -> None:
        """[see superclass]"""

        _, text_height = self.text_dimensions("0")

        # only create tick locations where there is enough vertical space for the label
        tick_locations = list(self.get_ytick_locations(weights=weights))

        ticks, tick_labels = zip(
            *(
                (loc, name)
                for lo, loc, hi, name in zip(
                    [-math.inf, *tick_locations],
                    tick_locations,
                    [*tick_locations[1:], math.inf],
                    names,
                )
                if (hi - lo) / 2 >= text_height
            )
        )

        # set the tick locations and labels
        y_axis = self.ax.yaxis
        y_axis.set_ticks(ticks=ticks)
        y_axis.set_ticklabels(ticklabels=tick_labels)
        # y_axis.set_tick_params(left=False)

    def finalize_drawing(
        self,
        *,
        leaf_label: Optional[str] = None,
        distance_label: Optional[str] = None,
        weight_label: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """
        Finalize the dendrogram, adding labels to the axes.

        :param leaf_label: the label for the leaf axis
        :param distance_label: the label for the distance axis
        :param weight_label: the label for the weight scale
        :param kwargs: additional drawer-specific arguments
        """

        super().finalize_drawing(colorbar_label=weight_label)

        self.colorbar.ax.yaxis.set_ticks([0.01, 0.02, 0.05, 0.10, 0.20, 0.50, 1.00])

        ax = self.ax
        # configure the axes
        ax.ticklabel_format(axis="x", scilimits=(-3, 3))
        if distance_label:
            ax.set_xlabel(distance_label)
        if leaf_label:
            ax.set_ylabel(leaf_label)

    @abstractmethod
    def get_ytick_locations(
        self, *, weights: Sequence[float]
    ) -> Iterable[Union[int, float]]:
        """
        Get the tick locations for the y axis.

        :param weights: weights of all leaves
        :return: the tick locations for the y axis
        """
        pass

    def plot_weight_label(
        self,
        *,
        weight: float,
        x: float,
        y: float,
        w: float,
        h: float,
        fill_color: ColorScheme.RgbaColor,
    ) -> None:
        """
        Plot a weight label for a link leg.

        :param weight: the weight to be shown in the label
        :param x: the x location of the label area
        :param y: the y location of the label area
        :param w: the width of the label area
        :param h: the height of the label area
        :param fill_color: the fill color for the label background
        """

        weight_percent = weight * 100

        label = (
            f"{weight_percent:.2g}%"
            if weight_percent < 99.5
            else f"{round(weight_percent):.3g}%"
        )

        x_text = x + w / 2
        y_text = y + h / 2
        text_width, text_height = self.text_dimensions(text=label, x=x_text, y=y_text)
        if text_width <= w and text_height <= h:
            t = self.ax.text(
                x_text,
                y_text,
                label,
                ha="center",
                va="center",
                color=text_contrast_color(fill_color),
            )
            t.set_bbox(
                dict(
                    facecolor=fill_color,
                    linewidth=0.0,
                    pad=t.get_fontsize() * self._TEXT_PADDING_RATIO,
                )
            )


__tracker.validate()

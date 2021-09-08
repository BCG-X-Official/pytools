"""
Dendrogram styles.
"""

import logging
from typing import Any, Iterable, Optional, Sequence, TextIO, Union

import numpy as np
from matplotlib.axes import Axes

from ...api import AllTracker, inheritdoc
from ...text import CharacterMatrix
from .. import TextStyle
from ..color import ColorScheme
from .base import DendrogramMatplotStyle, DendrogramStyle

log = logging.getLogger(__name__)


#
# Exported names
#

__all__ = [
    "DendrogramLineStyle",
    "DendrogramHeatmapStyle",
    "DendrogramReportStyle",
]


#
# Ensure all symbols introduced below are included in __all__
#

__tracker = AllTracker(globals())


#
# Classes
#


@inheritdoc(match="[see superclass]")
class DendrogramLineStyle(DendrogramMatplotStyle):
    """
    Draws dendrograms as "classical" trees, using coloring lines along a color gradient
    to indicate leaf/branch weights.
    """

    def __init__(
        self,
        *,
        ax: Optional[Axes] = None,
        colors: Optional[ColorScheme] = None,
        min_weight: float = 0.01,
        padding: float = 0.1,
    ) -> None:
        """
        :param padding: vertical padding to apply between lines, as a multiple of
            100% feature weight
        """
        super().__init__(ax=ax, colors=colors, min_weight=min_weight)

        if not 0.0 <= padding <= 1.0:
            raise ValueError("arg padding must be in the range from 0.0 to 1.0")

        self.padding = padding

    __init__.__doc__ = DendrogramMatplotStyle.__init__.__doc__ + __init__.__doc__

    @classmethod
    def get_default_style_name(cls) -> str:
        """[see superclass]"""
        return f"{super().get_default_style_name()}_line"

    def start_drawing(
        self,
        *,
        title: str,
        max_distance: Optional[float] = None,
        n_leaves: Optional[int] = None,
        **kwargs: Any,
    ) -> None:
        """
        Prepare a new dendrogram for drawing, using the given title.

        :param title: the title of the chart
        :param max_distance: the height (= maximum possible distance) of the dendrogram
        :param n_leaves: the number of leaves in the dendrogram
        :param kwargs: additional drawer-specific arguments
        """
        super().start_drawing(
            title=title, max_distance=max_distance, n_leaves=n_leaves, **kwargs
        )

        ax = self.ax

        spines = ax.spines
        for side in ["left", "top", "right"]:
            spines[side].set_visible(False)

        margin_x = 0.01 * max_distance
        ax.set_xlim(0.0 - margin_x, max_distance + margin_x)

        if self.padding > 0.0:
            margin_y = 0.0
        else:
            spines["bottom"].set_visible(False)
            margin_y = 0.01

        ax.set_ylim(
            -0.5 * self.padding - margin_y,
            1.0 + (n_leaves - 0.5) * self.padding + margin_y,
        )

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
        """[see superclass]"""
        padding = self.padding
        y = weight_cumulative + leaf * padding
        self._draw_hline(
            x1=bottom, x2=top, y=y, weight=weight, max_height=weight + padding
        )

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
        """[see superclass]"""

        lo = weight_cumulative + first_leaf * self.padding
        hi = lo + weight + (n_leaves_left + n_leaves_right - 1) * self.padding

        self._draw_hline(
            x1=bottom,
            x2=top,
            y=(lo + hi - weight) / 2,
            weight=weight,
            max_height=hi - lo + self.padding,
        )

        if self.padding > 0:
            # draw a vertical connection line
            y_0 = lo + (n_leaves_left - 1) / 2 * self.padding
            y_1 = (
                weight_cumulative
                + weight
                + (first_leaf + n_leaves_left + (n_leaves_right - 1) / 2) * self.padding
            )
            self.ax.plot(
                (bottom, bottom), (y_0, y_1), color=self.colors.foreground, linewidth=1
            )

    def get_ytick_locations(
        self, *, weights: Sequence[float]
    ) -> Iterable[Union[int, float]]:
        """[see superclass]"""
        weights_array = np.array(weights)
        return (
            weights_array.cumsum()
            - weights_array / 2
            + np.arange(len(weights)) * self.padding
        )

    def _draw_hline(
        self, x1: float, x2: float, y: float, weight: float, max_height: float
    ) -> None:
        fill_color = self.color_for_value(weight)
        self.ax.set_xlim()
        middle = y + weight / 2
        self.ax.barh(
            y=middle,
            width=x2 - x1,
            height=weight,
            left=x1,
            color=fill_color,
            edgecolor=self.colors.foreground,
            linewidth=1,
        )

        self.plot_weight_label(
            weight=weight,
            x=x1,
            y=middle - max_height / 2,
            w=x2 - x1,
            h=max_height,
            fill_color=fill_color,
        )


@inheritdoc(match="[see superclass]")
class DendrogramHeatmapStyle(DendrogramMatplotStyle):
    """
    Draws dendrograms as a tree composed of color tiles, coloring tiles as a heat map
    indicating leaf/branch weights.
    """

    def draw_link_leg(
        self,
        *,
        bottom: float,
        top: float,
        leaf: int,
        weight: float,
        weight_cumulative: float,
        tree_height: float,
    ) -> None:
        """[see superclass]"""
        self._draw_hbar(
            x=bottom, w=top - bottom, y=weight_cumulative, h=weight, weight=weight
        )

    def draw_link_connector(
        self,
        *,
        bottom: float,
        top: int,
        first_leaf: int,
        n_leaves_left: int,
        n_leaves_right: float,
        weight: float,
        weight_cumulative: float,
        tree_height: float,
    ) -> None:
        """[see superclass]"""
        self._draw_hbar(
            x=bottom,
            w=top - bottom,
            y=weight_cumulative,
            h=weight,
            weight=weight,
        )

    def start_drawing(
        self,
        *,
        title: str,
        max_distance: Optional[float] = None,
        **kwargs: Any,
    ) -> None:
        """
        Prepare a new dendrogram for drawing, using the given title.

        :param title: the title of the chart
        :param max_distance: the height (= maximum possible distance) of the dendrogram
        :param kwargs: additional drawer-specific arguments
        """
        super().start_drawing(
            title=title,
            max_distance=max_distance,
            **kwargs,
        )

        ax = self.ax
        ax.margins(0)

        ax.set_xlim(0.0, max_distance)
        ax.set_ylim(0, 1)

    def get_ytick_locations(
        self, *, weights: Sequence[float]
    ) -> Iterable[Union[int, float]]:
        """[see superclass]"""
        weights_array = np.array(weights)
        return weights_array.cumsum() - weights_array / 2

    def _draw_hbar(self, x: float, y: float, w: float, h: float, weight: float) -> None:
        fill_color = self.color_for_value(weight)

        self.ax.barh(
            y=y,
            width=w,
            height=h,
            left=x,
            align="edge",
            color=fill_color,
            edgecolor=self.colors.foreground,
            linewidth=1,
        )

        self.plot_weight_label(weight=weight, x=x, y=y, w=w, h=h, fill_color=fill_color)


@inheritdoc(match="[see superclass]")
class DendrogramReportStyle(DendrogramStyle, TextStyle):
    """
    Renders dendrograms as ASCII graphics for inclusion in plain-text reports.
    """

    #: The default width of labels.
    DEFAULT_LABEL_WIDTH = 20

    #: The number of characters that will be allocated for the label column,
    #: including the weight.
    label_width: int

    #: Maximum number of text lines to output including the title;
    #: additional lines of the dendrogram will be clipped (optional).
    max_height: int

    def __init__(
        self,
        out: TextIO = None,
        width: int = 80,
        label_width: Optional[int] = None,
        max_height: int = 100,
    ) -> None:
        """
        :param label_width: the number of characters that will be allocated for the
            label column, including the weight (optional; defaults to
            %DEFAULT_LABEL_WIDTH% characters or half of arg `width`,
            whichever is smaller)
        :param max_height: maximum number of text lines to output including the title;
            additional lines of the dendrogram will be clipped (default: 100)
        """
        super().__init__(out=out, width=width)
        if max_height <= 0:
            raise ValueError(
                f"arg max_height={max_height} expected to be a positive integer"
                f" {max_height}"
            )
        if label_width is not None and label_width > width // 2:
            raise ValueError(
                f"arg label_width={label_width} must be half or less of arg "
                f"width={width}"
            )
        self.max_height = max_height
        self.label_width = (
            min(DendrogramReportStyle.DEFAULT_LABEL_WIDTH, width // 2)
            if label_width is None
            else label_width
        )
        self._dendrogram_right = width - self.label_width
        self._char_matrix = None
        self._n_labels = None

    __init__.__doc__ = TextStyle.__init__.__doc__ + __init__.__doc__.replace(
        "%DEFAULT_LABEL_WIDTH%", str(DEFAULT_LABEL_WIDTH)
    )

    def draw_leaf_labels(
        self, *, names: Sequence[str], weights: Sequence[float]
    ) -> None:
        """[see superclass]"""

        matrix = self._char_matrix
        n_labels = len(names)
        if n_labels > self.max_height:
            n_labels = self.max_height - 1
            matrix[n_labels, :] = f"{'clipped':~^{self.width}s}\n"
        self._n_labels = n_labels
        name_width = self.__weight_column
        label_width = self.label_width
        for row, name, weight in zip(range(n_labels), names, weights):
            matrix[row, :name_width] = name + " "
            matrix[row, name_width:label_width] = f"{weight * 100:3.0f}%"

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
        """[see superclass]"""

        # determine the y coordinate in the character matrix
        line_y = int(leaf)

        # if leaf is in between two leaves, we want to draw a line in
        # between two text lines (using an underscore symbol)
        is_in_between_line = round(leaf * 2) & 1

        # draw the link leg in the character matrix
        self._char_matrix[
            line_y + is_in_between_line,
            self._x_pos(bottom, tree_height) : self._x_pos(top, tree_height),
        ] = (
            "_" if is_in_between_line else "-"
        )

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
        """[see superclass]"""

        y1 = first_leaf + n_leaves_left // 2
        y2 = first_leaf + n_leaves_left + (n_leaves_right - 1) // 2

        self.draw_link_leg(
            bottom=bottom,
            top=top,
            leaf=(first_leaf - 0.5) + (n_leaves_left + n_leaves_right) / 2,
            weight=weight,
            weight_cumulative=weight_cumulative,
            tree_height=tree_height,
        )

        x = self._x_pos(bottom, tree_height)
        matrix = self._char_matrix
        if y2 - y1 > 1:
            matrix[(y1 + 1) : y2, x] = "|"
        matrix[y1, x] = "/"
        matrix[y2, x] = "\\"

    def start_drawing(self, *, title: str, **kwargs: Any) -> None:
        """
        Prepare a new dendrogram for drawing, using the given title.

        :param title: the title of the chart
        :param kwargs: additional drawer-specific arguments
        """
        super().start_drawing(
            title=title,
            **kwargs,
        )
        self._char_matrix = CharacterMatrix(
            n_rows=self.max_height, n_columns=self.width
        )

    def finalize_drawing(self, **kwargs: Any) -> None:
        """
        Finalize the dendrogram, adding labels to the axes.

        :param kwargs: additional drawer-specific arguments
        """
        try:
            super().finalize_drawing(**kwargs)
            for row in reversed(range(self._n_labels + 1)):
                self.out.write(f"{self._char_matrix[row, :]}\n")
        finally:
            self._char_matrix = None
            self._n_labels = None

    def _x_pos(self, h: float, h_max: float) -> int:
        # calculate the horizontal position in the character grid,
        # ensuring that h=h_max still yields a position inside the grid (factor 0.99999)
        return self.label_width + int(self._dendrogram_right * h / h_max * 0.99999)

    @property
    def __weight_column(self) -> int:
        return self.label_width - 5


__tracker.validate()

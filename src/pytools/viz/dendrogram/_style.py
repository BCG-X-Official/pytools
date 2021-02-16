"""
Dendrogram styles.
"""

import logging
from typing import Optional, Sequence, TextIO

from .. import TextStyle
from ..color import text_contrast_color
from .base import DendrogramMatplotStyle, DendrogramStyle
from pytools.api import AllTracker, inheritdoc
from pytools.text import CharacterMatrix

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

    @classmethod
    def get_default_style_name(cls) -> str:
        """[see superclass]"""
        return f"{super().get_default_style_name()}_line"

    def draw_link_leg(
        self, bottom: float, top: float, leaf: float, weight: float, tree_height
    ) -> None:
        """[see superclass]"""
        self._draw_line(x1=bottom, x2=top, y1=leaf, y2=leaf, weight=weight)

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
        """[see superclass]"""
        self._draw_line(
            x1=bottom,
            x2=bottom,
            y1=first_leaf + (n_leaves_left - 1) / 2,
            y2=first_leaf + n_leaves_left + (n_leaves_right - 1) / 2,
            weight=weight,
        )

        self.draw_link_leg(
            bottom=bottom,
            top=top,
            leaf=(first_leaf + (n_leaves_left + n_leaves_right - 1) / 2),
            weight=weight,
            tree_height=0,
        )

    def _draw_line(
        self, x1: float, x2: float, y1: float, y2: float, weight: float
    ) -> None:
        self.ax.plot((x1, x2), (y1, y2), color=self.color_for_value(weight))


@inheritdoc(match="[see superclass]")
class DendrogramHeatmapStyle(DendrogramMatplotStyle):
    """
    Draws dendrograms as a tree composed of color tiles, coloring tiles as a heat map
    indicating leaf/branch weights.
    """

    def draw_link_leg(
        self, bottom: float, top: float, leaf: int, weight: float, tree_height: float
    ) -> None:
        """[see superclass]"""
        self._draw_hbar(x=bottom, w=top - bottom, y=leaf, h=1, weight=weight)

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
        """[see superclass]"""
        self._draw_hbar(
            x=bottom,
            w=top - bottom,
            y=first_leaf,
            h=n_leaves_left + n_leaves_right,
            weight=weight,
        )

    def start_drawing(self, title: str, **kwargs) -> None:
        """[see superclass]"""
        super().start_drawing(title=title, **kwargs)
        self.ax.margins(0, 0)

    def _draw_hbar(self, x: float, y: float, w: float, h: float, weight: float) -> None:
        fill_color = self.color_for_value(weight)

        self.ax.barh(
            y=[y - 0.5],
            width=[w],
            height=[h],
            left=[x],
            align="edge",
            color=fill_color,
            edgecolor=self.colors.foreground,
            linewidth=1,
        )

        weight_percent = weight * 100
        label = (
            f"{weight_percent:.2g}%"
            if weight_percent < 99.5
            else f"{round(weight_percent):.3g}%"
        )

        x_text = x + w / 2
        y_text = y + (h - 1) / 2
        text_width, _ = self.text_dimensions(text=label, x=x_text, y=y_text)

        if text_width <= w:
            self.ax.text(
                x_text,
                y_text,
                label,
                ha="center",
                va="center",
                color=text_contrast_color(fill_color),
            )


@inheritdoc(match="[see superclass]")
class DendrogramReportStyle(TextStyle, DendrogramStyle):
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

    def draw_leaf_names(self, *, names: Sequence[str]) -> None:
        """[see superclass]"""

        matrix = self._char_matrix
        n_labels = len(names)
        if n_labels > self.max_height:
            n_labels = self.max_height - 1
            matrix[n_labels, :] = f"{'clipped':~^{self.width}s}\n"
        self._n_labels = n_labels
        label_width = self.__weight_column
        for row, label in enumerate(names[:n_labels]):
            matrix[row, :label_width] = label + " "

    def draw_link_leg(
        self, bottom: float, top: float, leaf: float, weight: float, tree_height: float
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

        # if we're in a leaf, we can draw the weight next to he label
        if bottom == 0:
            self._char_matrix[
                line_y, self.__weight_column : self.label_width
            ] = f"{weight * 100:3.0f}%"

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
        """[see superclass]"""

        y1 = first_leaf + n_leaves_left // 2
        y2 = first_leaf + n_leaves_left + (n_leaves_right - 1) // 2

        self.draw_link_leg(
            bottom=bottom,
            top=top,
            leaf=(first_leaf - 0.5) + (n_leaves_left + n_leaves_right) / 2,
            weight=weight,
            tree_height=tree_height,
        )

        x = self._x_pos(bottom, tree_height)
        matrix = self._char_matrix
        if y2 - y1 > 1:
            matrix[(y1 + 1) : y2, x] = "|"
        matrix[y1, x] = "/"
        matrix[y2, x] = "\\"

    def start_drawing(self, title: str, **kwargs) -> None:
        """[see superclass]"""
        super().start_drawing(title=title, **kwargs)
        self._char_matrix = CharacterMatrix(
            n_rows=self.max_height, n_columns=self.width
        )

    def finalize_drawing(self, **kwargs) -> None:
        """[see superclass]"""
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

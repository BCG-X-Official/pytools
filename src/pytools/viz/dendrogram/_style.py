"""
Dendrogram styles.

The dendrogram styles are given as a parameter to a
:class:`.DendrogramDrawer` and determine the style of the
plot.

:class:`~BaseDendrogramMatplotStyle` is a an abstract base class for styles using
matplotlib.

:class:`~DendrogramLineStyle` renders dendrogram trees in the classical style as a line
drawing.

:class:`~DendrogramHeatmapStyle` renders dendrogram trees as a combination of tree and
heatmap for better visibility of feature importance.

:class:`~DendrogramReportStyle` renders dendrogram trees as ASCII graphics for
inclusion in text reports.
"""

import logging
from abc import ABCMeta, abstractmethod
from typing import Optional, Sequence, TextIO, Union

from matplotlib.axes import Axes
from matplotlib.colors import Colormap, LogNorm

from pytools.viz import (
    ColorbarMatplotStyle, DrawStyle, MatplotStyle, PercentageFormatter, RGBA_WHITE,
    TextStyle,
)
from pytools.viz.text import CharacterMatrix

log = logging.getLogger(__name__)


#
# Classes
#


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


class BaseDendrogramMatplotStyle(
    DendrogramStyle, ColorbarMatplotStyle, metaclass=ABCMeta
):
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
            colorbar_major_formatter=BaseDendrogramMatplotStyle._PERCENTAGE_FORMATTER,
            colorbar_minor_formatter=BaseDendrogramMatplotStyle._PERCENTAGE_FORMATTER,
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


class DendrogramLineStyle(BaseDendrogramMatplotStyle):
    """
    Plot dendrograms in the classical style, as a coloured tree diagram.
    """

    def draw_link_leg(
        self, bottom: float, top: float, leaf: float, weight: float, tree_height
    ) -> None:
        """
        Draw a horizontal link in the dendrogram between a node and one of its children.

        See :func:`~yieldengine.dendrogram.DendrogramStyle.draw_link_leg` for the
        documentation of the abstract method.

        :param tree_height:
        :param bottom: the x coordinate of the child node
        :param top: the x coordinate of the parent node
        :param leaf: the index of the first leaf in the current sub-tree
        :param weight: the weight of the child node
        """
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
        """
        Draw a vertical link between two sibling nodes and the outgoing vertical line.

        See :func:`~yieldengine.dendrogram.DendrogramStyle.draw_link_connector` for the
        documentation of the abstract method.

        :param bottom: the clustering level (i.e. similarity) of the child nodes
        :param top: the clustering level (i.e. similarity) of the parent node
        :param first_leaf: the index of the first leaf in the left sub-tree
        :param n_leaves_left: the number of leaves in the left sub-tree
        :param n_leaves_right: the number of leaves in the right sub-tree
        :param weight: the weight of the parent node
        :param tree_height: the total height of the tree
        """
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
        self.ax.plot((x1, x2), (y1, y2), color=self.value_color(weight))


class DendrogramHeatmapStyle(BaseDendrogramMatplotStyle):
    """
    Plot dendrograms with a heat map style.
    """

    def _drawing_start(self, title: str) -> None:
        """
        Called once by the drawer when starting to draw a new dendrogram.
        :param title: the title of the dendrogram
        """
        super()._drawing_start(title=title)
        self.ax.margins(0, 0)

    def draw_link_leg(
        self, bottom: float, top: float, leaf: int, weight: float, tree_height: float
    ) -> None:
        """
        Draw a horizontal box in the dendrogram for a leaf.

        See :func:`~yieldengine.dendrogram.DendrogramStyle.draw_link_leg` for the
        documentation of the abstract method.

        :param tree_height:
        :param bottom: the x coordinate of the child node
        :param top: the x coordinate of the parent node
        :param leaf: the index of the first leaf in the current sub-tree
        :param weight: the weight of the child node
        """
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
        """
        Draw a link between a node and its two children as a box.

        See :func:`~yieldengine.dendrogram.DendrogramStyle.draw_link_connector` for the
        documentation of the abstract method.

        :param bottom: the clustering level (i.e. similarity) of the child nodes
        :param top: the clustering level (i.e. similarity) of the parent node
        :param first_leaf: the index of the first leaf in the left sub-tree
        :param n_leaves_left: the number of leaves in the left sub-tree
        :param n_leaves_right: the number of leaves in the right sub-tree
        :param weight: the weight of the parent node
        :param tree_height: the total height of the tree
        """
        self._draw_hbar(
            x=bottom,
            w=top - bottom,
            y=first_leaf,
            h=n_leaves_left + n_leaves_right,
            weight=weight,
        )

    def _draw_hbar(self, x: float, y: float, w: float, h: float, weight: float) -> None:
        """
        Draw a box.

        :param x: left x position of the box
        :param y: top vertical position of the box
        :param w: the width of the box
        :param h: the height of the box
        :param weight: the weight used to compute the color of the box
        """
        fill_color = self.value_color(weight)

        self.ax.barh(
            y=[y - 0.5],
            width=[w],
            height=[h],
            left=[x],
            align="edge",
            color=fill_color,
            edgecolor=RGBA_WHITE,
            linewidth=1,
        )

        weight_percent = weight * 100
        label = (
            f"{weight_percent:.2g}%"
            if round(weight_percent, 1) < 100
            else f"{weight_percent:.3g}%"
        )

        x_text = x + w / 2
        y_text = y + (h - 1) / 2
        text_width, _ = self.text_size(text=label, x=x_text, y=y_text)

        if text_width <= w:
            self.ax.text(
                x_text,
                y_text,
                label,
                ha="center",
                va="center",
                color=self.text_contrast_color(fill_color),
            )


class DendrogramReportStyle(TextStyle, DendrogramStyle):
    """
    Dendrogram rendered as text.
    """

    _DEFAULT_LABEL_WIDTH = 20

    def __init__(
        self,
        out: TextIO = None,
        width: int = 80,
        label_width: Optional[int] = None,
        max_height: int = 100,
    ) -> None:
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
        self._max_height = max_height
        self._dendrogram_left = (
            min(DendrogramReportStyle._DEFAULT_LABEL_WIDTH, width // 2)
            if label_width is None
            else label_width
        )
        self._dendrogram_right = width - self._dendrogram_left
        self._char_matrix = None
        self._n_labels = None

    def _drawing_start(self, title: str) -> None:
        # write the title
        self.out.write(f"{f' {title} ':*^{self.width}s}\n")
        self._char_matrix = CharacterMatrix(
            n_rows=self._max_height, n_columns=self.width
        )

    def _drawing_finalize(self) -> None:
        """Finalize writing the text."""
        try:
            super()._drawing_finalize()
            for row in reversed(range(self._n_labels + 1)):
                self.out.write(f"{self._char_matrix[row, :]}\n")
        finally:
            self._char_matrix = None
            self._n_labels = None

    def draw_leaf_labels(self, labels: Sequence[str]) -> None:
        """
        Draw the feature labels in the drawing.

        :param labels: the name of the features
        """
        matrix = self._char_matrix
        n_labels = len(labels)
        if n_labels > self._max_height:
            n_labels = self._max_height - 1
            matrix[n_labels, :] = f"{'clipped':~^{self.width}s}\n"
        self._n_labels = n_labels
        label_width = self._weight_column
        for row, label in enumerate(labels[:n_labels]):
            matrix[row, :label_width] = label + " "

    @property
    def _weight_column(self) -> int:
        return self._dendrogram_left - 5

    def draw_link_leg(
        self, bottom: float, top: float, leaf: float, weight: float, tree_height: float
    ) -> None:
        """
        Draw a horizontal link in the dendrogram between a node and one of its children.

        :param tree_height:
        :param bottom: the x coordinate of the child node
        :param top: the x coordinate of the parent node
        :param leaf: the index of the first leaf in the current sub-tree
        :param weight: the weight of the child node
        """

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
                line_y, self._weight_column : self._dendrogram_left
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
        """
        Draw a vertical link between two sibling nodes and the outgoing vertical line.

        See :func:`.DendrogramStyle
        .draw_link_connector` for the documentation of the abstract method.

        :param bottom: the clustering level (i.e. similarity) of the child nodes
        :param top: the clustering level (i.e. similarity) of the parent node
        :param first_leaf: the index of the first leaf in the left sub-tree
        :param n_leaves_left: the number of leaves in the left sub-tree
        :param n_leaves_right: the number of leaves in the right sub-tree
        :param weight: the weight of the parent node
        :param tree_height: the total height of the tree
        """

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

    def _x_pos(self, h: float, h_max: float) -> int:
        # calculate the horizontal position in the character grid,
        # ensuring that h=h_max still yields a position inside the grid (factor 0.99999)
        return self._dendrogram_left + int(self._dendrogram_right * h / h_max * 0.99999)

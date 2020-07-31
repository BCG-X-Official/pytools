"""
Core implementation of :mod:`gamma.viz.matrix`
"""

import logging
from abc import ABCMeta, abstractmethod
from typing import *

import numpy as np
import pandas as pd
from matplotlib.axes import Axes, mticker
from matplotlib.axis import Axis
from matplotlib.colors import Colormap, Normalize
from matplotlib.ticker import Formatter, FuncFormatter

from gamma.common.typing import Function
from gamma.viz import (
    ColorbarMatplotStyle,
    Drawer,
    DrawStyle,
    PercentageFormatter,
    RGBA_WHITE,
    TextStyle,
)

log = logging.getLogger(__name__)

__all__ = [
    "MatrixDrawer",
    "MatrixMatplotStyle",
    "MatrixReportStyle",
    "MatrixStyle",
    "PercentageMatrixMatplotStyle",
]


#
# Style classes
#


class MatrixStyle(DrawStyle, metaclass=ABCMeta):
    """
    Base class for matrix drawer styles.
    """

    @abstractmethod
    def draw_matrix(self, matrix: pd.DataFrame) -> None:
        """
        Draw the matrix.
        :param matrix: the matrix represented as a data frame
        """
        pass


class MatrixMatplotStyle(MatrixStyle, ColorbarMatplotStyle):
    """
    Matplot style for matrices.

    Numerical values of matrix cells are rendered as colours, with a colour bar
    attached as a legend.
    """

    def __init__(
        self,
        *,
        ax: Optional[Axes] = None,
        colormap_normalize: Optional[Normalize] = None,
        colormap: Optional[Union[str, Colormap]] = None,
        colorbar_label: Optional[str] = None,
        colorbar_major_formatter: Optional[Formatter] = None,
        colorbar_minor_formatter: Optional[Formatter] = None,
        max_ticks: Optional[Tuple[int, int]] = None,
        cell_format: Union[str, Formatter, Function] = None,
        **kwargs,
    ):
        """
        :param max_ticks: the maximum number of ticks to put on the x and y axis; \
            ``None`` to determine number of labels automatically (default: ``None``)
        :param cell_format: optional string format, function, or \
            :class:`~matplotlib.ticker.Formatter` for annotating each matrix cell with \
            its value, if sufficient space is available; don't annotate cells if no \
            formatter is provided. String format should be a new-style python format \
            string, e.g., ``{:.3g}``. Function must take one positional argument \
            which is the value to be formatted, e.g., \
            ``lambda x: f"{x * 100:.3g}%"``. \
            If no colorbar major formatter is specified, the cell format is also used \
            for this.
        """
        if isinstance(cell_format, str):
            cell_formatter = FuncFormatter(func=lambda x, _: cell_format.format(x))
        elif isinstance(cell_format, Function):
            cell_formatter = FuncFormatter(func=lambda x, _: cell_format(x))
        else:
            cell_formatter = cell_format

        if colorbar_major_formatter is None:
            colorbar_major_formatter = cell_formatter

        super().__init__(
            colormap_normalize=colormap_normalize
            if colormap_normalize is not None
            else Normalize(),
            colormap=colormap,
            colorbar_label=colorbar_label,
            colorbar_major_formatter=colorbar_major_formatter,
            colorbar_minor_formatter=colorbar_minor_formatter,
            ax=ax,
            **kwargs,
        )

        if max_ticks is not None and not (
            isinstance(max_ticks, Tuple) and len(max_ticks) == 2
        ):
            raise ValueError(
                f"arg n_labels={max_ticks} expected to be a tuple of size 2"
            )
        self._max_ticks = max_ticks
        self._cell_formatter = cell_formatter

    __init__.__doc__ = ColorbarMatplotStyle.__init__.__doc__ + __init__.__doc__

    # noinspection PyMissingOrEmptyDocstring
    def draw_matrix(self, matrix: pd.DataFrame) -> None:

        ax: Axes = self.ax
        self.ax.margins(0, 0)

        # store values locally so we can label the matrix cells when finalizing the plot
        data = matrix.values
        ax.imshow(
            data,
            cmap=self.colormap,
            norm=self.colormap_normalize,
            origin="upper",
            interpolation="nearest",
            aspect="equal",
        )

        # determine if a number of labels has been configured for this style
        max_ticks = self._max_ticks
        if max_ticks is None:
            max_x_ticks = max_y_ticks = None
        else:
            max_x_ticks, max_y_ticks = max_ticks

        # rotate x labels if they are categorical
        tick_params = {False: {}, True: dict(rotation=45, ha="right")}

        def _set_ticks(index: pd.Index, max_bins: int, axis: Axis, rotate: bool):
            # set the x and y ticks

            # determine number of bins
            if max_bins is not None:
                n_bins = max_bins
            elif index.is_numeric():
                n_bins = "auto"
            else:
                n_bins = len(index)

            locator = mticker.MaxNLocator(
                nbins=n_bins, steps=[1, 2, 5, 10], integer=True, prune="both"
            )
            axis.set_major_locator(locator)

            tick_locations: np.ndarray = axis.get_ticklocs()
            if len(index) > len(tick_locations):
                # we can plot only selected tick labels: look up labels for the
                # visible tick indices
                labels = index[tick_locations.astype(int)]
            else:
                # we can plot all tick labels
                labels = index.values

            axis.set_ticklabels(labels, **tick_params[rotate])

        _set_ticks(
            index=matrix.columns,
            max_bins=max_x_ticks,
            axis=ax.xaxis,
            rotate=not matrix.columns.is_numeric(),
        )
        _set_ticks(
            index=matrix.index, max_bins=max_y_ticks, axis=ax.yaxis, rotate=False
        )

        # get the matrix size
        n_rows = data.shape[0]
        n_columns = data.shape[1]

        # only draw labels if minimal height/width is available
        if self._cell_formatter is not None and all(
            size <= 1 for size in self.text_size("0")
        ):
            # draw the axis to ensure we'll get correct coordinates
            ax.draw(self.renderer)

            # get the cell formatter as a local field
            cell_formatter = self._cell_formatter

            # render the text for every box where the text fits
            for y in range(n_rows):
                for x in range(n_columns):
                    x_text = x
                    y_text = y
                    cell_value = data[y, x]
                    label = cell_formatter(cell_value)
                    text_width, _ = self.text_size(text=label, x=x_text, y=y_text)

                    if text_width > 1:
                        # show ellipsis in cells where the text does not fit
                        label = "…"

                    self.ax.text(
                        x=x_text,
                        y=y_text,
                        s=label,
                        ha="center",
                        va="center",
                        color=(self.text_contrast_color(self.value_color(cell_value))),
                    )

        # hide spines
        for edge, spine in ax.spines.items():
            spine.set_visible(False)

        # create a white grid using minor tick positions
        ax.set_xticks(np.arange(n_columns + 1) - 0.5, minor=True)
        ax.set_yticks(np.arange(n_rows + 1) - 0.5, minor=True)
        ax.grid(which="minor", color=RGBA_WHITE, linestyle="-", linewidth=2)
        ax.tick_params(which="minor", bottom=False, left=False)

    draw_matrix.__doc__ = MatrixStyle.draw_matrix.__doc__


class PercentageMatrixMatplotStyle(MatrixMatplotStyle):
    """
    A matrix plot where all values are percentages.

    Annotates matrix cells with percentage values.
    """

    def __init__(
        self,
        *,
        ax: Optional[Axes] = None,
        colormap_normalize: Optional[Normalize] = None,
        colormap: Optional[Union[str, Colormap]] = None,
        colorbar_label: Optional[str] = None,
        max_ticks: Optional[Tuple[int, int]] = None,
        **kwargs,
    ):
        if any(
            field in kwargs
            for field in [
                "colorbar_major_formatter",
                "colorbar_minor_formatter",
                "cell_format",
            ]
        ):
            raise ValueError(
                f"arg cell_format is not supported by class {type(self).__name__}"
            )
        super().__init__(
            ax=ax,
            colormap_normalize=colormap_normalize,
            colormap=colormap,
            colorbar_label=colorbar_label,
            max_ticks=max_ticks,
            colorbar_major_formatter=PercentageFormatter(),
            colorbar_minor_formatter=None,
            cell_format=lambda x: f"{x * 100:.2g}"
            if abs(np.round(x, 2)) < 1.0
            else f"{np.round(x * 100):.3g}",
            **kwargs,
        )


class MatrixReportStyle(MatrixStyle, TextStyle):
    """
    Text report style for matrices.
    """

    # noinspection PyMissingOrEmptyDocstring
    def draw_matrix(self, matrix: pd.DataFrame):
        matrix.to_string(buf=self.out, line_width=self.width)

    draw_matrix.__doc__ = MatrixStyle.draw_matrix.__doc__


#
# Drawer classes
#


class MatrixDrawer(Drawer[pd.DataFrame, MatrixStyle]):
    """
    Drawer for matrices of numerical values.

    Comes with three pre-defined styles:
    - ``matplot``: matplotlib plot of the matrix using a default \
        :class:`gamma.viz.matrix.MatrixMatplotStyle`
    - ``matplot%``: matplotlib plot of matrix with percentage annotations, \
        using a default :class:`gamma.viz.matrix.PercentageMatrixMatplotStyle`
    - ``text``: print the matrix to stdout, using a default \
        :class:`gamma.viz.matrix.MatrixReportStyle`
    """

    _STYLES = {
        "matplot": MatrixMatplotStyle,
        "matplot%": PercentageMatrixMatplotStyle,
        "text": MatrixReportStyle,
    }

    @classmethod
    def _get_style_dict(cls) -> Mapping[str, Type[MatrixStyle]]:
        return MatrixDrawer._STYLES

    def _draw(self, data: pd.DataFrame) -> None:
        # draw the matrix
        self.style.draw_matrix(data)

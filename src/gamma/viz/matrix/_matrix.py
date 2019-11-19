"""
Core implementation of :mod:`gamma.viz.matrix`
"""

import logging
from abc import ABC, abstractmethod
from typing import *

import pandas as pd
from matplotlib.axes import Axes, mticker
from matplotlib.colors import Colormap, Normalize
from matplotlib.ticker import Formatter

from gamma.viz import ColorbarMatplotStyle, Drawer, DrawStyle, TextStyle

log = logging.getLogger(__name__)

__all__ = ["MatrixDrawer", "MatrixMatplotStyle", "MatrixReportStyle", "MatrixStyle"]


class MatrixStyle(DrawStyle, ABC):
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
        max_ticks: Optional[Tuple[float, float]] = None,
        colormap_normalize: Optional[Normalize] = None,
        colormap: Optional[Union[str, Colormap]] = None,
        colorbar_label: Optional[str] = None,
        colorbar_major_formatter: Optional[Formatter] = None,
        colorbar_minor_formatter: Optional[Formatter] = None,
        ax: Optional[Axes] = None,
        **kwargs,
    ):
        """
        :param max_ticks: the maximum number of ticks to put on the x and y axis; \
            `None` to determine number of labels automatically (default: `None`)
        """
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
        self.max_ticks = max_ticks

    __init__.__doc__ += ColorbarMatplotStyle.__init__.__doc__

    # noinspection PyMissingOrEmptyDocstring
    def draw_matrix(self, matrix: pd.DataFrame) -> None:
        ax = self.ax
        ax.imshow(
            matrix.values,
            cmap=self.colormap,
            norm=self.colormap_normalize,
            origin="upper",
            interpolation="nearest",
            aspect="equal",
        )

        # determine if a number of labels has been configured for this style
        n_ticks = self.max_ticks
        if n_ticks is None:
            x_bins = y_bins = None
        else:
            x_bins, y_bins = n_ticks

        # set the number of x and y ticks
        ax.xaxis.set_major_locator(
            mticker.MaxNLocator(
                nbins=x_bins if x_bins is not None else "auto",
                steps=[1, 2, 5, 10],
                integer=True,
                prune="lower",
            )
        )
        ax.yaxis.set_major_locator(
            mticker.MaxNLocator(
                nbins=y_bins if y_bins is not None else "auto",
                steps=[1, 2, 5, 10],
                integer=True,
                prune="lower",
            )
        )
        ax.set_xticklabels(matrix.columns)
        ax.set_yticklabels(matrix.index)

    draw_matrix.__doc__ = MatrixStyle.draw_matrix.__doc__


class MatrixReportStyle(MatrixStyle, TextStyle):
    """
    Text report style for matrices.
    """

    # noinspection PyMissingOrEmptyDocstring
    def draw_matrix(self, matrix: pd.DataFrame):
        matrix.to_string(buf=self.out, line_width=self.width)

    draw_matrix.__doc__ = MatrixStyle.draw_matrix.__doc__


class MatrixDrawer(Drawer[pd.DataFrame, MatrixStyle]):
    """
    Drawer for matrices of numerical values.
    """

    _STYLES = {"matplot": MatrixMatplotStyle, "text": MatrixReportStyle}

    @classmethod
    def _get_style_dict(cls) -> Mapping[str, Type[MatrixStyle]]:
        return MatrixDrawer._STYLES

    def _draw(self, data: pd.DataFrame) -> None:
        # draw the matrix
        self.style.draw_matrix(data)

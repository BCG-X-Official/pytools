"""
Core implementation of :mod:`gamma.viz.matrix`
"""

import logging
from abc import ABC, abstractmethod
from typing import *

import numpy as np
import pandas as pd
from matplotlib.axes import Axes, mticker
from matplotlib.axis import Axis
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
        max_ticks: Optional[Tuple[int, int]] = None,
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

        ax: Axes = self.ax
        ax.imshow(
            matrix.values,
            cmap=self.colormap,
            norm=self.colormap_normalize,
            origin="upper",
            interpolation="nearest",
            aspect="equal",
        )

        # determine if a number of labels has been configured for this style
        max_ticks = self.max_ticks
        if max_ticks is None:
            max_x_ticks = max_y_ticks = None
        else:
            max_x_ticks, max_y_ticks = max_ticks

        # rotate x labels if they are categorical
        if not matrix.columns.is_numeric():
            ax.tick_params(axis="x", labelrotation=45)

        # set the number of x and y ticks

        def _set_ticks(index: pd.Index, max_bins: int, axis: Axis):
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
                axis.set_ticklabels(index[tick_locations.astype(int)])
            else:
                # we can plot all tick labels
                axis.set_ticklabels(index.values)

        _set_ticks(index=matrix.columns, max_bins=max_x_ticks, axis=ax.xaxis)
        _set_ticks(index=matrix.index, max_bins=max_y_ticks, axis=ax.yaxis)

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

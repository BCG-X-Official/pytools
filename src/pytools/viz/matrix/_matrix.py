"""
Core implementation of :mod:`pytools.viz.matrix`.
"""

import logging
from typing import Any, Callable, Dict, Iterable, Optional, Tuple, Type, Union

import numpy as np
import pandas as pd
from matplotlib.axes import Axes, mticker
from matplotlib.axis import Axis
from matplotlib.colors import Normalize
from matplotlib.ticker import Formatter, FuncFormatter

from .. import ColorbarMatplotStyle, Drawer, TextStyle
from ..color import ColorScheme, text_contrast_color
from ..util import PercentageFormatter
from .base import MatrixStyle
from pytools.api import AllTracker, inheritdoc

log = logging.getLogger(__name__)


#
# exported names
#

__all__ = [
    "MatrixMatplotStyle",
    "PercentageMatrixMatplotStyle",
    "MatrixReportStyle",
    "MatrixDrawer",
]


#
# Ensure all symbols introduced below are included in __all__
#

__tracker = AllTracker(globals())


#
# Classes
#


@inheritdoc(match="[see superclass]")
class MatrixMatplotStyle(MatrixStyle, ColorbarMatplotStyle):
    """
    Matplot style for matrices.

    Numerical values of matrix cells are rendered as colors from a color map,
    with a color bar attached as a legend.

    Matrix cells will be annotated with their values if a *cell format* is specified.
    Cell formats can be defined in different ways:

    - a new-style Python format string, e.g., ``{:.3g}``
    - a function accepting the value to be formatted as its only positional argument,
      e.g., ``lambda x: f"{x * 100:.3g}%"``
    - a :class:`~matplotlib.ticker.Formatter` instance
    """

    #: The maximum number of ticks to put on the x and y axis;
    #: ``None`` to determine the number of ticks automatically.
    max_ticks: Optional[Tuple[int, int]]

    #: Formatter for annotating each matrix cell with its value; if ``None``,
    #: no cells are annotated.
    cell_formatter: Optional[Formatter]

    def __init__(
        self,
        *,
        ax: Optional[Axes] = None,
        colors: Optional[ColorScheme] = None,
        colormap_normalize: Optional[Normalize] = None,
        colorbar_major_formatter: Optional[Formatter] = None,
        colorbar_minor_formatter: Optional[Formatter] = None,
        max_ticks: Optional[Tuple[int, int]] = None,
        cell_format: Union[str, Formatter, Callable[[Any], str], None] = None,
        **kwargs,
    ) -> None:
        """
        :param max_ticks: the maximum number of ticks to put on the x and y axis;
            ``None`` to determine the number of ticks automatically (default: ``None``)
        :param cell_format: format for annotating each matrix cell with
            its value if sufficient space is available (optional – do not annotate
            cells if omitted);
            if no colorbar major formatter is specified, use the cell format also
            as the colorbar major formatter
        """
        if cell_format is None:
            cell_formatter = None
        elif isinstance(cell_format, str):
            cell_formatter = FuncFormatter(func=lambda x, _: cell_format.format(x))
        elif isinstance(cell_format, Formatter):
            cell_formatter = cell_format
        elif callable(cell_format):
            cell_formatter = FuncFormatter(func=lambda x, _: cell_format(x))
        else:
            raise TypeError(
                "arg cell_format must be a format string, a Formatter, or a callable, "
                f"but a {type(cell_format).__name__} was passed"
            )

        if colorbar_major_formatter is None:
            colorbar_major_formatter = cell_formatter

        super().__init__(
            ax=ax,
            colors=colors,
            colormap_normalize=(
                colormap_normalize if colormap_normalize is not None else Normalize()
            ),
            colorbar_major_formatter=colorbar_major_formatter,
            colorbar_minor_formatter=colorbar_minor_formatter,
            **kwargs,
        )

        if max_ticks is not None and not (
            isinstance(max_ticks, Tuple)
            and len(max_ticks) == 2
            and all(isinstance(x, int) for x in max_ticks)
        ):
            raise ValueError(
                f"arg max_ticks={max_ticks} must be None or a tuple of 2 integers"
            )
        self.max_ticks = max_ticks
        self.cell_formatter = cell_formatter

    __init__.__doc__ = ColorbarMatplotStyle.__init__.__doc__ + __init__.__doc__

    def draw_matrix(self, matrix: pd.DataFrame) -> None:
        """[see superclass]"""
        ax: Axes = self.ax
        self.ax.margins(0, 0)

        # store values locally so we can label the matrix cells when finalizing the plot
        data = matrix.values
        ax.imshow(
            data,
            cmap=self.colors.colormap,
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
        tick_params: Dict[bool, Dict[str, Any]] = {
            False: {},
            True: dict(rotation=45, ha="right"),
        }

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

            # Replace the tick locator with a fixed locator, preserving the tick
            # locations determined by the MaxNLocator. This is needed for compatibility
            # with the FixedFormatter that will be created when setting the tick labels
            axis.set_ticks(axis.get_ticklocs())

            # Set the tick labels; behind the scenes this will create a FixedFormatter.
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

        # only draw labels if a cell formatter is defined, and minimal height/width
        # is available
        if self.cell_formatter is not None and all(
            size <= 1 for size in self.text_dimensions("0")
        ):
            # draw the axis to ensure we'll get correct coordinates
            ax.draw(self.renderer)

            # get the cell formatter as a local field
            cell_formatter = self.cell_formatter

            # render the text for every box where the text fits
            for y in range(n_rows):
                for x in range(n_columns):
                    x_text = x
                    y_text = y
                    cell_value = data[y, x]
                    label = cell_formatter(cell_value)
                    text_width, _ = self.text_dimensions(text=label, x=x_text, y=y_text)

                    if text_width > 1:
                        # show ellipsis in cells where the text does not fit
                        label = "…"

                    self.ax.text(
                        x=x_text,
                        y=y_text,
                        s=label,
                        ha="center",
                        va="center",
                        color=text_contrast_color(
                            bg_color=self.color_for_value(z=cell_value)
                        ),
                    )

        # hide spines
        for _, spine in ax.spines.items():
            spine.set_visible(False)

        # create a white grid using minor tick positions
        ax.set_xticks(np.arange(n_columns + 1) - 0.5, minor=True)
        ax.set_yticks(np.arange(n_rows + 1) - 0.5, minor=True)
        ax.grid(which="minor", color=self.colors.foreground, linestyle="-", linewidth=2)
        ax.tick_params(which="minor", bottom=False, left=False)


class PercentageMatrixMatplotStyle(MatrixMatplotStyle):
    """
    A matrix plot where all values are percentages.

    Annotates matrix cells with percentage values.
    """

    def __init__(
        self,
        *,
        ax: Optional[Axes] = None,
        colors: Optional[ColorScheme] = None,
        colormap_normalize: Optional[Normalize] = None,
        max_ticks: Optional[Tuple[int, int]] = None,
        **kwargs,
    ) -> None:
        """
        :param max_ticks: the maximum number of ticks to put on the x and y axis;
            ``None`` to determine the number of ticks automatically (default: ``None``)
        """
        _unsupported_fields = {
            "colorbar_major_formatter",
            "colorbar_minor_formatter",
            "cell_format",
        }.intersection(kwargs.keys())
        if _unsupported_fields:
            if len(_unsupported_fields) == 1:
                _args = f"arg {next(iter(_unsupported_fields))} is"
            else:
                _args = f'args {", ".join(_unsupported_fields)} are'
            raise ValueError(f"{_args} not supported by class {type(self).__name__}")

        super().__init__(
            ax=ax,
            colors=colors,
            colormap_normalize=(
                colormap_normalize
                if colormap_normalize
                else Normalize(vmin=0.0, vmax=1.0)
            ),
            max_ticks=max_ticks,
            colorbar_major_formatter=PercentageFormatter(),
            colorbar_minor_formatter=None,
            cell_format=lambda x: (
                f"{np.round(x * 100, 1):.2g}"
                if abs(x) < 0.1
                else f"{np.round(x * 100):.0f}"
            ),
            **kwargs,
        )

    __init__.__doc__ = ColorbarMatplotStyle.__init__.__doc__ + __init__.__doc__

    @classmethod
    def get_default_style_name(cls) -> str:
        """[see superclass]"""
        return f"{super().get_default_style_name()}%"


@inheritdoc(match="[see superclass]")
class MatrixReportStyle(MatrixStyle, TextStyle):
    """
    Text report style for matrices.
    """

    def draw_matrix(self, matrix: pd.DataFrame) -> None:
        """[see superclass]"""
        matrix.to_string(buf=self.out, line_width=self.width)


#
# Drawer classes
#


@inheritdoc(match="[see superclass]")
class MatrixDrawer(Drawer[pd.DataFrame, MatrixStyle]):
    """
    Drawer for matrices of numerical values.

    Supports the following pre-defined styles:

    - ``"matplot"``: `matplotlib` plot of the matrix using a
      :class:`.MatrixMatplotStyle`
    - ``"matplot%"``: `matplotlib` plot of matrix with annotations formatted as
      percentages, using a :class:`.PercentageMatrixMatplotStyle`
    - ``"text"``: text representation of the matrix, using a :class:`.MatrixReportStyle`
    """

    def __init__(self, style: Optional[Union[MatrixStyle, str]] = None) -> None:
        """
        :param style: the style to be used for drawing (default: ``"matplot"``)
        """
        super().__init__(style=style)

    @classmethod
    def get_style_classes(cls) -> Iterable[Type[MatrixStyle]]:
        """[see superclass]"""
        return [
            MatrixMatplotStyle,
            PercentageMatrixMatplotStyle,
            MatrixReportStyle,
        ]

    def _draw(self, data: pd.DataFrame) -> None:
        # draw the matrix
        self.style.draw_matrix(data)


__tracker.validate()

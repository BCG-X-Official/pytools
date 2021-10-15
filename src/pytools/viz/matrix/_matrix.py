"""
Core implementation of :mod:`pytools.viz.matrix`.
"""

import logging
from typing import Any, Callable, Dict, Iterable, Optional, Tuple, Type, TypeVar, Union

import numpy as np
import pandas as pd
from matplotlib.axes import Axes
from matplotlib.axis import Axis
from matplotlib.colors import Normalize
from matplotlib.patches import Rectangle
from matplotlib.ticker import FixedLocator, Formatter, FuncFormatter, NullLocator

from ...data import Matrix
from .. import ColorbarMatplotStyle, Drawer, TextStyle
from ..color import ColorScheme
from ..util import FittedText, PercentageFormatter
from .base import MatrixStyle
from pytools.api import AllTracker, inheritdoc

log = logging.getLogger(__name__)


#
# exported names
#

__all__ = [
    "MatrixDrawer",
    "MatrixMatplotStyle",
    "MatrixReportStyle",
    "PercentageMatrixMatplotStyle",
]


#
# Type variables
#

T = TypeVar("T")


#
# Ensure all symbols introduced below are included in __all__
#

__tracker = AllTracker(globals())


#
# Style classes
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

    #: The value to look up in the colormap for undefined matrix cells.
    nan_substitute: float

    def __init__(
        self,
        *,
        ax: Optional[Axes] = None,
        colors: Optional[ColorScheme] = None,
        font_family: Optional[Union[str, Iterable[str]]] = None,
        colormap_normalize: Optional[Normalize] = None,
        colorbar_major_formatter: Optional[Formatter] = None,
        colorbar_minor_formatter: Optional[Formatter] = None,
        cell_format: Union[str, Formatter, Callable[..., str], None] = None,
        # todo: change to Callable[[Any], str] once sphinx "unhashable type" bug is
        #       fixed
        nan_substitute: float = None,
    ) -> None:
        """
        :param cell_format: format for annotating each matrix cell with
            its value if sufficient space is available (optional – do not annotate
            cells if omitted);
            if no colorbar major formatter is specified, use the cell format also
            as the colorbar major formatter
        :param nan_substitute: value to look up in the colormap for undefined matrix
            cells (default: 0.0)
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
            font_family=font_family,
            colormap_normalize=(
                colormap_normalize if colormap_normalize is not None else Normalize()
            ),
            colorbar_major_formatter=colorbar_major_formatter,
            colorbar_minor_formatter=colorbar_minor_formatter,
        )

        self.cell_formatter = cell_formatter
        self.nan_substitute = 0.0 if nan_substitute is None else nan_substitute

    __init__.__doc__ = ColorbarMatplotStyle.__init__.__doc__ + __init__.__doc__

    def draw_matrix(
        self,
        data: np.ndarray,
        *,
        names: Tuple[Optional[np.ndarray], Optional[np.ndarray]],
        weights: Tuple[Optional[np.ndarray], Optional[np.ndarray]],
    ) -> None:
        """[see superclass]"""
        ax: Axes = self.ax
        colors = self.colors

        # replace undefined weights with all ones
        weights_rows, weights_columns = tuple(
            np.ones(n) if w is None else w for w, n in zip(weights, data.shape)
        )

        # calculate the horizontal and vertical matrix cell bounds based on the
        # cumulative sums of the axis weights; default all weights to 1 if not defined
        column_bounds: np.ndarray
        row_bounds: np.ndarray

        row_bounds = -np.array([0, *weights_rows]).cumsum()
        column_bounds = np.array([0, *weights_columns]).cumsum()

        # calculate the colors based on the data
        cell_colors = self.color_for_value(
            np.nan_to_num(data.ravel(), nan=self.nan_substitute)
        ).reshape((*data.shape, 4))

        # define hatch parameters
        hatch_params: Dict[bool, Dict[str, Any]] = {
            False: {},
            True: dict(
                hatch="////",
                edgecolor=(
                    *colors.contrast_color(
                        self.color_for_value(self.nan_substitute)[:3]
                    ),
                    0.25,
                ),
            ),
        }

        # draw the matrix cells
        for c, (x0, x1) in enumerate(zip(column_bounds, column_bounds[1:])):
            for r, (y1, y0) in enumerate(zip(row_bounds, row_bounds[1:])):
                color: np.ndarray = cell_colors[r, c]
                ax.add_patch(
                    Rectangle(
                        (
                            x0,
                            y0,
                        ),
                        x1 - x0,
                        y1 - y0,
                        facecolor=color,
                        linewidth=0,
                        **hatch_params[np.isnan(data[r, c])],
                    )
                )

        # noinspection PyTypeChecker
        ax.update_datalim([(0, 0), (column_bounds[-1], row_bounds[-1])])

        # draw the tick marks and labels

        x_tick_locations = (column_bounds[:-1] + column_bounds[1:]) / 2
        y_tick_locations = (row_bounds[:-1] + row_bounds[1:]) / 2

        def _set_ticks(
            tick_locations: np.ndarray,
            tick_labels: np.ndarray,
            axis: Axis,
            tick_params: Dict[str, Any],
        ):
            # set the ticks for the given axis

            if tick_labels is None:
                axis.set_major_locator(NullLocator())

            else:
                # Replace the tick locator with a fixed locator, preserving the tick
                # locations determined by the MaxNLocator. This is needed for
                # compatibility with the FixedFormatter that will be created when
                # setting the tick labels
                axis.set_major_locator(FixedLocator(tick_locations))

                # Set the tick labels; behind the scenes this will create a
                # FixedFormatter.
                axis.set_ticklabels(tick_labels, **tick_params)

        # add tick labels

        row_names, column_names = names

        if (
            column_names is not None
            and not np.issubdtype(column_names.dtype, np.number)
            and any(len(str(name)) > 1 for name in column_names)
        ):
            # rotate column labels if they are categorical and not all single-character
            column_tick_params = dict(rotation=45, ha="right", rotation_mode="anchor")
        else:
            column_tick_params: Dict[str, Any] = {}

        _set_ticks(
            tick_locations=x_tick_locations,
            tick_labels=column_names,
            axis=ax.xaxis,
            tick_params=column_tick_params,
        )

        _set_ticks(
            tick_locations=y_tick_locations,
            tick_labels=row_names,
            axis=ax.yaxis,
            tick_params={},
        )

        # only draw cell labels if a cell formatter is defined, and minimal height/width
        # is available
        if self.cell_formatter is not None:
            # draw the axis to ensure we'll get correct coordinates
            # ax.draw(self.renderer)

            # get the cell formatter as a local field
            cell_formatter = self.cell_formatter

            # render the text for every box where the text fits

            for r, (y, height) in enumerate(zip(y_tick_locations, weights_rows)):
                for c, (x, width) in enumerate(zip(x_tick_locations, weights_columns)):
                    cell_value = data[r, c]
                    label = cell_formatter(cell_value)
                    ax.add_artist(
                        FittedText(
                            x=x,
                            y=y,
                            width=width,
                            height=height,
                            text=label,
                            ha="center",
                            va="center",
                            color=colors.contrast_color(
                                self.color_for_value(z=cell_value)
                            ),
                        )
                    )

        # create a white grid using minor tick positions
        ax.xaxis.set_minor_locator(FixedLocator(column_bounds[1:-1]))
        ax.yaxis.set_minor_locator(FixedLocator(row_bounds[1:-1]))
        ax.grid(
            b=True,
            which="minor",
            color=colors.background,
            linestyle="-",
            linewidth=0.5,
        )
        ax.tick_params(which="minor", bottom=False, left=False)

        # make sure we have no major grid, overriding any global settings
        ax.grid(b=False, which="major")

    def start_drawing(
        self,
        *,
        title: str,
        name_labels: Tuple[Optional[str], Optional[str]] = None,
        weight_label: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """[see superclass]"""
        super().start_drawing(
            title=title,
            name_labels=name_labels,
            weight_label=weight_label,
            colorbar_label=weight_label,
            **kwargs,
        )

        ax: Axes = self.ax

        # make this a square matrix
        ax.set_aspect("equal")

        # remove margins
        ax.margins(0)

        # set axis labels
        ax.set_ylabel(name_labels[0], color=self.colors.foreground)
        ax.set_xlabel(name_labels[1], color=self.colors.foreground)

        # hide spines
        for _, spine in ax.spines.items():
            spine.set_visible(False)


@inheritdoc(match="""[see superclass]""")
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
        font_family: Optional[Union[str, Iterable[str]]] = None,
        colormap_normalize: Optional[Normalize] = None,
        nan_substitute: float = None,
    ) -> None:
        """
        :param nan_substitute: the value to look up in the colormap for undefined matrix
            cells (default: 0.0)
        """
        super().__init__(
            ax=ax,
            colors=colors,
            font_family=font_family,
            colormap_normalize=(
                colormap_normalize
                if colormap_normalize
                else Normalize(vmin=0.0, vmax=1.0)
            ),
            nan_substitute=nan_substitute,
            colorbar_major_formatter=PercentageFormatter(),
            colorbar_minor_formatter=None,
            cell_format=lambda x: (
                f"{x * 100:.1f}" if abs(x) < 0.0995 else f"{x * 100:.0f}"
            ),
        )

    __init__.__doc__ = (
        "\n".join(
            line
            for line in ColorbarMatplotStyle.__init__.__doc__.split("\n")
            if "_formatter:" not in line
        )
        + __init__.__doc__
    )

    @classmethod
    def get_default_style_name(cls) -> str:
        """[see superclass]"""
        return f"{super().get_default_style_name()}%"


@inheritdoc(match="[see superclass]")
class MatrixReportStyle(MatrixStyle, TextStyle):
    """
    Text report style for matrices.
    """

    def start_drawing(
        self,
        *,
        title: str,
        name_labels: Tuple[Optional[str], Optional[str]] = None,
        weight_label: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """[see superclass]"""

        super().start_drawing(title=title, **kwargs)

        for i, dim_name in enumerate(("rows", "columns")):
            if name_labels[i]:
                print(f"{dim_name}: {name_labels[i]}", file=self.out)
        if weight_label:
            print(f"weights: {weight_label}", file=self.out)

    def draw_matrix(
        self,
        data: np.ndarray,
        *,
        names: Tuple[Optional[np.ndarray], Optional[np.ndarray]],
        weights: Tuple[Optional[np.ndarray], Optional[np.ndarray]],
    ) -> None:
        """[see superclass]"""

        def _axis_marks(
            axis_names: Optional[np.ndarray], axis_weights: Optional[np.ndarray]
        ) -> Optional[Iterable[Any]]:
            if axis_names is None:
                if axis_weights is None:
                    return None
                else:
                    axis_names = (f"#{i}" for i in range(len(axis_weights)))
            elif axis_weights is None:
                return axis_names

            return (
                f"{name} ({weight:g})" for name, weight in zip(axis_names, axis_weights)
            )

        row_labels, column_labels = (
            _axis_marks(axis_names, axis_weights)
            for axis_names, axis_weights in zip(names, weights)
        )

        pd.DataFrame(data, index=row_labels, columns=column_labels).to_string(
            buf=self.out, line_width=self.width
        )


#
# Drawer classes
#


@inheritdoc(match="[see superclass]")
class MatrixDrawer(Drawer[Matrix, MatrixStyle]):
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

    def get_style_kwargs(self, data: Matrix) -> Dict[str, Any]:
        """[see superclass]"""
        return dict(
            name_labels=data.name_labels,
            weight_label=data.value_label,
            **super().get_style_kwargs(data=data),
        )

    def _draw(self, data: Matrix) -> None:
        # draw the matrix
        self.style.draw_matrix(data.values, names=data.names, weights=data.weights)


__tracker.validate()

"""
Matplot styles for the Gamma visualization library
"""

import logging
from abc import ABCMeta
from typing import Optional, Tuple, Union

import matplotlib.pyplot as plt
from matplotlib import cm
from matplotlib import text as mt
from matplotlib.axes import Axes
from matplotlib.backend_bases import RendererBase
from matplotlib.colorbar import ColorbarBase, make_axes
from matplotlib.colors import Colormap, LinearSegmentedColormap, Normalize, to_rgba
from matplotlib.ticker import Formatter
from matplotlib.tight_layout import get_renderer

from ..api import AllTracker
from ._viz import DrawStyle

log = logging.getLogger(__name__)

__all__ = [
    "RgbaColor",
    "RGBA_BLACK",
    "RGBA_WHITE",
    "MatplotStyle",
    "ColorbarMatplotStyle",
    "PercentageFormatter",
]

#
# Ensure all symbols introduced below are included in __all__
#

__tracker = AllTracker(globals())

#
# Type definitions
#

# Rgba color type for use in  MatplotStyles
RgbaColor = Tuple[float, float, float, float]

#
# Constants
#

# color constants
RGBA_BLACK: RgbaColor = to_rgba("black")
RGBA_WHITE: RgbaColor = to_rgba("white")

#
# Class definitions
#


class MatplotStyle(DrawStyle, metaclass=ABCMeta):
    """Matplotlib drawer style.

    Implementations must define :meth:`~DrawStyle.draw_title`.
    """

    def __init__(self, *, ax: Optional[Axes] = None, **kwargs) -> None:
        """
        :param ax: optional axes object to draw on; if ``Null``, use pyplot's current \
            axes
        """
        super().__init__(**kwargs)
        self._ax = ax
        self._renderer: Optional[RendererBase] = None

    @property
    def ax(self) -> Axes:
        """
        The matplot :class:`~matplotlib.axes.Axes` object to draw the chart in.
        """
        ax = self._ax
        if ax is None:
            ax = self._ax = plt.gca()
        return ax

    @property
    def renderer(self) -> RendererBase:
        """
        The renderer used by this style's :class:`~matplotlib.axes.Axes` object
        (see :attr:`.ax`)
        """
        renderer = self._renderer
        if renderer is None:
            self._renderer = renderer = get_renderer(self.ax.figure)
        return renderer

    def _drawing_start(self, title: str) -> None:
        """
        Called once by the drawer when starting to draw a new chart.
        :param title: the title of the chart
        """
        self.ax.set_title(label=title)

    def _drawing_finalize(self) -> None:
        pass

    def text_size(
        self, text: str, x: Optional[float] = None, y: Optional[float] = None, **kwargs
    ) -> Tuple[float, float]:
        """
        Calculate the horizontal and vertical size of the given text in axis units.
        Constructs a :class:`matplotlib.text.Text` artist then calculates it size
        relative to the axis managed by this style object (attribute ``ax``)
        For non-linear axis scales text size differs depending on placement,
        so the intended placement (in data coordinates) should be provided

        :param text: text to calculate the size for
        :param x: intended horizontal text placement (optional, defaults to left of
            view)
        :param y: intended vertical text placement (optional, defaults to bottom of
            view)
        :param kwargs: additional arguments to use when constructing the
            :class:`~matplotlib.text.Text` artist, e.g., rotation
        :return: tuple `(width, height)` in absolute axis units
        """

        ax = self.ax

        if x is None or y is None:
            x0, y0, _, _ = ax.dataLim.bounds
            if x is None:
                x = x0
            if y is None:
                y = y0

        fig = ax.figure

        extent = mt.Text(x, y, text, figure=fig, **kwargs).get_window_extent(
            self.renderer
        )

        (x0, y0), (x1, y1) = ax.transData.inverted().transform(extent)

        return abs(x1 - x0), abs(y1 - y0)

    @staticmethod
    def text_contrast_color(bg_color: RgbaColor) -> RgbaColor:
        """
        Return a text color that maximises contrast with the given background color.

        Returns while for background luminance < 50%, and black otherwise. The alpha
        channel of the background color is ignored, and the text color is returned as
        fully opaque.

        :param bg_color: RGBA encoded colour for the background
        :return: the contrasting text color
        """
        fill_luminance = sum(bg_color[:3]) / 3
        text_color = RGBA_WHITE if fill_luminance < 0.5 else RGBA_BLACK
        return text_color


class ColorbarMatplotStyle(MatplotStyle, metaclass=ABCMeta):
    """
    Matplot style with added support for a color bar.

    The associated plot uses a color gradient to indicate a scalar value,
    and the color bar acts as the legend for this color gradient.
    """

    DEFAULT_COLORMAP = LinearSegmentedColormap.from_list(
        "facet",
        [(0, "#3d3a40"), (0.25, "#295e7e"), (0.65, "#30c1d7"), (1.0, "#43fda2")],
    )

    def __init__(
        self,
        *,
        ax: Optional[Axes] = None,
        colormap: Optional[Union[str, Colormap]] = None,
        colormap_normalize: Normalize = None,
        colorbar_label: Optional[str] = None,
        colorbar_major_formatter: Optional[Formatter] = None,
        colorbar_minor_formatter: Optional[Formatter] = None,
        **kwargs,
    ):
        """
        :param colormap: the color map to use; either a name or a \
            :class:`~matplotlib.colors.Colorbar` instance (default: ``"plasma"``). \
            For an overview of named color maps, see \
            `here <https://matplotlib.org/tutorials/colors/colormaps.html>`_
        :param colormap_normalize: the :class:`~matplotlib.colors.Normalize` object \
            that maps values to color indices; if ``None``, use a plain linear \
            :class:`~matplotlib.colors.Normalize` object with autoscaling \
            (default: ``None``)
        :param colorbar_label: test to use as the label for the color bar (optional)
        :param colorbar_major_formatter: major tick formatter for the color bar \
            (optional)
        :param colorbar_minor_formatter: minor tick formatter for the color bar \
            (optional)
        """
        super().__init__(ax=ax, **kwargs)

        if isinstance(colormap, Colormap):
            self.colormap = colormap
        else:
            if colormap is None:
                colormap = ColorbarMatplotStyle.DEFAULT_COLORMAP
            self.colormap = cm.get_cmap(name=colormap)
        self.colormap_normalize = (
            Normalize() if colormap_normalize is None else colormap_normalize
        )
        if colorbar_minor_formatter is not None and colorbar_major_formatter is None:
            raise ValueError(
                "arg colorbar_minor_formatter defined without defining "
                "arg colorbar_major_formatter"
            )
        self.colorbar_label = colorbar_label
        self.colorbar_major_formatter = colorbar_major_formatter
        self.colorbar_minor_formatter = colorbar_minor_formatter

        self.colorbar = None

    __init__.__doc__ = MatplotStyle.__init__.__doc__ + __init__.__doc__

    def _drawing_finalize(self) -> None:
        super()._drawing_finalize()

        cax, _ = make_axes(self.ax)
        self.colorbar = ColorbarBase(
            cax,
            cmap=self.colormap,
            norm=self.colormap_normalize,
            label="" if self.colorbar_label is None else self.colorbar_label,
            orientation="vertical",
        )

        if self.colorbar_major_formatter is not None:
            cax.yaxis.set_major_formatter(self.colorbar_major_formatter)

        if self.colorbar_minor_formatter is not None:
            cax.yaxis.set_minor_formatter(self.colorbar_minor_formatter)

    def value_color(self, z: float) -> RgbaColor:
        """
        Return the color associated with a given scalar, based on the normalization
        defined for this style

        :param z: the scalar to be color-encoded
        :return: the color as a RGBA tuple
        """
        # return self._cm(
        #     0
        #     if weight <= self._min_weight
        #     else 1 - math.log(weight) / math.log(self._min_weight)
        # )
        return self.colormap(self.colormap_normalize(z))


class PercentageFormatter(Formatter):
    """
    Formats floats as a percentages with 3 digits precision, omitting trailing zeros.

    Formatting examples:

    - ``0.0`` is formatted as ``0%``
    - ``0.1`` is formatted as ``10%``
    - ``1.0`` is formatted as ``100%``
    - ``0.01555`` is formatted as ``1.56%``
    - ``0.01555`` is formatted as ``1.56%``
    - ``0.1555`` is formatted as ``15.6%``
    - ``1.555`` is formatted as ``156%``
    """

    def __call__(self, x, pos=None) -> str:
        return f"{x * 100.0:.3g}%"


__tracker.validate()

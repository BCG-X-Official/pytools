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
from matplotlib.colors import Colormap, Normalize
from matplotlib.ticker import Formatter
from matplotlib.tight_layout import get_renderer

from ..api import AllTracker
from ._viz import DrawingStyle
from .colors import COLORMAP_FACET, RgbaColor

log = logging.getLogger(__name__)

#
# Exported names
#

__all__ = ["MatplotStyle", "ColorbarMatplotStyle"]


#
# Ensure all symbols introduced below are included in __all__
#

__tracker = AllTracker(globals())


#
# Classes
#


class MatplotStyle(DrawingStyle, metaclass=ABCMeta):
    """
    Base class of drawing styles using `matplotlib`.
    """

    def __init__(self, *, ax: Optional[Axes] = None, **kwargs) -> None:
        """
        :param ax: optional axes object to draw on; if ``Null``, use pyplot's current
            axes
        """
        super().__init__(**kwargs)
        self._ax = ax
        self._renderer: Optional[RendererBase] = None

    @property
    def ax(self) -> Axes:
        """
        The matplotlib :class:`~matplotlib.axes.Axes` object on which to draw
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

    def text_dimensions(
        self, text: str, x: Optional[float] = None, y: Optional[float] = None, **kwargs
    ) -> Tuple[float, float]:
        """
        Calculate the horizontal and vertical dimensions of the given text in axis
        units.

        Constructs a :class:`matplotlib.text.Text` artist then calculates it size
        relative to the axis :attr:`.ax` managed by this style object.
        For non-linear axis scales, text size differs depending on placement,
        so the intended placement (in data coordinates) should be provided.

        :param text: text to calculate the dimensions for
        :param x: intended horizontal text placement (optional, defaults to left of
            view)
        :param y: intended vertical text placement (optional, defaults to bottom of
            view)
        :param kwargs: additional keyword arguments to use when constructing the
            :class:`~matplotlib.text.Text` artist, e.g., rotation
        :return: tuple `(width, height)` in axis units
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

    def _drawing_start(self, title: str, **kwargs) -> None:
        """
        Set the title of the matplot chart to the given title.
        :param title: the chart title
        """
        self.ax.set_title(label=title)


class ColorbarMatplotStyle(MatplotStyle, metaclass=ABCMeta):
    """
    `matplotlib` style with added support for a color bar.

    The plot uses a color map to indicate a scalar value,
    and the color bar provides a legend for the color gradient.

    For an overview of matplotlib's named color maps, see
    `here <https://matplotlib.org/tutorials/colors/colormaps.html>`_
    """

    def __init__(
        self,
        *,
        ax: Optional[Axes] = None,
        colormap: Optional[Union[str, Colormap]] = None,
        colormap_normalize: Normalize = None,
        colorbar_major_formatter: Optional[Formatter] = None,
        colorbar_minor_formatter: Optional[Formatter] = None,
        **kwargs,
    ):
        """
        :param colormap: the color map to use; either a name or a
            :class:`~matplotlib.colors.Colormap` instance
            (default: :attr:`.colors.COLORMAP_FACET`)
        :param colormap_normalize: the :class:`~matplotlib.colors.Normalize` object
            that maps values to color indices; if ``None``, use a plain
            :class:`~matplotlib.colors.Normalize` object with linear autoscaling
            (default: ``None``)
        :param colorbar_major_formatter: major tick formatter for the color bar
            (optional)
        :param colorbar_minor_formatter: minor tick formatter for the color bar
            (optional; requires that also a major formatter is specified)
        """
        super().__init__(ax=ax, **kwargs)

        if isinstance(colormap, Colormap):
            self.colormap = colormap
        else:
            if colormap is None:
                colormap = COLORMAP_FACET
            self.colormap = cm.get_cmap(name=colormap)
        self.colormap_normalize = (
            Normalize() if colormap_normalize is None else colormap_normalize
        )
        if colorbar_minor_formatter is not None and colorbar_major_formatter is None:
            raise ValueError(
                "arg colorbar_minor_formatter passed without passing "
                "arg colorbar_major_formatter"
            )
        self.colorbar_major_formatter = colorbar_major_formatter
        self.colorbar_minor_formatter = colorbar_minor_formatter

        self.colorbar = None

    __init__.__doc__ = MatplotStyle.__init__.__doc__ + __init__.__doc__

    def color_for_value(self, z: float) -> RgbaColor:
        """
        Get the color associated with a given scalar, based on the color map and
        normalization defined for this style.

        :param z: the scalar to be color-encoded
        :return: the resulting color as a RGBA tuple
        """
        return self.colormap(self.colormap_normalize(z))

    def _drawing_finalize(self, colorbar_label: Optional[str] = None, **kwargs) -> None:
        # add the colorbar to the chart

        super()._drawing_finalize(**kwargs)

        cax, _ = make_axes(self.ax)
        self.colorbar = ColorbarBase(
            cax,
            cmap=self.colormap,
            norm=self.colormap_normalize,
            label="" if colorbar_label is None else colorbar_label,
            orientation="vertical",
        )

        if self.colorbar_major_formatter is not None:
            cax.yaxis.set_major_formatter(self.colorbar_major_formatter)

        if self.colorbar_minor_formatter is not None:
            cax.yaxis.set_minor_formatter(self.colorbar_minor_formatter)


__tracker.validate()

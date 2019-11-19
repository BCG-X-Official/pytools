"""
Matplot styles for the Gamma visualization library
"""

import logging
from abc import ABC
from typing import *

import matplotlib.pyplot as plt
from matplotlib import cm, text as mt
from matplotlib.axes import Axes
from matplotlib.backend_bases import RendererBase
from matplotlib.colorbar import ColorbarBase, make_axes
from matplotlib.colors import Normalize
from matplotlib.ticker import Formatter

from ._viz import DrawStyle

log = logging.getLogger(__name__)

__all__ = ["ColorbarMatplotStyle", "MatplotStyle", "RgbaColor"]

#
# Type definitions
#

# Rgba color class for use in  MatplotStyles
RgbaColor = Tuple[float, float, float, float]


#
# Class definitions
#


class MatplotStyle(DrawStyle, ABC):
    """Matplotlib drawer style.

    Implementations must define :meth:`~DrawStyle.draw_title`.
    """

    def __init__(self, *, ax: Optional[Axes] = None, **kwargs) -> None:
        """
        :param ax: optional axes object to draw on; if `Null` use pyplot's current axes
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
            self._renderer = renderer = self.ax.figure.canvas.get_renderer()
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
        relative to the axis managed by this style object (attribute `ax`)
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
            fig.canvas.get_renderer()
        )

        (x0, y0), (x1, y1) = ax.transData.inverted().transform(extent)

        return abs(x1 - x0), abs(y1 - y0)


class ColorbarMatplotStyle(MatplotStyle, ABC):
    """
    Matplot style with added support for a color bar.

    THe associated plot uses a color gradient to indicate a scalar value,
    and the color bar acts as the legend for this color gradient.
    """

    def __init__(
        self,
        *,
        normalize: Normalize,
        ax: Optional[Axes] = None,
        major_formatter: Optional[Formatter] = None,
        minor_formatter: Optional[Formatter] = None,
        **kwargs,
    ):
        super().__init__(ax=ax, **kwargs)

        self._normalize = normalize
        self._major_formatter = major_formatter
        self._minor_formatter = minor_formatter

        self._cm = None
        self._cb = None

    def _drawing_start(self, title: str) -> None:
        super()._drawing_start(title=title)

        cax, _ = make_axes(self.ax)
        self._cm = cm.get_cmap(name="plasma", lut=256)
        self._cb = ColorbarBase(
            cax,
            cmap=self._cm,
            norm=self._normalize,
            label="feature importance",
            orientation="vertical",
        )

        cax.yaxis.set_minor_formatter(self._minor_formatter)
        cax.yaxis.set_major_formatter(self._major_formatter)

    def color(self, z: float) -> RgbaColor:
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
        return self._cm(self._normalize(z))

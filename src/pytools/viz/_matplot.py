"""
Matplot styles for the GAMMA visualization library.
"""

import logging
from abc import ABCMeta
from typing import Optional, Tuple

import matplotlib.pyplot as plt
from matplotlib import text as mt
from matplotlib.axes import Axes
from matplotlib.backend_bases import RendererBase
from matplotlib.colorbar import ColorbarBase, make_axes
from matplotlib.colors import Normalize
from matplotlib.legend import Legend
from matplotlib.ticker import Formatter
from matplotlib.tight_layout import get_renderer

from ..api import AllTracker, inheritdoc
from ._viz import ColoredStyle
from .color import MatplotColorScheme, RgbaColor

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


@inheritdoc(match="[see superclass]")
class MatplotStyle(ColoredStyle[MatplotColorScheme], metaclass=ABCMeta):
    """
    Base class of drawing styles using `matplotlib`.
    """

    def __init__(
        self,
        *,
        ax: Optional[Axes] = None,
        colors: Optional[MatplotColorScheme] = None,
        **kwargs,
    ) -> None:
        """
        :param ax: optional axes object to draw on; create a new figure if not specified
        """
        super().__init__(colors=colors, **kwargs)
        self._ax = ax
        self._renderer: Optional[RendererBase] = None

    __init__.__doc__ += ColoredStyle.__init__.__doc__

    @classmethod
    def get_default_style_name(cls) -> str:
        """[see superclass]"""
        return "matplot"

    @property
    def ax(self) -> Axes:
        """
        The matplotlib :class:`~matplotlib.axes.Axes` object on which to draw.
        """
        ax = self._ax
        if ax is None:
            _, ax = plt.subplots()
            self._ax = ax
        return ax

    @property
    def renderer(self) -> RendererBase:
        """
        The renderer used by this style's :class:`~matplotlib.axes.Axes` object
        (see :attr:`.ax`).
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

        Constructs a :class:`~matplotlib.text.Text` artist then calculates it size
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

    def start_drawing(self, title: str, **kwargs) -> None:
        """
        Set the title of the matplot chart to the given title, and set the foreground
        and background color according to the color scheme.

        :param title: the chart title
        """

        ax = self.ax

        # set title plus title color
        ax.set_title(label=title, color=self.colors.foreground)

        # color the axes
        self._apply_color_scheme(ax)

        bg_color = self.colors.background

        # set the figure background color
        try:
            # does the axes background color conflict with the figure background color?
            if ax.figure.__pytools_viz_background != bg_color:
                log.warning(
                    "subplots have conflicting color schemes; setting background color "
                    f'according to color scheme {self.colors!r} of chart "{title}"'
                )
        except AttributeError:
            pass
        ax.figure.set_facecolor(bg_color)
        ax.figure.__pytools_viz_background = bg_color

    def finalize_drawing(self, **kwargs) -> None:
        """[see superclass]"""

        super().finalize_drawing(**kwargs)

        # set legend color
        legend: Legend = self.ax.get_legend()

        if legend:
            patch = legend.legendPatch
            fg_color = self.colors.foreground

            patch.set_facecolor(self.colors.background)
            patch.set_alpha(0.5)
            patch.set_edgecolor(fg_color)

            for text in legend.get_texts():
                text.set_color(fg_color)

    def _apply_color_scheme(self, ax: Axes) -> None:
        """
        Apply this style's color scheme to the given :class:`~matplotlib.axes.Axes`.

        Style implementations can use this to apply the color scheme to sub-axes.
        Does not need to be applied to main axes, as this is already done in method
        :meth:`.start_drawing`.

        This method will be public as of v1.1.

        :param ax: the axes to apply the color scheme to
        """

        fg_color = self.colors.foreground
        bg_color = self.colors.background

        # set face color
        ax.set_facecolor(bg_color)

        # set figure face color
        ax.patch.set_facecolor(bg_color)

        # set tick and tick label color
        ax.tick_params(color=fg_color, labelcolor=fg_color)

        # set the outline color
        for spine in ax.spines.values():
            spine.set_edgecolor(fg_color)


class ColorbarMatplotStyle(MatplotStyle, metaclass=ABCMeta):
    """
    `matplotlib` style with added support for a color bar.

    The plot uses a color map to indicate a scalar value,
    and the color bar provides a legend for the color gradient.

    The color map is provided by the :class:`.MatplotColorScheme` associated with the
    style.
    """

    def __init__(
        self,
        *,
        ax: Optional[Axes] = None,
        colors: Optional[MatplotColorScheme] = None,
        colormap_normalize: Normalize = None,
        colorbar_major_formatter: Optional[Formatter] = None,
        colorbar_minor_formatter: Optional[Formatter] = None,
        **kwargs,
    ):
        """
        :param colormap_normalize: the :class:`~matplotlib.colors.Normalize` object
            that maps values to color indices; unless otherwise specified, use a plain
            :class:`~matplotlib.colors.Normalize` object with linear autoscaling
        :param colorbar_major_formatter: major tick formatter for the color bar
            (optional)
        :param colorbar_minor_formatter: minor tick formatter for the color bar
            (optional; requires that also a major formatter is specified)
        """
        super().__init__(ax=ax, colors=colors, **kwargs)

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
        return self.colors.colormap(self.colormap_normalize(z))

    def finalize_drawing(self, colorbar_label: Optional[str] = None, **kwargs) -> None:
        """
        Add the color bar to the chart.

        :param colorbar_label: the label for the color bar
        """

        super().finalize_drawing(**kwargs)

        fg_color = self.colors.foreground

        cax, _ = make_axes(self.ax)
        self.colorbar = cb = ColorbarBase(
            cax,
            cmap=self.colors.colormap,
            norm=self.colormap_normalize,
            label=colorbar_label or "",
            orientation="vertical",
        )

        if self.colorbar_major_formatter is not None:
            cax.yaxis.set_major_formatter(self.colorbar_major_formatter)

        if self.colorbar_minor_formatter is not None:
            cax.yaxis.set_minor_formatter(self.colorbar_minor_formatter)

        # set colorbar tick color
        cb.ax.yaxis.set_tick_params(colors=fg_color)

        # set colorbar edge color
        cb.outline.set_edgecolor(fg_color)


__tracker.validate()

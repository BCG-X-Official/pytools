"""
Matplot styles for the GAMMA visualization library.
"""

import logging
from abc import ABCMeta
from typing import Any, Optional, Union

import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.backend_bases import RendererBase
from matplotlib.colorbar import ColorbarBase, make_axes
from matplotlib.colors import Normalize
from matplotlib.legend import Legend
from matplotlib.text import Text
from matplotlib.ticker import Formatter
from matplotlib.tight_layout import get_renderer

from ..api import AllTracker, inheritdoc
from ._viz import ColoredStyle
from .color import ColorScheme, MatplotColorScheme

log = logging.getLogger(__name__)

#
# Exported names
#

__all__ = ["FittedText", "MatplotStyle", "ColorbarMatplotStyle"]


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

    _TEXT_PADDING_RATIO = 0.1

    def __init__(
        self,
        *,
        ax: Optional[Axes] = None,
        colors: Optional[MatplotColorScheme] = None,
    ) -> None:
        """
        :param ax: optional axes object to draw on; create a new figure if not specified
        """
        super().__init__(colors=colors)
        self._ax = ax

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
            self._ax = ax = plt.gca()
        return ax

    def get_renderer(self) -> RendererBase:
        """
        Get the renderer used by this style's :class:`~matplotlib.axes.Axes` object
        (see :attr:`.ax`).

        :return: the renderer
        """
        return get_renderer(self.ax.figure)

    def start_drawing(self, *, title: str, **kwargs: Any) -> None:
        """
        Set the title of the matplot chart to the given title, and set the foreground
        and background color according to the color scheme.

        :param title: the chart title
        :param kwargs: additional drawer-specific arguments
        """

        super().start_drawing(title=title, **kwargs)

        ax = self.ax

        # set title plus title color
        ax.set_title(label=title, color=self.colors.foreground)

        # color the axes
        self.apply_color_scheme(ax)

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

    def finalize_drawing(self, **kwargs: Any) -> None:
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

    def apply_color_scheme(self, ax: Axes) -> None:
        """
        Apply this style's color scheme to the given :class:`~matplotlib.axes.Axes`.

        Style implementations can use this to apply the color scheme to sub-axes.
        Does not need to be applied to main axes, as this is already done in method
        :meth:`.start_drawing`.

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
    ) -> None:
        """
        :param colormap_normalize: the :class:`~matplotlib.colors.Normalize` object
            that maps values to color indices; unless otherwise specified, use a plain
            :class:`~matplotlib.colors.Normalize` object with linear autoscaling
        :param colorbar_major_formatter: major tick formatter for the color bar
            (optional)
        :param colorbar_minor_formatter: minor tick formatter for the color bar
            (optional; requires that also a major formatter is specified)
        """
        super().__init__(ax=ax, colors=colors)

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

    def color_for_value(self, z: float) -> ColorScheme.RgbaColor:
        """
        Get the color associated with a given scalar, based on the color map and
        normalization defined for this style.

        :param z: the scalar to be color-encoded
        :return: the resulting color as a RGBA tuple
        """
        return self.colors.colormap(self.colormap_normalize(z))

    def finalize_drawing(
        self, *, colorbar_label: Optional[str] = None, **kwargs: Any
    ) -> None:
        """
        Add the color bar to the chart.

        :param colorbar_label: the label for the color bar
        :param kwargs: additional arguments, to be passed on to the superclass
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
            cb.minorticks_on()
        else:
            cb.minorticks_off()

        # set colorbar tick color
        cb.ax.yaxis.set_tick_params(colors=fg_color)

        # set colorbar edge color
        cb.outline.set_edgecolor(fg_color)


class FittedText(Text):
    """
    Handle storing and drawing of text in window or data coordinates;
    only render text that does not exceed the given width and height in data
    coordinates.
    """

    def __init__(
        self,
        *,
        x: Union[int, float] = 0,
        y: Union[int, float] = 0,
        width: Union[int, float, None] = None,
        height: Union[int, float, None] = None,
        text: str = "",
        **kwargs: Any,
    ) -> None:
        """
        :param x: the `x` coordinate of the text
        :param y: the `y` coordinate of the text
        :param width: the maximum allowed width for this text, in data coordinates;
            if ``None``, width is unrestricted
        :param height: the maximum allowed height for this text, in data coordinates;
            if ``None``, height is unrestricted
        :param text: the text to be rendered
        :param kwargs: additional keyword arguments of class
            :class:`matplotlib.text.Text`
        """
        super().__init__(x=x, y=y, text=text, **kwargs)
        self._width = width
        self._height = height

    def set_width(self, width: Union[int, float, None]) -> None:
        """
        Set the maximum allowed width for this text, in data coordinates.

        :param width: the maximum allowed width; ``None`` if width is unrestricted
        """
        self.stale = width != self._width
        self._width = width

    def get_width(self) -> Union[int, float, None]:
        """
        Get the maximum allowed width for this text, in data coordinates.

        :return: the maximum allowed width; ``None`` if width is unrestricted
        """
        return self._width

    def set_height(self, height: Union[int, float, None]) -> None:
        """
        Set the maximum allowed height for this text, in data coordinates.

        :param height: the maximum allowed height; ``None`` if height is unrestricted
        """
        self.stale = height != self._height
        self._height = height

    def get_height(self) -> Union[int, float, None]:
        """
        Get the maximum allowed height for this text, in data coordinates.

        :return: the maximum allowed height; ``None`` if height is unrestricted
        """
        return self._height

    def draw(self, renderer: RendererBase) -> None:
        """
        Draw the text if it is visible, and if it does not exceed the maximum
        width and height.

        See also :meth:`~matplotlib.artist.Artist.draw`.

        :param renderer: the renderer used for drawing
        """
        width = self.get_width()
        height = self.get_height()

        if width is None and height is None:
            super().draw(renderer)
        else:
            (x0, y0), (x1, y1) = self.axes.transData.inverted().transform(
                self.get_window_extent(renderer)
            )

            if (width is None or abs(x1 - x0) <= width) and (
                height is None or abs(y1 - y0) <= height
            ):
                super().draw(renderer)


__tracker.validate()

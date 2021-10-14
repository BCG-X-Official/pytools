"""
Utilities related to matplotlib.
"""

import logging
from typing import Any, Union

from matplotlib.backend_bases import RendererBase
from matplotlib.text import Text
from matplotlib.ticker import Formatter

from pytools.api import AllTracker
from pytools.meta import SingletonMeta

log = logging.getLogger(__name__)


#
# Exported names
#

__all__ = [
    "FittedText",
    "PercentageFormatter",
]


#
# Ensure all symbols introduced below are included in __all__
#

__tracker = AllTracker(globals())


#
# Classes
#


class PercentageFormatter(Formatter, metaclass=SingletonMeta):
    """
    Formats floats as a percentages with 3 digits precision, omitting trailing zeros.

    For percentages above 100%, formats percentages as the nearest whole number.

    Formatting examples:

    - ``0.00005`` is formatted as ``0.01%``
    - ``0.0005`` is formatted as ``0.05%``
    - ``0.0`` is formatted as ``0%``
    - ``0.1`` is formatted as ``10%``
    - ``1.0`` is formatted as ``100%``
    - ``0.01555`` is formatted as ``1.56%``
    - ``0.1555`` is formatted as ``15.6%``
    - ``1.555`` is formatted as ``156%``
    - ``15.55`` is formatted as ``1556%``
    - ``1555`` is formatted as ``1.6e+05%``
    """

    def __call__(self, x, pos=None) -> str:
        if x < 1.0:
            return f"{x * 100.0:.3g}%"
        else:
            return f"{round(x * 100.0):.5g}%"


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


# check consistency of __all__

__tracker.validate()

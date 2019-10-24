#
# NOT FOR CLIENT USE!
#
# This is a pre-release library under development. Handling of IP rights is still
# being investigated. To avoid causing any potential IP disputes or issues, DO NOT USE
# ANY OF THIS CODE ON A CLIENT PROJECT, not even in modified form.
#
# Please direct any queries to any of:
# - Jan Ittner
# - Jörg Schneider
# - Florent Martin
#

"""
The Gamma visualization library, providing MVC-based classes for rendering data in
different styles, e.g., as charts or plain text.
"""
import logging
import sys
from abc import ABC, abstractmethod
from threading import Lock
from typing import *
from typing import TextIO

import matplotlib.pyplot as plt
from matplotlib import text as mt
from matplotlib.axes import Axes

log = logging.getLogger(__name__)

# Rgba color class for use in  MatplotStyles
RgbaColor = Tuple[float, float, float, float]

#
# view: class DrawStyle
#


class DrawStyle(ABC):
    """
    Base class for a drawer style.
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._lock = Lock()

    @abstractmethod
    def _drawing_start(self, title: str) -> None:
        """
        Start drawing a new chart.
        :title: the chart title
        """
        pass

    def _drawing_finalize(self) -> None:
        """
        Finalize the chart.
        """
        pass


class MatplotStyle(DrawStyle, ABC):
    """Matplotlib drawer style.

    Implementations must define :meth:`~DrawStyle.draw_title`.
    :param ax: optional axes object to draw on; if `Null` use pyplot's current axes
    """

    def __init__(self, ax: Optional[Axes] = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self._ax = ax = plt.gca() if ax is None else ax
        self._renderer = ax.figure.canvas.get_renderer()

    @property
    def ax(self) -> Axes:
        """
        The matplot :class:`~matplotlib.axes.Axes` object to draw the chart in.
        """
        return self._ax

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


class TextStyle(DrawStyle, ABC):
    """
    Plain text drawing style.

    :param width: the maximum width available to render the text, defaults to 80
    :param out: the output stream this style instance writes to, or `stdout` if \
      `None` is passed (defaults to `None`)
    """

    def __init__(self, out: TextIO = None, width: int = 80, **kwargs) -> None:
        super().__init__(**kwargs)

        if width <= 0:
            raise ValueError(
                f"arg width expected to be positive integer but is {width}"
            )
        self._out = sys.stdout if out is None else out
        self._width = width

    @property
    def out(self) -> TextIO:
        """
        The output stream this style instance writes to.
        """
        return self._out

    @property
    def width(self) -> int:
        """
        The maximum width of the text to be produced.
        """
        return self._width


#
# controller: class Drawer
#

# type variables
T_Model = TypeVar("T_Model")
T_Style = TypeVar("T_Style", bound=DrawStyle)


class Drawer(ABC, Generic[T_Model, T_Style]):
    """
    Base class for drawers.

    :param style: the style of the chart; either as a :class:`~gamma.viz.DrawStyle` \
        instance, or as the name of a default style. Permissible names include \
        "matplot" for a style supporting Matplotlib, and "text" if text rendering is \
        supported (default: `"matplot"`)
    """

    def __init__(self, style: Union[T_Style, str] = "matplot") -> None:
        if isinstance(style, str):
            try:
                # get the named style from the style dict, and instantiate it
                self._style: T_Style = self._get_style_dict()[style]()
            except KeyError:
                raise KeyError(f"Unknown named style: {style}")
        elif isinstance(style, DrawStyle):
            self._style = style
        else:
            raise TypeError(
                "arg style expected to be a string, or an instance of class "
                f"{DrawStyle.__name__}"
            )

    @property
    def style(self) -> T_Style:
        """The drawing style used by this drawer."""
        return self._style

    def draw(self, data: T_Model, title: str) -> None:
        """
        Draw the chart.
        :param data: the data to draw
        :param title: the title of the chart
        """
        style = self.style
        # styles might hold some drawing context, so make sure we are thread safe
        # noinspection PyProtectedMember
        with style._lock:
            # noinspection PyProtectedMember
            style._drawing_start(title)
            self._draw(data)
            # noinspection PyProtectedMember
            style._drawing_finalize()

    @classmethod
    @abstractmethod
    def _get_style_dict(cls) -> Mapping[str, Type[T_Style]]:
        """
        Get a mapping from names to style classes.
        """
        pass

    @abstractmethod
    def _draw(self, data: T_Model) -> None:
        pass

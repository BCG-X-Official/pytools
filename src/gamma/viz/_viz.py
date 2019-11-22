"""
The Gamma visualization library, providing MVC-based classes for rendering data in
different styles, e.g., as charts or plain text.
"""
import logging
from abc import ABC, abstractmethod
from threading import Lock
from typing import *

log = logging.getLogger(__name__)

__all__ = ["Drawer", "DrawStyle"]


#
# view: class DrawStyle
#


class DrawStyle(ABC):
    """
    Base class for a drawer style.
    """

    def __init__(self, **kwargs) -> None:
        super().__init__()
        if len(kwargs) > 0:
            raise KeyError(
                f'unknown argument{"s" if len(kwargs) > 1 else ""}: '
                f'{", ". join(kwargs.keys())}'
            )
        self._lock = Lock()

    @abstractmethod
    def _drawing_start(self, title: str) -> None:
        """
        Start drawing a new chart.
        :param title: the chart title
        """
        pass

    def _drawing_finalize(self) -> None:
        """
        Finalize the chart.
        """
        pass


#
# controller: class Drawer
#

# type variables
T_Model = TypeVar("T_Model")
T_Style = TypeVar("T_Style", bound=DrawStyle)


class Drawer(ABC, Generic[T_Model, T_Style]):
    """
    Base class for drawers.
    """

    def __init__(self, style: Union[T_Style, str] = "matplot") -> None:
        """
        :param style: the style of the chart; either as a
            :class:`~gamma.viz.DrawStyle` instance, or as the name of a default style. \
            Permissible names include "matplot" for a style supporting Matplotlib, and \
            "text" if text rendering is supported (default: `"matplot"`)
        """
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

    @classmethod
    def get_named_styles(cls) -> FrozenSet[str]:
        """
        The names of all named styles recognized by this drawer's initializer.
        """
        return cast(FrozenSet, cls._get_style_dict().keys())

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

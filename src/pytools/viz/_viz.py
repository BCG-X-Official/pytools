"""
The Gamma visualization library, providing `model/view/controller` oriented classes for
rendering data in different shapes, styles and formats, e.g., as matplot charts or
plain text.
"""
import logging
from abc import ABCMeta, abstractmethod
from threading import Lock
from typing import (
    Any,
    FrozenSet,
    Generic,
    Mapping,
    Optional,
    Type,
    TypeVar,
    Union,
    cast,
)

from ..api import AllTracker

log = logging.getLogger(__name__)


#
# Exported names
#

__all__ = ["DrawingStyle", "Drawer"]


#
# Type variables
#

T_Model = TypeVar("T_Model")
# noinspection PyTypeChecker
T_Style = TypeVar("T_Style", bound="DrawStyle")


#
# Ensure all symbols introduced below are included in __all__
#

__tracker = AllTracker(globals())


#
# Classes
#


# View: class DrawStyle


class DrawingStyle(metaclass=ABCMeta):
    """
    Base style class for a :class:`.Drawer`.

    Provides low-level rendering methods used by specific type of :class:`.Drawer`.
    Typically, there are several draw styles for one drawer type, offering the same
    rendering methods but implementing them differently (e.g., matplot output vs. text
    output).
    The style class and its rendering methods should not be aware of the actual object
    to be rendered; overall control of the rendering process stays with the
    :class:`.Drawer`; the associated style object only carries out the low-level
    rendering and controls formatting.

    For example, a :class:`.MatrixDrawer` requires a :class:`.MatrixStyle` to render
    matrices.
    :class:`.MatrixStyle` is an abstract subclass of :class:`DrawStyle` and has three
    implementations to output matrices as matplot charts or as a text report:
    :class: `.MatrixMatplotStyle`, :class:`PercentageMatrixMatplotStyle`,
    and :class:`MatrixReportStyle`.

    Many style objects can be further parameterised to control how objects are rendered.
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        if len(kwargs) > 0:
            raise KeyError(
                f'unknown argument{"s" if len(kwargs) > 1 else ""}: '
                f'{", ". join(kwargs.keys())}'
            )
        self._lock = Lock()

    @abstractmethod
    def _drawing_start(self, title: str, **kwargs) -> None:
        # Prepare the new chart for drawing, using the given title.
        #
        # Any additional drawer-specific attributes will be passed
        # as additional keyword arguments.
        pass

    def _drawing_finalize(self, **kwargs) -> None:
        # Finalize the drawing.
        #
        # Any additional drawer-specific attributes will be passed
        # as additional keyword arguments.
        #
        # Does nothing unless overloaded.
        pass


# Controller: class Drawer


class Drawer(Generic[T_Model, T_Style], metaclass=ABCMeta):
    """
    Base class for drawers.

    Drawers are associated with a :class:`.DrawStyle` object and are able to render
    a on object of a specific type (the `model`), using the drawing methods provided
    by the style object.
    """

    #: The :class:`.DrawStyle` object used by this drawer
    style: T_Style

    def __init__(self, style: Optional[Union[T_Style, str]] = None) -> None:
        """
        :param style: the style of the chart; either as a \
            :class:`.DrawStyle` instance, or as the name of a default style. \
            Permissible names include "matplot" for a style supporting Matplotlib, and \
            "text" if text rendering is supported (default: ``"matplot"``)
        """

        def _get_style_cls(_style_name) -> Type[T_Style]:
            # get the named style from the style dict
            try:
                return self._get_style_dict()[_style_name]
            except KeyError:
                raise KeyError(f"Unknown named style: {_style_name}")

        if style is None:
            self.style = _get_style_cls("matplot")()
        elif isinstance(style, str):
            self.style = _get_style_cls(style)()
        elif isinstance(style, DrawingStyle):
            self.style = style
        else:
            raise TypeError(
                "arg style expected to be a string, or an instance of class "
                f"{DrawingStyle.__name__}"
            )

    @classmethod
    def get_named_styles(cls) -> FrozenSet[str]:
        """
        The names of all default styles recognized by this drawer's initializer.
        """
        return cast(FrozenSet, cls._get_style_dict().keys())

    def draw(self, data: T_Model, title: str) -> None:
        """
        Render the data using the style associated with this drawer.

        :param data: the data to be rendered
        :param title: the title of the resulting chart
        """
        style = self.style

        # styles might hold some drawing context, so make sure we are thread safe
        # noinspection PyProtectedMember
        with style._lock:
            style_attributes = self._get_style_attributes(data)
            # noinspection PyProtectedMember
            style._drawing_start(title, **style_attributes)
            self._draw(data)
            # noinspection PyProtectedMember
            style._drawing_finalize(**style_attributes)

    @classmethod
    @abstractmethod
    def _get_style_dict(cls) -> Mapping[str, Type[T_Style]]:
        # Get a mapping from names to style classes.
        pass

    def _get_style_attributes(self, data: T_Model) -> Mapping[str, Any]:
        # using the given data object, derive attributes to be passed to the
        # style's _drawing_start and _drawing_finalize methods
        # Returns an empty mapping unless overloaded
        return dict()

    @abstractmethod
    def _draw(self, data: T_Model) -> None:
        # core drawing method invoked my method draw(), to be implemented by subclasses
        pass


__tracker.validate()

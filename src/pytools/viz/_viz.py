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
T_Style = TypeVar("T_Style", bound="DrawingStyle")


#
# Ensure all symbols introduced below are included in __all__
#

__tracker = AllTracker(globals())


#
# Classes
#


# View: class DrawingStyle


class DrawingStyle(metaclass=ABCMeta):
    """
    Base class for styles used by :class:`.Drawer` objects.

    Provides low-level rendering methods used by specific type of :class:`.Drawer`.
    Typically, there are several drawing styles for one drawer type, offering the same
    rendering methods but implementing them differently (e.g., matplot output vs. text
    output).
    The style class and its rendering methods should not be aware of the actual object
    to be rendered; overall control of the rendering process stays with the
    :class:`.Drawer`; the associated style object only carries out the low-level
    rendering and controls formatting.

    For example, a :class:`.MatrixDrawer` requires a :class:`.MatrixStyle` to render
    matrices.
    :class:`.MatrixStyle` is an abstract subclass of :class:`DrawingStyle` and has three
    implementations to output matrices as matplot charts or as a text report:
    :class:`.MatrixMatplotStyle`, :class:`.PercentageMatrixMatplotStyle`,
    and :class:`.MatrixReportStyle`.

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
        """
        Prepare a new chart for drawing, using the given title.

        Any additional drawer-specific attributes, obtained from
        method :meth:`Drawer._get_style_kwargs`, will be passed
        as keyword arguments.

        :meta public:
        :param title: the title of the chart
        """

    pass

    def _drawing_finalize(self, **kwargs) -> None:
        """
        Finalize the drawing.

        Any additional drawer-specific attributes, obtained from
        method :meth:`Drawer._get_style_kwargs`, will be passed
        as keyword arguments.

        :meta public:
        """
        pass


# Controller: class Drawer


class Drawer(Generic[T_Model, T_Style], metaclass=ABCMeta):
    """
    Base class for drawers.

    Drawers follow a `Model-View-Controller` design `(MVC)`.
    Each :class:`Drawer` (the `controller`) is associated with a :class:`.DrawingStyle`
    object (the `view`) and renders objects of a specific type (the `model`),
    using the low-level drawing methods provided by the style object.

    While the drawer controls the overall drawing process (e.g., drawing a tree or a
    matrix), the style objects determines the format of the output, e.g., a text or
    a line drawing.
    """

    #: The :class:`.DrawingStyle` used by this drawer
    style: T_Style

    def __init__(self, style: Optional[Union[T_Style, str]] = None) -> None:
        """
        :param style: the style to be used for drawing; either as a
            :class:`.DrawingStyle` instance, or as the name of a default style.
            Permissible names include ``"matplot"`` for a style supporting `matplotlib`,
            and ``"text"`` if text rendering is supported (default: ``"matplot"``)
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
        The names of all named styles recognized by this drawer's initializer.
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
            style_attributes = self._get_style_kwargs(data)
            # noinspection PyProtectedMember
            style._drawing_start(title, **style_attributes)
            self._draw(data)
            # noinspection PyProtectedMember
            style._drawing_finalize(**style_attributes)

    @classmethod
    @abstractmethod
    def _get_style_dict(cls) -> Mapping[str, Type[T_Style]]:
        """
        Get mapping of names to style classes available for this drawer type.

        :meta public:
        :returns: a mapping of names to style classes
        """
        pass

    def _get_style_kwargs(self, data: T_Model) -> Mapping[str, Any]:
        """
        Using the given data object, derive keyword arguments to be passed to the
        style's :meth:`.Drawer._drawing_start` and
        :meth:`.Drawer._drawing_finalize` methods.

        :meta public:
        :param data: the data to be rendered
        :returns: the style attributes for the given data object
        """
        return dict()

    @abstractmethod
    def _draw(self, data: T_Model) -> None:
        """
        Core drawing method invoked my method :meth:`.draw`.

        :meta public:
        :param data: the data to be rendered
        """
        pass


__tracker.validate()

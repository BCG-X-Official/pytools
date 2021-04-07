"""
The GAMMA visualization library, providing `model/view/controller` oriented classes for
rendering data in different shapes, styles and formats, e.g., as matplot charts or
plain text.
"""
import logging
from abc import ABCMeta, abstractmethod
from threading import Lock
from typing import Any, Dict, Generic, Iterable, Optional, Type, TypeVar, Union, cast

from ..api import AllTracker, inheritdoc
from .color import ColorScheme, FacetDarkColorScheme, FacetLightColorScheme

log = logging.getLogger(__name__)

#
# Exported names
#

__all__ = ["DrawingStyle", "ColoredStyle", "Drawer"]

#
# Type variables
#

T = TypeVar("T")
T_Model = TypeVar("T_Model")
T_Style = TypeVar("T_Style", bound="DrawingStyle")
T_Style_Class = TypeVar("T_Style_Class", bound=Type["DrawingStyle"])
T_ColorScheme = TypeVar("T_ColorScheme", bound=ColorScheme)


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
                f'{", ".join(kwargs.keys())}'
            )
        self._lock = Lock()

    @classmethod
    def get_named_styles(cls: T_Style_Class) -> Dict[str, T_Style_Class]:
        """
        Get a mapping of names to default instances of this style class.

        :return: a dictionary mapping of names to default instances of this style class
        """
        return {cls.get_default_style_name(): cls}

    @classmethod
    @abstractmethod
    def get_default_style_name(cls) -> str:
        """
        Get the name of the default style associated with this style class.

        The default style is obtained by instantiating this style class without
        parameters.

        Common examples for default style names are `matplot` and `text`.

        :return: the name of the default style
        """

    @abstractmethod
    def start_drawing(self, title: str, **kwargs) -> None:
        """
        Prepare a new chart for drawing, using the given title.

        Any additional drawer-specific attributes, obtained from
        method :meth:`Drawer._get_style_kwargs`, will be passed
        as keyword arguments.

        :param title: the title of the chart
        """

    def finalize_drawing(self, **kwargs) -> None:
        """
        Finalize the drawing.

        Any additional drawer-specific attributes, obtained from
        method :meth:`.Drawer._get_style_kwargs`, will be passed
        as keyword arguments.
        """


@inheritdoc(match="[see superclass]")
class ColoredStyle(DrawingStyle, Generic[T_ColorScheme], metaclass=ABCMeta):
    """
    A drawing style that supports color output.
    """

    def __init__(self, *, colors: Optional[T_ColorScheme] = None, **kwargs) -> None:
        """
        :param colors: the color scheme to be used by this drawing style
        """
        super().__init__(**kwargs)
        self._colors = colors or FacetLightColorScheme()

    @classmethod
    def dark(cls: T_Style_Class) -> T_Style_Class:
        """
        Create a dark variant of the given drawing style, using the default dark
        background color scheme :class:`.FacetDarkColorScheme`.

        :return: the dark drawing style class
        """

        class DarkStyle(ColoredStyle, metaclass=ABCMeta):
            """
            The dark variant of a :class:`.ColoredStyle`, using the
            :class:`.FacetDarkColorScheme`.
            """

            def __init__(self, **kwargs) -> None:
                """
                :param kwargs: init parameters for the new drawing style instance
                """
                super().__init__(colors=FacetDarkColorScheme(), **kwargs)

        dark_style_class = cast(
            T_Style_Class, type(f"Dark{cls.__name__}", (DarkStyle, cls), {})
        )
        dark_style_class.__module__ = cls.__module__
        return dark_style_class

    @classmethod
    def get_named_styles(cls: T_Style_Class) -> Dict[str, T_Style_Class]:
        """[see superclass]"""
        named_styles = super().get_named_styles()
        return {
            **named_styles,
            **{
                f"{name}_dark": cast(ColoredStyle, style).dark()
                for name, style in named_styles.items()
                if isinstance(style, type)
            },
        }

    @property
    def colors(self) -> T_ColorScheme:
        """
        The color scheme used by this style.
        """
        return self._colors


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

    #: The :class:`.DrawingStyle` used by this drawer.
    style: T_Style

    #: The name of the default drawing style.
    DEFAULT_STYLE = "matplot"

    def __init__(self, style: Optional[Union[T_Style, str]] = None) -> None:
        """
        :param style: the style to be used for drawing; either as a
            :class:`.DrawingStyle` instance, or as the name of a default style.
            Permissible names include ``"matplot"`` for a style supporting `matplotlib`,
            and ``"text"`` if text rendering is supported (default: ``"%DEFAULT%"``)
        """

        def _get_style_factory(_style_name) -> Type[T_Style]:
            # get the named style from the style dict
            try:
                return self.get_named_styles()[_style_name]
            except KeyError:
                raise KeyError(f"unknown named style: {_style_name}")

        if style is None:
            self.style = _get_style_factory(Drawer.DEFAULT_STYLE)()
        elif isinstance(style, str):
            self.style = _get_style_factory(style)()
        elif isinstance(style, DrawingStyle):
            self.style = style
        else:
            raise TypeError(
                "arg style expected to be a string, or an instance of class "
                f"{DrawingStyle.__name__}"
            )

    __init__.__doc__ = __init__.__doc__.replace("%DEFAULT%", DEFAULT_STYLE)

    @classmethod
    def get_named_styles(cls) -> Dict[str, Type[T_Style]]:
        """
        Get a mapping of names to style factories for all named styles recognized by
        this drawer's initializer.

        A factory is a class or function with no mandatory parameters.
        """

        return {
            name: style
            for style_class in cls.get_style_classes()
            for name, style in style_class.get_named_styles().items()
        }

    @classmethod
    @abstractmethod
    def get_style_classes(cls) -> Iterable[Type[T_Style]]:
        """
        Get all style classes available for this drawer type.

        :returns: an iterable of style classes
        """
        pass

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
            style.start_drawing(title, **style_attributes)
            self._draw(data)
            # noinspection PyProtectedMember
            style.finalize_drawing(**style_attributes)

    def _get_style_kwargs(self, data: T_Model) -> Dict[str, Any]:
        """
        Using the given data object, derive keyword arguments to be passed to the
        style's :meth:`~DrawingStyle.start_drawing` and
        :meth:`~DrawingStyle.finalize_drawing` methods.

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

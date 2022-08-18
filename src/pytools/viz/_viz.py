"""
The GAMMA visualization library, providing `model/view/controller` oriented classes for
rendering data in different shapes, styles and formats, e.g., as matplot charts or
plain text.
"""
import logging
from abc import ABCMeta, abstractmethod
from multiprocessing import Lock
from typing import (
    Any,
    Callable,
    Dict,
    Generic,
    Iterable,
    Optional,
    Type,
    TypeVar,
    Union,
    cast,
)

from ..api import AllTracker, inheritdoc
from .color import ColorScheme

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
    Typically, there are several drawing styles for one drawer type, implementing
    different rendering methods for the same data type (e.g., matplot output vs. text
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

    #: drawer status: drawing not started, started, finalized
    _status: int

    #: drawer status value: drawing not started
    _STATUS_NOT_STARTED = 0

    #: drawer status value: drawing started
    _STATUS_STARTED = 1

    #: drawer status value: drawing finalized
    _STATUS_FINALIZED = 2

    def __init__(self) -> None:
        super().__init__()
        self._lock = Lock()

    @classmethod
    def get_named_styles(cls: Type[T_Style]) -> Dict[str, Callable[..., T_Style]]:
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

    def start_drawing(self, *, title: str, **kwargs: Any) -> None:  # NOSONAR
        """
        Prepare a new chart for drawing, using the given title.

        Any additional drawer-specific arguments, obtained from
        method :meth:`Drawer.get_style_kwargs`, will be passed
        as keyword arguments.

        Subclasses overriding this method must call ``super().start_drawing()``
        *before* executing their own drawer-specific initializations.

        :param title: the title of the chart
        :param kwargs: additional drawer-specific arguments
        :raise ValueError: additional keyword arguments were specified
        """
        self._status = DrawingStyle._STATUS_STARTED

    def finalize_drawing(self, **kwargs: Any) -> None:  # NOSONAR
        """
        Finalize the drawing.

        Any additional drawer-specific arguments, obtained from
        method :meth:`.Drawer.get_style_kwargs`, will be passed
        as keyword arguments.

        Subclasses overriding this method must call ``super().finalize_drawing()``
        *after* executing their own drawer-specific finalization.

        :param kwargs: additional drawer-specific arguments
        """
        self._status = DrawingStyle._STATUS_FINALIZED


@inheritdoc(match="[see superclass]")
class ColoredStyle(DrawingStyle, Generic[T_ColorScheme], metaclass=ABCMeta):
    """
    A drawing style that supports color output.
    """

    #: the color scheme used by this drawing style
    _colors: T_ColorScheme

    def __init__(self, *, colors: Optional[T_ColorScheme] = None) -> None:
        """
        :param colors: the color scheme to be used by this drawing style
            (default: :class:`.%%COLORS_DEFAULT%%`)
        """
        super().__init__()
        self._colors = colors or cast(T_ColorScheme, ColorScheme.DEFAULT)

    __init__.__doc__ = cast(str, __init__.__doc__).replace(
        "%%COLORS_DEFAULT%%", repr(ColorScheme.DEFAULT)
    )

    @classmethod
    def get_named_styles(
        cls: Type[T_Style],
    ) -> Dict[str, Callable[..., T_Style]]:
        """[see superclass]"""
        named_styles: Dict[str, Callable[..., T_Style]] = cast(
            Type[T_Style], super()
        ).get_named_styles()

        return {
            **named_styles,
            **{
                f"{name}_dark": cast(
                    Callable[..., T_Style],
                    lambda s=style: s(colors=ColorScheme.DEFAULT_DARK),
                )
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

        def _get_style_factory(_style_name: str) -> Callable[..., T_Style]:
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

    __init__.__doc__ = cast(str, __init__.__doc__).replace("%DEFAULT%", DEFAULT_STYLE)

    @classmethod
    def get_named_styles(cls) -> Dict[str, Callable[..., T_Style]]:
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

    def draw(self, data: T_Model, *, title: str) -> None:
        """
        Render the data using the style associated with this drawer.

        Creates a thread-safe lock on this drawer, then calls the following methods in
        sequence:

        1. Method :meth:`~.DrawingStyle.start_drawing` of this drawer's :attr:`~style`
           attribute, passing the title and additional keyword arguments obtained from
           this drawer's :meth:`~get_style_kwargs`
        2. Method :meth:`._draw`, passing along the ``data`` argument
        3. Method :meth:`~.DrawingStyle.finalize_drawing` of this drawer's
           :attr:`~style` attribute, passing the keyword arguments obtained from this
           drawer's :meth:`~get_style_kwargs`

        :param data: the data to be rendered
        :param title: the title of the resulting chart
        """
        style = self.style

        # styles might hold some drawing context, so make sure we are thread safe
        # noinspection PyProtectedMember
        with style._lock:
            style_attributes = self.get_style_kwargs(data)

            # noinspection PyProtectedMember
            style._status = style._STATUS_NOT_STARTED
            style.start_drawing(title=title, **style_attributes)
            # noinspection PyProtectedMember
            if style._status != DrawingStyle._STATUS_STARTED:
                raise AssertionError(
                    "DrawingStyle.start_drawing() not called from overloaded method"
                )

            self._draw(data)

            style.finalize_drawing(**style_attributes)
            # noinspection PyProtectedMember
            if style._status != DrawingStyle._STATUS_FINALIZED:
                raise AssertionError(
                    "DrawingStyle.finalize_drawing() not called from overloaded method"
                )

    def get_style_kwargs(self, data: T_Model) -> Dict[str, Any]:
        """
        Using the given data object, derive keyword arguments to be passed to the
        style's :meth:`~.DrawingStyle.start_drawing` and
        :meth:`~.DrawingStyle.finalize_drawing` methods.

        :param data: the data to be rendered
        :returns: the style attributes for the given data object
        """
        return dict()

    @abstractmethod
    def _draw(self, data: T_Model) -> None:
        """
        Core drawing method invoked my method :meth:`.draw`.

        Must be implemented by subclasses of :class:`.Drawer`.

        :meta public:
        :param data: the data to be rendered
        """
        pass


__tracker.validate()

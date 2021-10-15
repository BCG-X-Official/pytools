"""
Core implementation of :mod:`pytools.viz.color`
"""

import logging
from typing import Set, TypeVar, Union

from matplotlib import cm
from matplotlib.colors import Colormap, LinearSegmentedColormap

from ._rgb import RgbaColor, RgbColor
from pytools.api import AllTracker, inheritdoc, validate_element_types, validate_type
from pytools.expression import Expression, HasExpressionRepr
from pytools.expression.atomic import Id
from pytools.meta import SingletonMeta, compose_meta

log = logging.getLogger(__name__)

#
# Exported names
#

__all__ = [
    "ColorScheme",
    "MatplotColorScheme",
    "FacetLightColorScheme",
    "FacetDarkColorScheme",
]

#
# Type variables
#

# noinspection PyTypeChecker
T_Color = TypeVar("T_Color", RgbColor, RgbaColor)

#
# Ensure all symbols introduced below are included in __all__
#

__tracker = AllTracker(globals())


#
# Constants
#

#: Black.
_RGB_BLACK = RgbColor("black")

#: White.
_RGB_WHITE = RgbColor("white")

#: FACET light grey.
_RGB_LIGHT_GREY = RgbColor("#c8c8c8")

#: FACET grey.
_RGB_GREY = RgbColor("#9a9a9a")

#: FACET dark grey.
_RGB_DARK_GREY = RgbColor("#3d3a40")

#: FACET dark blue.
_RGB_DARK_BLUE = RgbColor("#295e7e")

#: FACET blue.
_RGB_LIGHT_BLUE = RgbColor("#30c1d7")

#: FACET green.
_RGB_LIGHT_GREEN = RgbColor("#43fda2")

#: FACET status green.
_RGB_GREEN = RgbColor("#3ead92")

#: FACET status amber.
_RGB_AMBER = RgbColor("#a8b21c")

#: FACET status red.
_RGB_RED = RgbColor("#e61c57")

#: FACET dark red.
_RGB_DARK_RED = RgbColor("#c41310")

#: Standard colormap for FACET.
_COLORMAP_FACET = LinearSegmentedColormap.from_list(
    name="facet",
    colors=[
        (0, _RGB_DARK_GREY),
        (0.25, _RGB_DARK_BLUE),
        (0.65, _RGB_LIGHT_BLUE),
        (1.0, _RGB_LIGHT_GREEN),
    ],
)


#
# Classes
#


@inheritdoc(match="[see superclass]")
class ColorScheme(HasExpressionRepr):
    """
    A color scheme mapping semantic color designations to RGB colors,
    allowing code to refer to colors by usage rather than specific RGB values.
    """

    #: The default color scheme.
    DEFAULT: "ColorScheme"

    #: The default light color scheme.
    DEFAULT_LIGHT: "FacetLightColorScheme"

    #: The default dark color scheme.
    DEFAULT_DARK: "FacetDarkColorScheme"

    def __init__(
        self, foreground: RgbColor, background: RgbColor, **colors: RgbColor
    ) -> None:
        """
        :param foreground: the foreground color
        :param background: the background color
        :param colors: additional colors as keyword arguments; one or more of %COLORS%
        """
        validate_type(foreground, expected_type=tuple, name="arg foreground")
        validate_type(background, expected_type=tuple, name="arg background")
        unsupported_colors = colors.keys() - ColorScheme._SUPPORTED_COLORS
        if unsupported_colors:
            raise ValueError(f"unsupported color arguments: {unsupported_colors}")
        validate_element_types(colors.values(), expected_type=tuple, name="**colors")
        self._colors = {
            ColorScheme._COLOR_FOREGROUND: foreground,
            ColorScheme._COLOR_BACKGROUND: background,
            **colors,
        }

    @property
    def foreground(self) -> RgbColor:
        """
        The foreground color.
        """
        return self._colors[ColorScheme._COLOR_FOREGROUND]

    @property
    def background(self) -> RgbColor:
        """
        The background color.
        """
        return self._colors[ColorScheme._COLOR_BACKGROUND]

    @property
    def fill_1(self) -> RgbColor:
        """
        The primary fill color.

        Defaults to the halfway point between the foreground and background color
        if not defined explicitly.
        """
        return self._colors.get(ColorScheme._COLOR_FILL_1, None) or tuple(
            (f + b) / 2 for f, b in zip(self.foreground, self.background)
        )

    @property
    def fill_2(self) -> RgbColor:
        """
        The secondary fill color.

        Defaults to the primary fill color if not defined explicitly.
        """
        return self._colors.get(ColorScheme._COLOR_FILL_2, None) or self.fill_1

    @property
    def fill_3(self) -> RgbColor:
        """
        The tertiary fill color.

        Defaults to the primary fill color if not defined explicitly.
        """
        return self._colors.get(ColorScheme._COLOR_FILL_3, None) or self.fill_1

    @property
    def accent_1(self) -> RgbColor:
        """
        The primary accent color.

        Defaults to the foreground color if not defined explicitly.
        """
        return self._colors.get(ColorScheme._COLOR_ACCENT_1, None) or self.foreground

    @property
    def accent_2(self) -> RgbColor:
        """
        The secondary accent color.

        Defaults to the primary accent color if not defined explicitly.
        """
        return self._colors.get(ColorScheme._COLOR_ACCENT_2, None) or self.accent_1

    @property
    def accent_3(self) -> RgbColor:
        """
        The tertiary accent color.

        Defaults to the secondary accent color if not defined explicitly.
        """
        return self._colors.get(ColorScheme._COLOR_ACCENT_3, None) or self.accent_2

    @property
    def status_ok(self) -> RgbColor:
        """
        The traffic light color indicating "ok" status.

        Defaults to the primary accent color if not defined explicitly.
        """
        return self._colors.get(ColorScheme._COLOR_STATUS_OK, None) or self.accent_1

    @property
    def status_warning(self) -> RgbColor:
        """
        The traffic light color indicating "warning" status.

        Defaults to the secondary accent color if not defined explicitly.
        """
        return (
            self._colors.get(ColorScheme._COLOR_STATUS_WARNING, None) or self.accent_2
        )

    @property
    def status_critical(self) -> RgbColor:
        """
        The traffic light color indicating "critical" status.

        Defaults to the tertiary accent color if not defined explicitly.
        """
        return (
            self._colors.get(ColorScheme._COLOR_STATUS_CRITICAL, None) or self.accent_3
        )

    def contrast_color(self, fill_color: T_Color) -> T_Color:
        """
        Return the foreground color or background color of this color schema,
        depending on which maximises contrast with the given fill color.

        If the fill colour includes an alpha channel, this will be included unchanged
        with the resulting contrast colour.

        :param fill_color: RGB or RGBA encoded fill color to maximise contrast with
        :return: the matching contrast color
        """

        if not 3 <= len(fill_color) <= 4:
            raise ValueError(f"arg fill_color={fill_color!r} must be an RGB(A) color")

        def _luminance(c: T_Color) -> float:
            return sum(c[:3])

        # find the color that maximises contrast
        fill_luminance = _luminance(fill_color)
        contrast_color: RgbColor = (
            self.foreground
            if (
                abs(_luminance(self.foreground) - fill_luminance)
                > abs(_luminance(self.background) - fill_luminance)
            )
            else self.background
        )

        # preserve alpha channel of the fill color, if present
        if len(fill_color) > 3:
            return contrast_color + (fill_color[3],)
        else:
            return contrast_color

    def to_expression(self) -> Expression:
        """[see superclass]"""
        return Id(type(self))(**self._colors)

    _COLOR_FOREGROUND = foreground.fget.__name__
    _COLOR_BACKGROUND = background.fget.__name__
    _COLOR_FILL_1 = fill_1.fget.__name__
    _COLOR_FILL_2 = fill_2.fget.__name__
    _COLOR_FILL_3 = fill_3.fget.__name__
    _COLOR_ACCENT_1 = accent_1.fget.__name__
    _COLOR_ACCENT_2 = accent_2.fget.__name__
    _COLOR_ACCENT_3 = accent_3.fget.__name__
    _COLOR_STATUS_OK = status_ok.fget.__name__
    _COLOR_STATUS_WARNING = status_warning.fget.__name__
    _COLOR_STATUS_CRITICAL = status_critical.fget.__name__

    _SUPPORTED_COLORS: Set[str]


ColorScheme._SUPPORTED_COLORS = {
    v
    for k, v in vars(ColorScheme).items()
    if k.startswith("_COLOR_")
    and (
        k
        not in {
            ColorScheme.foreground.fget.__name__,
            ColorScheme.background.fget.__name__,
        }
    )
}

# noinspection PyProtectedMember
ColorScheme.__init__.__doc__ = ColorScheme.__init__.__doc__.replace(
    "%COLORS%",
    ", ".join(sorted(map(lambda code: f"``{code}``", ColorScheme._SUPPORTED_COLORS))),
)


@inheritdoc(match="[see superclass]")
class MatplotColorScheme(ColorScheme):
    """
    A color scheme for use with `matplotlib`, based on *semantic* color designations
    and a default color bar, preventing code from referring to colors.

    For an overview of matplotlib's named color maps, see
    `here <https://matplotlib.org/tutorials/colors/colormaps.html>`_.
    """

    _colormap: Colormap

    def __init__(
        self,
        foreground: RgbColor,
        background: RgbColor,
        colormap: Union[Colormap, str],
        **colors: RgbColor,
    ) -> None:
        """
        :param colormap: the colormap for this style (see `Colormap reference
            <https://matplotlib.org/stable/gallery/color/colormap_reference.html>`__)
        """
        super().__init__(foreground=foreground, background=background, **colors)

        if isinstance(colormap, Colormap):
            self._colormap = colormap
        elif isinstance(colormap, str):
            self._colormap = cm.get_cmap(name=colormap)
        else:
            raise ValueError("arg colormap must be a Colormap or a string")

    __doc_lines = ColorScheme.__init__.__doc__.split("\n")
    __doc_lines.insert(-2, __init__.__doc__[1:])
    __init__.__doc__ = "\n".join(__doc_lines)
    del __doc_lines

    @property
    def colormap(self) -> Colormap:
        """
        The default colormap to use for color gradients.
        """
        return self._colormap

    def to_expression(self) -> Expression:
        """[see superclass]"""
        return Id(type(self))(**self._colors, colormap=self.colormap)


@inheritdoc(match="[see superclass]")
class _FacetColorScheme(MatplotColorScheme):
    def __init__(self, foreground: RgbColor, background: RgbColor) -> None:
        super().__init__(
            foreground=foreground,
            background=background,
            colormap=_COLORMAP_FACET,
            **{
                ColorScheme._COLOR_FILL_1: _RGB_LIGHT_GREY,
                ColorScheme._COLOR_FILL_2: _RGB_GREY,
                ColorScheme._COLOR_FILL_3: _RGB_DARK_GREY,
                ColorScheme._COLOR_ACCENT_1: _RGB_LIGHT_GREEN,
                ColorScheme._COLOR_ACCENT_2: _RGB_LIGHT_BLUE,
                ColorScheme._COLOR_ACCENT_3: _RGB_DARK_BLUE,
                ColorScheme._COLOR_STATUS_OK: _RGB_GREEN,
                ColorScheme._COLOR_STATUS_WARNING: _RGB_AMBER,
                ColorScheme._COLOR_STATUS_CRITICAL: _RGB_RED,
            },
        )

    def to_expression(self) -> Expression:
        """[see superclass]"""
        return Id(type(self))()


class FacetLightColorScheme(
    _FacetColorScheme, metaclass=compose_meta(SingletonMeta, type(_FacetColorScheme))
):
    """
    The default FACET color scheme with a light background.
    """

    def __init__(self) -> None:
        super().__init__(foreground=_RGB_BLACK, background=_RGB_WHITE)


class FacetDarkColorScheme(
    _FacetColorScheme, metaclass=compose_meta(SingletonMeta, type(_FacetColorScheme))
):
    """
    The default FACET color scheme with a dark background.
    """

    def __init__(self) -> None:
        super().__init__(foreground=_RGB_WHITE, background=_RGB_BLACK)


# set the default color schemes
ColorScheme.DEFAULT_LIGHT = FacetLightColorScheme()
ColorScheme.DEFAULT_DARK = FacetDarkColorScheme()
ColorScheme.DEFAULT = ColorScheme.DEFAULT_LIGHT

# check consistency of __all__

__tracker.validate()

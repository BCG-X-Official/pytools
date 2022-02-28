"""
Core implementation of :mod:`pytools.viz.color`
"""
from __future__ import annotations

import logging
from typing import Iterable, Optional, Tuple, cast, overload

from matplotlib.colors import to_rgba

from pytools.api import AllTracker

log = logging.getLogger(__name__)

#
# Exported names
#

__all__ = [
    "RgbColor",
    "RgbaColor",
]


#
# Type Aliases
#
TupleRgba = Tuple[float, float, float, float]

#
# Ensure all symbols introduced below are included in __all__
#

__tracker = AllTracker(globals())


#
# Classes
#


class _RgbBase(tuple):
    @property
    def r(self) -> float:
        """
        The luminosity value for the *red* channel.
        """
        return self[0]

    @property
    def g(self) -> float:
        """
        The luminosity value for the *green* channel.
        """
        return self[1]

    @property
    def b(self) -> float:
        """
        The luminosity value for the *blue* channel.
        """
        return self[2]


class RgbColor(_RgbBase):
    """
    RGB color type for use in color schemas and colored drawing styles.
    """

    @overload
    def __new__(cls, r: float, g: float, b: float) -> RgbColor:
        pass

    @overload
    def __new__(cls, c: str) -> RgbColor:
        pass

    def __new__(cls, *args, alpha: None = None, **kwargs):
        """
        :param r: the luminosity value for the *red* channel
        :param g: the luminosity value for the *green* channel
        :param b: the luminosity value for the *blue* channel
        :param c: a named color (see
            `matplotlib.colors <https://matplotlib.org/stable/api/colors_api.html>`__)
        """
        if alpha is not None:
            raise ValueError(
                "alpha channel is not supported by RgbColor, use RgbaColor instead"
            )
        if len(args) not in [0, 1, 3]:
            raise ValueError(f"need 1 color name or 3 RGB values, but got {args}")

        return super().__new__(cls, cast(Iterable, _to_rgba(*args, **kwargs)[:3]))


class RgbaColor(_RgbBase):
    """
    RGB + Alpha color type for use in color schemas and colored drawing styles.
    """

    @overload
    def __new__(
        cls, r: float, g: float, b: float, alpha: Optional[float] = None
    ) -> RgbaColor:
        pass

    @overload
    def __new__(cls, c: str, alpha: Optional[float] = None) -> RgbaColor:
        pass

    def __new__(cls, *args, **kwargs):
        """
        :param r: the luminosity value for the *red* channel
        :param g: the luminosity value for the *green* channel
        :param b: the luminosity value for the *blue* channel
        :param alpha: the opacity value for the *alpha* channel
        :param c: a named color (see
            `matplotlib.colors <https://matplotlib.org/stable/api/colors_api.html>`__)
        """
        return super().__new__(cls, _to_rgba(*args, **kwargs))

    @property
    def alpha(self) -> float:
        """
        The opacity value for the *alpha* channel.
        """
        return self[3]


@overload
def _to_rgba(r: float, g: float, b: float, alpha: Optional[float] = None) -> TupleRgba:
    pass


@overload
def _to_rgba(c: str, alpha: Optional[float] = None) -> TupleRgba:
    pass


def _to_rgba(
    *args,
    r: Optional[float] = None,
    g: Optional[float] = None,
    b: Optional[float] = None,
    alpha: Optional[float] = None,
    c: Optional[str] = None,
) -> TupleRgba:
    n_rgb_kwargs = (r is not None) + (g is not None) + (b is not None)
    if n_rgb_kwargs in (1, 2):
        raise ValueError(
            "incomplete RGB keyword arguments: need to provide r, g, and b"
        )
    is_rgb = n_rgb_kwargs > 0

    is_c = c is not None

    if args and (is_rgb or is_c):
        raise ValueError(
            "mixed use of positional and keyword arguments for color arguments"
        )
    if is_rgb and is_c:
        raise ValueError("mixed use of named color and color channels")

    # case 1: named color

    if len(args) == 1:
        c = args[0]
    elif len(args) == 2:
        c, alpha = args

    if isinstance(c, str):
        if isinstance(alpha, (float, int)):
            return to_rgba(c, alpha)
        elif alpha is None:
            return to_rgba(c)
        else:
            raise ValueError(f"alpha must be numeric but is: {alpha!r}")
    elif c is not None:
        raise ValueError(f"single color argument must be a string but is: {c!r}")

    # case 2: color channels

    rgb: Tuple[float, ...]
    if is_rgb:
        assert not (r is None or g is None or b is None)
        rgb = (r, g, b)
    else:
        if not all(isinstance(x, (float, int)) for x in args):
            raise ValueError(f"all color arguments must be numeric, but are: {args}")
        rgb = args

    rgba: TupleRgba
    if alpha is not None:
        if len(rgb) != 3:
            raise ValueError(f"need 3 RGB values but got {rgb}")
        rgba = cast(TupleRgba, (*rgb, alpha))
    else:
        if len(rgb) == 3:
            rgba = cast(TupleRgba, (*rgb, 1.0))
        elif len(rgb) == 4:
            rgba = cast(TupleRgba, rgb)
        else:
            raise ValueError(f"need 3 RGB values or 4 RGBA values but got: {rgb}")

    if all(isinstance(x, (float, int)) and 0.0 <= x <= 1.0 for x in rgba):
        assert len(rgba) == 4
        return rgba
    else:
        raise ValueError(f"invalid RGBA values: {rgba}")


# check consistency of __all__

__tracker.validate()


#
# helper methods
#

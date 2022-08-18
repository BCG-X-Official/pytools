"""
Core implementation of :mod:`pytools.viz.color`
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Tuple, cast, overload

from matplotlib.colors import to_rgb

from pytools.api import AllTracker

log = logging.getLogger(__name__)


#
# Constants
#

ALPHA_DEFAULT = 1.0


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
TupleRgb = Tuple[float, float, float]

#
# Ensure all symbols introduced below are included in __all__
#

__tracker = AllTracker(globals())


#
# Classes
#


class _RgbBase(tuple):  # type: ignore
    @property
    def r(self: Tuple[float, ...]) -> float:
        """
        The luminosity value for the *red* channel.
        """
        return self[0]

    @property
    def g(self: Tuple[float, ...]) -> float:
        """
        The luminosity value for the *green* channel.
        """
        return self[1]

    @property
    def b(self: Tuple[float, ...]) -> float:
        """
        The luminosity value for the *blue* channel.
        """
        return self[2]

    @classmethod
    def _check_arg_count(
        cls, args: Tuple[Any, ...], kwargs: Dict[str, Any], max_allowed: int
    ) -> None:
        if len(args) + len(kwargs) > max_allowed:
            args_list = ", ".join(
                (
                    *map(repr, args),
                    *(f"{name}={value!r}" for name, value in kwargs.items()),
                )
            )
            raise ValueError(
                f"{cls.__name__} expects at most {max_allowed} arguments but got: "
                f"{args_list}"
            )


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

    def __new__(cls, *args: Any, **kwargs: Any) -> RgbColor:
        """
        :param r: the luminosity value for the *red* channel
        :param g: the luminosity value for the *green* channel
        :param b: the luminosity value for the *blue* channel
        :param c: a named color (see
            `matplotlib.colors <https://matplotlib.org/stable/api/colors_api.html>`__)
        """

        cls._check_arg_count(args, kwargs, 3)

        rgb, alpha = _to_rgba(*args, **kwargs)

        if alpha is not None:
            raise ValueError(
                "alpha channel is not supported by RgbColor, use RgbaColor instead"
            )

        return cast(_RgbBase, super()).__new__(cls, rgb)


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

    def __new__(cls, *args: Any, **kwargs: Any) -> RgbaColor:
        """
        :param r: the luminosity value for the *red* channel
        :param g: the luminosity value for the *green* channel
        :param b: the luminosity value for the *blue* channel
        :param alpha: the opacity value for the *alpha* channel
        :param c: a named color (see
            `matplotlib.colors <https://matplotlib.org/stable/api/colors_api.html>`__)
        """
        cls._check_arg_count(args, kwargs, 4)

        rgb, alpha = _to_rgba(*args, **kwargs)

        return cast(_RgbBase, super()).__new__(
            cls,
            (*rgb, ALPHA_DEFAULT if alpha is None else alpha),
        )

    @property
    def alpha(self: Tuple[float, ...]) -> float:
        """
        The opacity value for the *alpha* channel.
        """
        return self[3]


@overload
def _to_rgba(
    r: float, g: float, b: float, alpha: Optional[float] = None
) -> Tuple[TupleRgb, Optional[float]]:
    pass


@overload
def _to_rgba(c: str, alpha: Optional[float] = None) -> Tuple[TupleRgb, Optional[float]]:
    pass


def _to_rgba(
    *args: Any,
    r: Optional[float] = None,
    g: Optional[float] = None,
    b: Optional[float] = None,
    alpha: Optional[float] = None,
    c: Optional[str] = None,
) -> Tuple[TupleRgb, Optional[float]]:
    n_rgb_kwargs = (r is not None) + (g is not None) + (b is not None)
    if n_rgb_kwargs in (1, 2):
        raise ValueError(
            "incomplete RGB keyword arguments: need to provide r, g, and b"
        )

    has_rgb_kwargs = n_rgb_kwargs > 0
    has_c = c is not None

    if args and (has_rgb_kwargs or has_c):
        raise ValueError(
            "mixed use of positional and keyword arguments for color arguments"
        )
    if has_rgb_kwargs and has_c:
        raise ValueError("mixed use of named color and color channels")

    # case 1: named color

    if args and isinstance(args[0], str):
        if len(args) == 1:
            c = args[0]
        elif len(args) == 2 and alpha is None:
            c, alpha = args

    if not (alpha is None or isinstance(alpha, (float, int))):
        raise ValueError(f"alpha must be numeric but is: {alpha!r}")

    if isinstance(c, str):
        return to_rgb(c), alpha
    elif c is not None:
        raise ValueError(f"single color argument must be a string but is: {c!r}")

    # case 2: color channels

    rgb: TupleRgb

    if has_rgb_kwargs:
        assert not (r is None or g is None or b is None)
        rgb = (r, g, b)
    else:
        if not all(isinstance(x, (float, int)) for x in args):
            raise ValueError(f"all color arguments must be numeric, but are: {args}")

        if len(args) == 3:
            rgb = cast(TupleRgb, args)
        elif len(args) == 4:
            rgb = cast(TupleRgb, args[:3])
            if alpha is None:
                alpha = args[3]
            else:
                raise ValueError(f"need 3 RGB values but got {args}")
        else:
            raise ValueError(f"need 3 RGB values or 4 RGBA values but got: {args}")

    if not all(isinstance(x, (float, int)) and 0.0 <= x <= 1.0 for x in rgb):
        raise ValueError(f"invalid RGB values: {rgb}")

    if not (alpha is None or 0.0 <= alpha <= 1.0):
        raise ValueError(f"invalid alpha value: {alpha}")

    assert len(rgb) == 3

    return rgb, alpha


# check consistency of __all__

__tracker.validate()


#
# helper methods
#

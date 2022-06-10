import pytest

from pytools.viz.color import RgbaColor, RgbColor

MSG_INCOMPLETE_RGB_KWARG = (
    "incomplete RGB keyword arguments: need to provide r, g, and b"
)
MSG_MUST_BE_A_STRING = "single color argument must be a string"
MSG_NEED_COLOR_NAME_OR_RGB_VALUES = "need 1 color name or 3 RGB values"
MSG_INVALID_RGBA_VALUES = "invalid RGBA values"


def test_rgb() -> None:
    red = (1.0, 0.0, 0.0)

    assert RgbColor("red") == red
    assert RgbColor(c="red") == red
    assert RgbColor(1, 0, 0) == red
    assert RgbColor(r=1, g=0, b=0) == red

    with pytest.raises(ValueError, match=MSG_NEED_COLOR_NAME_OR_RGB_VALUES):
        RgbColor("red", 1)  # type: ignore
    with pytest.raises(ValueError, match=MSG_NEED_COLOR_NAME_OR_RGB_VALUES):
        RgbColor(1, 1)  # type: ignore
    with pytest.raises(ValueError, match=MSG_NEED_COLOR_NAME_OR_RGB_VALUES):
        # noinspection PyArgumentList
        RgbColor(1, 0, 2, 4)  # type: ignore

    with pytest.raises(
        ValueError,
        match="mixed use of positional and keyword arguments for color arguments",
    ):
        # noinspection PyArgumentList
        RgbColor("red", c=1)  # type: ignore

    with pytest.raises(ValueError, match="mixed use of named color and color channels"):
        # noinspection PyArgumentList
        RgbColor(r=1, g=1, b=1, c=0)  # type: ignore

    with pytest.raises(ValueError, match=MSG_MUST_BE_A_STRING):
        # noinspection PyTypeChecker
        RgbColor(1)  # type: ignore

    with pytest.raises(ValueError, match=MSG_INVALID_RGBA_VALUES):
        RgbColor(1, 0, 2)  # type: ignore

    with pytest.raises(
        ValueError,
        match=MSG_INCOMPLETE_RGB_KWARG,
    ):
        # noinspection PyArgumentList
        RgbColor(r=1, g=0)  # type: ignore

    with pytest.raises(
        ValueError,
        match=MSG_INCOMPLETE_RGB_KWARG,
    ):
        # noinspection PyArgumentList
        RgbColor(r=1, c=0)  # type: ignore


def test_rgba() -> None:
    red = (1.0, 0.0, 0.0, 1.0)

    assert RgbaColor("red") == red
    assert RgbaColor(c="red") == red
    assert RgbaColor(1, 0, 0) == red
    assert RgbaColor(r=1, g=0, b=0) == red

    red_alpha = (1.0, 0.0, 0.0, 0.5)

    assert RgbaColor("red", 0.5) == red_alpha
    assert RgbaColor("red", alpha=0.5) == red_alpha
    assert RgbaColor(c="red", alpha=0.5) == red_alpha
    assert RgbaColor(1, 0, 0, 0.5) == red_alpha
    assert RgbaColor(1, 0, 0, alpha=0.5) == red_alpha
    assert RgbaColor(r=1, g=0, b=0, alpha=0.5) == red_alpha

    with pytest.raises(ValueError, match="need 3 RGB values or 4 RGBA values"):
        # noinspection PyArgumentList
        RgbaColor(1, 1, 1, 1, 1)  # type: ignore

    with pytest.raises(
        ValueError,
        match=r"all color arguments must be numeric, but are: \('red', 1, 1, 1, 1\)",
    ):
        # noinspection PyArgumentList
        RgbaColor("red", 1, 1, 1, 1)  # type: ignore

    with pytest.raises(
        ValueError,
        match="mixed use of positional and keyword arguments for color arguments",
    ):
        # noinspection PyArgumentList
        RgbaColor("red", c=1, alpha=0)  # type: ignore

    with pytest.raises(ValueError, match="mixed use of named color and color channels"):
        # noinspection PyArgumentList
        RgbaColor(r=1, g=1, b=1, c=0, alpha=0)  # type: ignore

    with pytest.raises(ValueError, match=MSG_MUST_BE_A_STRING):
        # noinspection PyTypeChecker
        RgbaColor(1)  # type: ignore
    with pytest.raises(ValueError, match=MSG_MUST_BE_A_STRING):
        # noinspection PyTypeChecker
        RgbaColor(1, 1)  # type: ignore
    with pytest.raises(ValueError, match=MSG_MUST_BE_A_STRING):
        # noinspection PyTypeChecker
        RgbaColor(1, alpha=0)  # type: ignore

    with pytest.raises(ValueError, match=MSG_INVALID_RGBA_VALUES):
        RgbaColor(1, 0, 2)
    with pytest.raises(ValueError, match=MSG_INVALID_RGBA_VALUES):
        RgbaColor(1, 0, 1, alpha=2)

    with pytest.raises(
        ValueError,
        match="incomplete RGB keyword arguments: need to provide r, g, and b",
    ):
        # noinspection PyArgumentList
        RgbaColor(r=1, g=0, alpha=1)  # type: ignore

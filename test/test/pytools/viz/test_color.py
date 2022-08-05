import pytest

from pytools.viz.color import RgbaColor, RgbColor


def test_rgb() -> None:
    red = (1.0, 0.0, 0.0)

    assert RgbColor("red") == red
    assert RgbColor(c="red") == red
    assert RgbColor(1, 0, 0) == red
    assert RgbColor(r=1, g=0, b=0) == red

    with pytest.raises(
        ValueError,
        match="alpha channel is not supported by RgbColor, use RgbaColor instead",
    ):
        RgbColor("red", 1)  # type: ignore
    with pytest.raises(
        ValueError, match=r"need 3 RGB values or 4 RGBA values but got: \(1, 1\)"
    ):
        RgbColor(1, 1)  # type: ignore
    with pytest.raises(
        ValueError, match="RgbColor expects at most 3 arguments but got: 1, 0, 2, 4"
    ):
        # noinspection PyArgumentList
        RgbColor(1, 0, 2, 4)  # type: ignore

    with pytest.raises(
        ValueError,
        match="mixed use of positional and keyword arguments for color arguments",
    ):
        # noinspection PyArgumentList
        RgbColor("red", c=1)  # type: ignore

    with pytest.raises(
        ValueError,
        match="RgbColor expects at most 3 arguments but got: r=1, g=1, b=1, c=0",
    ):
        # noinspection PyArgumentList
        RgbColor(r=1, g=1, b=1, c=0)  # type: ignore

    with pytest.raises(
        ValueError, match=r"need 3 RGB values or 4 RGBA values but got: \(1,\)"
    ):
        # noinspection PyTypeChecker
        RgbColor(1)  # type: ignore

    with pytest.raises(ValueError, match="invalid RGB values"):
        RgbColor(1, 0, 2)

    with pytest.raises(
        ValueError,
        match="incomplete RGB keyword arguments: need to provide r, g, and b",
    ):
        # noinspection PyArgumentList
        RgbColor(r=1, g=0)  # type: ignore

    with pytest.raises(
        ValueError,
        match="incomplete RGB keyword arguments: need to provide r, g, and b",
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

    with pytest.raises(
        ValueError, match="RgbaColor expects at most 4 arguments but got: 1, 1, 1, 1, 1"
    ):
        # noinspection PyArgumentList
        RgbaColor(1, 1, 1, 1, 1)  # type: ignore

    with pytest.raises(
        ValueError,
        match="RgbaColor expects at most 4 arguments but got: 1, 1, 1, 1, alpha=1",
    ):
        # noinspection PyArgumentList
        RgbaColor(1, 1, 1, 1, alpha=1)  # type: ignore

    with pytest.raises(
        ValueError,
        match=(
            "RgbaColor expects at most 4 arguments but got: r=1, b=1, g=1, c=1, alpha=1"
        ),
    ):
        # noinspection PyArgumentList
        RgbaColor(r=1, b=1, g=1, c=1, alpha=1)  # type: ignore

    with pytest.raises(
        ValueError,
        match=r"all color arguments must be numeric, but are: \('red', 1, 1\)",
    ):
        # noinspection PyArgumentList
        RgbaColor("red", 1, 1)  # type: ignore

    with pytest.raises(
        ValueError,
        match="mixed use of positional and keyword arguments for color arguments",
    ):
        # noinspection PyArgumentList
        RgbaColor("red", c=1, alpha=0)  # type: ignore

    with pytest.raises(ValueError, match="mixed use of named color and color channels"):
        # noinspection PyArgumentList
        RgbaColor(r=1, g=1, b=1, c=0)  # type: ignore

    with pytest.raises(
        ValueError, match=r"need 3 RGB values or 4 RGBA values but got: \(1,\)"
    ):
        # noinspection PyTypeChecker
        RgbaColor(1)  # type: ignore
    with pytest.raises(
        ValueError, match=r"need 3 RGB values or 4 RGBA values but got: \(1, 1\)"
    ):
        # noinspection PyTypeChecker
        RgbaColor(1, 1)  # type: ignore
    with pytest.raises(
        ValueError, match=r"need 3 RGB values or 4 RGBA values but got: \(1,\)"
    ):
        # noinspection PyTypeChecker
        RgbaColor(1, alpha=0)  # type: ignore

    with pytest.raises(ValueError, match=r"invalid RGB values: \(1, 0, 2\)"):
        RgbaColor(1, 0, 2)
    with pytest.raises(ValueError, match="invalid alpha value: 2"):
        RgbaColor(1, 0, 1, alpha=2)

    with pytest.raises(
        ValueError,
        match="incomplete RGB keyword arguments: need to provide r, g, and b",
    ):
        # noinspection PyArgumentList
        RgbaColor(r=1, g=0, alpha=1)  # type: ignore

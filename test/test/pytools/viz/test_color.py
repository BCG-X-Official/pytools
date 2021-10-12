import pytest

from pytools.viz.color import RgbaColor, RgbColor


def test_rgb() -> None:
    red = (1.0, 0.0, 0.0)

    assert RgbColor("red") == red
    assert RgbColor(c="red") == red
    assert RgbColor(1, 0, 0) == red
    assert RgbColor(r=1, g=0, b=0) == red

    with pytest.raises(ValueError, match="need 1 color name or 3 RGB values"):
        RgbColor("red", 1)
    with pytest.raises(ValueError, match="need 1 color name or 3 RGB values"):
        RgbColor(1, 1)
    with pytest.raises(ValueError, match="need 1 color name or 3 RGB values"):
        # noinspection PyArgumentList
        RgbColor(1, 0, 2, 4)

    with pytest.raises(
        ValueError,
        match="mixed use of positional and keyword arguments for color arguments",
    ):
        # noinspection PyArgumentList
        RgbColor("red", c=1)

    with pytest.raises(ValueError, match="mixed use of named color and color channels"):
        # noinspection PyArgumentList
        RgbColor(r=1, c=0)

    with pytest.raises(ValueError, match="single color argument must be a string"):
        # noinspection PyTypeChecker
        RgbColor(1)

    with pytest.raises(ValueError, match="invalid RGBA values"):
        RgbColor(1, 0, 2)

    with pytest.raises(ValueError, match="invalid RGBA values"):
        # noinspection PyArgumentList
        RgbColor(r=1, g=0)


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
        RgbaColor("red", 1, 1, 1, 1)

    with pytest.raises(
        ValueError,
        match="mixed use of positional and keyword arguments for color arguments",
    ):
        # noinspection PyArgumentList
        RgbaColor("red", c=1, alpha=0)

    with pytest.raises(ValueError, match="mixed use of named color and color channels"):
        # noinspection PyArgumentList
        RgbaColor(r=1, c=0, alpha=0)

    with pytest.raises(ValueError, match="single color argument must be a string"):
        # noinspection PyTypeChecker
        RgbaColor(1)
    with pytest.raises(ValueError, match="single color argument must be a string"):
        # noinspection PyTypeChecker
        RgbaColor(1, 1)
    with pytest.raises(ValueError, match="single color argument must be a string"):
        # noinspection PyTypeChecker
        RgbaColor(1, alpha=0)

    with pytest.raises(ValueError, match="invalid RGBA values"):
        RgbaColor(1, 0, 2)
    with pytest.raises(ValueError, match="invalid RGBA values"):
        RgbaColor(1, 0, 1, alpha=2)

    with pytest.raises(ValueError, match="invalid RGBA values"):
        # noinspection PyArgumentList
        RgbColor(r=1, g=0)

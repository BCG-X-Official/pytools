"""
Basic test cases for the `pytools.data` module
"""


import numpy as np
import pandas as pd
import pytest

from pytools.data import Matrix


def test_matrix_validation() -> None:
    with pytest.raises(ValueError, match="got a 3d array"):
        Matrix(np.arange(20).reshape((4, 5, 1)))

    with pytest.raises(TypeError, match="got a str"):
        # noinspection PyTypeChecker
        Matrix(np.arange(20).reshape((4, 5)), names="invalid")

    with pytest.raises(ValueError, match="got a 3-tuple"):
        # noinspection PyTypeChecker
        Matrix(np.arange(20).reshape((4, 5)), names=("invalid", "invalid", "invalid"))

    with pytest.raises(
        ValueError,
        match=r"arg names\[0\] must be a 1d array, but has shape \(\)",
    ):
        Matrix(np.arange(20).reshape((4, 5)), names=("invalid", "invalid"))

    with pytest.raises(ValueError, match="got a 3-tuple"):
        # noinspection PyTypeChecker
        Matrix(np.arange(20).reshape((4, 5)), weights=(1, 2, 3))

    with pytest.raises(
        ValueError, match=r"arg weights\[0\] must be a 1d array, but has shape \(\)"
    ):
        # noinspection PyTypeChecker
        Matrix(np.arange(20).reshape((4, 5)), weights=(1, [2, 4]))

    with pytest.raises(
        ValueError,
        match=(
            r"arg weights\[1\] must have same length as arg values.shape\[1\]=5, "
            r"but has length 2"
        ),
    ):
        Matrix(np.arange(20).reshape((4, 5)), weights=(None, [2, 4]))

    with pytest.raises(
        ValueError,
        match=(
            r"arg weights\[1\] should be all positive, but contains negative weights"
        ),
    ):
        Matrix(np.arange(20).reshape((4, 5)), weights=(None, [2, 4, -3, 2, 1]))

    with pytest.raises(
        ValueError,
        match="got a 3-tuple",
    ):
        # noinspection PyTypeChecker
        Matrix(np.arange(20).reshape((4, 5)), name_labels=(1, 2, 3))


def test_matrix_from_frame() -> None:
    values = np.arange(20).reshape((4, 5))
    rows = list("ABCD")
    columns = list("abcde")

    matrix_from_frame = Matrix.from_frame(
        pd.DataFrame(values, index=rows, columns=columns)
    )
    matrix_expected = Matrix(values, names=(rows, columns))
    assert matrix_from_frame == matrix_expected


def test_matrix_resize() -> None:

    m: Matrix = Matrix(
        np.arange(20).reshape((4, 5)),
        names=(list("ABCD"), list("abcde")),
        weights=([2, 4, 2, 4], [1, 5, 4, 1, 5]),
        name_labels=("row", "column"),
        value_label="weight",
    )

    assert m.resize(1, None) == Matrix(
        np.array([[5, 6, 7, 8, 9]]),
        names=(["B"], list("abcde")),
        weights=([4], [1, 5, 4, 1, 5]),
        name_labels=("row", "column"),
        value_label="weight",
    )

    assert m.resize(None, 1) == Matrix(
        np.array([[1], [6], [11], [16]]),
        names=(list("ABCD"), ["b"]),
        weights=([2, 4, 2, 4], [5]),
        name_labels=("row", "column"),
        value_label="weight",
    )

    assert m.resize(1, 1) == Matrix(
        np.array([[6]]),
        names=(["B"], ["b"]),
        weights=([4], [5]),
        name_labels=("row", "column"),
        value_label="weight",
    )

    assert m.resize(3, 4) == Matrix(
        np.array([[0, 1, 2, 4], [5, 6, 7, 9], [15, 16, 17, 19]]),
        names=(list("ABD"), list("abce")),
        weights=([2, 4, 4], [1, 5, 4, 5]),
        name_labels=("row", "column"),
        value_label="weight",
    )

    assert m.resize(0.8, 0.0001) == Matrix(
        values=np.array([[1], [6], [16]]),
        names=(list("ABD"), ["b"]),
        weights=([2, 4, 4], [5]),
        name_labels=("row", "column"),
        value_label="weight",
    )

    assert m.resize(4, 5) == m

    assert m.resize(3, 3) != m

    with pytest.raises(
        ValueError,
        match="arg rows=5 must not be greater than the current number of rows",
    ):
        m.resize(5, 5)

    with pytest.raises(
        ValueError,
        match="arg columns=6 must not be greater than the current number of rows",
    ):
        m.resize(4, 6)

    with pytest.raises(ValueError, match="arg rows=-4 must not be negative"):
        m.resize(-4, 5)

    with pytest.raises(
        ValueError, match="arg columns=1.5 must not be greater than 1.0"
    ):
        m.resize(None, 1.5)

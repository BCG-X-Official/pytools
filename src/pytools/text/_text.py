"""
Utilities for rendering text.
"""
import logging
from typing import Any, Iterable, List, Optional, Sequence, Tuple, Union

import numpy as np
import pandas as pd

from pytools.api import AllTracker

log = logging.getLogger(__name__)


#
# Exported names
#

__all__ = ["CharacterMatrix", "format_table"]


#
# Ensure all symbols introduced below are included in __all__
#

__tracker = AllTracker(globals())


#
# Type definitions
#

_TextCoordinates = Tuple[Union[int, slice], Union[int, slice]]


#
# Classes
#


class CharacterMatrix:
    """
    A matrix of characters, indexed by rows and columns.

    The matrix is initialised with space characters (`" "`).

    Characters can be "painted" in the matrix using 2D index expressions:

    - ``matrix[r, c] = chr`` assigns character `chr` at position `(r, c)`
    - ``matrix[r, c1:c2] = str`` writes string `str` at positions
      `(r, c1) … (r, c2 – 1)`; excess characters in `str` are clipped if ``len(s)`` is
      greater than `c2 – c1`
    - ``matrix[r, c1:c2] = chr`` (where `chr` is a single character) repeats `chr` at
      every position `(r, c1) … (r, c2 – 1)`
    - ``matrix[r1:r2, …] = …`` applies the same insertion at each of rows `r1 … r2 – 1`
    - full slice notation is supported so even slices of shape ``start:stop:step`` work
      as expected

    :param n_rows: the matrix height
    :param n_columns: the matrix width
    """

    def __init__(self, n_rows: int, n_columns: int):
        if n_columns <= 0:
            raise ValueError(f"arg width must be positive but is {n_columns}")
        if n_rows <= 0:
            raise ValueError(f"arg height must be positive but is {n_rows}")
        self._n_columns = n_columns
        self._matrix = [[" " for _ in range(n_columns)] for _ in range(n_rows)]

    @property
    def n_rows(self) -> int:
        """
        The height of this matrix.

        Same as ``len(self)``.
        """
        return len(self._matrix)

    @property
    def n_columns(self) -> int:
        """
        The width of this matrix.
        """
        return self._n_columns

    def lines(self) -> Iterable[str]:
        """
        Get this character matrix as strings representing the matrix rows.

        :return: the rows in this matrix as strings
        """
        return ("".join(line) for line in self._matrix)

    @staticmethod
    def __key_as_slices(key: _TextCoordinates) -> Tuple[slice, slice]:
        def _to_slice(index: Union[int, slice]) -> slice:
            if isinstance(index, int):
                return slice(index, index + 1)
            else:
                return index

        if not isinstance(key, tuple) or len(key) != 2:
            raise ValueError(f"expected (row, column) tuple but got {key}")

        row, column = key
        return _to_slice(row), _to_slice(column)

    def __str__(self) -> str:
        return "\n".join(self.lines())

    def __len__(self) -> int:
        return self.n_rows

    def __getitem__(self, key: _TextCoordinates):
        rows, columns = self.__key_as_slices(key)
        return "\n".join("".join(line[columns]) for line in self._matrix[rows])

    def __setitem__(self, key: _TextCoordinates, value: Any) -> None:
        rows, columns = self.__key_as_slices(key)
        value = str(value)
        single_char = len(value) == 1
        positions = range(*columns.indices(self.n_columns))
        for line in self._matrix[rows]:
            if single_char:
                for pos in positions:
                    line[pos] = value
            else:
                for pos, char in zip(positions, value):
                    line[pos] = char


_ALIGNMENT_OPTIONS = ["<", "^", ">"]


def format_table(
    headings: Sequence[str],
    data: Union[pd.DataFrame, np.ndarray, Sequence[Sequence[Any]]],
    formats: Optional[Sequence[Optional[str]]] = None,
    alignment: Optional[Sequence[Optional[str]]] = None,
) -> str:
    """
    Print a formatted text table.

    :param headings: the table headings
    :param data: the table data, as an array-like with shape `[n_rows, n_columns]`
    :param formats: formatting strings for data in each row (optional);
        uses ``str()`` conversion for any formatting strings stated as ``None``
    :param alignment: text alignment for each column (optional); use ``"<"`` to align
        left, ``"="`` to center, ``">"`` to align right (defaults to left alignment)
    :return: the formatted table as a multi-line string
    """
    n_columns = len(headings)

    if formats is None:
        formats = [None] * n_columns
    elif len(formats) != n_columns:
        raise ValueError("arg formats must have the same length as arg headings")

    if alignment is None:
        alignment = ["<"] * n_columns
    elif len(alignment) != n_columns:
        raise ValueError("arg alignment must have the same length as arg headings")
    elif not all(align in _ALIGNMENT_OPTIONS for align in alignment):
        raise ValueError(
            f"arg alignment must only contain alignment options "
            f'{", ".join(_ALIGNMENT_OPTIONS)}'
        )

    def _formatted(item: Any, format_string: str) -> str:
        if format_string is None:
            return str(item)
        else:
            return f"{item:{format_string}}"

    def _iterate_row_data() -> Iterable[Sequence]:
        if isinstance(data, pd.DataFrame):
            return (row for _, row in data.iterrows())
        else:
            return iter(data)

    def _make_row(items: Sequence):
        if len(items) != n_columns:
            raise ValueError(
                "rows in data matrix must have the same length as arg headings"
            )
        return [
            _formatted(item, format_string)
            for item, format_string in zip(items, formats)
        ]

    body_rows = [_make_row(items) for items in _iterate_row_data()]

    column_widths = [
        max(column_lengths)
        for column_lengths in zip(
            *(
                (len(item) for item in row)
                for row in (
                    headings,
                    *[_make_row(items) for items in _iterate_row_data()],
                )
            )
        )
    ]

    dividers = ["=" * column_width for column_width in column_widths]

    def _format_rows(rows: List[List[str]], align: bool):
        return (
            "  ".join(
                (
                    f'{item:{align_char if align else ""}{column_width}s}'
                    for item, align_char, column_width in zip(
                        row, alignment, column_widths
                    )
                )
            )
            for row in rows
        )

    return "\n".join(
        (
            *(_format_rows(rows=[headings, dividers], align=False)),
            *(_format_rows(rows=body_rows, align=True)),
            "",
        )
    )


__tracker.validate()

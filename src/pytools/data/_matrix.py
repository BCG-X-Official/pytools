"""
Data type for matrices.
"""

import logging
from typing import Any, Iterable, List, Optional, Tuple, Union

import numpy as np
import pandas as pd

from pytools.api import AllTracker, inheritdoc, validate_element_types, validate_type
from pytools.expression import Expression, HasExpressionRepr
from pytools.expression.atomic import Id

log = logging.getLogger(__name__)


#
# Type aliases
#


Number = Union[int, float, np.number]


#
# exported names
#

__all__ = ["Matrix"]


#
# Ensure all symbols introduced below are included in __all__
#

__tracker = AllTracker(globals())


#
# Classes
#


@inheritdoc(match="[see superclass]")
class Matrix(HasExpressionRepr):
    """
    A 2d matrix with optional names and weights for rows and columns.
    """

    #: the values of the matrix cells, as a `rows x columns` array
    values: np.ndarray

    #: the names of the rows and columns
    names: Tuple[Optional[np.ndarray], Optional[np.ndarray]]

    #: the weights of the rows and columns
    weights: Tuple[Optional[np.ndarray], Optional[np.ndarray]]

    #: the labels for the row and column axes
    name_labels: Tuple[Optional[str], Optional[str]]

    #: the label for the value axis
    value_label: Optional[str]

    def __init__(
        self,
        values: np.ndarray,
        *,
        names: Optional[Tuple[Optional[Iterable[Any]], Optional[Iterable[Any]]]] = None,
        weights: Optional[
            Tuple[Optional[Iterable[Number]], Optional[Iterable[Number]]]
        ] = None,
        name_labels: Optional[Tuple[Optional[str], Optional[str]]] = None,
        value_label: Optional[str] = None,
    ) -> None:
        """
        :param values: the values of the matrix cells, as a `rows x columns` array
        :param names: the names of the rows and columns
        :param weights: the weights of the rows and columns
        :param name_labels: the labels for the row and column axes
        :param value_label: the label for the value axis
        """
        if not isinstance(values, np.ndarray):
            raise TypeError(
                "arg values expected to be a numpy array, "
                f"but got a {type(values).__name__}"
            )
        if values.ndim != 2:
            raise ValueError(
                "arg values expected to be a 2d numpy array, "
                f"but got a {values.ndim}d array"
            )
        self.values = values

        args: List[Tuple[Any, str]] = [
            (names, "names"),
            (weights, "weights"),
            (name_labels, "name_labels"),
        ]

        for arg, arg_name in args:
            if arg is None:
                continue
            if not isinstance(arg, tuple):
                raise TypeError(
                    f"arg {arg_name} expected to be tuple, but got a "
                    f"{type(arg).__name__}"
                )
            if len(arg) != 2:
                raise ValueError(
                    f"optional arg {arg_name} expected to be 2-tuple, "
                    f"but got a {len(arg)}-tuple"
                )

        def _arg_to_array(
            axis: int, axis_arg: Optional[Iterable[Number]], arg_name_: str
        ) -> Optional[np.ndarray]:
            if axis_arg is None:
                return None
            else:
                arr = np.array(axis_arg)
                if arr.ndim != 1:
                    raise ValueError(
                        f"arg {arg_name_}[{axis}] must be a 1d array, but has "
                        f"shape {arr.shape}"
                    )
                if arr.shape != (values.shape[axis],):
                    raise ValueError(
                        f"arg {arg_name_}[{axis}] must have same length as arg "
                        f"values.shape[{axis}]={values.shape[axis]}, "
                        f"but has length {len(arr)}"
                    )
                return arr

        if names is None:
            self.names = (None, None)
        else:
            self.names = (
                _arg_to_array(0, names[0], "names"),
                _arg_to_array(1, names[1], "names"),
            )

        if weights is None:
            self.weights = (None, None)
        else:

            def _ensure_positive(
                w: Optional[np.ndarray], axis: int
            ) -> Optional[np.ndarray]:
                if w is not None and (w < 0).any():
                    raise ValueError(
                        f"arg weights[{axis}] should be all positive, "
                        "but contains negative weights"
                    )
                else:
                    return w

            self.weights = (
                _ensure_positive(_arg_to_array(0, weights[0], "weights"), axis=0),
                _ensure_positive(_arg_to_array(1, weights[1], "weights"), axis=1),
            )

        self.name_labels = (
            validate_element_types(
                name_labels, expected_type=str, optional=True, name="arg name_labels"
            )
            if name_labels
            else (None, None)
        )

        self.value_label = validate_type(
            value_label, expected_type=str, optional=True, name="arg weight_label"
        )

    @classmethod
    def from_frame(
        cls,
        frame: pd.DataFrame,
        *,
        weights: Optional[Tuple[Optional[Number], Optional[Number]]] = None,
        name_labels: Optional[Tuple[Optional[str], Optional[str]]] = None,
        weight_label: Optional[str] = None,
    ):
        """
        Create a :class:`.Matrix` from a data frame, using the indices
        as the row and column names.

        :param frame: the data frame from which to create the matrix
        :param weights: the weights of the rows and columns
        :param name_labels: the labels for the row and column axes
        :param weight_label: the label for the weight axis
        :return:
        """
        return cls(
            frame.values,
            names=(frame.index, frame.columns),
            weights=weights,
            name_labels=name_labels,
            weight_label=weight_label,
        )

    def resize(
        self, rows: Union[int, float, None], columns: Union[int, float, None]
    ) -> "Matrix":
        r"""
        Create a version of this matrix with fewer rows and/or columns, keeping the
        rows and columns with the greatest weight, and prioritizing topmost rows and
        leftmost columns in case multiple rows and columns have the same weight and
        cannot all be included in the resulting, smaller matrix.

        A target size can be stated separately for rows and columns:

        - as a positive integer, indicating absolute target size (row or column count),
          not exceeding the original size
        - as a float, indicating target size as a ratio of the current size
          where :math:`0 < \mathit{ratio} \le 1`
        - as ``None``, preserving the original size

        :param rows: the rows target size
        :param columns: the columns target size
        :return: a resized version of this matrix
        """

        if rows is None and columns is None:
            return self

        n_rows_current, n_columns_current = self.values.shape
        weights_rows, weights_columns = self.weights
        names_rows, names_columns = self.names

        values = self.values

        if rows:
            values, weights_rows, names_rows = _resize_rows(
                values=values,
                weights=weights_rows,
                names=names_rows,
                current_size=n_rows_current,
                target_size=_validate_resize_arg(rows, n_rows_current, "rows"),
            )

        if columns:
            values_t, weights_columns, names_columns = _resize_rows(
                values=values.T,
                weights=weights_columns,
                names=names_columns,
                current_size=n_columns_current,
                target_size=_validate_resize_arg(columns, n_columns_current, "columns"),
            )
            values = values_t.T

        return Matrix(
            values,
            names=(names_rows, names_columns),
            weights=(weights_rows, weights_columns),
            name_labels=self.name_labels,
            value_label=self.value_label,
        )

    def to_expression(self) -> Expression:
        """[see superclass]"""
        return Id(type(self))(
            values=Id("…"),
            names=self.names,
            weights=self.weights,
            name_labels=self.name_labels,
            weight_label=self.value_label,
        )

    def __eq__(self, other: "Matrix") -> bool:
        return (
            isinstance(other, Matrix)
            and np.array_equal(self.values, other.values)
            and map(np.array_equal, zip(self.weights, other.weights))
            and map(np.array_equal, zip(self.names, other.names))
            and self.name_labels == other.name_labels
            and self.value_label == other.value_label
        )


def _validate_resize_arg(
    size_new: Union[int, float, None], size_current: int, arg_name: str
) -> Tuple[Optional[int], Optional[float]]:
    if size_new is None:
        return (None, None)

    if isinstance(size_new, int):
        if size_new > size_current:
            raise ValueError(
                f"arg {arg_name}={size_new} "
                "must not be greater than the current number of rows"
            )
        result = (size_new, None)

    elif isinstance(size_new, float):
        if size_new > 1.0:
            raise ValueError(f"arg {arg_name}={size_new} must not be greater than 1.0")
        result = (None, size_new)

    else:
        raise TypeError(f"arg {arg_name}={size_new!r} must be a number")

    if size_new <= 0:
        raise ValueError(f"arg {arg_name}={size_new} must not be negative")

    return result


def _top_items_mask(
    weights: Optional[np.ndarray],
    current_size: int,
    target_size: Tuple[Optional[int], Optional[float]],
) -> np.ndarray:
    target_n, target_ratio = target_size

    if target_n:
        if current_size == target_n:
            return np.ones(current_size, dtype=bool)
        elif weights is None:
            mask = np.ones(current_size, dtype=bool)
            mask[target_n:] = False
            return mask

    elif not target_ratio:
        assert target_ratio, "one of target size or target ratio is defined"

    mask = np.zeros(current_size, dtype=bool)
    ix_weights_descending_stable = (current_size - 1) - weights[::-1].argsort(
        kind="stable"
    )[::-1]
    if target_n:
        # pick the top n items with the highest weight
        mask[ix_weights_descending_stable[:target_n]] = True

    else:
        # in descending order of item weight, pick the minimum set of items whose
        # total weight is equal to or greater than the target weight
        #
        # target weight is expressed as a ratio of total weight (0 < target_ratio <= 1)

        weights_sorted_cumsum: np.ndarray = weights[
            ix_weights_descending_stable
        ].cumsum()
        mask[
            : weights_sorted_cumsum.searchsorted(
                weights_sorted_cumsum[-1] * target_ratio
            )
            + 1
        ] = True
        mask[ix_weights_descending_stable] = mask.copy()

    return mask


def _resize_rows(
    values: np.ndarray,
    weights: Optional[np.ndarray],
    names: Optional[np.ndarray],
    current_size: int,
    target_size: Tuple[Optional[int], Optional[float]],
) -> Tuple[np.ndarray, Optional[np.ndarray], Optional[Tuple[str, ...]]]:
    mask = _top_items_mask(
        weights=weights, current_size=current_size, target_size=target_size
    )

    return (
        values[mask],
        None if weights is None else weights[mask],
        None if names is None else names[mask],
    )


__tracker.validate()

"""
Data type for matrices.
"""

import logging
from typing import Any, Iterable, List, Optional, Tuple, Union

import numpy as np
import pandas as pd

from pytools.api import (
    AllTracker,
    inheritdoc,
    to_tuple,
    validate_element_types,
    validate_type,
)
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
    data: np.ndarray

    #: the names of the rows and columns
    names: Tuple[Optional[Tuple[str, ...]], Optional[Tuple[str, ...]]]

    #: the weights of the rows and columns
    weights: Tuple[Optional[np.ndarray], Optional[np.ndarray]]

    #: the labels for the row and column axes
    name_labels: Tuple[Optional[str], Optional[str]]

    #: the label for the weight axis
    weight_label: Optional[str]

    def __init__(
        self,
        data: np.ndarray,
        *,
        names: Optional[Tuple[Optional[Iterable[str]], Optional[Iterable[str]]]] = None,
        weights: Optional[
            Tuple[Optional[Iterable[Number]], Optional[Iterable[Number]]]
        ] = None,
        name_labels: Optional[Tuple[Optional[str], Optional[str]]] = None,
        weight_label: Optional[str] = None,
    ) -> None:
        """
        :param data: the values of the matrix cells, as a `rows x columns` array
        :param names: the names of the rows and columns
        :param weights: the weights of the rows and columns
        :param name_labels: the labels for the row and column axes
        :param weight_label: the label for the weight axis
        """
        if not isinstance(data, np.ndarray):
            raise TypeError(
                "arg data expected to be a numpy array, "
                f"but got a {type(data).__name__}"
            )
        if data.ndim != 2:
            raise ValueError(
                "arg data expected to be a 2d numpy array, "
                f"but got a {data.ndim}d array"
            )
        self.data = data

        args: List[Optional[Tuple[Optional[Tuple[Any, Any]]], str, type]] = [
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

        if names is None:
            self.names = (None, None)
        else:

            def _names_to_tuple(axis: int) -> Optional[Tuple[str, ...]]:
                axis_names = names[axis]
                if axis_names is None:
                    return None
                else:
                    axis_names = to_tuple(
                        axis_names, element_type=str, arg_name=f"names[{axis}]"
                    )
                    if len(axis_names) != data.shape[axis]:
                        raise ValueError(
                            f"arg names[{axis}] must have same length as arg "
                            f"data.shape[{axis}]={data.shape[axis]}, "
                            f"but has length {len(axis_names)}"
                        )
                    return axis_names

            self.names = (_names_to_tuple(axis=0), _names_to_tuple(axis=1))

        def _weights_to_array(
            axis: int, axis_weights: Optional[Iterable[Number]]
        ) -> Optional[np.ndarray]:
            if axis_weights is None:
                return None
            else:
                weights_arr = np.array(axis_weights)
                if weights_arr.ndim != 1:
                    raise ValueError(
                        f"arg weights[{axis}] must be a 1d array, but has "
                        f"shape {weights_arr.shape}"
                    )
                if weights_arr.shape != (data.shape[axis],):
                    raise ValueError(
                        f"arg weights[{axis}] must have same length as arg "
                        f"data.shape[{axis}]={data.shape[axis]}, "
                        f"but has length {len(weights_arr)}"
                    )
                return weights_arr

        if weights is None:
            self.weights = (None, None)
        else:
            self.weights = (
                _weights_to_array(0, weights[0]),
                _weights_to_array(1, weights[1]),
            )

        self.name_labels = (
            validate_element_types(
                name_labels, expected_type=str, optional=True, name="arg name_labels"
            )
            if name_labels
            else (None, None)
        )

        self.weight_label = validate_type(
            weight_label, expected_type=str, optional=True, name="arg weight_label"
        )

    @classmethod
    def from_frame(
        cls,
        data: pd.DataFrame,
        *,
        weights: Optional[Tuple[Optional[Number], Optional[Number]]] = None,
        name_labels: Optional[Tuple[Optional[str], Optional[str]]] = None,
        weight_label: Optional[str] = None,
    ):
        """
        Create a :class:`.Matrix` from a data frame, using the indices
        as the row and column names.

        :param data: the data frame from which to create the matrix
        :param weights: the weights of the rows and columns
        :param name_labels: the labels for the row and column axes
        :param weight_label: the label for the weight axis
        :return:
        """
        return cls(
            data.values,
            names=(data.index, data.columns),
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

        - as a positive intger, indicating absolute target size (row or column count),
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

        n_rows_current, n_columns_current = self.data.shape
        weights_rows, weights_columns = self.weights
        names_rows, names_columns = self.names

        data = self.data

        if rows:
            data, weights_rows, names_rows = _resize_rows(
                data=data,
                weights=weights_rows,
                names=names_rows,
                current_size=n_rows_current,
                target_size=_validate_resize_arg(rows, n_rows_current, "rows"),
            )

        if columns:
            data_t, weights_columns, names_columns = _resize_rows(
                data=data.T,
                weights=weights_columns,
                names=names_columns,
                current_size=n_columns_current,
                target_size=_validate_resize_arg(columns, n_columns_current, "columns"),
            )
            data = data_t.T

        return Matrix(
            data,
            names=(names_rows, names_columns),
            weights=(weights_rows, weights_columns),
            name_labels=self.name_labels,
            weight_label=self.weight_label,
        )

    def to_expression(self) -> Expression:
        """[see superclass]"""
        return self.get_class_id()(
            data=Id("…"),
            names=self.names,
            weights=self.weights,
            name_labels=self.name_labels,
            weight_label=self.weight_label,
        )

    def __eq__(self, other: "Matrix") -> bool:
        return (
            isinstance(other, Matrix)
            and np.array_equal(self.data, other.data)
            and map(np.array_equal, zip(self.weights, other.weights))
            and self.names == other.names
            and self.name_labels == other.name_labels
            and self.weight_label == other.weight_label
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
    data: np.ndarray,
    weights: Optional[np.ndarray],
    names: Optional[Tuple[str, ...]],
    current_size: int,
    target_size: Tuple[Optional[int], Optional[float]],
) -> Tuple[np.ndarray, Optional[np.ndarray], Optional[Tuple[str, ...]]]:
    mask = _top_items_mask(
        weights=weights, current_size=current_size, target_size=target_size
    )

    return (
        data[mask],
        weights[mask],
        (
            tuple(name for name, is_included in zip(names, mask) if is_included)
            if names
            else None
        ),
    )


__tracker.validate()

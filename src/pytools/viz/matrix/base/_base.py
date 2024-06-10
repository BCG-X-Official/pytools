"""
Base classes for matrix styles.
"""

import logging
from abc import ABCMeta, abstractmethod
from typing import Any

import numpy as np
import numpy.typing as npt

from pytools.api import AllTracker
from pytools.viz import DrawingStyle

log = logging.getLogger(__name__)

#
# Exported names
#

__all__ = ["MatrixStyle"]


#
# Ensure all symbols introduced below are included in __all__
#

__tracker = AllTracker(globals())


#
# Classes
#


class MatrixStyle(DrawingStyle, metaclass=ABCMeta):
    """
    Base class for matrix drawer styles.
    """

    def start_drawing(
        self,
        *,
        title: str,
        name_labels: tuple[str | None, str | None] = (None, None),
        weight_label: str | None = None,
        **kwargs: Any,
    ) -> None:
        """
        Initialize the matrix plot.

        :param title: the title of the matrix
        :param name_labels: the labels for the row and column axes
        :param weight_label: the label for the `weight` axis
        :param kwargs: additional drawer-specific arguments
        """

        super().start_drawing(title=title, **kwargs)

    @abstractmethod
    def draw_matrix(
        self,
        data: npt.NDArray[Any],
        *,
        names: tuple[
            npt.NDArray[Any] | None,
            npt.NDArray[Any] | None,
        ],
        weights: tuple[
            npt.NDArray[np.float_] | None,
            npt.NDArray[np.float_] | None,
        ],
    ) -> None:
        """
        Draw the matrix.

        :param data: the values of the matrix cells, as a 2d array
        :param names: the names of the rows and columns
        :param weights: the weights of the rows and columns
        """
        pass

    def finalize_drawing(
        self,
        name_labels: tuple[str | None, str | None] | None = None,
        weight_label: str | None = None,
        **kwargs: Any,
    ) -> None:
        """
        Finalize the matrix plot.

        :param name_labels: the labels for the row and column axes
        :param weight_label: the label for the `weight` axis
        :param kwargs: additional drawer-specific arguments
        """

        super().finalize_drawing(**kwargs)


__tracker.validate()

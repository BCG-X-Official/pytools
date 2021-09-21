"""
Base classes for matrix styles.
"""

import logging
from abc import ABCMeta, abstractmethod
from typing import Any, Optional, Tuple

import numpy as np

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
        name_labels: Tuple[Optional[str], Optional[str]] = None,
        weight_label: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """
        Add labels to the matrix plot, if defined.

        :param title: the title of the matrix
        :param name_labels: the labels for the row and column axes
        :param weight_label: the label for the `weight` axis
        :param kwargs: additional drawer-specific arguments
        """

        # ignore the labels
        super().start_drawing(title=title, **kwargs)

    @abstractmethod
    def draw_matrix(
        self,
        data: np.ndarray,
        *,
        names: Tuple[Optional[np.ndarray], Optional[np.ndarray]],
        weights: Tuple[Optional[np.ndarray], Optional[np.ndarray]],
    ) -> None:
        """
        Draw the matrix.

        :param data: the values of the matrix cells, as a `rows x columns` array
        :param names: the names of the rows and columns
        :param weights: the weights of the rows and columns
        """
        pass

    def finalize_drawing(
        self,
        name_labels: Tuple[Optional[str], Optional[str]] = None,
        weight_label: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """
        Add labels to the matrix plot, if defined.

        :param name_labels: the labels for the row and column axes
        :param weight_label: the label for the `weight` axis
        :param kwargs: additional drawer-specific arguments
        """

        # ignore the labels
        super().finalize_drawing(**kwargs)


__tracker.validate()

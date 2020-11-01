"""
Base classes for matrix styles.
"""

import logging
from abc import ABCMeta, abstractmethod

import pandas as pd

from pytools.viz import DrawingStyle

log = logging.getLogger(__name__)


class MatrixStyle(DrawingStyle, metaclass=ABCMeta):
    """
    Base class for matrix drawer styles.
    """

    @abstractmethod
    def draw_matrix(self, matrix: pd.DataFrame) -> None:
        """
        Draw the matrix.

        :param matrix: the matrix represented as a data frame
        """
        pass

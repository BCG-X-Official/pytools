"""
Base classes for matrix styles.
"""

import logging
from abc import ABCMeta, abstractmethod

import pandas as pd

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

    @abstractmethod
    def draw_matrix(self, matrix: pd.DataFrame) -> None:
        """
        Draw the matrix.

        :param matrix: the matrix represented as a data frame
        """
        pass


__tracker.validate()

"""
Base classes for distribution styles.
"""

import logging
from abc import ABCMeta, abstractmethod
from typing import Sequence

from pytools.api import AllTracker
from pytools.viz import DrawingStyle

log = logging.getLogger(__name__)

#
# Exported names
#

__all__ = ["XYSeries", "ECDF", "ECDFStyle"]


#
# Ensure all symbols introduced below are included in __all__
#

__tracker = AllTracker(globals())


#
# Classes
#


class XYSeries:
    """
    Series of `x` and `y` coordinates for plotting; `x` and `y` values are stored in two
    separate sequences of the same length.
    """

    def __init__(self, x: Sequence[float], y: Sequence[float]) -> None:
        """
        :param x: series of all `x` coordinate values
        :param y: series of all `y` coordinate values
        """
        assert len(x) == len(y), "x and y have the same length"
        self.x = x
        self.y = y

    #: series of all `x` coordinate values
    x: Sequence[float]

    #: series of all `y` coordinate values
    y: Sequence[float]


class ECDF:
    """
    Three sets of coordinates for plotting an ECDF: inliers, outliers, and far
    outliers.
    """

    def __init__(
        self, inliers: XYSeries, outliers: XYSeries, far_outliers: XYSeries
    ) -> None:
        """
        :param inliers: coordinates for inliers in the ECDF
        :param outliers: coordinates for outliers in the ECDF
        :param far_outliers: coordinates for far outliers in the ECDF
        """
        self._inliers = inliers
        self._outliers = outliers
        self._far_outliers = far_outliers

    @property
    def inliers(self) -> XYSeries:
        """
        Coordinates for inliers in the ECDF.
        """
        return self._inliers

    @property
    def outliers(self) -> XYSeries:
        """
        Coordinates for outliers in the ECDF.
        """
        return self._outliers

    @property
    def far_outliers(self) -> XYSeries:
        """
        Coordinates for far outliers in the ECDF.
        """
        return self._far_outliers


class ECDFStyle(DrawingStyle, metaclass=ABCMeta):
    """
    Base drawing style for ECDFs.
    """

    @abstractmethod
    def _draw_ecdf(
        self, ecdf: ECDF, x_label: str, iqr_multiple: float, iqr_multiple_far: float
    ) -> None:
        pass


__tracker.validate()

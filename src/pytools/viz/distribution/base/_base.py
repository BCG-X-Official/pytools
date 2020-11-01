"""
Base classes for distribution styles.
"""

import logging
from abc import ABCMeta, abstractmethod
from typing import NamedTuple, Sequence

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


class XYSeries(NamedTuple):
    """
    Series of x and y coordinates for plotting; x and y values are held in two
    separate sequences of the same length.
    """

    x: Sequence[float]
    y: Sequence[float]


class ECDF(NamedTuple):
    """
    Three sets of coordinates for plotting an ECDF: inliers, outliers, and far
    outliers.
    """

    inliers: XYSeries
    outliers: XYSeries
    far_outliers: XYSeries


class ECDFStyle(DrawingStyle, metaclass=ABCMeta):
    """
    The base drawing style for ECDFs
    """

    @abstractmethod
    def _draw_ecdf(
        self, ecdf: ECDF, x_label: str, iqr_multiple: float, iqr_multiple_far: float
    ) -> None:
        pass


__tracker.validate()

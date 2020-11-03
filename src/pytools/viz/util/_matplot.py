"""
Utilities related to matplotlib.
"""

import logging

from matplotlib.ticker import Formatter

from pytools.api import AllTracker

log = logging.getLogger(__name__)


#
# Exported names
#

__all__ = ["PercentageFormatter"]


#
# Ensure all symbols introduced below are included in __all__
#

__tracker = AllTracker(globals())


#
# Classes
#


class PercentageFormatter(Formatter):
    """
    Formats floats as a percentages with 3 digits precision, omitting trailing zeros.

    Formatting examples:

    - ``0.00005`` is formatted as ``0.01%``
    - ``0.0005`` is formatted as ``0.05%``
    - ``0.0`` is formatted as ``0%``
    - ``0.1`` is formatted as ``10%``
    - ``1.0`` is formatted as ``100%``
    - ``0.01555`` is formatted as ``1.56%``
    - ``0.1555`` is formatted as ``15.6%``
    - ``1.555`` is formatted as ``156%``
    """

    def __call__(self, x, pos=None) -> str:
        return f"{x * 100.0:.3g}%"


# check consistency of __all__

__tracker.validate()

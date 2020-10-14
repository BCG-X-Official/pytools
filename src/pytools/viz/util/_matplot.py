"""
Utilities related to matplotlib.
"""

import logging
from typing import Tuple

from matplotlib.colors import LinearSegmentedColormap, to_rgba
from matplotlib.ticker import Formatter

from pytools.api import AllTracker

log = logging.getLogger(__name__)


__all__ = [
    "RgbaColor",
    "RGBA_BLACK",
    "RGBA_WHITE",
    "FACET_COLORMAP",
    "PercentageFormatter",
]

#
# Ensure all symbols introduced below are included in __all__
#

__tracker = AllTracker(globals())


#
# Type definitions
#

#: RGBA color type for use in ``MatplotStyle`` classes
RgbaColor = Tuple[float, float, float, float]

#
# Constants
#

# color constants

#: color constant for black
RGBA_BLACK: RgbaColor = to_rgba("black")

#: color constant for white
RGBA_WHITE: RgbaColor = to_rgba("white")

#: standard colormap for Facet
FACET_COLORMAP = LinearSegmentedColormap.from_list(
    name="facet",
    colors=[(0, "#3d3a40"), (0.25, "#295e7e"), (0.65, "#30c1d7"), (1.0, "#43fda2")],
)


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

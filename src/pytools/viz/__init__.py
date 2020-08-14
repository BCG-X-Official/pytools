"""
A lean MVC framework for rendering basic visualizations in different styles, e.g.,
as Matplotlib charts or as plain text.
"""

from ._matplot import *
from ._text import *
from ._viz import *

__all__ = [
    "ColorbarMatplotStyle",
    "MatplotStyle",
    "RGBA_BLACK",
    "RGBA_WHITE",
    "RgbaColor",
    "PercentageFormatter",
    "TextStyle",
    "Drawer",
    "DrawStyle",
]

#
# NOT FOR CLIENT USE!
#
# This is a pre-release library under development. Handling of IP rights is still
# being investigated. To avoid causing any potential IP disputes or issues, DO NOT USE
# ANY OF THIS CODE ON A CLIENT PROJECT, not even in modified form.
#
# Please direct any queries to any of:
# - Jan Ittner
# - Jörg Schneider
# - Florent Martin
#

"""
Private dendrogram package; all public classes are provided by parent `viz` module
"""

from ._draw import DendrogramDrawer
from ._linkage import BaseNode, LinkageTree
from ._style import (
    DendrogramHeatmapStyle,
    DendrogramLineStyle,
    DendrogramReportStyle,
    DendrogramStyle,
)

__all__ = [
    "DendrogramDrawer",
    "DendrogramHeatmapStyle",
    "DendrogramLineStyle",
    "DendrogramReportStyle",
    "DendrogramStyle",
    "LinkageTree",
]

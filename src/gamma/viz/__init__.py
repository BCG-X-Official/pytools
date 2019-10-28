"""
The Gamma visualization library, providing a MVC framework for rendering data in
different styles, e.g., as Matplotlib charts or as plain text.
"""

import gamma.common.licensing as _licensing
from ._viz import *

_licensing.check_license(__package__)

__all__ = [member for member in _viz.__all__ if not member.startswith("Base")]

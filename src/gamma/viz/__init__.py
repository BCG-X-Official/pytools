"""
The Gamma visualization library, providing a MVC framework for rendering data in
different styles, e.g., as Matplotlib charts or as plain text.
"""

import gamma.common.licensing as _licensing
from ._matplot import *
from ._text import *
from ._viz import *

_licensing.check_license(__package__)

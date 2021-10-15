"""
Supporting tools and autodoc enhancements for generating Sphinx documentation.
"""

from sys import version_info as __python_version

from ._util import *

if __python_version[:2] > (3, 6):
    # import sphinx tools requiring at least Python 3.7
    from ._util_py37 import *

del __python_version

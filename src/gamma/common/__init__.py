"""
Global definitions of basic types and functions for use across all gamma libraries
"""
from . import licensing as _licensing
from ._common import *

_licensing.check_license(__package__)

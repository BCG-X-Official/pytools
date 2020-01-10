"""
Global definitions of basic types and functions for use across all gamma libraries
"""
from . import licensing
from . import fit
from . import parallelization
from . import typing
from ._common import *

licensing.check_license(__package__)

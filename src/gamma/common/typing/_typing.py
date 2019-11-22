"""
Core implementation of :mod:`gamma.common.typing`
"""
import logging

log = logging.getLogger(__name__)

#
# exported names
#

__all__ = ["Function"]

#
# Type definitions
#

#: type constant for proper functions defined using ``def`` or ``lambda``
Function = type(lambda: None)

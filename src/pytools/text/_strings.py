"""
String manipulation functions.
"""
import logging
import re

from pytools.api import AllTracker

log = logging.getLogger(__name__)


#
# Exported names
#

__all__ = ["camel_case_to_snake_case"]


#
# Constants
#

RE_CAMEL_CASE_CHUNKS = re.compile(
    r"("
    r"(?:"
    r"[A-Z]+(?=[^a-z]|\b)"
    r"|[A-Za-z0-9][a-z0-9]*"
    r"|\W+"
    r")"
    r"(?:_(?=_))*"
    r")",
    re.ASCII,
)


#
# Ensure all symbols introduced below are included in __all__
#

__tracker = AllTracker(globals())


#
# Functions
#


def camel_case_to_snake_case(camel: str) -> str:
    """
    Convert a string from ``CamelCase`` to ``snake_case``.

    :param camel: a string in camel case
    :return: the string converted to snake case
    """
    return "_".join(re.findall(RE_CAMEL_CASE_CHUNKS, camel)).lower()


__tracker.validate()

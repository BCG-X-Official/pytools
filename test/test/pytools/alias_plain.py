"""
Test module defining a string type alias before the AllTracker is created, in a module
without postponed evaluation of annotations; used in test_alltracker_str_alias.py.
"""

from collections.abc import Sequence
from typing import TypeAlias

from pytools.api import AllTracker

StrAlias: TypeAlias = "int | str"

__tracker = AllTracker(globals())


class Holder:
    """A class with an annotation referring to a string type alias."""

    x: "StrAlias | Sequence[StrAlias] | None"


__all__ = ["Holder"]

__tracker.validate()

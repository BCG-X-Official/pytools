"""
Test module exporting a string type alias; used in test_alltracker_str_alias.py.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TypeAlias

from pytools.api import AllTracker

__tracker = AllTracker(globals())

StrAlias: TypeAlias = "int | str"


class Holder:
    """A class with an annotation referring to a string type alias."""

    x: StrAlias | Sequence[StrAlias] | None


__all__ = ["Holder", "StrAlias"]

__tracker.validate()

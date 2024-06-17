# noinspection GrazieInspection
"""
Implements a :class:`Taxonomy` as a tree of categories, where each category can have
subcategories.

Categories are implemented as a composite pattern, where the base class
:class:`Category` is abstract and defines the interface for all categories.
"""

from ._category import *
from ._taxonomy import *

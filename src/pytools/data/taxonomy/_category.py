"""
Implementation of ``MyClass``.
"""

from __future__ import annotations

import functools
import logging
from abc import ABCMeta, abstractmethod
from collections.abc import Iterable
from typing import Any, cast, final

from typing_extensions import Self

from pytools.api import as_tuple

log = logging.getLogger(__name__)

__all__ = [
    "Category",
]


#
# Classes
#


@functools.total_ordering
class Category(metaclass=ABCMeta):
    """
    A category.

    Implements the "composite" pattern in one single abstract class.
    """

    _children: tuple[Category, ...]

    def __init__(self, *, children: Self | Iterable[Self] | None = None) -> None:
        """
        :param children: the subcategories of the category (optional)
        """
        self._children = as_tuple(
            children, element_type=type(self), arg_name="subcategories", optional=True
        )

    @property
    @abstractmethod
    def name(self) -> str:
        """
        The name of the category.
        """

    @property
    @final
    def children(self) -> tuple[Self, ...]:
        """
        The subcategories of this category.
        """
        return cast(tuple[Self, ...], self._children)

    @property
    @final
    def has_children(self) -> bool:
        """
        ``True`` if this category is a group, ``False`` otherwise.
        """
        return bool(self._children)

    def traverse(self) -> Iterable[Self]:
        """
        Yield this category and all its subcategories, recursively and depth-first.

        :return: an iterator that yields this category and all its subcategories
        """
        yield self
        for child in self.children:
            yield from child.traverse()

    def __eq__(self, other: Any) -> bool:
        return (
            type(self) is type(other)
            and self.name == other.name
            and self.children == other.children
        )

    def __lt__(self, other: Category) -> bool:
        return self.name < other.name

    def __hash__(self) -> int:
        return hash(self.name)

    def __repr__(self) -> str:
        return repr(self.name)

    def __str__(self) -> str:
        return self.name

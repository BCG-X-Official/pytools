"""
Implementation of the 'taxonomy' class.
"""

from __future__ import annotations

import logging
from collections import Counter
from collections.abc import Iterable
from typing import Any, Generic, TypeVar

from ...repr import HasDictRepr
from ._category import Category

log = logging.getLogger(__name__)

__all__ = [
    "Taxonomy",
]


#
# Type variables
#

T_Category = TypeVar("T_Category", bound=Category)


class Taxonomy(HasDictRepr, Generic[T_Category]):
    """
    A taxonomy of categories.

    Wraps a hierarchy of categories, and adds additional methods to work with the
    hierarchy.

    Categories can be looked up by their name using the indexing operator, e.g.,
    ``taxonomy["name"]``.
    """

    #: the root category of the taxonomy
    root: T_Category

    #: maps category names to category paths along the hierarchy
    _paths: dict[str, tuple[T_Category, ...]]

    def __init__(self, root: T_Category) -> None:
        """
        :param root: the root category of the taxonomy
        """

        self.root = root

        # Store the paths to all subcategories for quick retrieval.
        # This has a worst-case memory complexity of O(n^2), but it's
        # acceptable given the typically small size of the data.
        path_tuples: list[tuple[str, tuple[T_Category, ...]]] = list(_get_paths(root))

        self._paths = paths = dict(path_tuples)

        if len(paths) != len(path_tuples):
            # Duplicate category names are not allowed (they would break the path
            # lookup). List them and raise an error.
            raise ValueError(
                "Duplicate category names: "
                + ", ".join(
                    name
                    for name, count in Counter(name for name, _ in path_tuples).items()
                    if count > 1
                )
            )

    def get_leaves(self) -> Iterable[T_Category]:
        """
        Yield the categories at the lowest level of the taxonomy.

        :return: the leaf categories of the taxonomy
        """
        return (
            category for category in self.root.traverse() if not category.has_children
        )

    def get_path_to(self, category: T_Category) -> tuple[T_Category, ...]:
        """
        Get the path from the root category to the given category.

        :param category: the category to get the path to
        :return: the path to the given category
        :raises KeyError: if the given category is not part of this taxonomy
        """
        return self._paths[category.name]

    def is_descendant(self, *, parent: T_Category, child: T_Category) -> bool:
        """
        ``True`` if ``child`` is a direct or indirect descendant of ``parent``;
        ``False`` otherwise.

        :param parent: parent category
        :param child: child category to check
        :return: ``True`` if child is a descendant of parent, ``False`` otherwise
        """
        return any(category == parent for category in self._paths[child.name][:-1])

    def __getitem__(self, name: str) -> T_Category:
        """
        Get a category by its name.

        :param name: a category name
        :return: the category with the given name
        :raises KeyError: if no category with the given name exists
        """
        return self._paths[name][-1]

    def __contains__(self, category: T_Category | str) -> bool:
        """
        ``True`` if the given category, or a category with the given name, is part of
        this taxonomy; ``False`` otherwise.

        :param category: a category or category name
        """
        return (
            category.name if isinstance(category, Category) else category
        ) in self._paths

    def __eq__(self, other: Any) -> bool:
        return type(self) is type(other) and self.root == other.root

    def __hash__(self) -> int:
        return hash((type(self), self.root))


def _get_paths(
    category: T_Category, path_to_here: tuple[T_Category, ...] = ()
) -> Iterable[tuple[str, tuple[T_Category, ...]]]:
    """
    Get the paths along the hierarchy to all subcategories of the given category, and to
    the category itself.

    :param category: the category to get the paths for
    :param path_to_here: the path to the given category
    :return: an iterable of tuples, mapping unique object ids of categories to category
        paths along the hierarchy
    """

    path_to_here = (*path_to_here, category)
    yield category.name, path_to_here
    for subcategory in category.children:
        yield from _get_paths(subcategory, path_to_here)

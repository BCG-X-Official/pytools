from collections.abc import Iterable

import pytest
from typing_extensions import Self

from pytools.data.taxonomy import Category, Taxonomy


class TestCategory(Category):
    #: The name of the category.
    _name: str

    def __init__(
        self, name: str, *, children: Self | Iterable[Self] | None = None
    ) -> None:
        super().__init__(children=children)
        self._name = name

    @property
    def name(self) -> str:
        return self._name


def test_double_categories() -> None:
    """
    Raise an error if a taxonomy is created with duplicate category names.
    """

    categories = TestCategory(
        name="root",
        children=[
            TestCategory(name="duplicated"),
            TestCategory(name="duplicated"),
            TestCategory(name="duplicated2"),
            TestCategory(name="duplicated2"),
        ],
    )

    with pytest.raises(
        ValueError,
        match=r"^Duplicate category names: duplicated, duplicated2$",
    ):
        Taxonomy(root=categories)


def test_lookup() -> None:
    child1 = TestCategory(name="child1")
    child2 = TestCategory(name="child2")
    root = TestCategory(name="root", children=[child1, child2])
    taxonomy = Taxonomy(root=root)
    assert taxonomy["root"] == root
    assert taxonomy["child1"] == child1
    assert taxonomy["child2"] == child2
    assert taxonomy.get_path_to(root) == (root,)
    assert taxonomy.get_path_to(child1) == (root, child1)
    assert taxonomy.get_path_to(child2) == (root, child2)


def test_is_descendant() -> None:
    child1 = TestCategory(name="child1")
    child2 = TestCategory(name="child2")
    root = TestCategory(name="root", children=[child1, child2])
    taxonomy = Taxonomy(root=root)
    assert taxonomy.is_descendant(parent=taxonomy["root"], child=taxonomy["child1"])
    assert taxonomy.is_descendant(parent=taxonomy["root"], child=taxonomy["child2"])
    assert not taxonomy.is_descendant(parent=taxonomy["child1"], child=taxonomy["root"])
    assert not taxonomy.is_descendant(
        parent=taxonomy["child1"], child=taxonomy["child1"]
    )

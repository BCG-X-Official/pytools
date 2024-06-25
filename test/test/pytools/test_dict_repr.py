"""
Tests for dictionary representations of objects.
"""

import logging
from collections.abc import Iterable

import pytest
from typing_extensions import Self

from pytools.data.taxonomy import Category
from pytools.repr import HasDictRepr

log = logging.getLogger(__name__)


class A(HasDictRepr):
    """
    A persona.
    """

    def __init__(self, x: str) -> None:
        self.x = x

    def __eq__(self, other: object) -> bool:
        return isinstance(other, A) and self.x == other.x


class B(HasDictRepr):
    """
    A challenge generated from the perspective of a persona.
    """

    def __init__(self, y: str, *, a: A) -> None:
        self.y = y
        self.a = a

    def __eq__(self, other: object) -> bool:
        return isinstance(other, B) and self.y == other.y and self.a == other.a


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


def test_invalid_dict_repr() -> None:
    """
    Test that invalid or missing keys in the dictionary representation raise a
    ValueError.
    """

    # missing key
    with pytest.raises(ValueError):
        HasDictRepr.from_dict({"cls": "unknown_module.UnknownClass"})
    with pytest.raises(ValueError):
        HasDictRepr.from_dict({"params": "value"})

    # invalid key
    with pytest.raises(ValueError):
        HasDictRepr.from_dict({"invalid": "value"})

    # invalid nested dict
    with pytest.raises(ValueError):
        HasDictRepr.from_dict(
            {
                "cls": "TestCategory",
                "params": dict(
                    name={"a": 1},
                    description="description",
                    children=[],
                ),
            }
        )

    with pytest.raises(ValueError):
        HasDictRepr.from_dict(
            {
                "cls": "TestCategory",
                "params": dict(
                    name={"a": 1, "b": 2},
                    description="description",
                    children=[],
                ),
            }
        )

    with pytest.raises(ValueError):
        HasDictRepr.from_dict(
            {
                "cls": "TestCategory",
                "params": dict(
                    name={"a": 1, "b": 2, "c": 3},
                    description="description",
                    children=[],
                ),
            }
        )

    with pytest.raises(ValueError):
        HasDictRepr.from_dict(
            {
                "cls": "TestCategory",
                "params": dict(
                    name=object(),
                    description="description",
                    children=[],
                ),
            }
        )


def test_invalid_source_object() -> None:
    """c
    Test that attempts to convert objects that do not have a dictionary representation
    raise a ValueError.
    """

    class NoDictRepr:
        pass

    class WithDictRepr(HasDictRepr):
        def __init__(self, no_dict_repr: NoDictRepr) -> None:
            self.no_dict_repr = no_dict_repr

    with pytest.raises(ValueError):
        WithDictRepr(NoDictRepr()).to_dict()

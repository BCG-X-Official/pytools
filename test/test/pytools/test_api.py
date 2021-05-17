"""
Basic test cases for the `pytools.api` module
"""
# noinspection PyPackageRequirements
import sys

import pytest

print(sys.path)

from pytools.api import (
    deprecated,
    subsdoc,
    to_collection,
    to_list,
    to_set,
    to_tuple,
    validate_element_types,
)


def test_deprecated() -> None:
    @deprecated
    def _f() -> None:
        pass

    with pytest.warns(
        expected_warning=FutureWarning,
        match="Call to deprecated function test_deprecated.<locals>._f",
    ):
        _f()

    @deprecated(message="test message")
    def _g() -> None:
        pass

    with pytest.warns(
        expected_warning=FutureWarning,
        match="Call to deprecated function test_deprecated.<locals>._g: test message",
    ):
        _g()


def test_subsdoc() -> None:
    class _A:
        @subsdoc(pattern=r"a(\d)c", replacement=r"A\1C")
        def _f(self) -> None:
            """a5c aac a3c"""

    assert _A._f.__doc__ == "A5C aac A3C"


def test_collection_conversions() -> None:
    assert to_set(1) == {1}
    assert to_list(1) == [1]
    assert to_tuple(1) == (1,)
    assert to_collection(1) == (1,)

    assert to_set([1, 2]) == {1, 2}
    assert to_list((1, 2)) == [1, 2]
    assert to_tuple([1, 2]) == (1, 2)
    assert to_collection({1, 2}) == {1, 2}
    assert to_collection([1, 2]) == [1, 2]
    assert to_collection((1, 2)) == (1, 2)
    assert to_collection(iter([1, 2])) == (1, 2)

    s = {1, 2}
    l = [1, 2]
    t = (1, 2)
    d = {1: 10, 2: 20}

    assert to_set(s) is s
    assert to_list(l) is l
    assert to_tuple(t) is t
    assert to_collection(s) is s
    assert to_collection(l) is l
    assert to_collection(t) is t
    assert to_collection(d) is d

    with pytest.raises(TypeError):
        to_set(1, element_type=str)
    with pytest.raises(TypeError):
        to_list(1, element_type=str)
    with pytest.raises(TypeError):
        to_tuple(1, element_type=str)
    with pytest.raises(TypeError):
        to_collection(1, element_type=str)

    with pytest.raises(TypeError):
        to_set(["a", 1], element_type=str)
    with pytest.raises(TypeError):
        to_list(["a", 1], element_type=str)
    with pytest.raises(TypeError):
        to_tuple(["a", 1], element_type=str)
    with pytest.raises(TypeError):
        to_collection(["a", 1], element_type=str)

    validate_element_types([1, 2, 3], expected_type=int)
    with pytest.raises(TypeError, match=r"^xyz "):
        validate_element_types(iter([1, 2, 3]), expected_type=str, name="xyz")

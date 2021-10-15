"""
Basic test cases for the `pytools.api` module
"""

import pytest

from pytools.api import (
    deprecated,
    subsdoc,
    to_collection,
    to_list,
    to_set,
    to_tuple,
    validate_element_types,
    validate_type,
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


def test_type_validation() -> None:
    validate_type(3, expected_type=int)
    validate_type(3, expected_type=int, optional=True)
    validate_type(None, expected_type=int, optional=True)

    validate_type(3, expected_type=(int, float))
    validate_type(3.0, expected_type=(int, float))
    validate_type(3.0, expected_type=(int, float), optional=True)
    validate_type(None, expected_type=(int, float), optional=True)

    with pytest.raises(
        TypeError, match="^expected an instance of float but got an int$"
    ):
        validate_type(3, expected_type=float)

    with pytest.raises(
        TypeError, match="^value requires an instance of float but got an int$"
    ):
        validate_type(3, expected_type=float, name="value")

    with pytest.raises(
        TypeError, match="^value requires an instance of float but got an int$"
    ):
        validate_type(3, expected_type=float, name="value")

    with pytest.raises(
        TypeError, match="^value requires an instance of int or float but got a str$"
    ):
        validate_type("3", expected_type=(int, float), name="value")

    with pytest.raises(
        TypeError,
        match="^value requires an instance of int or float or NoneType but got a str$",
    ):
        validate_type("3", expected_type=(int, float), optional=True, name="value")

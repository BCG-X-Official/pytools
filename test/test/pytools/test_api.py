"""
Basic test cases for the `pytools.api` module
"""

from typing import Any, TypeAlias, Union

import pytest

from pytools.api import (
    AllTracker,
    as_collection,
    as_list,
    as_set,
    as_tuple,
    deprecated,
    subsdoc,
    validate_element_types,
    validate_type,
)

PKG_TEST_PYTOOLS_TEST_API = "test.pytools.test_api"
MyTypeAlias: TypeAlias = Union["str", int]


def test_deprecated() -> None:
    @deprecated
    def _f() -> None:
        # dummy function to test the @deprecated decorator
        pass

    with pytest.warns(
        expected_warning=FutureWarning,
        match="Call to deprecated function test_deprecated.<locals>._f",
    ):
        _f()

    @deprecated(message="test message")
    def _g() -> None:
        # dummy function to test the @deprecated decorator
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

    @subsdoc(pattern="A5C", replacement="Foo", using=_A._f)
    def _g() -> None:
        # empty function
        pass

    assert _g.__doc__ == "Foo aac A3C"


def test_collection_conversions() -> None:
    assert as_set(1) == {1}
    assert as_list(1) == [1]
    assert as_tuple(1) == (1,)
    assert as_collection(1) == (1,)

    assert as_set([1, 2]) == {1, 2}
    assert as_list((1, 2)) == [1, 2]
    assert as_tuple([1, 2]) == (1, 2)
    assert as_collection({1, 2}) == {1, 2}
    assert as_collection([1, 2]) == [1, 2]
    assert as_collection((1, 2)) == (1, 2)
    assert as_collection(iter([1, 2])) == (1, 2)

    my_set = {1, 2}
    my_list = [1, 2]
    my_tuple = (1, 2)
    my_dict = {1: 10, 2: 20}

    assert as_set(my_set) is my_set  # NOSONAR
    assert as_list(my_list) is my_list  # NOSONAR
    assert as_tuple(my_tuple) is my_tuple  # NOSONAR
    assert as_collection(my_set) is my_set  # NOSONAR
    assert as_collection(my_list) is my_list  # NOSONAR
    assert as_collection(my_tuple) is my_tuple  # NOSONAR
    assert as_collection(my_dict) is my_dict  # NOSONAR

    assert as_set(None, optional=True) == set()
    assert as_list(None, optional=True) == []
    assert as_tuple(None, optional=True) == ()
    assert as_collection(None, optional=True) == ()

    assert as_set(None) == {None}
    assert as_list(None) == [None]
    assert as_tuple(None) == (None,)
    assert as_collection(None) == (None,)

    with pytest.raises(TypeError):
        as_set(1, element_type=str)
    with pytest.raises(TypeError):
        as_list(1, element_type=str)
    with pytest.raises(TypeError):
        as_tuple(1, element_type=str)
    with pytest.raises(TypeError):
        as_collection(1, element_type=str)

    with pytest.raises(TypeError):
        as_set(["a", 1], element_type=str)
    with pytest.raises(TypeError):
        as_list(["a", 1], element_type=str)
    with pytest.raises(TypeError):
        as_tuple(["a", 1], element_type=str)
    with pytest.raises(TypeError):
        as_collection(["a", 1], element_type=str)

    validate_element_types([1, 2, 3], expected_type=int)
    with pytest.raises(TypeError, match=r"^xyz "):
        validate_element_types(iter([1, 2, 3]), expected_type=str, name="xyz")

    with pytest.raises(
        TypeError, match=r"^xyz must not be a string or bytes instance$"
    ):
        validate_element_types("abc", expected_type=str, name="xyz")

    with pytest.raises(
        TypeError, match=r"^expected an iterable other than a string or bytes instance$"
    ):
        validate_element_types("abc", expected_type=str)


def test_type_validation() -> None:
    validate_type(3, expected_type=int)
    validate_type(3, expected_type=int, optional=True)
    validate_type(None, expected_type=int, optional=True)

    # noinspection PyTypeChecker
    validate_type(3, expected_type=(int, float))
    # noinspection PyTypeChecker
    validate_type(3.0, expected_type=(int, float))
    # noinspection PyTypeChecker
    validate_type(3.0, expected_type=(int, float), optional=True)
    # noinspection PyTypeChecker
    validate_type(None, expected_type=(int, float), optional=True)

    with pytest.raises(
        TypeError, match=r"^expected an instance of float but got: int$"
    ):
        validate_type(3, expected_type=float)

    with pytest.raises(
        TypeError, match=r"^value requires an instance of float but got: int$"
    ):
        validate_type(3, expected_type=float, name="value")

    with pytest.raises(
        TypeError, match=r"^value requires an instance of float but got: int$"
    ):
        validate_type(3, expected_type=float, name="value")

    with pytest.raises(
        TypeError,
        match=r"^value requires an instance of one of {int, float} but got: str$",
    ):
        # noinspection PyTypeChecker
        validate_type("3", expected_type=(int, float), name="value")

    with pytest.raises(
        TypeError,
        match=(
            r"^value requires an instance of one of \{int, float, NoneType\} "
            r"but got: str$"
        ),
    ):
        # noinspection PyTypeChecker
        validate_type("3", expected_type=(int, float), optional=True, name="value")


def test_all_tracker() -> None:
    class A:
        pass

    class B:
        pass

    class _C:
        pass

    # test with defaults, no constant declaration

    mock_globals: dict[str, Any] = dict(
        __all__=["A", "B", "MyTypeAlias"],
        __name__=PKG_TEST_PYTOOLS_TEST_API,
    )
    tracker = AllTracker(mock_globals)

    mock_globals.update(
        dict(
            A=A,
            B=B,
            _C=_C,
            MyTypeAlias=MyTypeAlias,
        )
    )
    tracker.validate()

    assert tracker.get_tracked() == ["A", "B", "MyTypeAlias"]
    assert tracker.is_tracked("A", A)
    assert tracker.is_tracked("B", B)
    assert not tracker.is_tracked("_C", _C)
    assert mock_globals["MyTypeAlias"] == Union[str, int]

    # test with defaults, with constant declaration

    mock_globals = dict(
        __all__=["A", "B", "CONST"],
        __name__=PKG_TEST_PYTOOLS_TEST_API,
    )
    tracker = AllTracker(mock_globals)

    mock_globals.update(
        dict(
            A=A,
            B=B,
            _C=_C,
            CONST=1,
        )
    )
    with pytest.raises(
        AssertionError, match=r"^exporting a global constant is not permitted: 1$"
    ):
        tracker.validate()

    # test with constant declarations allowed

    mock_globals = dict(
        __all__=["A", "B", "CONST"],
        __name__=PKG_TEST_PYTOOLS_TEST_API,
    )
    tracker = AllTracker(mock_globals, allow_global_constants=True)

    mock_globals.update(
        dict(
            A=A,
            B=B,
            _C=_C,
            CONST=1,
        )
    )
    tracker.validate()

    # test with defaults, with foreign import

    mock_globals = dict(
        __all__=["A", "B"],
        __name__="test.pytools.test_api_other",
    )
    tracker = AllTracker(mock_globals)

    mock_globals.update(
        dict(
            A=A,
            B=B,
            _C=_C,
        )
    )
    with pytest.raises(
        AssertionError,
        match=(
            r"A is exported by module test\.pytools\.test_api_other but defined in "
            r"module test\.pytools\.test_api"
        ),
    ):
        tracker.validate()

    # test with imported definitions allowed

    mock_globals = dict(
        __all__=["A", "B"],
        __name__="test.pytools.test_api_other",
    )
    tracker = AllTracker(mock_globals, allow_imported_definitions=True)

    mock_globals.update(
        dict(
            A=A,
            B=B,
            _C=_C,
        )
    )
    tracker.validate()

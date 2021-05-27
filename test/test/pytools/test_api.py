"""
Basic test cases for the `pytools.api` module
"""
# noinspection PyPackageRequirements
import sys

import pytest

print(sys.path)

from pytools.api import deprecated, subsdoc


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

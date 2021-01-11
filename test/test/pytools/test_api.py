"""
Basic test cases for the `pytools.api` module
"""
# noinspection PyPackageRequirements
import sys

import pytest

print(sys.path)

from pytools.api import deprecated


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

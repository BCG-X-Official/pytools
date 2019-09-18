"""
Basic test cases for the `gamma.common` module
"""
# noinspection PyPackageRequirements
import pytest

from gamma.common import deprecated


def test_deprecated() -> None:
    @deprecated
    def _f() -> None:
        pass

    with pytest.warns(
        expected_warning=DeprecationWarning, match="Call to deprecated function _f"
    ):
        _f()

    @deprecated(message="test message")
    def _g() -> None:
        pass

    with pytest.warns(
        expected_warning=DeprecationWarning,
        match="Call to deprecated function _g: test message",
    ):
        _g()

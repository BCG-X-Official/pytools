import pytest

from gamma.common import deprecated


def test_deprecated() -> None:
    @deprecated(message=None)
    def f() -> None:
        pass

    with pytest.warns(expected_warning=DeprecationWarning):
        f()

    @deprecated(message="test message")
    def g() -> None:
        pass

    with pytest.warns(expected_warning=DeprecationWarning):
        g()

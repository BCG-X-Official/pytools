from gamma.common import deprecated


def test_deprecated() -> None:
    @deprecated(message=None)
    def f() -> None:
        pass

    f()

    @deprecated(message="test message")
    def g() -> None:
        pass

    g()

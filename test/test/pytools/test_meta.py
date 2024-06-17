"""
Tests for the pytools.meta package
"""

from pytools.meta import SingletonABCMeta, SingletonMeta


def test_singleton_meta() -> None:
    """
    Test the singleton metaclasses
    """

    class TestSingleton(metaclass=SingletonMeta):
        """
        Test class for the singleton metaclass
        """

    assert TestSingleton() is TestSingleton()

    class TestSingletonABC(metaclass=SingletonABCMeta):
        """
        Test class for the singleton ABC metaclass
        """

    assert TestSingletonABC() is TestSingletonABC()

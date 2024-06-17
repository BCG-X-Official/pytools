"""
Tests for utility functions related to generic types.
"""

import typing
from collections.abc import AsyncIterable
from collections.abc import AsyncIterable as AsyncIterable_typing
from collections.abc import AsyncIterator
from collections.abc import AsyncIterator as AsyncIterator_typing
from collections.abc import Iterable, Iterator, Mapping
from typing import Any, Generic, TypeVar

import pytest

from pytools.typing import get_generic_instance, issubclass_generic

Iterable_typing = getattr(typing, "Iterable")
Iterator_typing = getattr(typing, "Iterator")


T = TypeVar("T")
T_arg = TypeVar("T_arg", contravariant=True)
T_ret = TypeVar("T_ret", covariant=True)


class A:
    pass


class B(A, Generic[T]):
    pass


class BArg(Generic[T_arg]):
    pass


class BRet(Generic[T_ret]):
    pass


class C(B[int]):
    pass


class CArg(BArg[T_arg], Generic[T_arg]):
    pass


class CRet(BRet[T_ret], Generic[T_ret]):
    pass


class CNotGeneric(B):  # type: ignore[type-arg]
    pass


def test_issubclass_generic() -> None:

    assert issubclass_generic(CRet[list[A]], BRet[list[A]])

    assert issubclass_generic(C, B[int])
    assert not issubclass_generic(C, B[float])
    assert not issubclass_generic(C, B)

    assert issubclass_generic(C, A)
    assert issubclass_generic(B[float], A)

    assert not issubclass_generic(C, int)

    assert issubclass_generic(CArg[A], BArg[C])
    assert not issubclass_generic(CArg[C], BArg[A])

    assert not issubclass_generic(CRet[A], BRet[C])
    assert issubclass_generic(CRet[C], BRet[A])

    assert not issubclass_generic(CNotGeneric, B[int])
    assert issubclass_generic(CNotGeneric, B[Any])
    assert issubclass_generic(CNotGeneric, B)

    with pytest.raises(TypeError, match=r"^Unsupported type construct: tuple\["):
        issubclass_generic(
            CRet[tuple[B, ...]], BRet[tuple[A, ...]]  # type: ignore[type-arg]
        )
    with pytest.raises(TypeError, match=r"^Unsupported type construct: tuple\["):
        assert issubclass_generic(
            CRet[tuple[A, B]], BRet[tuple[A, B]]  # type: ignore[type-arg]
        )
    with pytest.raises(TypeError, match=r"^Unsupported type construct: tuple\["):
        assert not issubclass_generic(
            CRet[tuple[A, B]], BRet[tuple[A, Any]]  # type: ignore[type-arg]
        )
    with pytest.raises(TypeError, match=r"^Unsupported type construct: tuple\["):
        assert not issubclass_generic(
            CRet[tuple[A, ...]], BRet[tuple[B, ...]]  # type: ignore[type-arg]
        )

    assert issubclass_generic(AsyncIterator[int], AsyncIterable[int])
    assert issubclass_generic(Iterator[int], Iterable[int])
    assert issubclass_generic(AsyncIterator_typing[int], AsyncIterable_typing[int])
    assert issubclass_generic(Iterator_typing[int], Iterable_typing[int])
    assert not issubclass_generic(
        AsyncIterator_typing[dict[str, int]], AsyncIterable[dict[str, Any]]
    )
    assert issubclass_generic(
        AsyncIterator_typing[Mapping[str, int]], AsyncIterable[Mapping[str, Any]]
    )


def test_get_generic_instance() -> None:

    assert get_generic_instance(CRet[int], BRet) == [BRet[int]]
    assert get_generic_instance(CNotGeneric, B) == [B[Any]]
    assert get_generic_instance(AsyncIterator[int], AsyncIterable) == [
        AsyncIterable[int]
    ]
    assert get_generic_instance(Iterator_typing[int], Iterable) == [Iterable[int]]
    assert get_generic_instance(Iterator[int], Iterable_typing) == [Iterable[int]]

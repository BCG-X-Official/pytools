"""
Native classes, enhanced with mixin class :class:`.HasExpressionRepr`.
"""

from __future__ import annotations

import logging
from typing import Generic, TypeVar

from typing_extensions import TypeVarTuple, Unpack

from pytools.api import inheritdoc
from pytools.expression import Expression, HasExpressionRepr
from pytools.expression.atomic import Id
from pytools.expression.composite import (
    DictLiteral,
    ListLiteral,
    SetLiteral,
    TupleLiteral,
)

log = logging.getLogger(__name__)

__all__ = [
    "DictWithExpressionRepr",
    "ListWithExpressionRepr",
    "SetWithExpressionRepr",
    "TupleWithExpressionRepr",
]

#
# Type variables
#

T = TypeVar("T")
Ts = TypeVarTuple("Ts")
KT = TypeVar("KT")
VT = TypeVar("VT")


#
# Classes
#


@inheritdoc(match="[see superclass]")
class ListWithExpressionRepr(HasExpressionRepr, list[T], Generic[T]):
    """
    A list that formats its string representation as an expression.
    """

    def to_expression(self) -> Expression:
        """[see superclass]"""
        return ListLiteral(*self)


@inheritdoc(match="[see superclass]")
class TupleWithExpressionRepr(
    HasExpressionRepr, tuple[Unpack[Ts]], Generic[Unpack[Ts]]
):
    """
    A tuple that formats its string representation as an expression.
    """

    def to_expression(self) -> Expression:
        """[see superclass]"""
        return TupleLiteral(*self)


@inheritdoc(match="[see superclass]")
class SetWithExpressionRepr(HasExpressionRepr, set[T], Generic[T]):
    """
    A set that formats its string representation as an expression.
    """

    def to_expression(self) -> Expression:
        """[see superclass]"""
        return SetLiteral(*self) if self else Id(set)()


@inheritdoc(match="[see superclass]")
class DictWithExpressionRepr(HasExpressionRepr, dict[KT, VT], Generic[KT, VT]):
    """
    A dictionary that formats its string representation as an expression.
    """

    def to_expression(self) -> Expression:
        """[see superclass]"""
        return DictLiteral(*self.items())

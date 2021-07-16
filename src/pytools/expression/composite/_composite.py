"""
Implementation of :mod:`pytools.expression` and subpackages.
"""
import itertools
import logging
from abc import ABCMeta
from typing import Any, Tuple, TypeVar, Union, cast

from ...api import AllTracker, inheritdoc
from .. import Expression, ExpressionAlias, make_expression
from ..atomic import Epsilon, Id
from ..base import (
    BracketPair,
    CollectionLiteral,
    InfixExpression,
    Invocation,
    Operation,
    SimplePrefixExpression,
)
from ..operator import BinaryOperator, UnaryOperator
from .base import DictEntry, KeywordArgument, LambdaDefinition

log = logging.getLogger(__name__)


#
# Exported names
#

__all__ = [
    "ListLiteral",
    "TupleLiteral",
    "SetLiteral",
    "DictLiteral",
    "UnaryOperation",
    "BinaryOperation",
    "Call",
    "Index",
    "Lambda",
    "Attr",
]

#
# Type variables
#

T = TypeVar("T")
T_Literal = TypeVar("T_Literal", bool, int, float, complex, str, bytes)


#
# Ensure all symbols introduced below are included in __all__
#

__tracker = AllTracker(globals())


#
# Class definitions
#


#
# Bracketed expressions
#


class ListLiteral(CollectionLiteral):
    """
    A list expression.
    """

    def __init__(self, *elements: Any) -> None:
        """
        :param elements: the list elements
        """
        super().__init__(brackets=BracketPair.SQUARE, elements=elements)


class TupleLiteral(CollectionLiteral):
    """
    A tuple expression.
    """

    def __init__(self, *elements: Any) -> None:
        """
        :param elements: the tuple elements
        """
        super().__init__(brackets=BracketPair.ROUND, elements=elements)


class SetLiteral(CollectionLiteral):
    """
    A set expression.
    """

    def __init__(self, *elements: Any) -> None:
        """
        :param elements: the set elements
        """
        super().__init__(brackets=BracketPair.CURLY, elements=elements)


class DictLiteral(CollectionLiteral):
    """
    A dictionary expression.
    """

    def __init__(self, *args: Tuple[Any, Any], **kwargs: Tuple[str, Any]) -> None:
        """
        :param args: dictionary entries as tuples ``(key, value)``
        :param kwargs: dictionary entries as keyword arguments
        """
        super().__init__(
            brackets=BracketPair.CURLY,
            elements=(
                DictEntry(key, value)
                for key, value in itertools.chain(args, kwargs.items())
            ),
        )


#
# Operations
#


@inheritdoc(match="[see superclass]")
class UnaryOperation(SimplePrefixExpression, Operation, metaclass=ABCMeta):
    """
    A unary operation.
    """

    def __init__(self, operator: UnaryOperator, operand: Any) -> None:
        """
        :param operator: the unary operator
        :param operand: the operand
        """
        super().__init__(prefix=Epsilon(), body=operand)
        self._operator = operator

    @property
    def separator_(self) -> str:
        """[see superclass]"""
        return self._operator.symbol

    @property
    def operator_(self) -> UnaryOperator:
        """[see superclass]"""
        return self._operator

    @property
    def operands_(self) -> Tuple[Expression, ...]:
        """[see superclass]"""
        return self.subexpressions_

    @property
    def precedence_(self) -> int:
        """[see superclass]"""
        return self._operator.precedence


@inheritdoc(match="[see superclass]")
class BinaryOperation(InfixExpression, Operation):
    """
    A operation with two or more operands.
    """

    def __init__(self, operator: BinaryOperator, *operands: Any) -> None:
        """
        :param operator: the binary operator applied by this operation
        :param operands: the operands applied to the binary operator
        """
        super().__init__()
        if not isinstance(operator, BinaryOperator):
            raise TypeError(f"arg operator={operator} must be an BinaryOperator")

        if len(operands) < 2:
            raise ValueError("operation requires at least two operands")

        operands: Tuple[Expression, ...] = tuple(
            make_expression(operand) for operand in operands
        )

        first_operand = operands[0]

        if (
            isinstance(first_operand, BinaryOperation)
            and first_operand.operator_ == operator
        ):
            # if first operand has the same operator, we flatten the operand
            # noinspection PyUnresolvedReferences
            operands = (*first_operand.operands_, *operands[1:])

        self._operator = operator
        self._operands = operands

    @property
    def operator_(self) -> BinaryOperator:
        """[see superclass]"""
        return self._operator

    @property
    def operands_(self) -> Tuple[Expression, ...]:
        """[see superclass]"""
        return self._operands

    @property
    def infix_(self) -> BinaryOperator:
        """[see superclass]"""
        return self._operator

    @property
    def precedence_(self) -> int:
        """[see superclass]"""
        return self.infix_.precedence

    def _flattened_operands(self) -> Tuple[Expression, ...]:
        operands = self.operands_
        first_operand = operands[0]

        while isinstance(first_operand, ExpressionAlias):
            first_operand = first_operand.expression_

            if (
                isinstance(first_operand, BinaryOperation)
                and first_operand.operator_ == self.operator_
            ):
                return (*first_operand._flattened_operands(), *operands[1:])

        return operands

    def _eq_same_type(self, other: "BinaryOperation") -> bool:
        if self.operator_ == other.operator_:
            self_operands_ = self._flattened_operands()
            other_operands_ = other._flattened_operands()
            return len(self_operands_) == len(other_operands_) and all(
                a.eq_(b) for a, b in zip(self_operands_, other_operands_)
            )
        else:
            return False


#
# Invocations
#


class Call(Invocation):
    """
    A call expression.
    """

    def __init__(self, callee: Any, *args: Any, **kwargs: Any) -> None:
        """
        :param callee: the expression representing the object being called
        :param args: the positional argument(s) of the call
        :param kwargs: the keyword arguments of the call
        """
        super().__init__(
            prefix=callee,
            brackets=BracketPair.ROUND,
            args=(
                *args,
                *(KeywordArgument(name, item) for name, item in kwargs.items()),
            ),
        )

    @property
    def callee_(self) -> Expression:
        """
        The expression being called; identical with the prefix of this expression.
        """
        return self.prefix_


class Index(Invocation):
    """
    An indexing operation.
    """

    def __init__(self, collection: Any, key: Any) -> None:
        """
        :param collection: the collection to be indexed
        :param key: the index key
        """
        keys = key if isinstance(key, tuple) else (key,)
        super().__init__(prefix=collection, brackets=BracketPair.SQUARE, args=keys)

    @property
    def collection_(self) -> Expression:
        """
        The collection to be indexed; same as :attr:`prefix_`.
        """
        return self.prefix_


#
# Lambda
#


@inheritdoc(match="[see superclass]")
class Lambda(SimplePrefixExpression):
    """
    A lambda expression.
    """

    _PRECEDENCE = UnaryOperator.LAMBDA.precedence

    def __init__(self, *params: Id, body: Any) -> None:
        """
        :param params: the parameters of the lambda expression
        :param body: the body of the lambda expression
        """
        super().__init__(prefix=Epsilon(), body=LambdaDefinition(*params, body=body))
        self._has_params = len(params) > 0

    @property
    def precedence_(self) -> int:
        """[see superclass]"""
        return Lambda._PRECEDENCE

    @property
    def separator_(self) -> str:
        """[see superclass]"""
        if self._has_params:
            return f"{UnaryOperator.LAMBDA.symbol} "
        else:
            return UnaryOperator.LAMBDA.symbol


#
# Attr
#


class Attr(BinaryOperation):
    """
    The ``….…`` ("dot") operation to reference an attribute of an object.
    """

    def __init__(self, obj: Any, attribute: Union[Id, str]) -> None:
        """
        :param obj: the object whose attribute is referenced
        :param attribute: the name of the attribute being referenced
        """
        if isinstance(attribute, str):
            attribute = Id(attribute)
        elif not isinstance(attribute, cast(type, Id)):
            raise TypeError("arg attribute must be a string or an Identifier")

        if isinstance(obj, Attr):
            sub = obj.subexpressions_
            super().__init__(BinaryOperator.DOT, sub[0], *(sub[1:]), attribute)
        else:
            super().__init__(BinaryOperator.DOT, obj, attribute)


__tracker.validate()

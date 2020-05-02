"""
Basic utilities for constructing complex expressions and rendering them as indented
strings; useful for generating representations of complex Python objects.
"""
from __future__ import annotations

import logging
from abc import ABCMeta, abstractmethod
from typing import *

from gamma.common.expression._representation import ExpressionRepresentation

log = logging.getLogger(__name__)

__all__ = [
    "Expression",
    "Literal",
    "Identifier",
    "Operation",
    "UnaryOperation",
    "Enumeration",
    "KeywordArgument",
    "Call",
]

__OPERATOR_PRECEDENCE_ORDER = (
    {"."},
    {"**"},
    {"~"},
    {"+ x", "- x"},
    {"*", "/", "//", "%"},
    {"+", "-"},
    {"<<", ">>"},
    {"&"},
    {"^"},
    {"|"},
    {"in", "not in", "is", "is not", "<", "<=", ">", ">="},
    {"<>", "!=", "=="},
    {"not x"},
    {"and"},
    {"or"},
    {"lambda"},
    {"=", ":"},
    {","},
)

OPERATOR_PRECEDENCE = {
    operator: priority
    for priority, operators in enumerate(__OPERATOR_PRECEDENCE_ORDER)
    for operator in operators
}

MAX_PRECEDENCE = len(__OPERATOR_PRECEDENCE_ORDER)


class Expression(metaclass=ABCMeta):
    """
    A nested expression
    """

    @staticmethod
    def from_value(value: Any) -> Expression:
        """
        Convert a python object into an expression.

        Conversions:
        - expressions are returned as themselves
        - standard containers are turned into their expression equivalents
        - strings are turned into literals
        - other iterables are turned into a Call expression
        - all other values are turned into literals

        :param value: value to turn into an expression
        :return: the resulting expression
        """

        def _from_collection(values: Iterable) -> Iterable[Expression]:
            return (Expression.from_value(value) for value in values)

        if isinstance(value, Expression):
            return value
        elif isinstance(value, str):
            return Literal(value)
        elif isinstance(value, list):
            return ListExpression(_from_collection(value))
        elif isinstance(value, tuple):
            return TupleExpression(_from_collection(value))
        elif isinstance(value, set):
            return SetExpression(_from_collection(value))
        elif isinstance(value, dict):
            return DictExpression(
                {
                    Expression.from_value(key): Expression.from_value(value)
                    for key, value in value.items()
                }
            )
        elif isinstance(value, Iterable):
            return Call(name=type(value).__name__, *_from_collection(value))
        else:
            return Literal(value)

    @abstractmethod
    def representation(self) -> ExpressionRepresentation:
        """
        Return a nested text representation of this expression
        """
        pass

    def precedence(self) -> int:
        """
        :return: the precedence of this expression, used to determine the need for \
            parentheses
        """
        return -1

    def _subexpression_representation(
        self, subexpression: Expression
    ) -> ExpressionRepresentation:
        subexpression_representation = subexpression.representation()

        if subexpression_representation.prefix and subexpression_representation.suffix:
            # subexpression is already encapsulated, it is safe to use as-is
            return subexpression_representation
        if subexpression.precedence() > self.precedence():
            # if the subexpression takes higher precedence, we need to encapsulate it
            if (
                subexpression_representation.prefix
                or subexpression_representation.suffix
            ):
                # create new representation wrapper to protect existing prefix or suffix
                return ExpressionRepresentation(
                    prefix="(", inner=(subexpression_representation,), suffix=")"
                )
            else:
                # add wrapper to existing representation
                return subexpression_representation.with_wrapper(prefix="(", suffix=")")
        else:
            # subexpression has lower precedence, we can keep it
            return subexpression_representation

    def __repr__(self) -> str:
        return str(self.representation())

    def __add__(self, other: Expression) -> Operation:
        return Operation("+", (self, other))

    def __sub__(self, other: Expression) -> Operation:
        return Operation("-", (self, other))

    def __mul__(self, other: Expression) -> Operation:
        return Operation("*", (self, other))

    def __matmul__(self, other: Expression) -> Operation:
        return Operation("@", (self, other))

    def __truediv__(self, other: Expression) -> Operation:
        return Operation("/", (self, other))

    def __floordiv__(self, other: Expression) -> Operation:
        return Operation("//", (self, other))

    def __mod__(self, other: Expression) -> Operation:
        return Operation("%", (self, other))

    def __pow__(self, power, modulo=None) -> Operation:
        if modulo is not None:
            raise NotImplementedError("modulo is not supported")
        return Operation("**", (self, power))

    def __lshift__(self, other: Expression) -> Operation:
        return Operation("<<", (self, other))

    def __rshift__(self, other: Expression) -> Operation:
        return Operation(">>", (self, other))

    def __and__(self, other: Expression) -> Operation:
        return Operation("&", (self, other))

    def __xor__(self, other: Expression) -> Operation:
        return Operation("^", (self, other))

    def __or__(self, other: Expression) -> Operation:
        return Operation("|", (self, other))

    def __neg__(self) -> UnaryOperation:
        return UnaryOperation("-", self)

    def __pos__(self) -> UnaryOperation:
        return UnaryOperation("+", self)

    def __invert__(self) -> UnaryOperation:
        return UnaryOperation("~", self)


class Literal(Expression):
    """
    A literal
    """

    def __init__(self, value: Any):
        self.value = value

    # noinspection PyMissingOrEmptyDocstring
    def representation(self) -> ExpressionRepresentation:
        return ExpressionRepresentation(repr(self.value))

    representation.__doc__ = Expression.representation.__doc__


class Identifier(Expression):
    """
    An identifier
    """

    def __init__(self, name: str):
        if not isinstance(name, str):
            raise ValueError("arg name must be a string")
        self.name = name

    def __call__(self, *args: Expression, **kwargs: Expression) -> Call:
        return Call(name=self.name, *args, **kwargs)

    # noinspection PyMissingOrEmptyDocstring
    def representation(self) -> ExpressionRepresentation:
        return ExpressionRepresentation(self.name)

    representation.__doc__ = Expression.representation.__doc__


class BaseOperation(Expression, metaclass=ABCMeta):
    """
    Abstract base class for operation expressions
    """

    def __init__(self, operator: str) -> None:
        if len(operator.split()) > 1:
            raise ValueError("operator must not contain whitespace")
        self.operator = operator

    # noinspection PyMissingOrEmptyDocstring
    def precedence(self) -> int:
        return _operator_precedence(self.operator)

    precedence.__doc__ = Expression.precedence.__doc__


class Operation(BaseOperation):
    """
    A operation with at least two operands
    """

    def __init__(self, operator: str, subexpressions: Tuple[Expression, ...]):
        super().__init__(operator=operator)
        if len(subexpressions) < 2:
            raise ValueError("need to pass at least two subexpressions")
        if not all(isinstance(expression, Expression) for expression in subexpressions):
            raise ValueError("all subexpressions must implement class Expression")

        first_subexpression = subexpressions[0]
        if (
            isinstance(first_subexpression, Operation)
            and first_subexpression.operator == operator
        ):
            # if first subexpression has the same operator, we flatten the subexpression
            self.subexpressions = (
                *first_subexpression.subexpressions,
                *subexpressions[1:],
            )
        else:
            self.subexpressions = subexpressions

    # noinspection PyMissingOrEmptyDocstring
    def representation(self) -> ExpressionRepresentation:
        return ExpressionRepresentation(
            infix=self.operator,
            inner=tuple(
                self._subexpression_representation(subexpression=subexpression)
                for subexpression in self.subexpressions
            ),
        )

    representation.__doc__ = Expression.representation.__doc__


class UnaryOperation(BaseOperation):
    """
    A unary operation
    """

    def __init__(self, operator: str, subexpression: Expression):
        super().__init__(operator=operator)
        if not isinstance(subexpression, Expression):
            raise ValueError("subexpression must implement class Expression")

        self.subexpression = subexpression

    # noinspection PyMissingOrEmptyDocstring
    def precedence(self) -> int:
        return OPERATOR_PRECEDENCE.get(f"{self.operator} x", MAX_PRECEDENCE)

    precedence.__doc__ = Expression.precedence.__doc__

    # noinspection PyMissingOrEmptyDocstring
    def representation(self) -> ExpressionRepresentation:
        return ExpressionRepresentation(
            prefix=self.operator,
            inner=(self._subexpression_representation(self.subexpression),),
        )

    representation.__doc__ = Expression.representation.__doc__


class Enumeration(Expression):
    """
    An enumeration of expressions, separated by commas
    """

    _PRECEDENCE = OPERATOR_PRECEDENCE[","]

    def __init__(
        self, delimiter_left: str, elements: Iterable[Expression], delimiter_right: str
    ) -> None:
        if not isinstance(elements, tuple):
            elements = tuple(elements)
        if not all(isinstance(element, Expression) for element in elements):
            raise ValueError("all elements must implement class Expression")
        self.delimiter_left = delimiter_left
        self.delimiter_right = delimiter_right
        self.elements = elements

    # noinspection PyMissingOrEmptyDocstring
    def representation(self) -> ExpressionRepresentation:
        return ExpressionRepresentation(
            prefix=self.delimiter_left,
            inner=tuple(
                self._subexpression_representation(element) for element in self.elements
            ),
            infix=",",
            infix_keep_with_left=True,
            suffix=self.delimiter_right,
        )

    representation.__doc__ = Expression.representation.__doc__

    # noinspection PyMissingOrEmptyDocstring
    def precedence(self) -> int:
        return self._PRECEDENCE

    precedence.__doc__ = Expression.precedence.__doc__


class KeywordArgument(BaseOperation):
    """
    A keyword argument, used by functions
    """

    def __init__(self, name: str, value: Expression):
        super().__init__("=")
        self.name = name
        self.value = value

    # noinspection PyMissingOrEmptyDocstring
    def representation(self) -> ExpressionRepresentation:
        return ExpressionRepresentation(
            infix=self.operator,
            inner=(
                Identifier(self.name).representation(),
                self._subexpression_representation(self.value),
            ),
            infix_spacing=False,
        )

    representation.__doc__ = Expression.representation.__doc__


class DictEntry(BaseOperation):
    """
    A keyword argument, used by functions
    """

    def __init__(self, key: Expression, value: Expression):
        super().__init__(":")
        self.key = key
        self.value = value

    # noinspection PyMissingOrEmptyDocstring
    def representation(self) -> ExpressionRepresentation:
        return ExpressionRepresentation(
            infix=self.operator,
            inner=(
                self._subexpression_representation(self.key),
                self._subexpression_representation(self.value),
            ),
            infix_keep_with_left=True,
            infix_spacing=False,
        )

    representation.__doc__ = Expression.representation.__doc__


class Call(Enumeration):
    """
    A function invocation
    """

    def __init__(self, name: str, *args: Expression, **kwargs: Expression):
        super().__init__(
            delimiter_left=f"{name}(",
            elements=(
                *args,
                *(
                    KeywordArgument(name, expression)
                    for name, expression in kwargs.items()
                ),
            ),
            delimiter_right=")",
        )
        self.name = name


class ListExpression(Enumeration):
    """
    A list of expressions
    """

    def __init__(self, values: Iterable[Expression]):
        super().__init__(delimiter_left="[", elements=values, delimiter_right="]")


class TupleExpression(Enumeration):
    """
    A list of expressions
    """

    def __init__(self, values: Iterable[Expression]):
        super().__init__(delimiter_left="(", elements=values, delimiter_right=")")


class SetExpression(Enumeration):
    """
    A list of expressions
    """

    def __init__(self, values: Iterable[Expression]):
        super().__init__(delimiter_left="{", elements=values, delimiter_right="}")


class DictExpression(Enumeration):
    """
    A list of expressions
    """

    def __init__(self, entries: Dict[Expression, Expression]):
        super().__init__(
            delimiter_left="{",
            elements=tuple(DictEntry(key, value) for key, value in entries.items()),
            delimiter_right="}",
        )


def _operator_precedence(operator: str):
    return OPERATOR_PRECEDENCE.get(operator, MAX_PRECEDENCE)

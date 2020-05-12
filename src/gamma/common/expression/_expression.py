"""
Basic utilities for constructing complex expressions and rendering them as indented
strings; useful for generating representations of complex Python objects.
"""
from __future__ import annotations

import logging
from abc import ABCMeta, abstractmethod
from typing import Any, Dict, Iterable

from gamma.common.expression._representation import ExpressionRepresentation

log = logging.getLogger(__name__)

__all__ = [
    "HasExpressionRepr",
    "Expression",
    "Literal",
    "Identifier",
    "Operation",
    "UnaryOperation",
    "Call",
    "ListExpression",
    "TupleExpression",
    "SetExpression",
    "DictExpression",
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


class HasExpressionRepr(metaclass=ABCMeta):
    """
    Mix-in class for classes whose `repr` representations are rendered as expressions
    """

    @abstractmethod
    def to_expression(self) -> Expression:
        """
        Render this object as an expression
        :return: the expression representing this object
        """
        pass

    def __repr__(self) -> str:
        return repr(self.to_expression())


class Expression(HasExpressionRepr, metaclass=ABCMeta):
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
            return (Expression.from_value(_value) for _value in values)

        if isinstance(value, HasExpressionRepr):
            return value.to_expression()
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

    def to_expression(self) -> Expression:
        """
        Return self
        :return: `self`
        """
        return self

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
        self, subexpression: Expression, encapsulate_on_same_precedence: bool = True
    ) -> ExpressionRepresentation:
        subexpression_representation = subexpression.representation()

        if subexpression_representation.prefix and subexpression_representation.suffix:
            # operand is already encapsulated, it is safe to use as-is
            return subexpression_representation
        subexpression_precedence = subexpression.precedence()
        self_precedence = self.precedence()
        if subexpression_precedence > self_precedence or (
            encapsulate_on_same_precedence
            and subexpression_precedence == self_precedence
        ):
            # if the operand takes same or higher precedence, we need to encapsulate it
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
            # operand has lower precedence, we can keep it
            return subexpression_representation

    def __repr__(self) -> str:
        return repr(self.representation())

    @abstractmethod
    def __eq__(self, other) -> bool:
        pass

    @abstractmethod
    def __hash__(self) -> int:
        pass

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

    def __eq__(self, other: Literal) -> bool:
        return isinstance(other, type(self)) and other.value == self.value

    def __hash__(self) -> int:
        return hash((type(self), self.value))


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

    def __eq__(self, other: Identifier) -> bool:
        return isinstance(other, type(self)) and other.name == self.name

    def __hash__(self) -> int:
        return hash((type(self), self.name))


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

    def __eq__(self, other: BaseOperation) -> bool:
        return isinstance(other, type(self)) and other.operator == self.operator

    def __hash__(self) -> int:
        return hash((type(self), self.operator))


class Operation(BaseOperation):
    """
    A operation with at least two operands
    """

    def __init__(self, operator: str, operands: Iterable[Expression, ...]):
        super().__init__(operator=operator)
        if not isinstance(operands, tuple):
            operands = tuple(operands)
        if len(operands) < 2:
            raise ValueError("need to pass at least two operands")
        if not all(isinstance(expression, Expression) for expression in operands):
            raise ValueError("all operands must implement class Expression")

        first_operand = operands[0]
        if isinstance(first_operand, Operation) and first_operand.operator == operator:
            # if first operand has the same operator, we flatten the operand
            self.operands = (*first_operand.operands, *operands[1:])
        else:
            self.operands = operands

    # noinspection PyMissingOrEmptyDocstring
    def representation(self) -> ExpressionRepresentation:
        return ExpressionRepresentation(
            infix=self.operator,
            inner=tuple(
                self._subexpression_representation(
                    subexpression=operand, encapsulate_on_same_precedence=(pos > 0)
                )
                for pos, operand in enumerate(self.operands)
            ),
        )

    representation.__doc__ = Expression.representation.__doc__

    def __eq__(self, other: Operation) -> bool:
        return super().__eq__(other) and self.operands == other.operands

    def __hash__(self) -> int:
        return hash((super().__hash__(), self.operands))


class UnaryOperation(BaseOperation):
    """
    A unary operation
    """

    def __init__(self, operator: str, operand: Expression):
        super().__init__(operator=operator)
        if not isinstance(operand, Expression):
            raise ValueError("operand must implement class Expression")

        self.operand = operand

    # noinspection PyMissingOrEmptyDocstring
    def precedence(self) -> int:
        return OPERATOR_PRECEDENCE.get(f"{self.operator} x", MAX_PRECEDENCE)

    precedence.__doc__ = Expression.precedence.__doc__

    # noinspection PyMissingOrEmptyDocstring
    def representation(self) -> ExpressionRepresentation:
        return ExpressionRepresentation(
            prefix=self.operator,
            inner=(self._subexpression_representation(self.operand),),
        )

    representation.__doc__ = Expression.representation.__doc__

    def __eq__(self, other: UnaryOperation) -> bool:
        return super().__eq__(other) and self.operand == other.operand

    def __hash__(self) -> int:
        return hash((super().__hash__(), self.operand))


class BaseEnumeration(Expression):
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

    def __eq__(self, other: BaseEnumeration) -> bool:
        return (
            isinstance(other, type(self))
            and self.delimiter_left == other.delimiter_left
            and self.delimiter_right == other.delimiter_right
            and self.elements == other.elements
        )

    def __hash__(self) -> int:
        return hash(
            (
                super().__hash__(),
                self.delimiter_left,
                self.elements,
                self.delimiter_right,
            )
        )


class _KeywordArgument(Expression):
    """
    A keyword argument, used by functions
    """

    def __init__(self, name: str, value: Expression):
        self.name = name
        self.value = value

    # noinspection PyMissingOrEmptyDocstring
    def representation(self) -> ExpressionRepresentation:
        return ExpressionRepresentation(
            prefix=f"{self.name}=", inner=(self.value.representation(),)
        )

    representation.__doc__ = Expression.representation.__doc__

    def __eq__(self, other: _KeywordArgument) -> bool:
        return (
            isinstance(other, type(self))
            and self.name == other.name
            and self.value == other.value
        )

    def __hash__(self) -> int:
        return hash((super().__hash__(), self.name, self.value))


class _DictEntry(BaseOperation):
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
        )

    representation.__doc__ = Expression.representation.__doc__

    def __eq__(self, other: _KeywordArgument) -> bool:
        return (
            isinstance(other, type(self))
            and self.key == other.key
            and self.value == other.value
        )

    def __hash__(self) -> int:
        return hash((super().__hash__(), self.key, self.value))


class Call(BaseEnumeration):
    """
    A function invocation
    """

    def __init__(self, name: str, *args: Expression, **kwargs: Expression):
        super().__init__(
            delimiter_left=f"{name}(",
            elements=(
                *args,
                *(
                    _KeywordArgument(name, expression)
                    for name, expression in kwargs.items()
                ),
            ),
            delimiter_right=")",
        )

    @property
    def name(self) -> str:
        """
        the name of the function being called
        :return: the name of the function being called
        """
        return self.delimiter_left[:-1]


class ListExpression(BaseEnumeration):
    """
    A list of expressions
    """

    def __init__(self, elements: Iterable[Expression]):
        super().__init__(delimiter_left="[", elements=elements, delimiter_right="]")


class TupleExpression(BaseEnumeration):
    """
    A list of expressions
    """

    def __init__(self, elements: Iterable[Expression]):
        super().__init__(delimiter_left="(", elements=elements, delimiter_right=")")


class SetExpression(BaseEnumeration):
    """
    A list of expressions
    """

    def __init__(self, elements: Iterable[Expression]):
        super().__init__(delimiter_left="{", elements=elements, delimiter_right="}")


class DictExpression(BaseEnumeration):
    """
    A list of expressions
    """

    def __init__(self, entries: Dict[Expression, Expression]):
        super().__init__(
            delimiter_left="{",
            elements=tuple(_DictEntry(key, value) for key, value in entries.items()),
            delimiter_right="}",
        )


def _operator_precedence(operator: str):
    return OPERATOR_PRECEDENCE.get(operator, MAX_PRECEDENCE)

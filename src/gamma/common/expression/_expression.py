"""
Basic utilities for constructing complex expressions and rendering them as indented
strings; useful for generating representations of complex Python objects.
"""
from __future__ import annotations

import logging
from abc import ABCMeta, abstractmethod
from typing import *

log = logging.getLogger(__name__)

__all__ = [
    "IndentedText",
    "Expression",
    "Literal",
    "Identifier",
    "Operation",
    "UnaryOperation",
    "Enumeration",
    "Function",
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
    {"="},
    {","},
)

OPERATOR_PRECEDENCE = {
    operator: priority
    for priority, operators in enumerate(__OPERATOR_PRECEDENCE_ORDER)
    for operator in operators
}

MAX_PRECEDENCE = len(__OPERATOR_PRECEDENCE_ORDER)


class IndentedText(NamedTuple):
    """
    An indented line of text
    """

    indent: int
    text: str


class Expression(metaclass=ABCMeta):
    """
    A nested expression
    """

    @abstractmethod
    def walk(self, indent: int = 0) -> Generator[IndentedText, None, int]:
        """
        Generate all elements of this expression
        :param indent: the outermost indentation level of the expression
        :return: the number of characters in the expression, excluding indentation
        """
        pass

    def _walk_subexpression(
        self, parent_indent: int, subexpression: Expression
    ) -> Generator[IndentedText, None, int]:
        if subexpression.precedence() >= self.precedence():
            yield IndentedText(indent=parent_indent, text="(")
            len_subexpression = yield from subexpression.walk(indent=parent_indent + 1)
            yield IndentedText(indent=parent_indent, text=")")
            return len_subexpression + 2
        else:
            return (yield from subexpression.walk(indent=parent_indent))

    def precedence(self) -> int:
        """
        :return: the precedence of this expression, used to determine the need for \
            parentheses
        """
        return -1

    def __repr__(self) -> str:
        return "\n".join(" " * element.indent + element.text for element in self.walk())

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
    def walk(self, indent: int = 0) -> Generator[IndentedText, None, int]:
        text = repr(self.value)
        yield IndentedText(indent=indent, text=text)
        return len(text)

    walk.__doc__ = Expression.walk.__doc__


class Identifier(Expression):
    """
    An identifier
    """

    def __init__(self, name: str):
        if not isinstance(name, str):
            raise ValueError("arg name must be a string")
        self.name = name

    def __call__(self, *args: Expression, **kwargs: Expression) -> Function:
        return Function(name=self.name, *args, **kwargs)

    # noinspection PyMissingOrEmptyDocstring
    def walk(self, indent: int = 0) -> Generator[IndentedText, None, int]:
        yield IndentedText(indent=indent, text=self.name)
        return len(self.name)

    walk.__doc__ = Expression.walk.__doc__


class BaseOperation(Expression, metaclass=ABCMeta):
    """
    Abstract base class for operation expressions
    """

    def __init__(self, operator: str) -> None:
        if len(operator.split()) > 1:
            raise ValueError("operator must not contain whitespace")
        self.operator = operator


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
    def precedence(self) -> int:
        return OPERATOR_PRECEDENCE.get(self.operator, MAX_PRECEDENCE)

    precedence.__doc__ = Expression.precedence.__doc__

    # noinspection PyMissingOrEmptyDocstring
    def walk(self, indent: int = 0) -> Generator[IndentedText, None, int]:
        subexpressions = self.subexpressions
        if len(subexpressions) == 1:
            return (yield from subexpressions[0].walk(indent=indent))
        else:
            not_first = False
            length = 0
            for subexpression in subexpressions:
                if not_first:
                    yield IndentedText(indent=indent, text=self.operator)
                    length += 2 + len(self.operator)  # count spaces left and right
                not_first = True
                length += yield from self._walk_subexpression(
                    parent_indent=indent, subexpression=subexpression
                )
            return length

    walk.__doc__ = Expression.walk.__doc__


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
    def walk(self, indent: int = 0) -> Generator[IndentedText, None, int]:
        yield IndentedText(indent=indent, text=self.operator)
        return len(self.operator) + (
            yield from self._walk_subexpression(
                parent_indent=indent, subexpression=self.subexpression
            )
        )

    walk.__doc__ = Expression.walk.__doc__


class Enumeration(Expression):
    """
    An enumeration of expressions, separated by commas
    """

    _PRECEDENCE = OPERATOR_PRECEDENCE[","]

    def __init__(
        self,
        delimiter_left: str,
        elements: Tuple[Expression, ...],
        delimiter_right: str,
    ) -> None:
        if not all(isinstance(element, Expression) for element in elements):
            raise ValueError("all elements must implement class Expression")
        self.delimiter_left = delimiter_left
        self.delimiter_right = delimiter_right
        self.elements = elements

    # noinspection PyMissingOrEmptyDocstring
    def walk(self, indent: int = 0) -> Generator[IndentedText, None, int]:
        length = len(self.delimiter_left) + len(self.delimiter_right)
        yield IndentedText(indent=indent, text=self.delimiter_left)
        elements = self.elements
        if elements:
            elements_indent = indent + 1
            length += yield from self._walk_subexpression(
                parent_indent=elements_indent, subexpression=elements[0]
            )
            for element in elements[1:]:
                yield IndentedText(indent=elements_indent, text=", ")
                length += 2 + (
                    yield from self._walk_subexpression(
                        parent_indent=elements_indent, subexpression=element
                    )
                )
        yield IndentedText(indent=indent, text=self.delimiter_right)
        return length

    walk.__doc__ = Expression.walk.__doc__

    # noinspection PyMissingOrEmptyDocstring
    def precedence(self) -> int:
        return self._PRECEDENCE

    precedence.__doc__ = Expression.precedence.__doc__


class _KeywordArgument(Operation):
    """
    A keyword argument, used by functions
    """

    def __init__(self, name: str, value: Expression):
        super().__init__(operator="=", subexpressions=(Identifier(name), value))


class Function(Enumeration):
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
        self.name = name


def main() -> None:
    """
    Basic tests
    Todo: convert into unit tests
    """
    e = Function(
        "f",
        (Literal(1) | Literal(2)) >> Literal("x") % Identifier("x"),
        abc=-Literal(5),
    )
    print(e)


if __name__ == "__main__":
    main()

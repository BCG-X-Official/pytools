"""
Basic utilities for constructing complex expressions and rendering them as indented
strings; useful for generating representations of complex Python objects.
"""
import logging
from abc import ABCMeta, abstractmethod
from typing import Any, Dict, Iterable, Optional, Tuple

from gamma.common import AllTracker

log = logging.getLogger(__name__)

__all__ = [
    "ExpressionFormatter",
    "HasExpressionRepr",
    "Expression",
    "Literal",
    "Identifier",
    "BaseOperation",
    "Operation",
    "UnaryOperation",
    "BaseEnumeration",
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


__tracker = AllTracker((globals()))


class ExpressionFormatter(metaclass=ABCMeta):
    """
    An expression formatter produces text representations of expressions.
    """

    __default_format: Optional["ExpressionFormatter"] = None

    @abstractmethod
    def to_text(self, expression: "Expression") -> str:
        """
        Construct a text representation of the given expression.

        :return: a text representation of the expression
        """
        pass

    @staticmethod
    def default() -> "ExpressionFormatter":
        """
        Get the default expression format.
        """
        return ExpressionFormatter.__default_format

    @staticmethod
    def _register_default_format(expression_format: "ExpressionFormatter") -> None:
        if ExpressionFormatter.__default_format is not None:
            raise RuntimeError("default format is already registered")
        ExpressionFormatter.__default_format = expression_format


class HasExpressionRepr(metaclass=ABCMeta):
    """
    Mix-in class for classes whose `repr` representations are rendered as expressions
    """

    @abstractmethod
    def to_expression(self) -> "Expression":
        """
        Render this object as an expression
        :return: the expression representing this object
        """
        pass

    def __repr__(self) -> str:
        # get the expression representing this object, and use the default formatter
        # to get a text representation of the expression
        return ExpressionFormatter.default().to_text(self.to_expression())


class Expression(HasExpressionRepr, metaclass=ABCMeta):
    """
    A nested expression
    """

    @staticmethod
    def from_value(value: Any) -> "Expression":
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

    @property
    def prefix(self) -> str:
        """
        The prefix of this expression
        """
        return ""

    @property
    def brackets(self) -> Optional[Tuple[str, str]]:
        """
        The brackets surrounding this expression's subexpressions.

        A value of `None` indicates no brackets.
        """
        return None

    @property
    def infix(self) -> str:
        """
        The infix used to separate this expression's subexpressions.
        """
        return ""

    @property
    def subexpressions(self) -> Tuple["Expression", ...]:
        """
        The subexpressions of this expression.
        """
        return ()

    def to_expression(self) -> "Expression":
        """
        Return self
        :return: `self`
        """
        return self

    def precedence(self) -> int:
        """
        :return: the precedence of this expression, used to determine the need for \
            parentheses
        """
        return -1

    @abstractmethod
    def __eq__(self, other) -> bool:
        pass

    @abstractmethod
    def __hash__(self) -> int:
        pass

    def __add__(self, other: "Expression") -> "Operation":
        return Operation("+", (self, other))

    def __sub__(self, other: "Expression") -> "Operation":
        return Operation("-", (self, other))

    def __mul__(self, other: "Expression") -> "Operation":
        return Operation("*", (self, other))

    def __matmul__(self, other: "Expression") -> "Operation":
        return Operation("@", (self, other))

    def __truediv__(self, other: "Expression") -> "Operation":
        return Operation("/", (self, other))

    def __floordiv__(self, other: "Expression") -> "Operation":
        return Operation("//", (self, other))

    def __mod__(self, other: "Expression") -> "Operation":
        return Operation("%", (self, other))

    def __pow__(self, power, modulo=None) -> "Operation":
        if modulo is not None:
            raise NotImplementedError("modulo is not supported")
        return Operation("**", (self, power))

    def __lshift__(self, other: "Expression") -> "Operation":
        return Operation("<<", (self, other))

    def __rshift__(self, other: "Expression") -> "Operation":
        return Operation(">>", (self, other))

    def __and__(self, other: "Expression") -> "Operation":
        return Operation("&", (self, other))

    def __xor__(self, other: "Expression") -> "Operation":
        return Operation("^", (self, other))

    def __or__(self, other: "Expression") -> "Operation":
        return Operation("|", (self, other))

    def __neg__(self) -> "UnaryOperation":
        return UnaryOperation("-", self)

    def __pos__(self) -> "UnaryOperation":
        return UnaryOperation("+", self)

    def __invert__(self) -> "UnaryOperation":
        return UnaryOperation("~", self)


class Literal(Expression):
    """
    A literal
    """

    def __init__(self, value: Any):
        self.value = value

    @property
    def prefix(self) -> str:
        """[see superclass]"""
        return repr(self.value)

    prefix.__doc__ = Expression.prefix.__doc__

    def __eq__(self, other: "Literal") -> bool:
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

    @property
    def prefix(self) -> str:
        """[see superclass]"""
        return self.name

    prefix.__doc__ = Expression.prefix.__doc__

    def __call__(self, *args: Expression, **kwargs: Expression) -> "Call":
        return Call(name=self.name, *args, **kwargs)

    def __eq__(self, other: "Identifier") -> bool:
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
        return OPERATOR_PRECEDENCE.get(self.operator, MAX_PRECEDENCE)

    precedence.__doc__ = Expression.precedence.__doc__

    def __eq__(self, other: "BaseOperation") -> bool:
        return isinstance(other, type(self)) and other.operator == self.operator

    def __hash__(self) -> int:
        return hash((type(self), self.operator))


class Operation(BaseOperation):
    """
    A operation with at least two operands
    """

    def __init__(self, operator: str, operands: Iterable[Expression]):
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

    @property
    def infix(self) -> str:
        """[see superclass]"""
        return self.operator

    infix.__doc__ = Expression.infix.__doc__

    @property
    def subexpressions(self) -> Tuple["Expression", ...]:
        """[see superclass]"""
        return self.operands

    subexpressions.__doc__ = Expression.subexpressions.__doc__

    def __eq__(self, other: "Operation") -> bool:
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

    @property
    def prefix(self) -> str:
        """[see superclass]"""
        return self.operator

    prefix.__doc__ = Expression.prefix.__doc__

    @property
    def subexpressions(self) -> Tuple["Expression", ...]:
        """[see superclass]"""
        return (self.operand,)

    subexpressions.__doc__ = Expression.subexpressions.__doc__

    # noinspection PyMissingOrEmptyDocstring
    def precedence(self) -> int:
        return OPERATOR_PRECEDENCE.get(f"{self.operator} x", MAX_PRECEDENCE)

    precedence.__doc__ = Expression.precedence.__doc__

    def __eq__(self, other: "UnaryOperation") -> bool:
        return super().__eq__(other) and self.operand == other.operand

    def __hash__(self) -> int:
        return hash((super().__hash__(), self.operand))


class BaseEnumeration(Expression):
    """
    An enumeration of expressions, separated by commas
    """

    _PRECEDENCE = OPERATOR_PRECEDENCE[","]

    def __init__(
        self,
        *,
        brackets: Tuple[str, str],
        elements: Iterable[Expression],
        prefix: str = "",
    ) -> None:
        if not isinstance(elements, tuple):
            elements = tuple(elements)
        if not all(isinstance(element, Expression) for element in elements):
            raise ValueError("all elements must implement class Expression")
        self._prefix = prefix
        self._brackets = brackets
        self.elements = elements

    @property
    def prefix(self) -> str:
        """[see superclass]"""
        return self._prefix

    prefix.__doc__ = Expression.prefix.__doc__

    @property
    def brackets(self) -> Tuple[str, str]:
        """[see superclass]"""
        return self._brackets

    brackets.__doc__ = Expression.brackets.__doc__

    @property
    def infix(self) -> str:
        """[see superclass]"""
        return ","

    infix.__doc__ = Expression.infix.__doc__

    @property
    def subexpressions(self) -> Tuple["Expression", ...]:
        """[see superclass]"""
        return self.elements

    subexpressions.__doc__ = Expression.subexpressions.__doc__

    # noinspection PyMissingOrEmptyDocstring
    def precedence(self) -> int:
        return self._PRECEDENCE

    precedence.__doc__ = Expression.precedence.__doc__

    def __eq__(self, other: "BaseEnumeration") -> bool:
        return (
            isinstance(other, type(self))
            and self.prefix == other.prefix
            and self.brackets == other.brackets
            and self.elements == other.elements
        )

    def __hash__(self) -> int:
        return hash((super().__hash__(), self.prefix, self.brackets, self.elements))


class _KeywordArgument(Expression):
    """
    A keyword argument, used by functions
    """

    def __init__(self, name: str, value: Expression):
        self.name = name
        self.value = value

    @property
    def prefix(self) -> str:
        """[see superclass]"""
        return f"{self.name}="

    prefix.__doc__ = Expression.prefix.__doc__

    @property
    def subexpressions(self) -> Tuple["Expression", ...]:
        """[see superclass]"""
        return (self.value,)

    subexpressions.__doc__ = Expression.subexpressions.__doc__

    def __eq__(self, other: "_KeywordArgument") -> bool:
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

    @property
    def infix(self) -> str:
        """[see superclass]"""
        return self.operator

    infix.__doc__ = Expression.infix.__doc__

    @property
    def subexpressions(self) -> Tuple["Expression", ...]:
        """[see superclass]"""
        return self.key, self.value

    subexpressions.__doc__ = Expression.subexpressions.__doc__

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
            prefix=name,
            brackets=("(", ")"),
            elements=(
                *args,
                *(
                    _KeywordArgument(name, expression)
                    for name, expression in kwargs.items()
                ),
            ),
        )

    @property
    def name(self) -> str:
        """
        the name of the function being called
        :return: the name of the function being called
        """
        return self.prefix


class ListExpression(BaseEnumeration):
    """
    A list of expressions
    """

    def __init__(self, elements: Iterable[Expression]):
        super().__init__(brackets=("[", "]"), elements=elements)


class TupleExpression(BaseEnumeration):
    """
    A list of expressions
    """

    def __init__(self, elements: Iterable[Expression]):
        super().__init__(brackets=("(", ")"), elements=elements)


class SetExpression(BaseEnumeration):
    """
    A list of expressions
    """

    def __init__(self, elements: Iterable[Expression]):
        super().__init__(brackets=("{", "}"), elements=elements)


class DictExpression(BaseEnumeration):
    """
    A list of expressions
    """

    def __init__(self, entries: Dict[Expression, Expression]):
        super().__init__(
            brackets=("{", "}"),
            elements=tuple(_DictEntry(key, value) for key, value in entries.items()),
        )


__tracker.validate()

"""
Basic utilities for constructing complex expressions and rendering them as indented
strings; useful for generating representations of complex Python objects.
"""
import logging
from abc import ABCMeta, abstractmethod
from typing import Any, Dict, Iterable, Optional, Tuple, Union

from gamma.common import AllTracker, to_tuple

log = logging.getLogger(__name__)

__all__ = [
    "ExpressionFormatter",
    "HasExpressionRepr",
    "Expression",
    "AtomicExpression",
    "ComplexExpression",
    "Literal",
    "Identifier",
    "BaseOperation",
    "BaseInfixOperation",
    "Operation",
    "UnaryOperation",
    "BaseEnumeration",
    "Call",
    "Index",
    "ListExpression",
    "TupleExpression",
    "SetExpression",
    "DictExpression",
    "Attr",
    "Lambda",
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
    {"lambda x"},
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
            return Call(
                callee=Identifier(type(value).__name__), *_from_collection(value)
            )
        else:
            return Literal(value)

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

    def __call__(self, *args: Any, **kwargs: Any) -> "Call":
        return Call(
            callee=self,
            *(Expression.from_value(arg) for arg in args),
            **{k: Expression.from_value(v) for k, v in kwargs.items()},
        )

    def __getitem__(self, *args: "Expression") -> "Index":
        return Index(callee=self, *args)


class AtomicExpression(Expression):
    @property
    @abstractmethod
    def text(self) -> str:
        pass


class ComplexExpression(Expression):
    @property
    def prefix(self) -> Optional[Expression]:
        """
        The prefix of this expression
        """
        return None

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
    def subexpressions(self) -> Tuple[Expression, ...]:
        """
        The subexpressions of this expression.
        """
        return ()


class Literal(AtomicExpression):
    """
    A literal
    """

    def __init__(self, value: Any):
        self.value = value

    @property
    def text(self) -> str:
        """[see superclass]"""
        return repr(self.value)

    text.__doc__ = AtomicExpression.text.__doc__

    def __eq__(self, other: "Literal") -> bool:
        return isinstance(other, type(self)) and other.value == self.value

    def __hash__(self) -> int:
        return hash((type(self), self.value))


class Identifier(AtomicExpression):
    """
    An identifier
    """

    def __init__(self, name: str):
        if not isinstance(name, str):
            raise ValueError("arg name must be a string")
        self.name = name

    @property
    def text(self) -> str:
        """[see superclass]"""
        return self.name

    text.__doc__ = AtomicExpression.text.__doc__

    def __eq__(self, other: "Identifier") -> bool:
        return isinstance(other, type(self)) and other.name == self.name

    def __hash__(self) -> int:
        return hash((type(self), self.name))


class BaseOperation(ComplexExpression, metaclass=ABCMeta):
    """
    Abstract base class for operation expressions
    """

    def __init__(self, operator: str) -> None:
        if len(operator.split()) > 1:
            raise ValueError("operator must not contain whitespace")
        self.operator = operator

    def __eq__(self, other: "BaseOperation") -> bool:
        return isinstance(other, type(self)) and other.operator == self.operator

    def __hash__(self) -> int:
        return hash((type(self), self.operator))


class BaseInfixOperation(BaseOperation, metaclass=ABCMeta):
    """
    Abstract base class for operation expressions with an infix operator
    """

    @property
    def infix(self) -> str:
        """[see superclass]"""
        return self.operator

    infix.__doc__ = ComplexExpression.infix.__doc__

    # noinspection PyMissingOrEmptyDocstring
    def precedence(self) -> int:
        return OPERATOR_PRECEDENCE.get(self.operator, MAX_PRECEDENCE)

    precedence.__doc__ = Expression.precedence.__doc__


class Operation(BaseInfixOperation):
    """
    A operation with at least two operands
    """

    def __init__(
        self, operator: str, operands: Union[Expression, Iterable[Expression]]
    ):
        super().__init__(operator=operator)
        operands: Tuple[Expression, ...] = to_tuple(operands)
        if len(operands) < 2:
            raise ValueError("need to pass at least two operands")
        if not all(isinstance(expression, Expression) for expression in operands):
            raise ValueError("all operands must implement class Expression")

        first_operand = operands[0]

        # noinspection PyUnresolvedReferences
        if isinstance(first_operand, Operation) and first_operand.operator == operator:
            # if first operand has the same operator, we flatten the operand
            # noinspection PyUnresolvedReferences
            self.operands = (*first_operand.operands, *operands[1:])
        else:
            self.operands = operands

    @property
    def subexpressions(self) -> Tuple["Expression", ...]:
        """[see superclass]"""
        return self.operands

    subexpressions.__doc__ = ComplexExpression.subexpressions.__doc__

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
    def prefix(self) -> Expression:
        """[see superclass]"""
        return Identifier(self.operator)

    prefix.__doc__ = ComplexExpression.prefix.__doc__

    @property
    def subexpressions(self) -> Tuple["Expression", ...]:
        """[see superclass]"""
        return (self.operand,)

    subexpressions.__doc__ = ComplexExpression.subexpressions.__doc__

    # noinspection PyMissingOrEmptyDocstring
    def precedence(self) -> int:
        return OPERATOR_PRECEDENCE.get(f"{self.operator} x", MAX_PRECEDENCE)

    precedence.__doc__ = Expression.precedence.__doc__

    def __eq__(self, other: "UnaryOperation") -> bool:
        return super().__eq__(other) and self.operand == other.operand

    def __hash__(self) -> int:
        return hash((super().__hash__(), self.operand))


class BaseEnumeration(ComplexExpression, metaclass=ABCMeta):
    """
    An enumeration of expressions, separated by commas
    """

    _PRECEDENCE = OPERATOR_PRECEDENCE[","]

    def __init__(
        self,
        *,
        prefix: Optional[Expression] = None,
        brackets: Tuple[str, str],
        elements: Iterable[Expression],
    ) -> None:
        self._prefix = prefix
        self._brackets = brackets
        self.elements = to_tuple(elements, element_type=Expression)

    @property
    def prefix(self) -> Expression:
        """[see superclass]"""
        return self._prefix

    prefix.__doc__ = ComplexExpression.prefix.__doc__

    @property
    def brackets(self) -> Tuple[str, str]:
        """[see superclass]"""
        return self._brackets

    brackets.__doc__ = ComplexExpression.brackets.__doc__

    @property
    def infix(self) -> str:
        """[see superclass]"""
        return ","

    infix.__doc__ = ComplexExpression.infix.__doc__

    @property
    def subexpressions(self) -> Tuple["Expression", ...]:
        """[see superclass]"""
        return self.elements

    subexpressions.__doc__ = ComplexExpression.subexpressions.__doc__

    # noinspection PyMissingOrEmptyDocstring
    def precedence(self) -> int:
        return BaseEnumeration._PRECEDENCE

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


class _KeywordArgument(ComplexExpression):
    """
    A keyword argument, used by functions
    """

    def __init__(self, name: str, value: Expression):
        self.name = name
        self.value = value

    @property
    def prefix(self) -> Expression:
        """[see superclass]"""
        return Identifier(f"{self.name}=")

    prefix.__doc__ = ComplexExpression.prefix.__doc__

    @property
    def subexpressions(self) -> Tuple["Expression", ...]:
        """[see superclass]"""
        return (self.value,)

    subexpressions.__doc__ = ComplexExpression.subexpressions.__doc__

    def __eq__(self, other: "_KeywordArgument") -> bool:
        return (
            isinstance(other, type(self))
            and self.name == other.name
            and self.value == other.value
        )

    def __hash__(self) -> int:
        return hash((super().__hash__(), self.name, self.value))


class _ColonPair(BaseInfixOperation):
    """
    Two expressions separated by a colon, used in dictionaries and lambda expressions
    """

    def __init__(self, key: Expression, value: Expression):
        super().__init__(":")
        self.key = key
        self.value = value

    @property
    def subexpressions(self) -> Tuple["Expression", ...]:
        """[see superclass]"""
        return self.key, self.value

    subexpressions.__doc__ = ComplexExpression.subexpressions.__doc__

    def __eq__(self, other: "_ColonPair") -> bool:
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

    def __init__(self, callee: Expression, *args: Expression, **kwargs: Expression):
        super().__init__(
            prefix=callee,
            brackets=("(", ")"),
            elements=(
                *args,
                *(
                    _KeywordArgument(name, expression)
                    for name, expression in kwargs.items()
                ),
            ),
        )


class Index(BaseEnumeration):
    """
    An indexing operation in the shape of `x[i]`
    """

    def __init__(self, callee: Expression, *args: Expression):
        super().__init__(prefix=callee, brackets=("[", "]"), elements=args),


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
            elements=tuple(_ColonPair(key, value) for key, value in entries.items()),
        )


class Attr(BaseInfixOperation):
    """
    The "dot" operation to reference an attribute of an object
    """

    def __init__(self, obj: Expression, attribute: Identifier) -> None:
        super().__init__(operator=".")
        self.obj = obj
        self.attribute = attribute

    @property
    def subexpressions(self) -> Tuple[Expression, ...]:
        """
        [see superclass]
        """
        return self.obj, self.attribute

    subexpressions.__doc__ = ComplexExpression.subexpressions.__doc__


class Lambda(UnaryOperation):
    """
    A lambda expression
    """

    def __init__(
        self, variables: Union[Identifier, Iterable[Identifier]], body: Expression
    ):
        super().__init__(
            operator="lambda",
            operand=_ColonPair(
                key=Operation(operator=",", operands=variables), value=body
            ),
        )


__tracker.validate()

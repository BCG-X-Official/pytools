"""
Basic utilities for constructing complex expressions and rendering them as indented
strings; useful for generating representations of complex Python objects.
"""
import logging
from abc import ABCMeta, abstractmethod
from typing import Any, Generic, Iterable, Mapping, Optional, Tuple, TypeVar, Union

from gamma.common import AllTracker, to_tuple

log = logging.getLogger(__name__)

__all__ = [
    "ExpressionFormatter",
    "HasExpressionRepr",
    "Expression",
    "AtomicExpression",
    "Literal",
    "Identifier",
    "EPSILON",
    "BaseOperation",
    "PrefixExpression",
    "BasePrefixExpression",
    "UnaryOperation",
    "BaseInvocation",
    "Call",
    "Index",
    "InfixExpression",
    "Operation",
    "Attr",
    "BracketedExpression",
    "CollectionExpression",
    "ListExpression",
    "TupleExpression",
    "SetExpression",
    "DictExpression",
    "Lambda",
]

__OPERATOR_PRECEDENCE_ORDER = (
    {"."},
    {"**"},
    {"~"},
    {"+x", "-x"},
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

MAX_PRECEDENCE = -1
MIN_PRECEDENCE = len(__OPERATOR_PRECEDENCE_ORDER)

T = TypeVar("T")

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

    @property
    @abstractmethod
    def precedence(self) -> int:
        """
        :return: the precedence of this expression, used to determine the need for \
            parentheses
        """
        pass

    @abstractmethod
    def __eq__(self, other) -> bool:
        pass

    @abstractmethod
    def __hash__(self) -> int:
        pass

    def __add__(self, other: Any) -> "Operation":
        return Operation("+", (self, other))

    def __sub__(self, other: Any) -> "Operation":
        return Operation("-", (self, other))

    def __mul__(self, other: Any) -> "Operation":
        return Operation("*", (self, other))

    def __matmul__(self, other: Any) -> "Operation":
        return Operation("@", (self, other))

    def __truediv__(self, other: Any) -> "Operation":
        return Operation("/", (self, other))

    def __floordiv__(self, other: Any) -> "Operation":
        return Operation("//", (self, other))

    def __mod__(self, other: Any) -> "Operation":
        return Operation("%", (self, other))

    def __pow__(self, power: Any, modulo=None) -> "Operation":
        if modulo is not None:
            raise NotImplementedError("modulo is not supported")
        return Operation("**", (self, power))

    def __lshift__(self, other: Any) -> "Operation":
        return Operation("<<", (self, other))

    def __rshift__(self, other: Any) -> "Operation":
        return Operation(">>", (self, other))

    def __and__(self, other: Any) -> "Operation":
        return Operation("&", (self, other))

    def __xor__(self, other: Any) -> "Operation":
        return Operation("^", (self, other))

    def __or__(self, other: Any) -> "Operation":
        return Operation("|", (self, other))

    def __radd__(self, other: Any) -> "Operation":
        return Operation("+", (other, self))

    def __rsub__(self, other: Any) -> "Operation":
        return Operation("-", (other, self))

    def __rmul__(self, other: Any) -> "Operation":
        return Operation("*", (other, self))

    def __rmatmul__(self, other: Any) -> "Operation":
        return Operation("@", (other, self))

    def __rtruediv__(self, other: Any) -> "Operation":
        return Operation("/", (other, self))

    def __rfloordiv__(self, other: Any) -> "Operation":
        return Operation("//", (other, self))

    def __rmod__(self, other: Any) -> "Operation":
        return Operation("%", (other, self))

    def __rpow__(self, power: Any, modulo=None) -> "Operation":
        if modulo is not None:
            raise NotImplementedError("modulo is not supported")
        return Operation("**", (power, self))

    def __rlshift__(self, other: Any) -> "Operation":
        return Operation("<<", (other, self))

    def __rrshift__(self, other: Any) -> "Operation":
        return Operation(">>", (other, self))

    def __rand__(self, other: Any) -> "Operation":
        return Operation("&", (other, self))

    def __rxor__(self, other: Any) -> "Operation":
        return Operation("^", (other, self))

    def __ror__(self, other: Any) -> "Operation":
        return Operation("|", (other, self))

    def __neg__(self) -> "UnaryOperation":
        return UnaryOperation("-", self)

    def __pos__(self) -> "UnaryOperation":
        return UnaryOperation("+", self)

    def __invert__(self) -> "UnaryOperation":
        return UnaryOperation("~", self)

    def __call__(self, *args: Any, **kwargs: Any) -> "Call":
        _items = {k: Expression.from_value(v) for k, v in kwargs.items()}
        return Call(self, *(Expression.from_value(arg) for arg in args), **_items)

    def __getitem__(self, *args: Any) -> "Index":
        return Index(callee=self, *args)


#
# Atomic expressions
#


class AtomicExpression(Expression, Generic[T], metaclass=ABCMeta):
    """
    An atomic expression.

    Atomic expressions include literals and identifiers, and have no subexpressions.
    """

    @property
    @abstractmethod
    def text(self) -> str:
        """
        The text representing this atomic expression
        """
        pass

    @property
    @abstractmethod
    def value(self) -> T:
        """
        The underlying valye of this atomic expression
        """
        pass

    @property
    def precedence(self) -> int:
        """[see superclass]"""
        return MAX_PRECEDENCE

    precedence.__doc__ = Expression.precedence.__doc__

    def __eq__(self, other: "AtomicExpression") -> bool:
        return isinstance(other, type(self)) and other.value == self.value

    def __hash__(self) -> int:
        return hash((type(self), self.value))


class Literal(AtomicExpression[T], Generic[T]):
    """
    A literal
    """

    def __init__(self, value: T):
        self._value = value

    @property
    def value(self) -> T:
        """[see superclass]"""
        return self._value

    value.__doc__ = AtomicExpression.value.__doc__

    @property
    def text(self) -> str:
        """[see superclass]"""
        return repr(self.value)

    text.__doc__ = AtomicExpression.text.__doc__


class Identifier(AtomicExpression[str]):
    """
    An identifier
    """

    def __init__(self, name: str):
        if not isinstance(name, str):
            raise ValueError("arg name must be a string")
        self.name = name

    @property
    def value(self) -> str:
        """[see superclass]"""
        return self.name

    value.__doc__ = AtomicExpression.value.__doc__

    @property
    def text(self) -> str:
        """[see superclass]"""
        return self.name

    text.__doc__ = AtomicExpression.text.__doc__


class _Epsilon(AtomicExpression[None]):
    """
    The empty expression.
    """

    @property
    def value(self) -> None:
        """[see superclass]"""
        return None

    @property
    def text(self) -> str:
        """[see superclass]"""
        return ""

    text.__doc__ = AtomicExpression.text.__doc__


EPSILON = _Epsilon()


#
# Operations
#


class BaseOperation(metaclass=ABCMeta):
    """
    Abstract base class for operation expressions
    """

    @property
    @abstractmethod
    def operator(self) -> str:
        """
        The operator of this operation
        """
        pass

    @property
    @abstractmethod
    def operands(self) -> Tuple[Expression, ...]:
        """
        The operands of this operation
        """
        pass


#
# Prefix expressions
#


class PrefixExpression(Expression, metaclass=ABCMeta):
    """
    A prefix expression.

    A prefix expression combines a prefix and a subexpression, optionally separated
    by one or more characters.
    """

    @property
    @abstractmethod
    def prefix(self) -> Expression:
        """
        The prefix of this expression
        """
        pass

    @property
    def separator(self) -> str:
        """
        One or more characters separating the prefix and the subexpression
        """
        return ""

    @property
    @abstractmethod
    def subexpression(self) -> Expression:
        """
        The subexpression prefixed by this expression.
        """
        pass

    def __eq__(self, other: "PrefixExpression") -> bool:
        return (
            isinstance(other, type(self))
            and self.prefix == other.prefix
            and self.subexpression == other.subexpression
        )

    def __hash__(self) -> int:
        return hash((type(self), self.prefix, self.subexpression))


class BasePrefixExpression(PrefixExpression, metaclass=ABCMeta):
    """
    Base implementation for prefix expressions
    """

    def __init__(self, prefix: Any, subexpression: Any):
        self._prefix = Expression.from_value(prefix)
        self._subexpression = Expression.from_value(subexpression)

    @property
    def prefix(self) -> Expression:
        """[see superclass]"""
        return self._prefix

    prefix.__doc__ = PrefixExpression.prefix.__doc__

    @property
    def subexpression(self) -> Expression:
        """[see superclass]"""
        return self._subexpression

    subexpression.__doc__ = PrefixExpression.subexpression.__doc__


class UnaryOperation(BasePrefixExpression, BaseOperation, metaclass=ABCMeta):
    """
    A unary operation
    """

    def __init__(self, operator: str, operand: Any):
        super().__init__(prefix=Identifier(operator), subexpression=operand)
        self._operator = operator

    @property
    def operator(self) -> str:
        """[see superclass]"""
        return self._operator

    operator.__doc__ = BaseOperation.operator.__doc__

    @property
    def operands(self) -> Tuple[Expression, ...]:
        """[see superclass]"""
        return (self.subexpression,)

    operator.__doc__ = BaseOperation.operator.__doc__

    @property
    def precedence(self) -> int:
        """[see superclass]"""
        return OPERATOR_PRECEDENCE.get(f"{self._operator}x", MIN_PRECEDENCE)

    precedence.__doc__ = Expression.precedence.__doc__


# noinspection DuplicatedCode
class _KeywordArgument(BasePrefixExpression):
    """
    A keyword argument, used by functions
    """

    _PRECEDENCE = OPERATOR_PRECEDENCE["="]

    def __init__(self, name: str, value: Any):
        super().__init__(prefix=Identifier(name), subexpression=value)
        self._name = name

    @property
    def name(self) -> str:
        """
        The name of this keyword argument
        """
        return self._name

    @property
    def separator(self) -> str:
        """[see superclass]"""
        return "="

    separator.__doc__ = PrefixExpression.separator.__doc__

    @property
    def value(self) -> Expression:
        """
        The name of this keyword argument
        """
        return self.subexpression

    @property
    def precedence(self) -> int:
        """[see superclass]"""
        return self._PRECEDENCE

    precedence.__doc__ = Expression.precedence.__doc__


# noinspection DuplicatedCode
class _DictEntry(BasePrefixExpression):
    """
    Two expressions separated by a colon, used in dictionaries and lambda expressions
    """

    _PRECEDENCE = OPERATOR_PRECEDENCE[":"]

    def __init__(self, key: Any, value: Any):
        super().__init__(prefix=key, subexpression=value)

    @property
    def key(self) -> Expression:
        """
        The key of this dictionary entry
        """
        return self.prefix

    @property
    def separator(self) -> str:
        """[see superclass]"""
        return ": "

    separator.__doc__ = PrefixExpression.separator.__doc__

    @property
    def value(self) -> Expression:
        """
        The value of this dictionary entry
        """
        return self.subexpression

    @property
    def precedence(self) -> int:
        """[see superclass]"""
        return _DictEntry._PRECEDENCE

    precedence.__doc__ = Expression.precedence.__doc__


class BaseInvocation(PrefixExpression):
    """
    An invocation in the shape of `<expression>(<expression>)` or
    `<expression>[<expression>]`
    """

    _PRECEDENCE = OPERATOR_PRECEDENCE["."]

    def __init__(self, callee: Any, brackets: Tuple[str, str], args: Tuple[Any, ...]):
        self.callee = Expression.from_value(callee)
        self.brackets = brackets
        self.invocation = _InvocationExpression(brackets=brackets, args=args)

    @property
    def prefix(self) -> Expression:
        """[see superclass]"""
        return self.callee

    prefix.__doc__ = PrefixExpression.prefix.__doc__

    @property
    def subexpression(self) -> Expression:
        """[see superclass]"""
        return self.invocation

    subexpression.__doc__ = PrefixExpression.subexpression.__doc__

    @property
    def args(self) -> Tuple[Expression, ...]:
        """
        The arguments passed to this invocation
        """
        return self.invocation.elements

    @property
    def precedence(self) -> int:
        """[see superclass]"""
        return BaseInvocation._PRECEDENCE

    precedence.__doc__ = Expression.precedence.__doc__


class Call(BaseInvocation):
    """
    A function invocation
    """

    def __init__(self, callee: Any, *args: Any, **kwargs: Any):
        super().__init__(
            callee=callee,
            brackets=("(", ")"),
            args=(
                *args,
                *(
                    _KeywordArgument(name, expression)
                    for name, expression in kwargs.items()
                ),
            ),
        )


class Index(BaseInvocation):
    """
    An indexing operation in the shape of `x[i]`
    """

    def __init__(self, callee: Any, *args: Any):
        super().__init__(callee=callee, brackets=("[", "]"), args=args),


# noinspection DuplicatedCode
class _LambdaColon(BasePrefixExpression):
    """
    Two expressions separated by a colon, used in dictionaries and lambda expressions
    """

    _PRECEDENCE = OPERATOR_PRECEDENCE["lambda x"]

    def __init__(self, params: Any, body: Any):
        super().__init__(prefix=params, subexpression=body)

    @property
    def params(self) -> Expression:
        """
        The parameters of the lambda expression
        """
        return self.prefix

    @property
    def separator(self) -> str:
        """[see superclass]"""
        return ": "

    separator.__doc__ = PrefixExpression.separator.__doc__

    @property
    def body(self) -> Expression:
        """
        The body of the lambda expression
        """
        return self.subexpression

    @property
    def precedence(self) -> int:
        """[see superclass]"""
        return _LambdaColon._PRECEDENCE

    precedence.__doc__ = Expression.precedence.__doc__


class Lambda(UnaryOperation):
    """
    A lambda expression
    """

    def __init__(
        self,
        params: Union[Union[str, Identifier], Iterable[Union[str, Identifier]]],
        body: Any,
    ):
        params = to_tuple(params)

        def _to_identifier(param: Union[str, Identifier]) -> Identifier:
            if isinstance(param, str):
                return Identifier(param)
            elif isinstance(param, Identifier):
                return param
            else:
                raise TypeError("arg params may only contain strings and Identifiers")

        params = tuple(_to_identifier(param) for param in params)

        if not params:
            arg_list = EPSILON
        elif len(params) == 1:
            arg_list = params[0]
        else:
            arg_list = Operation(operator=",", operands=params)

        super().__init__(
            operator="lambda ", operand=_LambdaColon(params=arg_list, body=body)
        )


#
# Infix expressions
#


class InfixExpression(Expression, metaclass=ABCMeta):
    """
    An infix expression, where any number of subexpressions are separated by a specific
    infix.
    """

    @property
    @abstractmethod
    def infix(self) -> str:
        """
        The infix used to separate this expression's subexpressions.
        """
        pass

    @property
    @abstractmethod
    def subexpressions(self) -> Tuple[Expression, ...]:
        """
        The subexpressions of this expression.
        """
        pass

    def __eq__(self, other: "InfixExpression") -> bool:
        return (
            isinstance(other, type(self))
            and self.infix == other.infix
            and self.subexpressions == other.subexpressions
        )

    def __hash__(self) -> int:
        return hash((type(self), self.infix, self.subexpressions))


class Operation(InfixExpression, BaseOperation):
    """
    A operation with at least two operands
    """

    def __init__(self, operator: str, operands: Any):

        operands = to_tuple(operands)
        if not operands:
            raise ValueError("operation requires at least one operand")

        operands = tuple(Expression.from_value(operand) for operand in operands)

        first_operand = operands[0]

        # noinspection PyUnresolvedReferences
        if isinstance(first_operand, Operation) and first_operand.operator == operator:
            # if first operand has the same operator, we flatten the operand
            # noinspection PyUnresolvedReferences
            operands = (*first_operand.operands, *operands[1:])

        self._operator = operator
        self._operands = operands

    @property
    def operator(self) -> str:
        """[see superclass]"""
        return self._operator

    operator.__doc__ = BaseOperation.operator.__doc__

    @property
    def operands(self) -> Tuple[Expression, ...]:
        """[see superclass]"""
        return self._operands

    operands.__doc__ = BaseOperation.operands.__doc__

    @property
    def infix(self) -> str:
        """[see superclass]"""
        return self._operator

    infix.__doc__ = InfixExpression.infix.__doc__

    @property
    def subexpressions(self) -> Tuple[Expression, ...]:
        """[see superclass]"""
        return self._operands

    subexpressions.__doc__ = InfixExpression.subexpressions.__doc__

    @property
    def precedence(self) -> int:
        """[see superclass]"""
        return OPERATOR_PRECEDENCE.get(self.infix, MIN_PRECEDENCE)

    precedence.__doc__ = Expression.precedence.__doc__


class Attr(Operation):
    """
    The "dot" operation to reference an attribute of an object
    """

    def __init__(self, obj: Any, attribute: Union[Identifier, str]) -> None:
        if isinstance(attribute, str):
            attribute = Identifier(attribute)
        elif not isinstance(attribute, Identifier):
            raise TypeError("arg attribute must be a string or an Identifier")
        super().__init__(operator=".", operands=(obj, attribute))


#
# Bracketed expressions
#


class BracketedExpression(Expression, metaclass=ABCMeta):
    """
    An expression surrounded by brackets.
    """

    @property
    @abstractmethod
    def brackets(self) -> Tuple[str, str]:
        """
        The brackets surrounding this expression's subexpressions.
        """
        pass

    @property
    @abstractmethod
    def subexpression(self) -> Expression:
        """
        The subexpression bracketed by this expression.
        """
        pass

    @property
    def precedence(self) -> int:
        """[see superclass]"""
        return MAX_PRECEDENCE

    precedence.__doc__ = Expression.precedence.__doc__

    def __eq__(self, other: "BracketedExpression") -> bool:
        return (
            isinstance(other, type(self))
            and self.brackets == other.brackets
            and self.subexpression == other.subexpression
        )

    def __hash__(self) -> int:
        return hash((type(self), self.brackets, self.subexpression))


class CollectionExpression(BracketedExpression):
    """
    A collection literal, e.g. a list, set, tuple, or dictionary
    """

    def __init__(self, *, brackets: Tuple[str, str], elements: Iterable[Any]) -> None:
        elements = tuple(
            Expression.from_value(element) for element in to_tuple(elements)
        )

        subexpression: Expression
        if not elements:
            subexpression = EPSILON
        elif len(elements) == 1:
            subexpression = elements[0]
        else:
            subexpression = Operation(operator=",", operands=elements)

        self.elements = elements
        self._subexpression = subexpression
        self._brackets = brackets

    @property
    def brackets(self) -> Tuple[str, str]:
        """[see superclass]"""
        return self._brackets

    brackets.__doc__ = BracketedExpression.brackets.__doc__

    @property
    def subexpression(self) -> Expression:
        """[see superclass]"""
        return self._subexpression

    subexpression.__doc__ = BracketedExpression.subexpression.__doc__


class ListExpression(CollectionExpression):
    """
    A list of expressions
    """

    def __init__(self, elements: Iterable[Any]):
        super().__init__(brackets=("[", "]"), elements=elements)


class TupleExpression(CollectionExpression):
    """
    A list of expressions
    """

    def __init__(self, elements: Iterable[Any]):
        super().__init__(brackets=("(", ")"), elements=elements)


class _InvocationExpression(CollectionExpression):
    """
    A list of expressions
    """

    def __init__(self, brackets: Tuple[str, str], args: Iterable[Any]):
        super().__init__(brackets=brackets, elements=args)


class SetExpression(CollectionExpression):
    """
    A list of expressions
    """

    def __init__(self, elements: Iterable[Any]):
        super().__init__(brackets=("{", "}"), elements=elements)


class DictExpression(CollectionExpression):
    """
    A list of expressions
    """

    def __init__(self, entries: Mapping[Any, Any]):
        super().__init__(
            brackets=("{", "}"),
            elements=tuple(_DictEntry(key, value) for key, value in entries.items()),
        )


__tracker.validate()

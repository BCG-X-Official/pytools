"""
Basic utilities for constructing complex expressions and rendering them as indented
strings; useful for generating representations of complex Python objects.
"""
import itertools
import logging
from abc import ABCMeta, abstractmethod
from typing import Any, Generic, Iterable, NamedTuple, Optional, Tuple, TypeVar, Union

import gamma.common.expression.operator as op
from gamma.common import AllTracker, to_list
from gamma.common.expression.operator import (
    BinaryOperator,
    MAX_PRECEDENCE,
    Operator,
    UnaryOperator,
)

log = logging.getLogger(__name__)

__all__ = [
    "ExpressionFormatter",
    "HasExpressionRepr",
    "Expression",
    "make_expression",
    "AtomicExpression",
    "Literal",
    "Identifier",
    "EPSILON",
    "SingletonExpression",
    "BracketPair",
    "BRACKETS_ROUND",
    "BRACKETS_SQUARE",
    "BRACKETS_CURLY",
    "BRACKETS_ANGLE",
    "BracketedExpression",
    "CollectionLiteral",
    "ListLiteral",
    "TupleLiteral",
    "SetLiteral",
    "DictLiteral",
    "BaseOperation",
    "PrefixExpression",
    "BasePrefixExpression",
    "UnaryOperation",
    "KeywordArgument",
    "DictEntry",
    "BaseInvocation",
    "Call",
    "Index",
    "LambdaDefinition",
    "Lambda",
    "InfixExpression",
    "Operation",
    "Attr",
    "ExpressionAlias",
]

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


class Expression(metaclass=ABCMeta):
    """
    An expression composed of literals and (possibly nested) operations.
    """

    @property
    @abstractmethod
    def precedence_(self) -> int:
        """
        :return: the precedence of this expression, used to determine the need for \
            parentheses
        """
        pass

    @property
    @abstractmethod
    def subexpressions_(self) -> Tuple["Expression", ...]:
        """
        The subexpressions of this expression.
        """

    def eq_(self, other: Any) -> "Operation":
        """
        Generate an expression that compares for equality (`a == b` in Python).

        We cannot generate such expressions using a native Python shorthand,
        since we need to preserve the semantics of the native equality operation
        for set operations etc.

        :param other: the RHS of the comparison
        :return: the comparison operation
        """
        return Operation(op.EQ, self, other)

    def ne_(self, other: Any) -> "Operation":
        """
        Generate an expression that compares for inequality (`a != b` in Python)

        We cannot generate such expressions using a native Python shorthand,
        since we need to preserve the semantics of the native equality operation
        for set operations etc.

        :param other: the RHS of the comparison
        :return: the comparison operation
        """
        return Operation(op.NEQ, self, other)

    def gt_(self, other: Any) -> "Operation":
        """
        Generate a "greater than" expression (`a > b` in Python)

        We cannot generate such expressions using a native Python shorthand,
        since we need to preserve the semantics of the native comparison operation.

        :param other: the RHS of the comparison
        :return: the comparison operation
        """
        return Operation(op.GT, self, other)

    def ge_(self, other: Any) -> "Operation":
        """
        Generate a "equal or greater than" expression (`a >= b` in Python)

        We cannot generate such expressions using a native Python shorthand,
        since we need to preserve the semantics of the native comparison operation.

        :param other: the RHS of the comparison
        :return: the comparison operation
        """
        return Operation(op.GE, self, other)

    def lt_(self, other: Any) -> "Operation":
        """
        Generate a "less than" expression (`a < b` in Python)

        We cannot generate such expressions using a native Python shorthand,
        since we need to preserve the semantics of the native comparison operation.

        :param other: the RHS of the comparison
        :return: the comparison operation
        """
        return Operation(op.LT, self, other)

    def le_(self, other: Any) -> "Operation":
        """
        Generate a "equal or less than" expression (`a <= b` in Python)

        We cannot generate such expressions using a native Python shorthand,
        since we need to preserve the semantics of the native comparison operation.

        :param other: the RHS of the comparison
        :return: the comparison operation
        """
        return Operation(op.LE, self, other)

    @abstractmethod
    def _equals(self: T, other: T) -> bool:
        # assuming other is the same type as self, check if self and other are equal
        pass

    def __eq__(self, other: "Expression") -> bool:
        self_type = type(self)
        other_type = type(other)
        if self_type == ExpressionAlias:
            self: ExpressionAlias
            return other == self.expression_
        elif other_type == ExpressionAlias:
            other: ExpressionAlias
            return self == other.expression_
        else:
            return self_type is other_type and self._equals(other)

    @abstractmethod
    def __hash__(self) -> int:
        pass

    def __add__(self, other: Any) -> "Operation":
        return Operation(op.ADD, self, other)

    def __sub__(self, other: Any) -> "Operation":
        return Operation(op.SUB, self, other)

    def __mul__(self, other: Any) -> "Operation":
        return Operation(op.MUL, self, other)

    def __matmul__(self, other: Any) -> "Operation":
        return Operation(op.MATMUL, self, other)

    def __truediv__(self, other: Any) -> "Operation":
        return Operation(op.DIV, self, other)

    def __floordiv__(self, other: Any) -> "Operation":
        return Operation(op.FLOOR_DIV, self, other)

    def __mod__(self, other: Any) -> "Operation":
        return Operation(op.MOD, self, other)

    def __pow__(self, power: Any, modulo=None) -> "Operation":
        if modulo is not None:
            raise NotImplementedError("modulo is not supported")
        return Operation(op.POW, self, power)

    def __lshift__(self, other: Any) -> "Operation":
        return Operation(op.LSHIFT, self, other)

    def __rshift__(self, other: Any) -> "Operation":
        return Operation(op.RSHIFT, self, other)

    def __and__(self, other: Any) -> "Operation":
        return Operation(op.AND_BITWISE, self, other)

    def __xor__(self, other: Any) -> "Operation":
        return Operation(op.XOR_BITWISE, self, other)

    def __or__(self, other: Any) -> "Operation":
        return Operation(op.OR_BITWISE, self, other)

    def __radd__(self, other: Any) -> "Operation":
        return Operation(op.ADD, other, self)

    def __rsub__(self, other: Any) -> "Operation":
        return Operation(op.SUB, other, self)

    def __rmul__(self, other: Any) -> "Operation":
        return Operation(op.MUL, other, self)

    def __rmatmul__(self, other: Any) -> "Operation":
        return Operation(op.MATMUL, other, self)

    def __rtruediv__(self, other: Any) -> "Operation":
        return Operation(op.DIV, other, self)

    def __rfloordiv__(self, other: Any) -> "Operation":
        return Operation(op.FLOOR_DIV, other, self)

    def __rmod__(self, other: Any) -> "Operation":
        return Operation(op.MOD, other, self)

    def __rpow__(self, power: Any, modulo=None) -> "Operation":
        if modulo is not None:
            raise NotImplementedError("modulo is not supported")
        return Operation(op.POW, (power, self))

    def __rlshift__(self, other: Any) -> "Operation":
        return Operation(op.LSHIFT, other, self)

    def __rrshift__(self, other: Any) -> "Operation":
        return Operation(op.RSHIFT, other, self)

    def __rand__(self, other: Any) -> "Operation":
        return Operation(op.AND_BITWISE, other, self)

    def __rxor__(self, other: Any) -> "Operation":
        return Operation(op.XOR_BITWISE, other, self)

    def __ror__(self, other: Any) -> "Operation":
        return Operation(op.OR_BITWISE, other, self)

    def __neg__(self) -> "UnaryOperation":
        return UnaryOperation(op.NEG, self)

    def __pos__(self) -> "UnaryOperation":
        return UnaryOperation(op.POS, self)

    def __invert__(self) -> "UnaryOperation":
        return UnaryOperation(op.INVERT, self)

    def __call__(self, *args: Any, **kwargs: Any) -> "Call":
        return Call(
            self,
            *(make_expression(arg) for arg in args),
            **{k: make_expression(v) for k, v in kwargs.items()},
        )

    def __getitem__(self, key: Any) -> "Index":
        return Index(self, key)

    def __setitem__(self, key: Any, value: Any) -> "Index":
        raise TypeError(f"cannot set indexed item of Expression: {to_list(key)}")

    def __delitem__(self, key: Any) -> "Index":
        raise TypeError(f"cannot delete indexed item of Expression: {to_list(key)}")

    def __getattr__(self, key: str) -> "Expression":
        if key[:1] == "_":
            raise AttributeError(key)
        else:
            return Attr(obj=self, attribute=key)

    def __setattr__(self, key: Any, value: Any) -> None:
        if key[:1] == "_":
            super().__setattr__(key, value)
        else:
            raise TypeError(f"cannot set public field of Expression: {key}")

    def __iter__(self) -> None:
        # we need to rule iteration out explicitly, otherwise we'd get infinite 'for'
        # loops through iterating via __getitem__
        raise TypeError(f"'{Expression.__name__}' object is not iterable")

    def __repr__(self) -> str:
        # get the expression representing this object, and use the default formatter
        # to get a text representation of the expression
        return ExpressionFormatter.default().to_text(self)


def make_expression(value: Any) -> "Expression":
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

    if isinstance(value, Expression):
        return value
    if isinstance(value, HasExpressionRepr):
        return value.to_expression()
    elif isinstance(value, str):
        return Literal(value)
    elif isinstance(value, list):
        return ListLiteral(*value)
    elif isinstance(value, tuple):
        return TupleLiteral(*value)
    elif isinstance(value, set):
        return SetLiteral(*value)
    elif isinstance(value, dict):
        return DictLiteral(*value.items())
    elif isinstance(value, slice):
        args = [
            EPSILON if value is None else value
            for value in (value.start, value.stop, value.step)
        ]
        if value.step is not None:
            return Operation(op.SLICE, *args)
        else:
            return Operation(op.SLICE, args[0], args[1])
    elif isinstance(value, Iterable):
        return Call(Identifier(type(value)), *value)
    else:
        name: Optional[str] = getattr(value, "__name__", None)
        if name:
            return Identifier(value)
        else:

            return Literal(value)


#
# Atomic expressions
#


class AtomicExpression(Expression, Generic[T], metaclass=ABCMeta):
    """
    An atomic expression.

    Atomic expressions include literals and identifiers, and have no subexpressions.
    """

    @property
    def subexpressions_(self) -> Tuple["Expression", ...]:
        """
        The subexpressions of this expression.
        Always returns an empty tuple for atomic expressions.
        """
        return ()

    subexpressions_.__doc__ = Expression.subexpressions_.__doc__

    @property
    @abstractmethod
    def text_(self) -> str:
        """
        The text representing this atomic expression
        """
        pass

    @property
    @abstractmethod
    def value_(self) -> T:
        """
        The underlying value of this atomic expression
        """
        pass

    @property
    def precedence_(self) -> int:
        """[see superclass]"""
        return MAX_PRECEDENCE

    precedence_.__doc__ = Expression.precedence_.__doc__

    def _equals(self, other: Expression) -> bool:
        return self.value_ == other.value_

    def __hash__(self) -> int:
        return hash((type(self), self.value_))


class Literal(AtomicExpression[T], Generic[T]):
    """
    A literal
    """

    def __init__(self, value: T):
        self._value = value

    @property
    def value_(self) -> T:
        """[see superclass]"""
        return self._value

    value_.__doc__ = AtomicExpression.value_.__doc__

    @property
    def text_(self) -> str:
        """[see superclass]"""
        return repr(self.value_)

    text_.__doc__ = AtomicExpression.text_.__doc__


class Identifier(AtomicExpression[str]):
    """
    An identifier
    """

    def __init__(self, name: Any) -> None:
        if not isinstance(name, str):
            name = getattr(name, "__name__", None)
            if not name:
                raise TypeError(
                    "arg name must be a string, or must have attribute __name__"
                )
        self._name = name

    @property
    def value_(self) -> str:
        """[see superclass]"""
        return self._name

    value_.__doc__ = AtomicExpression.value_.__doc__

    @property
    def text_(self) -> str:
        """[see superclass]"""
        return self._name

    text_.__doc__ = AtomicExpression.text_.__doc__


class _Epsilon(AtomicExpression[None]):
    """
    The empty expression.
    """

    @property
    def value_(self) -> None:
        """[see superclass]"""
        return None

    @property
    def text_(self) -> str:
        """[see superclass]"""
        return ""

    text_.__doc__ = AtomicExpression.text_.__doc__


EPSILON = _Epsilon()


#
# Complex expressions
#


class SingletonExpression(Expression, metaclass=ABCMeta):
    """
    An expression with a single subexpression.
    """

    @property
    @abstractmethod
    def subexpression_(self) -> Expression:
        """
        The subexpression of this expression.
        """

    @property
    def subexpressions_(self) -> Tuple[Expression, ...]:
        """[see superclass]"""
        return (self.subexpression_,)

    subexpressions_.__doc__ = Expression.subexpressions_.__doc__


#
# Bracketed expressions
#


class BracketPair(NamedTuple):
    """
    A pair of brackets.
    """

    opening: str
    closing: str


BRACKETS_ROUND = BracketPair("(", ")")
BRACKETS_SQUARE = BracketPair("[", "]")
BRACKETS_CURLY = BracketPair("{", "}")
BRACKETS_ANGLE = BracketPair("<", ">")


class BracketedExpression(SingletonExpression, metaclass=ABCMeta):
    """
    An expression surrounded by brackets.
    """

    def __init__(self, brackets: BracketPair, subexpression: Expression) -> None:
        self._brackets = brackets
        self._subexpression = subexpression

    @property
    def brackets_(self) -> BracketPair:
        """
        The brackets surrounding this expression's subexpressions.
        """
        return self._brackets

    @property
    def subexpression_(self) -> Expression:
        """
        The subexpression bracketed by this expression.
        """
        return self._subexpression

    @property
    def precedence_(self) -> int:
        """[see superclass]"""
        return MAX_PRECEDENCE

    precedence_.__doc__ = Expression.precedence_.__doc__

    def _equals(self, other: "BracketedExpression") -> bool:
        return (
            self.brackets_ == other.brackets_
            and self.subexpression_ == other.subexpression_
        )

    def __hash__(self) -> int:
        return hash((type(self), self.brackets_, self.subexpression_))


class CollectionLiteral(BracketedExpression):
    """
    A collection literal, e.g. a list, set, tuple, or dictionary
    """

    def __init__(self, brackets: BracketPair, elements: Iterable[Any]) -> None:
        elements: Tuple[Expression, ...] = tuple(
            make_expression(element) for element in elements
        )

        subexpression: Expression
        if not elements:
            subexpression = EPSILON
        elif len(elements) == 1:
            subexpression = elements[0]
        else:
            subexpression = Operation(op.COMMA, *elements)

        super().__init__(brackets, subexpression)


class ListLiteral(CollectionLiteral):
    """
    A list of expressions
    """

    def __init__(self, *elements: Any):
        super().__init__(brackets=BRACKETS_SQUARE, elements=elements)


class TupleLiteral(CollectionLiteral):
    """
    A list of expressions
    """

    def __init__(self, *elements: Any):
        super().__init__(brackets=BRACKETS_ROUND, elements=elements)


class SetLiteral(CollectionLiteral):
    """
    A list of expressions
    """

    def __init__(self, *elements: Any):
        super().__init__(brackets=BRACKETS_CURLY, elements=elements)


class DictLiteral(CollectionLiteral):
    """
    A list of expressions
    """

    def __init__(self, *args: Tuple[Any, Any], **entries: Tuple[str, Any]):
        super().__init__(
            brackets=BRACKETS_CURLY,
            elements=(
                DictEntry(key, value)
                for key, value in itertools.chain(args, entries.items())
            ),
        )


class _Invocation(CollectionLiteral):
    """
    A list of expressions
    """

    def __init__(self, brackets: BracketPair, args: Iterable[Any]):
        super().__init__(brackets=brackets, elements=args)


#
# Operations
#


class BaseOperation(Expression, metaclass=ABCMeta):
    """
    Abstract base class for operation expressions
    """

    @property
    @abstractmethod
    def operator_(self) -> Operator:
        """
        The operator of this operation
        """
        pass

    @property
    @abstractmethod
    def operands_(self) -> Tuple[Expression, ...]:
        """
        The operands of this operation
        """
        return self.subexpressions_


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
    def prefix_(self) -> Expression:
        """
        The prefix of this expression
        """
        pass

    @property
    def separator_(self) -> str:
        """
        One or more characters separating the prefix and the subexpression
        """
        return ""

    @property
    @abstractmethod
    def body_(self) -> Expression:
        """
        The prefix of this expression
        """
        pass

    @property
    def subexpressions_(self) -> Tuple[Expression, ...]:
        """[see superclass]"""
        return self.prefix_, self.body_

    subexpressions_.__doc__ = Expression.subexpressions_.__doc__

    def _equals(self, other: "PrefixExpression") -> bool:
        return (
            self.prefix_ == other.prefix_
            and self.subexpressions_ == other.subexpressions_
        )

    def __hash__(self) -> int:
        return hash((type(self), self.prefix_, self.subexpression_))


class BasePrefixExpression(PrefixExpression, metaclass=ABCMeta):
    """
    Base implementation for prefix expressions
    """

    def __init__(self, prefix: Any, body: Any):
        self._prefix = make_expression(prefix)
        self._body = make_expression(body)

    @property
    def prefix_(self) -> Expression:
        """[see superclass]"""
        return self._prefix

    prefix_.__doc__ = PrefixExpression.prefix_.__doc__

    @property
    def body_(self) -> Expression:
        """[see superclass]"""
        return self._body

    body_.__doc__ = PrefixExpression.body_.__doc__


class UnaryOperation(BasePrefixExpression, BaseOperation, metaclass=ABCMeta):
    """
    A unary operation
    """

    def __init__(self, operator: UnaryOperator, operand: Any):
        super().__init__(prefix=EPSILON, body=operand)
        self._operator = operator

    @property
    def separator_(self) -> str:
        """[see superclass]"""
        return self._operator.symbol

    separator_.__doc__ = PrefixExpression.separator_.__doc__

    @property
    def operator_(self) -> op.UnaryOperator:
        """[see superclass]"""
        return self._operator

    operator_.__doc__ = BaseOperation.operator_.__doc__

    @property
    def operands_(self) -> Tuple[Expression, ...]:
        """[see superclass]"""
        return self.subexpressions_

    operator_.__doc__ = BaseOperation.operator_.__doc__

    @property
    def precedence_(self) -> int:
        """[see superclass]"""
        return self._operator.precedence

    precedence_.__doc__ = Expression.precedence_.__doc__


# noinspection DuplicatedCode
class KeywordArgument(BasePrefixExpression):
    """
    A keyword argument, used by functions
    """

    _PRECEDENCE = op.EQ.precedence

    def __init__(self, name: str, value: Any):
        super().__init__(prefix=Identifier(name), body=value)
        self._name = name

    @property
    def name_(self) -> str:
        """
        The name of this keyword argument
        """
        return self._name

    @property
    def separator_(self) -> str:
        """[see superclass]"""
        return "="

    separator_.__doc__ = PrefixExpression.separator_.__doc__

    @property
    def value_(self) -> Expression:
        """
        The name of this keyword argument
        """
        return self.body_

    @property
    def precedence_(self) -> int:
        """[see superclass]"""
        return self._PRECEDENCE

    precedence_.__doc__ = Expression.precedence_.__doc__


# noinspection DuplicatedCode
class DictEntry(BasePrefixExpression):
    """
    Two expressions separated by a colon, used in dictionaries and lambda expressions
    """

    _PRECEDENCE = op.COLON.precedence

    def __init__(self, key: Any, value: Any):
        super().__init__(prefix=key, body=value)

    @property
    def key_(self) -> Expression:
        """
        The key of this dictionary entry
        """
        return self.prefix_

    @property
    def separator_(self) -> str:
        """[see superclass]"""
        return ": "

    separator_.__doc__ = PrefixExpression.separator_.__doc__

    @property
    def value_(self) -> Expression:
        """
        The value of this dictionary entry
        """
        return self.body_

    @property
    def precedence_(self) -> int:
        """[see superclass]"""
        return DictEntry._PRECEDENCE

    precedence_.__doc__ = Expression.precedence_.__doc__


class BaseInvocation(PrefixExpression):
    """
    An invocation in the shape of `<expression>(<expression>)` or
    `<expression>[<expression>]`
    """

    _PRECEDENCE = op.DOT.precedence

    def __init__(self, prefix: Any, brackets: BracketPair, args: Iterable[Any]):
        self._prefix = make_expression(prefix)
        self._invocation = _Invocation(brackets, args=args)

    @property
    def prefix_(self) -> Expression:
        """[see superclass]"""
        return self._prefix

    prefix_.__doc__ = PrefixExpression.prefix_.__doc__

    @property
    def body_(self) -> Expression:
        """[see superclass]"""
        return self._invocation

    body_.__doc__ = PrefixExpression.body_.__doc__

    @property
    def precedence_(self) -> int:
        """[see superclass]"""
        return BaseInvocation._PRECEDENCE

    precedence_.__doc__ = Expression.precedence_.__doc__


class Call(BaseInvocation):
    """
    A function invocation
    """

    def __init__(self, callee: Any, *args: Any, **kwargs: Any):
        super().__init__(
            prefix=callee,
            brackets=BRACKETS_ROUND,
            args=(
                *args,
                *(
                    KeywordArgument(name, expression)
                    for name, expression in kwargs.items()
                ),
            ),
        )

    @property
    def callee_(self) -> Expression:
        """
        The expression invoked by this call.
        """
        return self.prefix_


class Index(BaseInvocation):
    """
    An indexing operation in the shape of `x[i]`
    """

    def __init__(self, collection: Any, key: Any):
        keys = key if isinstance(key, tuple) else (key,)
        super().__init__(prefix=collection, brackets=BRACKETS_SQUARE, args=keys)


# noinspection DuplicatedCode
class LambdaDefinition(BasePrefixExpression):
    """
    function arguments and body separated by a colon, used inside lambda expressions
    """

    _PRECEDENCE = op.LAMBDA.precedence

    def __init__(self, params: Any, body: Any):
        super().__init__(prefix=params, body=body)

    @property
    def params_(self) -> Expression:
        """
        The parameters of the lambda expression
        """
        return self.prefix_

    @property
    def separator_(self) -> str:
        """[see superclass]"""
        return ": "

    separator_.__doc__ = PrefixExpression.separator_.__doc__

    @property
    def precedence_(self) -> int:
        """[see superclass]"""
        return LambdaDefinition._PRECEDENCE

    precedence_.__doc__ = Expression.precedence_.__doc__


class Lambda(BasePrefixExpression):
    """
    A lambda expression
    """

    _PRECEDENCE = op.LAMBDA.precedence

    def __init__(
        self,
        params: Union[Union[str, Identifier], Iterable[Union[str, Identifier]]],
        body: Any,
    ):
        def _to_identifier(param: Union[str, Identifier]) -> Identifier:
            if isinstance(param, str):
                return Identifier(param)
            elif isinstance(param, Identifier):
                return param
            else:
                raise TypeError("arg params may only contain strings and Identifiers")

        if isinstance(params, str) or isinstance(params, Expression):
            params = (_to_identifier(params),)
        else:
            params = tuple(_to_identifier(param) for param in params)

        if not params:
            arg_list = EPSILON
        elif len(params) == 1:
            arg_list = params[0]
        else:
            arg_list = Operation(operator=op.COMMA, *params)

        super().__init__(
            prefix=EPSILON, body=LambdaDefinition(params=arg_list, body=body)
        )

    @property
    def precedence_(self) -> int:
        return Lambda._PRECEDENCE

    @property
    def separator_(self) -> str:
        """[see superclass]"""
        return f"{op.LAMBDA.symbol} "


#
# BinaryOperator expressions
#


class InfixExpression(Expression, metaclass=ABCMeta):
    """
    An infix expression, where any number of subexpressions are separated by a specific
    infix.
    """

    @property
    @abstractmethod
    def infix_(self) -> BinaryOperator:
        """
        The infix used to separate this expression's subexpressions.
        """
        pass

    def _equals(self, other: "InfixExpression") -> bool:
        return (
            self.infix_ == other.infix_
            and self.subexpressions_ == other.subexpressions_
        )

    def __hash__(self) -> int:
        return hash((type(self), self.infix_, self.subexpressions_))


class Operation(InfixExpression, BaseOperation):
    """
    A operation with at least two operands
    """

    def __init__(self, operator: BinaryOperator, *operands: Any):

        if not isinstance(operator, BinaryOperator):
            raise TypeError(f"arg operator={operator} must be an BinaryOperator")

        if len(operands) < 2:
            raise ValueError("operation requires at least two operands")

        operands = tuple(make_expression(operand) for operand in operands)

        first_operand = operands[0]

        if isinstance(first_operand, Operation):
            first_operand: Operation
            if first_operand.operator_ == operator:
                # if first operand has the same operator, we flatten the operand
                # noinspection PyUnresolvedReferences
                operands = (*first_operand.operands_, *operands[1:])

        self._operator = operator
        self._operands = operands

    @property
    def operator_(self) -> BinaryOperator:
        """[see superclass]"""
        return self._operator

    operator_.__doc__ = BaseOperation.operator_.__doc__

    @property
    def operands_(self) -> Tuple[Expression, ...]:
        """[see superclass]"""
        return self._operands

    operands_.__doc__ = BaseOperation.operands_.__doc__

    @property
    def infix_(self) -> BinaryOperator:
        """[see superclass]"""
        return self._operator

    infix_.__doc__ = InfixExpression.infix_.__doc__

    @property
    def subexpressions_(self) -> Tuple[Expression, ...]:
        """[see superclass]"""
        return self._operands

    subexpressions_.__doc__ = InfixExpression.subexpressions_.__doc__

    @property
    def precedence_(self) -> int:
        """[see superclass]"""
        return self.infix_.precedence

    precedence_.__doc__ = Expression.precedence_.__doc__


class Attr(Operation):
    """
    The "dot" operation to reference an attribute of an object
    """

    def __init__(self, obj: Any, attribute: Union[Identifier, str]) -> None:
        if isinstance(attribute, str):
            attribute = Identifier(attribute)
        elif not isinstance(attribute, Identifier):
            raise TypeError("arg attribute must be a string or an Identifier")

        if isinstance(obj, Attr):
            sub = obj.subexpressions_
            super().__init__(op.DOT, sub[0], *(sub[1:]), attribute)
        else:
            super().__init__(op.DOT, obj, attribute)


#
# Expression alias
#


class ExpressionAlias(SingletonExpression):
    """
    An alias pointing to another expression, and representing that expression.

    Useful for substituting subexpressions of expressions without having to reconstruct
    the surrounding expression.

    When comparing or hashing expressions, an expression alias transparently defers to
    the expression it represents, hence expressions containing aliases are
    indistinguishable from their non-aliased counterparts.
    """

    def __init__(self, expression: Expression) -> None:
        self._expression = expression

    @property
    def expression_(self) -> Expression:
        """
        The expression represented by this ExpressionAlias.
        """
        return self._expression

    def set_expression_(self, expression: Expression) -> None:
        """
        Set the expression represented by this ExpressionAlias.
        :param expression: the expression to be set
        """
        self._expression = expression

    @property
    def precedence_(self) -> int:
        """
        [see superclass]
        """
        return self.expression_.precedence_

    precedence_.__doc__ = Expression.precedence_.__doc__

    @property
    def subexpression_(self) -> Expression:
        """
        [see superclass]
        """
        return self.expression_

    subexpression_.__doc__ = SingletonExpression.subexpression_.__doc__

    def _equals(self, other: "ExpressionAlias") -> bool:
        return self._expression == other._expression

    def __hash__(self) -> int:
        return hash(self.expression_)


__tracker.validate()

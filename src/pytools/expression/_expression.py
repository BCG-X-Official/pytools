"""
Basic utilities for constructing complex expressions and rendering them as indented
strings; useful for generating representations of complex Python objects.
"""
import itertools
import logging
from abc import ABCMeta, abstractmethod
from typing import Any, Dict, Generic, Iterable, Optional, Tuple, TypeVar, Union
from weakref import WeakValueDictionary

from ..api import AllTracker, inheritdoc, to_list
from ..meta import SingletonMeta, compose_meta
from .operator import BinaryOperator, Operator, UnaryOperator

log = logging.getLogger(__name__)


#
# Exported names
#

__all__ = [
    "ExpressionFormatter",
    "HasExpressionRepr",
    "Expression",
    "FrozenExpression",
    "make_expression",
    "freeze",
    "AtomicExpression",
    "Lit",
    "Id",
    "Epsilon",
    "SingletonExpression",
    "BracketPair",
    "BracketedExpression",
    "CollectionLiteral",
    "ListLiteral",
    "TupleLiteral",
    "SetLiteral",
    "DictLiteral",
    "BaseOperation",
    "PrefixExpression",
    "SimplePrefixExpression",
    "UnaryOperation",
    "KeywordArgument",
    "DictEntry",
    "Invocation",
    "Call",
    "Index",
    "LambdaDefinition",
    "Lambda",
    "InfixExpression",
    "Operation",
    "Attr",
    "ExpressionAlias",
]

#
# Type variables
#

T = TypeVar("T")
T_Literal = TypeVar("T_Literal", bool, int, float, complex, str, bytes)


#
# Ensure all symbols introduced below are included in __all__
#

__tracker = AllTracker((globals()))


class ExpressionFormatter(metaclass=ABCMeta):
    """
    An expression formatter produces text representations of expressions.
    """

    __default_format: Dict[bool, "ExpressionFormatter"] = {}

    @abstractmethod
    def to_text(self, expression: "Expression") -> str:
        """
        Construct a text representation of the given expression.

        :param expression: the expression to represent as text
        :return: a text representation of the expression
        """
        pass

    @staticmethod
    def default(single_line: bool) -> "ExpressionFormatter":
        """
        Get the default expression formatter.

        :param single_line: if ``True``, return a formatter that does not generate line
            breaks
        """
        return ExpressionFormatter.__default_format[single_line]

    @staticmethod
    def _register_default_format(
        expression_format: "ExpressionFormatter", single_line: bool
    ) -> None:
        if single_line in ExpressionFormatter.__default_format:
            raise RuntimeError(
                f"default format is already registered for single_line={single_line}"
            )
        ExpressionFormatter.__default_format[single_line] = expression_format


class HasExpressionRepr(metaclass=ABCMeta):
    """
    Mix-in class, rendering :func:`repr` and :class:`str` representations using
    expressions.
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
        # to get a textual representation of the expression
        return repr(self.to_expression())

    def __str__(self) -> str:
        # get the expression representing this object, and use the default formatter
        # to convert the expression to a formatted string
        return str(self.to_expression())


@inheritdoc(match="[see superclass]")
class Expression(HasExpressionRepr, metaclass=ABCMeta):
    """
    An expression composed of literals and (possibly nested) operations.
    """

    @property
    @abstractmethod
    def precedence_(self) -> int:
        """
        The precedence of this expression, used to determine the need for parentheses
        """
        pass

    @property
    @abstractmethod
    def subexpressions_(self) -> Tuple["Expression", ...]:
        """
        The subexpressions of this expression
        """

    def or_(self, other: "Expression") -> "Operation":
        """
        Create a logical `or` expression using this and another expression as operands.

        :param other: other operand to combine with this expression using a logical `or`
        :return: the logical `or` expression
        """
        return Operation(BinaryOperator.OR, self, other)

    def and_(self, other: "Expression") -> "Operation":
        """
        Create a logical `and` expression using this and another expression as operands.

        :param other: other operand to combine with this expression using a logical
            `and`
        :return: the logical `and` expression
        """
        return Operation(BinaryOperator.AND, self, other)

    def not_(self) -> "UnaryOperation":
        """
        Create a logical `not` expression using this expression as the operand.

        :return: the logical `not` expression
        """
        return UnaryOperation(UnaryOperator.NOT, self)

    def eq_(self, other: "Expression") -> bool:
        """
        Compare this expression with another for equality.

        For using Python's native equality operator ``==``, see
        :class:`.FrozenExpression`.

        :param other: the expression to compare this expression with
        :return: ``True`` if both expressions are equal; ``False`` otherwise
        """
        self_type = type(self)
        other_type = type(other)

        if self_type is ExpressionAlias:
            self: ExpressionAlias
            return other.eq_(self.expression_)
        elif other_type is ExpressionAlias:
            other: ExpressionAlias
            return self.eq_(other.expression_)
        else:
            # noinspection PyProtectedMember
            return self_type is other_type and self._eq_same_type(other)

    @abstractmethod
    def hash_(self) -> int:
        """
        Calculate the hash for this expression.

        For using Python's native ``hash`` function, see :class:`.FrozenExpression`.
        """
        pass

    def to_expression(self) -> "Expression":
        """[see superclass]"""
        return self

    @abstractmethod
    def _eq_same_type(self: T, other: T) -> bool:
        # assuming other is the same type as self, check if self and other are equal
        pass

    def __add__(self, other: Any) -> "Operation":
        return Operation(BinaryOperator.ADD, self, other)

    def __sub__(self, other: Any) -> "Operation":
        return Operation(BinaryOperator.SUB, self, other)

    def __mul__(self, other: Any) -> "Operation":
        return Operation(BinaryOperator.MUL, self, other)

    def __matmul__(self, other: Any) -> "Operation":
        return Operation(BinaryOperator.MATMUL, self, other)

    def __truediv__(self, other: Any) -> "Operation":
        return Operation(BinaryOperator.DIV, self, other)

    def __floordiv__(self, other: Any) -> "Operation":
        return Operation(BinaryOperator.FLOOR_DIV, self, other)

    def __mod__(self, other: Any) -> "Operation":
        return Operation(BinaryOperator.MOD, self, other)

    def __pow__(self, power: Any, modulo=None) -> "Operation":
        if modulo is not None:
            return NotImplemented
        return Operation(BinaryOperator.POW, self, power)

    def __lshift__(self, other: Any) -> "Operation":
        return Operation(BinaryOperator.LSHIFT, self, other)

    def __rshift__(self, other: Any) -> "Operation":
        return Operation(BinaryOperator.RSHIFT, self, other)

    def __and__(self, other: Any) -> "Operation":
        return Operation(BinaryOperator.AND_BITWISE, self, other)

    def __xor__(self, other: Any) -> "Operation":
        return Operation(BinaryOperator.XOR_BITWISE, self, other)

    def __or__(self, other: Any) -> "Operation":
        return Operation(BinaryOperator.OR_BITWISE, self, other)

    def __radd__(self, other: Any) -> "Operation":
        return Operation(BinaryOperator.ADD, other, self)

    def __rsub__(self, other: Any) -> "Operation":
        return Operation(BinaryOperator.SUB, other, self)

    def __rmul__(self, other: Any) -> "Operation":
        return Operation(BinaryOperator.MUL, other, self)

    def __rmatmul__(self, other: Any) -> "Operation":
        return Operation(BinaryOperator.MATMUL, other, self)

    def __rtruediv__(self, other: Any) -> "Operation":
        return Operation(BinaryOperator.DIV, other, self)

    def __rfloordiv__(self, other: Any) -> "Operation":
        return Operation(BinaryOperator.FLOOR_DIV, other, self)

    def __rmod__(self, other: Any) -> "Operation":
        return Operation(BinaryOperator.MOD, other, self)

    def __rpow__(self, power: Any, modulo=None) -> "Operation":
        if modulo is not None:
            return NotImplemented
        return Operation(BinaryOperator.POW, (power, self))

    def __rlshift__(self, other: Any) -> "Operation":
        return Operation(BinaryOperator.LSHIFT, other, self)

    def __rrshift__(self, other: Any) -> "Operation":
        return Operation(BinaryOperator.RSHIFT, other, self)

    def __rand__(self, other: Any) -> "Operation":
        return Operation(BinaryOperator.AND_BITWISE, other, self)

    def __rxor__(self, other: Any) -> "Operation":
        return Operation(BinaryOperator.XOR_BITWISE, other, self)

    def __ror__(self, other: Any) -> "Operation":
        return Operation(BinaryOperator.OR_BITWISE, other, self)

    def __neg__(self) -> "UnaryOperation":
        return UnaryOperation(UnaryOperator.NEG, self)

    def __pos__(self) -> "UnaryOperation":
        return UnaryOperation(UnaryOperator.POS, self)

    def __invert__(self) -> "UnaryOperation":
        return UnaryOperation(UnaryOperator.INVERT, self)

    def __eq__(self, other: Any) -> "Operation":
        return Operation(BinaryOperator.EQ, self, other)

    def __ne__(self, other: Any) -> "Operation":
        return Operation(BinaryOperator.NEQ, self, other)

    def __gt__(self, other: Any) -> "Operation":
        return Operation(BinaryOperator.GT, self, other)

    def __ge__(self, other: Any) -> "Operation":
        return Operation(BinaryOperator.GE, self, other)

    def __lt__(self, other: Any) -> "Operation":
        return Operation(BinaryOperator.LT, self, other)

    def __le__(self, other: Any) -> "Operation":
        return Operation(BinaryOperator.LE, self, other)

    def __call__(self, *args: Any, **kwargs: Any) -> "Call":
        """
        Generate a :class:`.Call` expression.

        :return: the resulting expression
        """
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
        if key.startswith("_") or key.endswith("_"):
            raise AttributeError(key)
        else:
            return Attr(obj=self, attribute=key)

    def __setattr__(self, key: str, value: Any) -> None:
        if key.startswith("_") or key.endswith("_"):
            super().__setattr__(key, value)
        else:
            raise TypeError(f"cannot set public field of Expression: {key}")

    def __iter__(self) -> None:
        # we need to rule iteration out explicitly, otherwise we'd get infinite 'for'
        # loops through iterating via __getitem__
        raise TypeError(f"'{type(self).__name__}' object is not iterable: {repr(self)}")

    def __repr__(self) -> str:
        # get a textual representation of the expression using the default formatter
        return ExpressionFormatter.default(single_line=True).to_text(self)

    def __str__(self) -> str:
        # convert the expression to a formatted string using the default formatter
        return ExpressionFormatter.default(single_line=False).to_text(self)

    __hash__ = None


class FrozenExpression(HasExpressionRepr):
    """
    A frozen expression.

    Frozen expressions cannot be used as subexpressions in other expressions,
    but instead support Python's native semantics for equality and hashing.
    """

    def __init__(self, expression: Expression) -> None:
        """
        :param expression: the expression to be frozen
        """
        self._expression = expression

    def to_expression(self) -> "Expression":
        """
        Get the underlying un-frozen expression.

        :return: the underlying un-frozen expression
        """
        return self._expression

    def __eq__(self, other: "FrozenExpression") -> bool:
        return type(self) is type(other) and self._expression.eq_(other._expression)

    def __hash__(self) -> int:
        return self._expression.hash_()


def make_expression(value: Any) -> Expression:
    """
    Convert a Python :class:`object` into an expression.

    Expressions are generated as follows:

    - Instances of :class:`HasExpressionRepr` are converted by calling method
      :meth:`~.HasExpressionRepr.to_expression`
    - Python literals (strings, numbers) are converted to :class:`Lit` expressions
    - Python tuples, lists, sets, and dictionaries are converted to equivalent
      expressions, and all elements are converted to expressions recursively
    - Other iterables are converted to a :class:`Call` expression, with the
      name of the iterable as the callee, and its elements as the arguments
    - Other objects implementing the ``__name__`` attribute are converted to an
      :class:`Id` expression with the same name
    - All other values are converted to a :class:`Lit` expression

    :param value: value to convert to an expression
    :return: the resulting expression
    """

    if isinstance(value, HasExpressionRepr):
        return value.to_expression()
    elif isinstance(value, str):
        return Lit(value)
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
            Epsilon() if value is None else value
            for value in (value.start, value.stop, value.step)
        ]
        if value.step is not None:
            return Operation(BinaryOperator.SLICE, *args)
        else:
            return Operation(BinaryOperator.SLICE, args[0], args[1])
    elif isinstance(value, Iterable):
        return Call(Id(type(value)), *value)
    else:
        name: Optional[str] = getattr(value, "__name__", None)
        if name:
            return Id(value)
        else:

            return Lit(value)


def freeze(expression: Expression) -> FrozenExpression:
    """
    Convenience function to freeze an expression.

    Equivalent to ``FrozenExpression(expression)``.

    :param expression: the expression to freeze
    :return: the resulting frozen expression
    """
    return FrozenExpression(expression)


#
# Atomic expressions
#


@inheritdoc(match="[see superclass]")
class AtomicExpression(Expression, Generic[T], metaclass=ABCMeta):
    """
    An atomic expression.

    Atomic expressions include literals and identifiers, and have no subexpressions.
    """

    @property
    def subexpressions_(self) -> Tuple[Expression, ...]:
        """
        The subexpressions of this expression
        (an empty tuple, as this expression is atomic)
        """
        return ()

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
        return BinaryOperator.MAX_PRECEDENCE

    def _eq_same_type(self, other: "AtomicExpression") -> bool:
        return self.value_ == other.value_

    def hash_(self) -> int:
        """[see superclass]"""
        return hash((type(self), self.value_))


@inheritdoc(match="[see superclass]")
class Lit(AtomicExpression[T_Literal], Generic[T_Literal]):
    """
    A literal value (usually a number or string).
    """

    def __init__(self, value: T_Literal):
        """
        :param value: the literal value represented by this expression
        """
        super().__init__()
        self._value = value

    @property
    def value_(self) -> T_Literal:
        """[see superclass]"""
        return self._value

    @property
    def text_(self) -> str:
        """[see superclass]"""
        return repr(self.value_)


class _IdentifierMeta(type):
    _identifiers: Dict[str, "Id"] = WeakValueDictionary()

    def __getattr__(self, name: str) -> "Id":
        if name.startswith("_") or name.endswith("_") or name == "Id":
            # we do not allow creating identifiers with leading or trailing underscores
            # we also disallow "Id" to avoid a compatibility issue with sphinx
            raise AttributeError(name)

        identifier = _IdentifierMeta._identifiers.get(name, None)
        if not identifier:
            _IdentifierMeta._identifiers[name] = identifier = Id(name)

        return identifier


@inheritdoc(match="[see superclass]")
class Id(AtomicExpression[str], metaclass=compose_meta(_IdentifierMeta, ABCMeta)):
    """
    An identifier.

    Identifiers can be created either by

    - class instantiation: ``Id("x")``
    - attribute access: ``Id.x``

    The attribute access method will return the identical :class:`Id` instance
    for subsequent access to an attribute of the same name (stored internally using a
    weak reference dictionary).
    Attribute access requires attribute names that do not start or end with an
    underscore character (``_``), otherwise an :class:`AttributeError` is raised.
    For compatibility reasons, attribute access does not work for the ``Id`` name, i.e.,
    ``Id.Id`` will raise an :class:`AttributeError`.
    """

    def __init__(self, name: Any) -> None:
        """
        :param name: the name of the identifier
        """
        super().__init__()
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

    @property
    def text_(self) -> str:
        """[see superclass]"""
        return self._name


@inheritdoc(match="[see superclass]")
class Epsilon(AtomicExpression[None], metaclass=compose_meta(ABCMeta, SingletonMeta)):
    """
    A singleton class representing the empty expression.
    """

    @property
    def value_(self) -> None:
        """[see superclass]"""
        return None

    @property
    def text_(self) -> str:
        """[see superclass]"""
        return ""


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
        The subexpression of this expression
        """

    @property
    def subexpressions_(self) -> Tuple[Expression, ...]:
        """
        A tuple with the this expression's subexpression as its only element
        """
        return (self.subexpression_,)


#
# Bracketed expressions
#


@inheritdoc(match="[see superclass]")
class BracketPair(HasExpressionRepr):
    """
    A pair of brackets.
    """

    #: a pair of round brackets
    ROUND = None
    #: a pair of square brackets
    SQUARE = None
    #: a pair of curly brackets
    CURLY = None
    #: a pair of angled brackets
    ANGLED = None

    #: the opening bracket
    opening: str
    #: the closing bracket
    closing: str

    def __init__(self, opening: str, closing: str) -> None:
        """
        :param opening: the opening bracket
        :param closing: the closing bracket
        """
        self.opening = opening
        self.closing = closing

    def to_expression(self) -> Expression:
        """[see superclass]"""
        return Id.BracketPair(opening=self.opening, closing=self.closing)


BracketPair.ROUND = BracketPair("(", ")")
BracketPair.SQUARE = BracketPair("[", "]")
BracketPair.CURLY = BracketPair("{", "}")
BracketPair.ANGLED = BracketPair("<", ">")


@inheritdoc(match="[see superclass]")
class BracketedExpression(SingletonExpression, metaclass=ABCMeta):
    """
    An expression surrounded by brackets.
    """

    def __init__(self, brackets: BracketPair, subexpression: Any) -> None:
        """
        :param brackets: the brackets enclosing this expression's subexpressions
        :param subexpression: the subexpression enclosed by brackets
        """
        super().__init__()
        self._brackets = brackets
        self._subexpression = make_expression(subexpression)

    @property
    def brackets_(self) -> BracketPair:
        """
        The brackets enclosing this expression's subexpressions
        """
        return self._brackets

    @property
    def subexpression_(self) -> Expression:
        """
        The subexpression enclosed by the brackets
        """
        return self._subexpression

    @property
    def precedence_(self) -> int:
        """[see superclass]"""
        return Operator.MAX_PRECEDENCE

    def hash_(self) -> int:
        """[see superclass]"""
        return hash((type(self), self.brackets_, self.subexpression_.hash_()))

    def _eq_same_type(self, other: "BracketedExpression") -> bool:
        return self.brackets_ == other.brackets_ and self.subexpression_.eq_(
            other.subexpression_
        )


class CollectionLiteral(BracketedExpression):
    """
    A collection literal, e.g., a list, set, tuple, or dictionary.
    """

    def __init__(self, brackets: BracketPair, elements: Iterable[Any]) -> None:
        """
        :param brackets: the brackets enclosing the collection
        :param elements: the elements of the collection
        """
        elements: Tuple[Expression, ...] = tuple(
            make_expression(element) for element in elements
        )

        subexpression: Expression
        if not elements:
            subexpression = Epsilon()
        elif len(elements) == 1:
            subexpression = elements[0]
        else:
            subexpression = Operation(BinaryOperator.COMMA, *elements)

        super().__init__(brackets, subexpression)

        self._elements = elements

    @property
    def subexpression_(self) -> Expression:
        """
        The subexpression representing the element(s) of this collection literal

        - an :class:`Epsilon` expression for an empty collection
        - an arbitrary expression for a collection with a single element
        - an :class:`Operation` with a :attr:`pytools.expression.operator.COMMA`
          operator for collections with two or more elements
        """
        return super().subexpression_

    @property
    def elements_(self) -> Tuple[Expression]:
        """
        The expression(s) representing the elements of this expression
        """
        return self._elements


class ListLiteral(CollectionLiteral):
    """
    A list expression.
    """

    def __init__(self, *elements: Any):
        """
        :param elements: the list elements
        """
        super().__init__(brackets=BracketPair.SQUARE, elements=elements)


class TupleLiteral(CollectionLiteral):
    """
    A tuple expression.
    """

    def __init__(self, *elements: Any):
        """
        :param elements: the tuple elements
        """
        super().__init__(brackets=BracketPair.ROUND, elements=elements)


class SetLiteral(CollectionLiteral):
    """
    A set expression.
    """

    def __init__(self, *elements: Any):
        """
        :param elements: the set elements
        """
        super().__init__(brackets=BracketPair.CURLY, elements=elements)


class DictLiteral(CollectionLiteral):
    """
    A dictionary expression.
    """

    def __init__(self, *args: Tuple[Any, Any], **kwargs: Tuple[str, Any]):
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
class BaseOperation(Expression, metaclass=ABCMeta):
    """
    Abstract base class for operation expressions.
    """

    @property
    def subexpressions_(self) -> Tuple["Expression", ...]:
        """[see superclass]"""
        return self.operands_

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
        The operands of this operation; same as :attr:`subexpressions_`
        """
        pass


#
# Prefix expressions
#


@inheritdoc(match="[see superclass]")
class PrefixExpression(Expression, metaclass=ABCMeta):
    """
    A prefix expression.

    Combines a prefix and a subexpression, optionally separated by one or more
    characters.
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
        The body of this expression
        """
        pass

    @property
    def subexpressions_(self) -> Tuple[Expression, ...]:
        """
        A tuple containing the prefix and the body of this expression
        """
        return self.prefix_, self.body_

    def _eq_same_type(self, other: "PrefixExpression") -> bool:
        return self.prefix_.eq_(other.prefix_) and self.body_.eq_(other.body_)

    def hash_(self) -> int:
        """[see superclass]"""
        return hash(
            (type(self), self.prefix_.hash_(), self.separator_, self.body_.hash_())
        )


@inheritdoc(match="[see superclass]")
class SimplePrefixExpression(PrefixExpression, metaclass=ABCMeta):
    """
    An abstract base implementation of simple prefix expressions.
    """

    def __init__(self, prefix: Any, body: Any):
        """
        :param prefix: the prefix of the expression
        :param body: the body of the expression
        """
        super().__init__()
        self._prefix = make_expression(prefix)
        self._body = make_expression(body)

    @property
    def prefix_(self) -> Expression:
        """[see superclass]"""
        return self._prefix

    @property
    def body_(self) -> Expression:
        """[see superclass]"""
        return self._body


@inheritdoc(match="[see superclass]")
class UnaryOperation(SimplePrefixExpression, BaseOperation, metaclass=ABCMeta):
    """
    A unary operation.
    """

    def __init__(self, operator: UnaryOperator, operand: Any):
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
class KeywordArgument(SimplePrefixExpression):
    """
    A keyword argument, used by functions.
    """

    _PRECEDENCE = BinaryOperator.EQ.precedence

    def __init__(self, name: str, value: Any):
        """
        :param name: the name of the keyword
        :param value: the value for the keyword
        """
        super().__init__(prefix=Id(name), body=value)
        self._name = name

    @property
    def name_(self) -> str:
        """
        The name of this keyword argument.
        """
        return self._name

    @property
    def separator_(self) -> str:
        """[see superclass]"""
        return "="

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


@inheritdoc(match="[see superclass]")
class DictEntry(SimplePrefixExpression):
    """
    Two expressions separated by a colon, used in dictionaries.
    """

    _PRECEDENCE = BinaryOperator.COLON.precedence

    def __init__(self, key: Any, value: Any):
        """
        :param key: the key of the dictionary entry
        :param value: the value of the dictionary entry
        """
        super().__init__(prefix=key, body=value)

    @property
    def key_(self) -> Expression:
        """
        The key of this dictionary entry; identical with the expression prefix
        """
        return self.prefix_

    @property
    def separator_(self) -> str:
        """A ``:``, followed by a space"""
        return ": "

    @property
    def value_(self) -> Expression:
        """
        The value of this dictionary entry; identical with the expression body
        """
        return self.body_

    @property
    def precedence_(self) -> int:
        """[see superclass]"""
        return DictEntry._PRECEDENCE


@inheritdoc(match="[see superclass]")
class Invocation(PrefixExpression):
    """
    An invocation in the shape of ``<expression>(<expression>)`` or
    ``<expression>[<expression>]``.
    """

    _PRECEDENCE = BinaryOperator.DOT.precedence

    def __init__(self, prefix: Any, brackets: BracketPair, args: Iterable[Any]):
        """
        :param prefix: the expression representing the object being invoked
        :param brackets: the brackets surrounding the invocation argument(s)
        :param args: the invocation argument(s); can also be an empty iterable
        """
        super().__init__()
        self._prefix = make_expression(prefix)
        self._invocation = CollectionLiteral(brackets=brackets, elements=args)

    @property
    def prefix_(self) -> Expression:
        """[see superclass]"""
        return self._prefix

    @property
    def body_(self) -> CollectionLiteral:
        """
        The expression representing the arguments enclosed by brackets
        """
        return self._invocation

    @property
    def precedence_(self) -> int:
        """[see superclass]"""
        return Invocation._PRECEDENCE


class Call(Invocation):
    """
    A call expression.
    """

    def __init__(self, callee: Any, *args: Any, **kwargs: Any):
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
                *(
                    KeywordArgument(name, expression)
                    for name, expression in kwargs.items()
                ),
            ),
        )

    @property
    def callee_(self) -> Expression:
        """
        The expression being called; identical with the prefix of this expression
        """
        return self.prefix_


class Index(Invocation):
    """
    An indexing operation.
    """

    def __init__(self, collection: Any, key: Any):
        """
        :param collection: the collection to be indexed
        :param key: the index key
        """
        keys = key if isinstance(key, tuple) else (key,)
        super().__init__(prefix=collection, brackets=BracketPair.SQUARE, args=keys)

    @property
    def collection_(self) -> Expression:
        """
        The collection to be indexed; same as :attr:`prefix_`
        """
        return self.prefix_


@inheritdoc(match="[see superclass]")
class LambdaDefinition(SimplePrefixExpression):
    """
    Function parameters and body separated by a colon, used inside lambda expressions.
    """

    _PRECEDENCE = UnaryOperator.LAMBDA.precedence

    def __init__(self, *params: Id, body: Any):
        """
        :param params: the parameters of the lambda expression
        :param body: the body of the lambda expression
        """
        if not params:
            params_expression = Epsilon()
        elif len(params) == 1:
            params_expression = params[0]
        else:
            params_expression = Operation(operator=BinaryOperator.COMMA, *params)
        super().__init__(prefix=params_expression, body=body)

    @property
    def params_(self) -> Expression:
        """
        The parameters of the lambda expression.
        """
        return self.prefix_

    @property
    def separator_(self) -> str:
        """A ``:``, followed by a space"""
        return ": "

    @property
    def precedence_(self) -> int:
        """[see superclass]"""
        return LambdaDefinition._PRECEDENCE


@inheritdoc(match="[see superclass]")
class Lambda(SimplePrefixExpression):
    """
    A lambda expression.
    """

    _PRECEDENCE = UnaryOperator.LAMBDA.precedence

    def __init__(self, *params: Id, body: Any):
        """
        :param params: the parameters of the lambda expression
        :param body: the body of the lambda expression
        """
        super().__init__(prefix=Epsilon(), body=LambdaDefinition(*params, body=body))

    @property
    def precedence_(self) -> int:
        """[see superclass]"""
        return Lambda._PRECEDENCE

    @property
    def separator_(self) -> str:
        """[see superclass]"""
        return f"{UnaryOperator.LAMBDA.symbol} "


#
# BinaryOperator expressions
#


@inheritdoc(match="[see superclass]")
class InfixExpression(Expression, metaclass=ABCMeta):
    """
    An infix expression, separating any number of subexpressions with an infix symbol.
    """

    @property
    @abstractmethod
    def infix_(self) -> BinaryOperator:
        """
        The infix used to separate this expression's subexpressions
        """
        pass

    def hash_(self) -> int:
        """[see superclass]"""
        return hash(
            (
                type(self),
                self.infix_,
                *(subexpression.hash_() for subexpression in self.subexpressions_),
            )
        )

    def _eq_same_type(self, other: "InfixExpression") -> bool:
        return self.infix_ == other.infix_ and all(
            a.eq_(b) for a, b in zip(self.subexpressions_, other.subexpressions_)
        )


@inheritdoc(match="[see superclass]")
class Operation(InfixExpression, BaseOperation):
    """
    A operation with two or more operands.
    """

    def __init__(self, operator: BinaryOperator, *operands: Any):
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

        if isinstance(first_operand, Operation):
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


class Attr(Operation):
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
        elif not isinstance(attribute, Id):
            raise TypeError("arg attribute must be a string or an Identifier")

        if isinstance(obj, Attr):
            sub = obj.subexpressions_
            super().__init__(BinaryOperator.DOT, sub[0], *(sub[1:]), attribute)
        else:
            super().__init__(BinaryOperator.DOT, obj, attribute)


#
# Expression alias
#


@inheritdoc(match="[see superclass]")
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
        """
        :param expression: the expression referred to by this alias
        """
        super().__init__()
        self._expression = expression

    @property
    def expression_(self) -> Expression:
        """
        The expression represented by this alias; may be set to a new expression
        """
        return self._expression

    @expression_.setter
    def expression_(self, expression: Expression) -> None:
        """
        Set the expression represented by this alias

        :param expression: the expression to be set
        """
        self._expression = expression

    @property
    def precedence_(self) -> int:
        """[see superclass]"""
        return self.expression_.precedence_

    @property
    def subexpression_(self) -> Expression:
        """[see superclass]"""
        return self._expression

    def hash_(self) -> int:
        """[see superclass]"""
        return self.expression_.hash_()

    def _eq_same_type(self, other: "ExpressionAlias") -> bool:
        return self._expression.eq_(other._expression)


__tracker.validate()

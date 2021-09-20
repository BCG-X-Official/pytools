"""
Implementation of :mod:`pytools.expression` and subpackages.
"""
import logging
from abc import ABCMeta, abstractmethod
from typing import Any, Generic, Iterable, Tuple, TypeVar

from ...api import AllTracker, inheritdoc
from .. import Expression, HasExpressionRepr, make_expression
from ..operator import BinaryOperator, Operator

log = logging.getLogger(__name__)


#
# Exported names
#

__all__ = [
    "AtomicExpression",
    "SingletonExpression",
    "BracketPair",
    "BracketedExpression",
    "CollectionLiteral",
    "Operation",
    "PrefixExpression",
    "SimplePrefixExpression",
    "Invocation",
    "InfixExpression",
]

#
# Type variables
#

T = TypeVar("T")


#
# Ensure all symbols introduced below are included in __all__
#

__tracker = AllTracker(globals())


#
# Class definitions
#


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
        (an empty tuple, as this expression is atomic).
        """
        return ()

    @property
    @abstractmethod
    def text_(self) -> str:
        """
        The text representing this atomic expression.
        """
        pass

    @property
    @abstractmethod
    def value_(self) -> T:
        """
        The underlying value of this atomic expression.
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
        """
        A tuple with the this expression's subexpression as its only element.
        """
        return (self.subexpression_,)


#
# Bracketed expressions
#

# noinspection PyTypeHints,PyTypeChecker
_BracketPair = TypeVar("BracketPair", bound="BracketPair")


@inheritdoc(match="[see superclass]")
class BracketPair(HasExpressionRepr):
    """
    A pair of brackets.
    """

    #: A pair of round brackets.
    ROUND: _BracketPair = None
    #: A pair of square brackets.
    SQUARE: _BracketPair = None
    #: A pair of curly brackets.
    CURLY: _BracketPair = None
    #: A pair of angled brackets.
    ANGLED: _BracketPair = None

    #: The opening bracket.
    opening: str
    #: The closing bracket.
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
        from ..atomic import Id

        return Id(BracketPair.__name__)(opening=self.opening, closing=self.closing)


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
        The brackets enclosing this expression's subexpressions.
        """
        return self._brackets

    @property
    def subexpression_(self) -> Expression:
        """
        The subexpression enclosed by the brackets.
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

        from ..atomic import Epsilon
        from ..composite import BinaryOperation

        elements: Tuple[Expression, ...] = tuple(map(make_expression, elements))

        subexpression: Expression
        if not elements:
            subexpression = Epsilon()
        elif len(elements) == 1:
            subexpression = elements[0]
        else:
            subexpression = BinaryOperation(BinaryOperator.COMMA, *elements)

        super().__init__(brackets, subexpression)

        self._elements = elements

    @property
    def subexpression_(self) -> Expression:
        """
        The subexpression representing the element(s) of this collection literal

        - an :class:`.Epsilon` expression for an empty collection
        - an arbitrary expression for a collection with a single element
        - a :class:`.BinaryOperation` with a :attr:`.BinaryOperator.COMMA`
          operator for collections with two or more elements
        """
        return super().subexpression_

    @property
    def elements_(self) -> Tuple[Expression]:
        """
        The expression(s) representing the elements of this expression.
        """
        return self._elements


#
# Operations
#


@inheritdoc(match="[see superclass]")
class Operation(Expression, metaclass=ABCMeta):
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
        The operator of this operation.
        """
        pass

    @property
    @abstractmethod
    def operands_(self) -> Tuple[Expression, ...]:
        """
        The operands of this operation; same as :attr:`subexpressions_`.
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
        The prefix of this expression.
        """
        pass

    @property
    def separator_(self) -> str:
        """
        One or more characters separating the prefix and the subexpression.
        """
        return ""

    @property
    @abstractmethod
    def body_(self) -> Expression:
        """
        The body of this expression.
        """
        pass

    @property
    def subexpressions_(self) -> Tuple[Expression, ...]:
        """
        A tuple containing the prefix and the body of this expression.
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

    def __init__(self, prefix: Any, body: Any) -> None:
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
class Invocation(PrefixExpression):
    """
    An invocation in the shape of ``<expression>(<expression>)`` or
    ``<expression>[<expression>]``.
    """

    _PRECEDENCE = BinaryOperator.DOT.precedence

    def __init__(self, prefix: Any, brackets: BracketPair, args: Iterable[Any]) -> None:
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
        The expression representing the arguments enclosed by brackets.
        """
        return self._invocation

    @property
    def precedence_(self) -> int:
        """[see superclass]"""
        return Invocation._PRECEDENCE


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
        The infix used to separate this expression's subexpressions.
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


__tracker.validate()

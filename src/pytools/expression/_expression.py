"""
Implementation of :mod:`pytools.expression` and subpackages.
"""
import logging
from abc import ABCMeta, abstractmethod
from typing import Any, Optional, Tuple, TypeVar

import numpy as np

from ..api import AllTracker, inheritdoc, to_list
from .operator import BinaryOperator, UnaryOperator

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
    "ExpressionAlias",
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


class ExpressionFormatter(metaclass=ABCMeta):
    """
    Generates text representations of expression objects.

    This is an abstract base class; use :meth:`default` to create a default expression
    formatter.
    """

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
        Get the default expression formatter, formatting expression objects as
        `Python` expressions with correct spacing and formatting.

        :param single_line: if ``True``, return a formatter that does not generate line
            breaks
        :return: a :class:`.PythonExpressionFormatter` with default parameters for all
            formatting settings except for ``single_line``
        """
        from .formatter import PythonExpressionFormatter

        return PythonExpressionFormatter(single_line=single_line)


class HasExpressionRepr(metaclass=ABCMeta):
    """
    Mix-in class for arbitrary classes, rendering :func:`repr` and :class:`str`
    representations using expression objects.
    """

    __ATTR_CLASS_ID = "__HasExpressionRepr__class_id"

    @abstractmethod
    def to_expression(self) -> "Expression":
        """
        Render this object as an expression.

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
    A representation of an expression.
    """

    @property
    @abstractmethod
    def precedence_(self) -> int:
        """
        The precedence of this expression, used to determine the need for parentheses.
        """
        pass

    @property
    @abstractmethod
    def subexpressions_(self) -> Tuple["Expression", ...]:
        """
        The subexpressions of this expression.
        """

    def or_(self, other: "Expression") -> "Expression":
        """
        Create a logical `or` expression using this and another expression as operands.

        :param other: other operand to combine with this expression using a logical `or`
        :return: the logical `or` expression
        """
        from .composite import BinaryOperation

        return BinaryOperation(BinaryOperator.OR, self, other)

    def and_(self, other: "Expression") -> "Expression":
        """
        Create a logical `and` expression using this and another expression as operands.

        :param other: other operand to combine with this expression using a logical
            `and`
        :return: the logical `and` expression
        """
        from .composite import BinaryOperation

        return BinaryOperation(BinaryOperator.AND, self, other)

    def not_(self) -> "Expression":
        """
        Create a logical `not` expression using this expression as the operand.

        :return: the logical `not` expression
        """
        from .composite import UnaryOperation

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
        Calculate the hash code for this expression.

        For using Python's native ``hash`` function, see :class:`.FrozenExpression`.

        :return: the hash code for this expression
        """
        pass

    def to_expression(self) -> "Expression":
        """[see superclass]"""
        return self

    @abstractmethod
    def _eq_same_type(self: T, other: T) -> bool:
        # assuming other is the same type as self, check if self and other are equal
        pass

    def __add__(self, other: Any) -> "Expression":
        from .composite import BinaryOperation

        return BinaryOperation(BinaryOperator.ADD, self, other)

    def __sub__(self, other: Any) -> "Expression":
        from .composite import BinaryOperation

        return BinaryOperation(BinaryOperator.SUB, self, other)

    def __mul__(self, other: Any) -> "Expression":
        from .composite import BinaryOperation

        return BinaryOperation(BinaryOperator.MUL, self, other)

    def __matmul__(self, other: Any) -> "Expression":
        from .composite import BinaryOperation

        return BinaryOperation(BinaryOperator.MATMUL, self, other)

    def __truediv__(self, other: Any) -> "Expression":
        from .composite import BinaryOperation

        return BinaryOperation(BinaryOperator.DIV, self, other)

    def __floordiv__(self, other: Any) -> "Expression":
        from .composite import BinaryOperation

        return BinaryOperation(BinaryOperator.FLOOR_DIV, self, other)

    def __mod__(self, other: Any) -> "Expression":
        from .composite import BinaryOperation

        return BinaryOperation(BinaryOperator.MOD, self, other)

    def __pow__(self, power: Any, modulo=None) -> "Expression":
        if modulo is not None:
            return NotImplemented
        from .composite import BinaryOperation

        return BinaryOperation(BinaryOperator.POW, self, power)

    def __lshift__(self, other: Any) -> "Expression":
        from .composite import BinaryOperation

        return BinaryOperation(BinaryOperator.LSHIFT, self, other)

    def __rshift__(self, other: Any) -> "Expression":
        from .composite import BinaryOperation

        return BinaryOperation(BinaryOperator.RSHIFT, self, other)

    def __and__(self, other: Any) -> "Expression":
        from .composite import BinaryOperation

        return BinaryOperation(BinaryOperator.AND_BITWISE, self, other)

    def __xor__(self, other: Any) -> "Expression":
        from .composite import BinaryOperation

        return BinaryOperation(BinaryOperator.XOR_BITWISE, self, other)

    def __or__(self, other: Any) -> "Expression":
        from .composite import BinaryOperation

        return BinaryOperation(BinaryOperator.OR_BITWISE, self, other)

    def __radd__(self, other: Any) -> "Expression":
        from .composite import BinaryOperation

        return BinaryOperation(BinaryOperator.ADD, other, self)

    def __rsub__(self, other: Any) -> "Expression":
        from .composite import BinaryOperation

        return BinaryOperation(BinaryOperator.SUB, other, self)

    def __rmul__(self, other: Any) -> "Expression":
        from .composite import BinaryOperation

        return BinaryOperation(BinaryOperator.MUL, other, self)

    def __rmatmul__(self, other: Any) -> "Expression":
        from .composite import BinaryOperation

        return BinaryOperation(BinaryOperator.MATMUL, other, self)

    def __rtruediv__(self, other: Any) -> "Expression":
        from .composite import BinaryOperation

        return BinaryOperation(BinaryOperator.DIV, other, self)

    def __rfloordiv__(self, other: Any) -> "Expression":
        from .composite import BinaryOperation

        return BinaryOperation(BinaryOperator.FLOOR_DIV, other, self)

    def __rmod__(self, other: Any) -> "Expression":
        from .composite import BinaryOperation

        return BinaryOperation(BinaryOperator.MOD, other, self)

    def __rpow__(self, power: Any, modulo=None) -> "Expression":
        if modulo is not None:
            return NotImplemented
        from .composite import BinaryOperation

        return BinaryOperation(BinaryOperator.POW, (power, self))

    def __rlshift__(self, other: Any) -> "Expression":
        from .composite import BinaryOperation

        return BinaryOperation(BinaryOperator.LSHIFT, other, self)

    def __rrshift__(self, other: Any) -> "Expression":
        from .composite import BinaryOperation

        return BinaryOperation(BinaryOperator.RSHIFT, other, self)

    def __rand__(self, other: Any) -> "Expression":
        from .composite import BinaryOperation

        return BinaryOperation(BinaryOperator.AND_BITWISE, other, self)

    def __rxor__(self, other: Any) -> "Expression":
        from .composite import BinaryOperation

        return BinaryOperation(BinaryOperator.XOR_BITWISE, other, self)

    def __ror__(self, other: Any) -> "Expression":
        from .composite import BinaryOperation

        return BinaryOperation(BinaryOperator.OR_BITWISE, other, self)

    def __neg__(self) -> "Expression":
        from .composite import UnaryOperation

        return UnaryOperation(UnaryOperator.NEG, self)

    def __pos__(self) -> "Expression":
        from .composite import UnaryOperation

        return UnaryOperation(UnaryOperator.POS, self)

    def __invert__(self) -> "Expression":
        from .composite import UnaryOperation

        return UnaryOperation(UnaryOperator.INVERT, self)

    def __eq__(self, other: Any) -> "Expression":
        from .composite import BinaryOperation

        return BinaryOperation(BinaryOperator.EQ, self, other)

    def __ne__(self, other: Any) -> "Expression":
        from .composite import BinaryOperation

        return BinaryOperation(BinaryOperator.NEQ, self, other)

    def __gt__(self, other: Any) -> "Expression":
        from .composite import BinaryOperation

        return BinaryOperation(BinaryOperator.GT, self, other)

    def __ge__(self, other: Any) -> "Expression":
        from .composite import BinaryOperation

        return BinaryOperation(BinaryOperator.GE, self, other)

    def __lt__(self, other: Any) -> "Expression":
        from .composite import BinaryOperation

        return BinaryOperation(BinaryOperator.LT, self, other)

    def __le__(self, other: Any) -> "Expression":
        from .composite import BinaryOperation

        return BinaryOperation(BinaryOperator.LE, self, other)

    def __call__(self, *args: Any, **kwargs: Any) -> "Expression":
        """
        Generate a :class:`.Call` expression.

        :return: the resulting expression
        """
        from .composite import Call

        return Call(self, *args, **kwargs)

    def __getitem__(self, key: Any) -> "Expression":
        from .composite import Index

        return Index(self, key)

    def __setitem__(self, key: Any, value: Any) -> None:
        raise TypeError(f"cannot set indexed item of Expression: {to_list(key)}")

    def __delitem__(self, key: Any) -> None:
        raise TypeError(f"cannot delete indexed item of Expression: {to_list(key)}")

    def __getattr__(self, key: str) -> "Expression":
        if key.startswith("_") or key.endswith("_"):
            raise AttributeError(key)
        else:
            from .composite import Attr

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

    def __bool__(self) -> bool:
        raise TypeError(f"{Expression.__name__} does not permit casting to bool type")

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
    - Numpy arrays are converted to ``array(…)`` expressions, and all elements
      are converted to expressions recursively
    - Other objects implementing the ``__name__`` attribute are converted to an
      :class:`Id` expression with the same name
    - All other values are converted to a :class:`Lit` expression

    :param value: value to convert to an expression
    :return: the resulting expression
    """

    if isinstance(value, HasExpressionRepr):
        return value.to_expression()
    elif isinstance(value, str):
        from .atomic import Lit

        return Lit(value)
    elif isinstance(value, list):
        from .composite import ListLiteral

        return ListLiteral(*value)
    elif isinstance(value, tuple):
        from .composite import TupleLiteral

        return TupleLiteral(*value)
    elif isinstance(value, set):
        from .composite import SetLiteral

        return SetLiteral(*value)
    elif isinstance(value, dict):
        from .composite import DictLiteral

        return DictLiteral(*value.items())
    elif isinstance(value, np.ndarray):
        from .atomic import Id
        from .composite import ListLiteral

        def _ndarray_to_expression(array: np.ndarray) -> Expression:
            if array.ndim == 0:
                return array[()]
            if array.ndim == 1:
                return ListLiteral(*array)
            else:
                return ListLiteral(*map(_ndarray_to_expression, array))

        return Id.array(_ndarray_to_expression(value))

    elif isinstance(value, slice):
        from .atomic import Epsilon
        from .composite import BinaryOperation

        args = [
            Epsilon() if value is None else value
            for value in (value.start, value.stop, value.step)
        ]
        if value.step is not None:
            return BinaryOperation(BinaryOperator.SLICE, *args)
        else:
            return BinaryOperation(BinaryOperator.SLICE, args[0], args[1])
    else:
        name: Optional[str] = getattr(value, "__name__", None)
        if name:
            from .atomic import Id

            return Id(value)
        else:
            from .atomic import Lit

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
# Expression alias
#


@inheritdoc(match="[see superclass]")
class ExpressionAlias(Expression):
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
        The expression represented by this alias; may be set to a new expression.
        """
        return self._expression

    @expression_.setter
    def expression_(self, expression: Expression) -> None:
        """
        Set the expression represented by this alias.

        :param expression: the expression to be set
        """
        self._expression = expression

    @property
    def precedence_(self) -> int:
        """[see superclass]"""
        return self.expression_.precedence_

    @property
    def subexpressions_(self) -> Tuple["Expression", ...]:
        """[see superclass]"""
        return (self._expression,)

    def hash_(self) -> int:
        """[see superclass]"""
        return self.expression_.hash_()

    def _eq_same_type(self, other: "ExpressionAlias") -> bool:
        return self._expression.eq_(other._expression)


__tracker.validate()

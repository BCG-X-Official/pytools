import logging
from abc import ABCMeta, abstractmethod
from typing import Mapping, Optional, Set, Tuple

from pytools.api import AllTracker

log = logging.getLogger(__name__)

__all__ = [
    "Operator",
    "BinaryOperator",
    "UnaryOperator",
    "DOT",
    "POW",
    "POS",
    "NEG",
    "MUL",
    "MATMUL",
    "DIV",
    "TRUE_DIV",
    "FLOOR_DIV",
    "INVERT",
    "MOD",
    "ADD",
    "SUB",
    "LSHIFT",
    "RSHIFT",
    "AND_BITWISE",
    "XOR_BITWISE",
    "OR_BITWISE",
    "IN",
    "NOT_IN",
    "IS",
    "IS_NOT",
    "LT",
    "LE",
    "GT",
    "GE",
    "NEQ_",
    "NEQ",
    "EQ",
    "NOT",
    "AND",
    "OR",
    "LAMBDA",
    "ASSIGN",
    "COLON",
    "SLICE",
    "COMMA",
    "NONE",
    "MIN_PRECEDENCE",
    "MAX_PRECEDENCE",
]

__tracker = AllTracker(globals_=globals())


class Operator(metaclass=ABCMeta):
    """
    Base class for operators used in expressions
    """

    def __init__(self, symbol: str, precedence: Optional[int] = None) -> None:
        self.symbol = symbol
        self._precedence = precedence

    @property
    @abstractmethod
    def is_unary(self) -> bool:
        """
        ``True`` if this is a unary operator
        """
        pass

    @property
    def precedence(self) -> int:
        return (
            _OPERATOR_PRECEDENCE.get(self, MIN_PRECEDENCE)
            if self._precedence is None
            else self._precedence
        )

    def __repr__(self) -> str:
        return f"Operator({self.symbol})@{id(self)}"

    def __str__(self) -> str:
        return self.symbol


class BinaryOperator(Operator):
    """
    A binary operator
    """

    @property
    def is_unary(self) -> bool:
        """[see superclass]"""
        return False

    is_unary.__doc__ = Operator.is_unary.__doc__


class UnaryOperator(Operator):
    """
    A unary rator
    """

    @property
    def is_unary(self) -> bool:
        """[see superclass]"""
        return True

    is_unary.__doc__ = Operator.is_unary.__doc__


DOT = BinaryOperator(".")
POW = BinaryOperator("**")
POS = UnaryOperator("+")
NEG = UnaryOperator("-")
MUL = BinaryOperator("*")
MATMUL = BinaryOperator("@")
DIV = TRUE_DIV = BinaryOperator("/")
FLOOR_DIV = BinaryOperator("//")
INVERT = UnaryOperator("~")
MOD = BinaryOperator("%")
ADD = BinaryOperator("+")
SUB = BinaryOperator("-")
LSHIFT = BinaryOperator("<<")
RSHIFT = BinaryOperator(">>")
AND_BITWISE = BinaryOperator("&")
XOR_BITWISE = BinaryOperator("^")
OR_BITWISE = BinaryOperator("|")
IN = BinaryOperator("in")
NOT_IN = BinaryOperator("not in")
IS = BinaryOperator("is")
IS_NOT = BinaryOperator("is not")
LT = BinaryOperator("<")
LE = BinaryOperator("<=")
GT = BinaryOperator(">")
GE = BinaryOperator(">=")
NEQ_ = BinaryOperator("<>")
NEQ = BinaryOperator("!=")
EQ = BinaryOperator("==")
NOT = UnaryOperator("not")
AND = BinaryOperator("and")
OR = BinaryOperator("or")
LAMBDA = UnaryOperator("lambda")
ASSIGN = BinaryOperator("=")
COLON = BinaryOperator(":")
SLICE = BinaryOperator(":")
COMMA = BinaryOperator(",")
NONE = BinaryOperator("")


__OPERATOR_PRECEDENCE_ORDER: Tuple[Set[Operator], ...] = (
    {COMMA},
    {ASSIGN, COLON, SLICE},
    {LAMBDA},
    {OR},
    {AND},
    {NOT},
    {NEQ_, NEQ, EQ},
    {IN, NOT_IN, IS, IS_NOT, LT, LE, GT, GE},
    {OR_BITWISE},
    {XOR_BITWISE},
    {AND_BITWISE},
    {LSHIFT, RSHIFT},
    {ADD, SUB},
    {MUL, MATMUL, DIV, FLOOR_DIV, MOD},
    {POS, NEG},
    {INVERT},
    {POW},
    {DOT},
)

_OPERATOR_PRECEDENCE: Mapping[Operator, int] = {
    operator: priority
    for priority, operators in enumerate(__OPERATOR_PRECEDENCE_ORDER)
    for operator in operators
}
MIN_PRECEDENCE = -1
MAX_PRECEDENCE = len(__OPERATOR_PRECEDENCE_ORDER)


__tracker.validate()

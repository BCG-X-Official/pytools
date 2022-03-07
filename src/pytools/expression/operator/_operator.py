"""
Operators used in expressions.
"""
from __future__ import annotations

import logging
from abc import ABCMeta, abstractmethod
from typing import Mapping, Optional, Set, Tuple

from pytools.api import AllTracker

log = logging.getLogger(__name__)

__all__ = [
    "Operator",
    "BinaryOperator",
    "UnaryOperator",
]

__tracker = AllTracker(globals_=globals())


class Operator(metaclass=ABCMeta):
    """
    Base class for operators used in expressions.
    """

    #: the symbol representing this operator
    symbol: str

    #: Minimal value for :attr:`.precedence` (lower than the precedence of any
    #: Python operator).
    MIN_PRECEDENCE: int = -1

    #: Largest possible value of :attr:`.precedence` for default operators.
    MAX_PRECEDENCE: int

    def __init__(self, symbol: str, precedence: Optional[int] = None) -> None:
        """
        :param symbol: the symbol representing this operator
        :param precedence: the precedence of this operator; defaults to Python's
            standard precedence for symbols representing Python operators, and to
            :attr:`MIN_PRECEDENCE` for all other operators
        """
        self.symbol = symbol
        self._precedence = precedence

    @property
    @abstractmethod
    def is_unary(self) -> bool:
        """
        ``True`` if this is a unary operator.
        """
        pass

    @property
    def precedence(self) -> int:
        """
        The precedence of this operator (higher integers denote higher precedence).
        """
        return (
            _OPERATOR_PRECEDENCE.get(self, Operator.MIN_PRECEDENCE)
            if self._precedence is None
            else self._precedence
        )

    def __repr__(self) -> str:
        precedence = (
            f", precedence={self._precedence}" if self._precedence is not None else ""
        )
        return f'{type(self).__name__}("{self.symbol}"{precedence})'

    def __str__(self) -> str:
        return self.symbol


class BinaryOperator(Operator):
    """
    A binary operator.
    """

    #: Inherited from :attr:`.Operator.MIN_PRECEDENCE`.
    MIN_PRECEDENCE: int

    #: Inherited from :attr:`.Operator.MAX_PRECEDENCE`.
    MAX_PRECEDENCE: int

    DOT: BinaryOperator  #: The ``.`` operator.
    POW: BinaryOperator  #: The ``**`` operator.
    MUL: BinaryOperator  #: The ``*`` operator.
    MATMUL: BinaryOperator  #: The ``@`` operator.
    DIV: BinaryOperator  #: The ``/`` operator (same as :attr:`.TRUE_DIV`).
    TRUE_DIV: BinaryOperator  #: The ``/`` operator (same as :attr:`.DIV`).
    FLOOR_DIV: BinaryOperator  #: The ``//`` operator.
    MOD: BinaryOperator  #: The ``%`` operator.
    ADD: BinaryOperator  #: The ``+`` operator.
    SUB: BinaryOperator  #: The ``-`` operator.
    LSHIFT: BinaryOperator  #: The ``<<`` operator.
    RSHIFT: BinaryOperator  #: The ``>>`` operator.
    AND_BITWISE: BinaryOperator  #: The ``&`` operator.
    XOR_BITWISE: BinaryOperator  #: The ``^`` operator.
    OR_BITWISE: BinaryOperator  #: The ``|`` operator.
    IN: BinaryOperator  #: The ``in`` operator.
    NOT_IN: BinaryOperator  #: The ``not in`` operator.
    IS: BinaryOperator  #: The ``is`` operator.
    IS_NOT: BinaryOperator  #: The ``is not`` operator.
    LT: BinaryOperator  #: The ``<`` operator.
    LE: BinaryOperator  #: The ``<=`` operator.
    GT: BinaryOperator  #: The ``>`` operator.
    GE: BinaryOperator  #: The ``>=`` operator.
    NEQ_: BinaryOperator  #: The ``<>`` operator.
    NEQ: BinaryOperator  #: The ``!=`` operator.
    EQ: BinaryOperator  #: The ``==`` operator.
    AND: BinaryOperator  #: The ``and`` operator.
    OR: BinaryOperator  #: The ``or`` operator.
    ASSIGN: BinaryOperator  #: The ``=`` operator.
    COLON: BinaryOperator  #: The ``:`` operator.
    SLICE: BinaryOperator  #: The ``:`` operator used in slice expressions.
    COMMA: BinaryOperator  #: The ``,`` operator.
    NONE: BinaryOperator  #: The empty operator.

    # defined in superclass, repeated here for Sphinx
    symbol: str

    @property
    def is_unary(self) -> bool:
        """
        ``False``, as this is not a unary operator.
        """
        return False


class UnaryOperator(Operator):
    """
    A unary operator.
    """

    #: Inherited from :attr:`.Operator.MIN_PRECEDENCE`.
    MIN_PRECEDENCE: int

    #: Inherited from :attr:`.Operator.MAX_PRECEDENCE`.
    MAX_PRECEDENCE: int

    POS: UnaryOperator  #: The ``+`` prefix operator.
    NEG: UnaryOperator  #: The ``-`` prefix operator.
    INVERT: UnaryOperator  #: The ``~`` prefix operator.
    NOT: UnaryOperator  #: The ``not`` prefix operator.
    LAMBDA: UnaryOperator  #: The ``lambda`` prefix operator.

    #: the symbol representing this operator
    symbol: str

    @property
    def is_unary(self) -> bool:
        """
        ``True``, as this is a unary operator.
        """
        return True


BinaryOperator.DOT = BinaryOperator(".")
BinaryOperator.POW = BinaryOperator("**")
BinaryOperator.MUL = BinaryOperator("*")
BinaryOperator.MATMUL = BinaryOperator("@")
BinaryOperator.DIV = BinaryOperator.TRUE_DIV = BinaryOperator("/")
BinaryOperator.FLOOR_DIV = BinaryOperator("//")
BinaryOperator.MOD = BinaryOperator("%")
BinaryOperator.ADD = BinaryOperator("+")
BinaryOperator.SUB = BinaryOperator("-")
BinaryOperator.LSHIFT = BinaryOperator("<<")
BinaryOperator.RSHIFT = BinaryOperator(">>")
BinaryOperator.AND_BITWISE = BinaryOperator("&")
BinaryOperator.XOR_BITWISE = BinaryOperator("^")
BinaryOperator.OR_BITWISE = BinaryOperator("|")
BinaryOperator.IN = BinaryOperator("in")
BinaryOperator.NOT_IN = BinaryOperator("not in")
BinaryOperator.IS = BinaryOperator("is")
BinaryOperator.IS_NOT = BinaryOperator("is not")
BinaryOperator.LT = BinaryOperator("<")
BinaryOperator.LE = BinaryOperator("<=")
BinaryOperator.GT = BinaryOperator(">")
BinaryOperator.GE = BinaryOperator(">=")
BinaryOperator.NEQ_ = BinaryOperator("<>")
BinaryOperator.NEQ = BinaryOperator("!=")
BinaryOperator.EQ = BinaryOperator("==")
BinaryOperator.AND = BinaryOperator("and")
BinaryOperator.OR = BinaryOperator("or")
BinaryOperator.ASSIGN = BinaryOperator("=")
BinaryOperator.COLON = BinaryOperator(":")
BinaryOperator.SLICE = BinaryOperator(":")
BinaryOperator.COMMA = BinaryOperator(",")
BinaryOperator.NONE = BinaryOperator("")

UnaryOperator.POS = UnaryOperator("+")
UnaryOperator.NEG = UnaryOperator("-")
UnaryOperator.INVERT = UnaryOperator("~")
UnaryOperator.NOT = UnaryOperator("not")
UnaryOperator.LAMBDA = UnaryOperator("lambda")

__OPERATOR_PRECEDENCE_ORDER: Tuple[Set[Operator], ...] = (
    {BinaryOperator.ASSIGN},
    {BinaryOperator.COMMA, UnaryOperator.LAMBDA},
    {BinaryOperator.COLON, BinaryOperator.SLICE},
    {BinaryOperator.OR},
    {BinaryOperator.AND},
    {UnaryOperator.NOT},
    {BinaryOperator.NEQ_, BinaryOperator.NEQ, BinaryOperator.EQ},
    {
        BinaryOperator.IN,
        BinaryOperator.NOT_IN,
        BinaryOperator.IS,
        BinaryOperator.IS_NOT,
        BinaryOperator.LT,
        BinaryOperator.LE,
        BinaryOperator.GT,
        BinaryOperator.GE,
    },
    {BinaryOperator.OR_BITWISE},
    {BinaryOperator.XOR_BITWISE},
    {BinaryOperator.AND_BITWISE},
    {BinaryOperator.LSHIFT, BinaryOperator.RSHIFT},
    {BinaryOperator.ADD, BinaryOperator.SUB},
    {
        BinaryOperator.MUL,
        BinaryOperator.MATMUL,
        BinaryOperator.TRUE_DIV,
        BinaryOperator.FLOOR_DIV,
        BinaryOperator.MOD,
    },
    {UnaryOperator.POS, UnaryOperator.NEG},
    {UnaryOperator.INVERT},
    {BinaryOperator.POW},
    {BinaryOperator.DOT},
)

_OPERATOR_PRECEDENCE: Mapping[Operator, int] = {
    operator: priority
    for priority, operators in enumerate(__OPERATOR_PRECEDENCE_ORDER)
    for operator in operators
}

Operator.MAX_PRECEDENCE = len(__OPERATOR_PRECEDENCE_ORDER)

__tracker.validate()

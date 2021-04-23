"""
Operators used in expressions.
"""
import logging
from abc import ABCMeta, abstractmethod
from typing import Mapping, Optional, Set, Tuple, TypeVar

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


# Create a placeholder type so Sphinx will generate correct type hints
# for class attributes
# noinspection PyTypeHints,PyTypeChecker
_BinaryOperator = TypeVar("BinaryOperator", bound="BinaryOperator")


class BinaryOperator(Operator):
    """
    A binary operator.
    """

    #: Inherited from :attr:`.Operator.MIN_PRECEDENCE`.
    MIN_PRECEDENCE: int

    #: Inherited from :attr:`.Operator.MAX_PRECEDENCE`.
    MAX_PRECEDENCE: int

    DOT: _BinaryOperator  #: The ``.`` operator.
    POW: _BinaryOperator  #: The ``**`` operator.
    MUL: _BinaryOperator  #: The ``*`` operator.
    MATMUL: _BinaryOperator  #: The ``@`` operator.
    DIV: _BinaryOperator  #: The ``/`` operator (same as :attr:`.TRUE_DIV`).
    TRUE_DIV: _BinaryOperator  #: The ``/`` operator (same as :attr:`.DIV`).
    FLOOR_DIV: _BinaryOperator  #: The ``//`` operator.
    MOD: _BinaryOperator  #: The ``%`` operator.
    ADD: _BinaryOperator  #: The ``+`` operator.
    SUB: _BinaryOperator  #: The ``-`` operator.
    LSHIFT: _BinaryOperator  #: The ``<<`` operator.
    RSHIFT: _BinaryOperator  #: The ``>>`` operator.
    AND_BITWISE: _BinaryOperator  #: The ``&`` operator.
    XOR_BITWISE: _BinaryOperator  #: The ``^`` operator.
    OR_BITWISE: _BinaryOperator  #: The ``|`` operator.
    IN: _BinaryOperator  #: The ``in`` operator.
    NOT_IN: _BinaryOperator  #: The ``not in`` operator.
    IS: _BinaryOperator  #: The ``is`` operator.
    IS_NOT: _BinaryOperator  #: The ``is not`` operator.
    LT: _BinaryOperator  #: The ``<`` operator.
    LE: _BinaryOperator  #: The ``<=`` operator.
    GT: _BinaryOperator  #: The ``>`` operator.
    GE: _BinaryOperator  #: The ``>=`` operator.
    NEQ_: _BinaryOperator  #: The ``<>`` operator.
    NEQ: _BinaryOperator  #: The ``!=`` operator.
    EQ: _BinaryOperator  #: The ``==`` operator.
    AND: _BinaryOperator  #: The ``and`` operator.
    OR: _BinaryOperator  #: The ``or`` operator.
    ASSIGN: _BinaryOperator  #: The ``=`` operator.
    COLON: _BinaryOperator  #: The ``:`` operator.
    SLICE: _BinaryOperator  #: The ``:`` operator used in slice expressions.
    COMMA: _BinaryOperator  #: The ``,`` operator.
    NONE: _BinaryOperator  #: The empty operator.

    @property
    def is_unary(self) -> bool:
        """
        ``False``, as this is not a unary operator.
        """
        return False


# Create a placeholder type so Sphinx will generate correct type hints
# for class attributes
# noinspection PyTypeHints,PyTypeChecker
_UnaryOperator = TypeVar("UnaryOperator", bound="UnaryOperator")


class UnaryOperator(Operator):
    """
    A unary operator.
    """

    #: Inherited from :attr:`.Operator.MIN_PRECEDENCE`.
    MIN_PRECEDENCE: int

    #: Inherited from :attr:`.Operator.MAX_PRECEDENCE`.
    MAX_PRECEDENCE: int

    POS: _UnaryOperator  #: The ``+`` prefix operator.
    NEG: _UnaryOperator  #: The ``-`` prefix operator.
    INVERT: _UnaryOperator  #: The ``~`` prefix operator.
    NOT: _UnaryOperator  #: The ``not`` prefix operator.
    LAMBDA: _UnaryOperator  #: The ``lambda`` prefix operator.

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

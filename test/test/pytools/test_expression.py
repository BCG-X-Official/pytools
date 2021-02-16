"""
Tests for module pytools.expression
"""

import logging

import pytest

from pytools.expression import Expression, freeze, make_expression
from pytools.expression.atomic import Id, Lit
from pytools.expression.composite import (
    BinaryOperation,
    Call,
    DictLiteral,
    Lambda,
    ListLiteral,
    SetLiteral,
    TupleLiteral,
    UnaryOperation,
)
from pytools.expression.formatter import PythonExpressionFormatter
from pytools.expression.formatter._python import TextualForm
from pytools.expression.operator import BinaryOperator, UnaryOperator

log = logging.getLogger(__name__)


def test_base_import() -> None:
    """
    Test if the expression base package can be imported without errors.
    """
    from pytools.expression import base

    assert base.AtomicExpression is not None


def test_expression_formatting() -> None:
    """
    Basic formatting tests
    """

    # expression 1

    e = Call(Id.f, (1 | Lit(2)) >> Lit("x") % Id.x, abc=-Lit(5))

    expr_1 = e * (e + e + e - e * e)
    form_1 = TextualForm.from_expression(expr_1)
    repr_1 = PythonExpressionFormatter(single_line=True).to_text(expr_1)
    assert len(form_1) == len(repr_1), f"length of {repr_1}"

    assert (
        str(expr_1)
        == """(
    f((1 | 2) >> 'x' % x, abc=-5)
    * (
        f((1 | 2) >> 'x' % x, abc=-5)
        + f((1 | 2) >> 'x' % x, abc=-5)
        + f((1 | 2) >> 'x' % x, abc=-5)
        - f((1 | 2) >> 'x' % x, abc=-5) * f((1 | 2) >> 'x' % x, abc=-5)
    )
)"""
    )

    # expression 2, generated with from_value

    expr_2 = make_expression([1, 2, {3: 4, 5: e}])
    assert str(expr_2) == "[1, 2, {3: 4, 5: f((1 | 2) >> 'x' % x, abc=-5)}]"

    # expression 3

    expr_3 = Id.g(param=(e, e + e, ~(e * e + e)))
    assert (
        str(expr_3)
        == """g(
    param=(
        f((1 | 2) >> 'x' % x, abc=-5),
        f((1 | 2) >> 'x' % x, abc=-5) + f((1 | 2) >> 'x' % x, abc=-5),
        ~(
            f((1 | 2) >> 'x' % x, abc=-5) * f((1 | 2) >> 'x' % x, abc=-5)
            + f((1 | 2) >> 'x' % x, abc=-5)
        )
    )
)"""
    )

    expr_4 = Lambda(body=e)
    assert repr(expr_4) == "lambda : f((1 | 2) >> 'x' % x, abc=-5)"

    expr_5 = Lambda(Id.x, body=e)(Lit(5))
    assert repr(expr_5) == "(lambda x: f((1 | 2) >> 'x' % x, abc=-5))(5)"

    expr_6 = Lambda(Id.x, Id.y, body=e)(Lit(5), 6)
    assert repr(expr_6) == "(lambda x, y: f((1 | 2) >> 'x' % x, abc=-5))(5, 6)"


def test_expression() -> None:
    lit_5 = Lit(5)
    lit_abc = Lit("abc")
    expressions = [
        (lit_5, "5"),
        (lit_abc, "'abc'"),
        (Id.xx, "xx"),
        (Call(Id("func"), lit_5, lit_abc), "func(5, 'abc')"),
        (ListLiteral(lit_5, lit_abc, Id.xx), "[5, 'abc', xx]"),
        (SetLiteral(lit_5, lit_abc, Id.xx), "{5, 'abc', xx}"),
        (TupleLiteral(lit_5, lit_abc, Id.xx), "(5, 'abc', xx)"),
        (DictLiteral(**{"5": lit_abc, "x": lit_5}), "{'5': 'abc', 'x': 5}"),
        (DictLiteral((lit_5, lit_abc), (Id.xx, lit_5)), "{5: 'abc', xx: 5}"),
        (BinaryOperation(BinaryOperator.ADD, lit_5, lit_abc, Id.xx), "5 + 'abc' + xx"),
        (Call(Id("func")), "func()"),
        (ListLiteral(), "[]"),
        (SetLiteral(), "{}"),
        (TupleLiteral(), "()"),
        (DictLiteral(), "{}"),
        (Id.xx.isalpha(), "xx.isalpha()"),
        (Id.xx[:], "xx[:]"),
        (Id.xx[::1], "xx[::1]"),
        (Id.xx[2::3, 1], "xx[2::3, 1]"),
        (Id.xx[4:], "xx[4:]"),
    ]

    for expression, expected_str in expressions:
        representation = TextualForm.from_expression(expression)
        assert len(representation) == len(expected_str), f"length of {representation}"
        assert str(representation) == expected_str
        assert len(
            PythonExpressionFormatter(single_line=True).to_text(expression)
        ) == len(expected_str)


def test_expression_setting() -> None:
    x = Id.x

    # we cannot assign by index
    with pytest.raises(TypeError):
        x[5] = 7

    # we cannot delete by index
    with pytest.raises(TypeError):
        del x[5]

    # we do not get an Attr expression for names with leading "_"
    with pytest.raises(AttributeError):
        x._private_a(3)

    # ... but we can assign private fields to the expression
    x._private_b = 3
    assert x._private_b == 3

    # we cannot assign values to public fields
    with pytest.raises(TypeError):
        x.public = 3


def test_comparison_expressions() -> None:
    x, y = Id.x, Id.y

    assert repr(x == y) == "x == y"
    assert repr(x != y) == "x != y"
    assert repr(x > y) == "x > y"
    assert repr(x >= y) == "x >= y"
    assert repr(x < y) == "x < y"
    assert repr(x <= y) == "x <= y"

    assert freeze(x) != freeze(y)
    assert not freeze(x) == freeze(y)

    a: Expression = make_expression([(x + (y * 3)), {freeze(y): x}])
    a_copy: Expression = make_expression([(x + (y * 3)), {freeze(y): x}])
    assert isinstance(a == a_copy, Expression)
    assert isinstance(freeze(a) == a_copy, bool)
    assert freeze(a) == freeze(a_copy)
    assert freeze(a) != a_copy
    assert freeze(a) != (a_copy + 1)


def test_expression_operators() -> None:
    a, b = Id.a, Id.b
    assert a + b == BinaryOperation(BinaryOperator.ADD, a, b)
    assert a - b == BinaryOperation(BinaryOperator.SUB, a, b)
    assert a * b == BinaryOperation(BinaryOperator.MUL, a, b)
    assert a @ b == BinaryOperation(BinaryOperator.MATMUL, a, b)
    assert a / b == BinaryOperation(BinaryOperator.DIV, a, b)
    assert a // b == BinaryOperation(BinaryOperator.FLOOR_DIV, a, b)
    assert a % b == BinaryOperation(BinaryOperator.MOD, a, b)
    assert a ** b == BinaryOperation(BinaryOperator.POW, a, b)
    assert a << b == BinaryOperation(BinaryOperator.LSHIFT, a, b)
    assert a >> b == BinaryOperation(BinaryOperator.RSHIFT, a, b)
    assert a & b == BinaryOperation(BinaryOperator.AND_BITWISE, a, b)
    assert a ^ b == BinaryOperation(BinaryOperator.XOR_BITWISE, a, b)
    assert a | b == BinaryOperation(BinaryOperator.OR_BITWISE, a, b)
    assert -a == UnaryOperation(UnaryOperator.NEG, operand=a)
    assert +a == UnaryOperation(UnaryOperator.POS, operand=a)
    assert ~a == UnaryOperation(UnaryOperator.INVERT, operand=a)
    assert (not a) == UnaryOperation(UnaryOperator.NOT, operand=a)


def test_operator_precedence() -> None:
    a, b, c = Id.a, Id.b, Id.c
    assert str(a + b + c) == "a + b + c"
    assert str((a + b) + c) == "a + b + c"
    assert str(a + (b + c)) == "a + (b + c)"
    assert str(a / b / c) == "a / b / c"
    assert str((a / b) / c) == "a / b / c"
    assert str(a / (b / c)) == "a / (b / c)"
    assert str(a * b + c) == "a * b + c"
    assert str((a * b) + c) == "a * b + c"
    assert str(a * (b + c)) == "a * (b + c)"
    assert str(a + b * c) == "a + b * c"
    assert str((a + b) * c) == "(a + b) * c"
    assert str(a + (b * c)) == "a + b * c"

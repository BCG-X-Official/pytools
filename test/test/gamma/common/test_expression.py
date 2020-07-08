"""
Tests for module gamma.common.expression
"""

import logging

import pytest

import gamma.common.expression.operator as op
from gamma.common.expression import (
    Call,
    DictLiteral,
    Expression,
    Id,
    Lambda,
    ListLiteral,
    Lit,
    make_expression,
    Operation,
    PythonExpressionFormatter,
    SetLiteral,
    TupleLiteral,
    UnaryOperation,
)

# noinspection PyProtectedMember
from gamma.common.expression._text import TextualForm

log = logging.getLogger(__name__)


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
        repr(expr_3)
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

    expr_4 = Lambda(Id.x, body=e)(Lit(5))
    assert repr(expr_4) == "(lambda x: f((1 | 2) >> 'x' % x, abc=-5))(5)"


def test_expression() -> None:
    lit_5 = Lit(5)
    lit_abc = Lit("abc")
    expressions = [
        (lit_5, "5"),
        (lit_abc, "'abc'"),
        ((Id.xx), "xx"),
        (Call(Id("func"), lit_5, lit_abc), "func(5, 'abc')"),
        (ListLiteral(lit_5, lit_abc, Id.xx), "[5, 'abc', xx]"),
        (SetLiteral(lit_5, lit_abc, Id.xx), "{5, 'abc', xx}"),
        (TupleLiteral(lit_5, lit_abc, Id.xx), "(5, 'abc', xx)"),
        (DictLiteral(**{"5": lit_abc, "x": lit_5}), "{'5': 'abc', 'x': 5}"),
        (DictLiteral((lit_5, lit_abc), (Id.xx, lit_5)), "{5: 'abc', xx: 5}"),
        (Operation(op.ADD, lit_5, lit_abc, Id.xx), "5 + 'abc' + xx"),
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

    assert x.freeze_() != y
    assert not x.freeze_() == y

    a: Expression = make_expression([(x + (y * 3)), {y.freeze_(): x}])
    a_copy: Expression = make_expression([(x + (y * 3)), {y.freeze_(): x}])
    assert isinstance(a == a_copy, Expression)
    assert isinstance(a.freeze_() == a_copy, bool)
    assert a.freeze_() == a_copy.freeze_()
    assert a.freeze_() != a_copy
    assert a.freeze_() != (a_copy + 1)


def test_expression_operators() -> None:
    a, b = Id.a, Id.b
    assert a + b == Operation(op.ADD, a, b)
    assert a - b == Operation(op.SUB, a, b)
    assert a * b == Operation(op.MUL, a, b)
    assert a @ b == Operation(op.MATMUL, a, b)
    assert a / b == Operation(op.DIV, a, b)
    assert a // b == Operation(op.FLOOR_DIV, a, b)
    assert a % b == Operation(op.MOD, a, b)
    assert a ** b == Operation(op.POW, a, b)
    assert a << b == Operation(op.LSHIFT, a, b)
    assert a >> b == Operation(op.RSHIFT, a, b)
    assert a & b == Operation(op.AND_BITWISE, a, b)
    assert a ^ b == Operation(op.XOR_BITWISE, a, b)
    assert a | b == Operation(op.OR_BITWISE, a, b)
    assert -a == UnaryOperation(op.NEG, operand=a)
    assert +a == UnaryOperation(op.POS, operand=a)
    assert ~a == UnaryOperation(op.INVERT, operand=a)


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

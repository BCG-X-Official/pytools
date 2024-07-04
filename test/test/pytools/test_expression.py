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


def test_expression_repr_html() -> None:
    # create an expression
    e = Call(Id.f, (1 | Lit(2)) >> Lit("x") % Id.x, abc=-Lit(5))
    expr = e * (e + e + e - e * e)

    # create the expected representations
    expected_formatted_expression = """(
    f((1 | 2) >> 'x' % x, abc=-5)
    * (
        f((1 | 2) >> 'x' % x, abc=-5)
        + f((1 | 2) >> 'x' % x, abc=-5)
        + f((1 | 2) >> 'x' % x, abc=-5)
        - f((1 | 2) >> 'x' % x, abc=-5) * f((1 | 2) >> 'x' % x, abc=-5)
    )
)"""
    # test if the string representation is generated as expected
    assert str(expr) == expected_formatted_expression

    # test if the html representation is generated as expected
    assert expr._repr_html_() == f"<pre>{expected_formatted_expression}\n</pre>\n"


def test_expression() -> None:
    lit_5 = Lit(5)
    lit_abc = Lit("abc")
    expressions: list[tuple[Expression, str]] = [
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
        (SetLiteral(1), "{1}"),
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

    with pytest.raises(
        TypeError, match="^set literals must have at least one element$"
    ):
        # Set literals must have at least one element
        SetLiteral()


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
    assert not freeze(x) == freeze(y)  # NOSONAR

    a: Expression = make_expression([(x + (y * 3)), {freeze(y): x}])
    a_copy: Expression = make_expression([(x + (y * 3)), {freeze(y): x}])
    assert isinstance(a == a_copy, Expression)
    assert isinstance(freeze(a) == a_copy, bool)
    assert freeze(a) == freeze(a_copy)
    assert freeze(a) != a_copy
    assert freeze(a) != (a_copy + 1)


def test_make_expression() -> None:
    assert freeze(make_expression([1, 2, 3])) == freeze(
        ListLiteral(Lit(1), Lit(2), Lit(3))
    )
    assert freeze(make_expression((1, 2, 3))) == freeze(
        TupleLiteral(Lit(1), Lit(2), Lit(3))
    )
    assert freeze(make_expression({1, 2, 3})) == freeze(
        SetLiteral(Lit(1), Lit(2), Lit(3))
    )
    assert freeze(make_expression(set())) == freeze(Id(set)())
    assert freeze(make_expression({1: 2, 3: 4})) == freeze(
        DictLiteral((Lit(1), Lit(2)), (Lit(3), Lit(4)))
    )
    assert freeze(make_expression({"a": 2, "b": 4})) == freeze(
        DictLiteral((Lit("a"), Lit(2)), (Lit("b"), Lit(4)))
    )
    assert freeze(make_expression(frozenset({1, 2, 3}))) == freeze(
        Id(frozenset)(Lit(1), Lit(2), Lit(3))
    )
    assert freeze(make_expression([1, 2, ...])) == freeze(
        ListLiteral(Lit(1), Lit(2), Ellipsis)
    )


def test_expression_operators() -> None:
    a, b = Id.a, Id.b
    assert freeze(a + b) == freeze(BinaryOperation(BinaryOperator.ADD, a, b))
    assert freeze(a - b) == freeze(BinaryOperation(BinaryOperator.SUB, a, b))
    assert freeze(a * b) == freeze(BinaryOperation(BinaryOperator.MUL, a, b))
    assert freeze(a @ b) == freeze(BinaryOperation(BinaryOperator.MATMUL, a, b))
    assert freeze(a / b) == freeze(BinaryOperation(BinaryOperator.DIV, a, b))
    assert freeze(a // b) == freeze(BinaryOperation(BinaryOperator.FLOOR_DIV, a, b))
    assert freeze(a % b) == freeze(BinaryOperation(BinaryOperator.MOD, a, b))
    assert freeze(a**b) == freeze(BinaryOperation(BinaryOperator.POW, a, b))
    assert freeze(a << b) == freeze(BinaryOperation(BinaryOperator.LSHIFT, a, b))
    assert freeze(a >> b) == freeze(BinaryOperation(BinaryOperator.RSHIFT, a, b))
    assert freeze(a & b) == freeze(BinaryOperation(BinaryOperator.AND_BITWISE, a, b))
    assert freeze(a ^ b) == freeze(BinaryOperation(BinaryOperator.XOR_BITWISE, a, b))
    assert freeze(a | b) == freeze(BinaryOperation(BinaryOperator.OR_BITWISE, a, b))
    assert freeze(-a) == freeze(UnaryOperation(UnaryOperator.NEG, operand=a))
    assert freeze(+a) == freeze(UnaryOperation(UnaryOperator.POS, operand=a))
    assert freeze(~a) == freeze(UnaryOperation(UnaryOperator.INVERT, operand=a))


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

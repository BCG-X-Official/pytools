"""
Tests for module gamma.common.expression
"""

import logging

import gamma.common.expression.operator as op
from gamma.common.expression import (
    Call,
    DictExpression,
    Expression,
    Identifier,
    Lambda,
    ListExpression,
    Literal,
    Operation,
    PythonExpressionFormatter,
    SetExpression,
    TupleExpression,
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

    e = Call(
        Identifier("f"),
        (1 | Literal(2)) >> Literal("x") % Identifier("x"),
        abc=-Literal(5),
    )

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

    expr_2 = Expression.from_value([1, 2, {3: 4, 5: e}])
    assert str(expr_2) == "[1, 2, {3: 4, 5: f((1 | 2) >> 'x' % x, abc=-5)}]"

    # expression 3

    expr_3 = Identifier("g")(param=(e, e + e, e * e + e))
    assert (
        repr(expr_3)
        == """g(
    param=(
        f((1 | 2) >> 'x' % x, abc=-5),
        f((1 | 2) >> 'x' % x, abc=-5) + f((1 | 2) >> 'x' % x, abc=-5),
        (
            f((1 | 2) >> 'x' % x, abc=-5) * f((1 | 2) >> 'x' % x, abc=-5)
            + f((1 | 2) >> 'x' % x, abc=-5)
        )
    )
)"""
    )

    expr_4 = Lambda(params=Identifier("x"), body=e)(Literal(5))
    assert repr(expr_4) == "(lambda x: f((1 | 2) >> 'x' % x, abc=-5))(5)"


def test_expression() -> None:
    lit_5 = Literal(5)
    lit_abc = Literal("abc")
    ident_xx = Identifier("xx")
    expressions = [
        (lit_5, "5"),
        (lit_abc, "'abc'"),
        (ident_xx, "xx"),
        (Call(Identifier("func"), lit_5, lit_abc), "func(5, 'abc')"),
        (ListExpression(elements=[lit_5, lit_abc, ident_xx]), "[5, 'abc', xx]"),
        (SetExpression(elements=[lit_5, lit_abc, ident_xx]), "{5, 'abc', xx}"),
        (TupleExpression(elements=[lit_5, lit_abc, ident_xx]), "(5, 'abc', xx)"),
        (
            DictExpression(entries={lit_5: lit_abc, ident_xx: lit_5}),
            "{5: 'abc', xx: 5}",
        ),
        (
            Operation(operator=op.ADD, operands=(lit_5, lit_abc, ident_xx)),
            "5 + 'abc' + xx",
        ),
        (Call(Identifier("func")), "func()"),
        (ListExpression(elements=[]), "[]"),
        (SetExpression(elements=[]), "{}"),
        (TupleExpression(elements=[]), "()"),
        (DictExpression(entries=dict()), "{}"),
        (ident_xx.attr.isalpha(), "xx.isalpha()"),
    ]

    for expression, expected_str in expressions:
        representation = TextualForm.from_expression(expression)
        assert len(representation) == len(expected_str), f"length of {expected_str}"
        assert str(representation) == expected_str
        assert len(
            PythonExpressionFormatter(single_line=True).to_text(expression)
        ) == len(expected_str)


def test_expression_operators() -> None:
    a, b = Identifier("a"), Identifier("b")
    assert a + b == Operation(op.ADD, operands=[a, b])
    assert a - b == Operation(op.SUB, operands=(a, b))
    assert a * b == Operation(op.MUL, operands=(a, b))
    assert a @ b == Operation(op.MATMUL, operands=(a, b))
    assert a / b == Operation(op.DIV, operands=(a, b))
    assert a // b == Operation(op.FLOOR_DIV, operands=(a, b))
    assert a % b == Operation(op.MOD, operands=(a, b))
    assert a ** b == Operation(op.POW, operands=(a, b))
    assert a << b == Operation(op.LSHIFT, operands=(a, b))
    assert a >> b == Operation(op.RSHIFT, operands=(a, b))
    assert a & b == Operation(op.AND_BITWISE, operands=(a, b))
    assert a ^ b == Operation(op.XOR_BITWISE, operands=(a, b))
    assert a | b == Operation(op.OR_BITWISE, operands=(a, b))
    assert -a == UnaryOperation(op.NEG, operand=a)
    assert +a == UnaryOperation(op.POS, operand=a)
    assert ~a == UnaryOperation(op.INVERT, operand=a)


def test_operator_precedence() -> None:
    a, b, c = Identifier("a"), Identifier("b"), Identifier("c")
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

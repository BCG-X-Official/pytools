"""
Tests for module gamma.common.expression
"""

import logging

from gamma.common.expression import (
    Call,
    DictExpression,
    Expression,
    Identifier,
    ListExpression,
    Literal,
    Operation,
    PythonExpressionFormatter,
    SetExpression,
    TupleExpression,
    UnaryOperation,
)

# noinspection PyProtectedMember
from gamma.common.expression._text import _TextualForm

log = logging.getLogger(__name__)


def test_expression_formatting() -> None:
    """
    Basic formatting tests
    """

    # expression 1

    e = Call(
        "f",
        (Literal(1) | Literal(2)) >> Literal("x") % Identifier("x"),
        abc=-Literal(5),
    )

    expr_1 = e * (e + e + e - e * e)
    repr_1 = _TextualForm(expr_1)
    assert len(repr_1) == len(
        PythonExpressionFormatter(single_line=True).to_text(expr_1)
    )

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

    expr_3 = Call("g", param=Expression.from_value((e, e + e, e * e + e)))
    assert (
        repr(expr_3)
        == """g(
    param=(
        f((1 | 2) >> 'x' % x, abc=-5),
        f((1 | 2) >> 'x' % x, abc=-5) + f((1 | 2) >> 'x' % x, abc=-5),
        f((1 | 2) >> 'x' % x, abc=-5) * f((1 | 2) >> 'x' % x, abc=-5)
        + f((1 | 2) >> 'x' % x, abc=-5)
    )
)"""
    )


def test_expression() -> None:
    lit_5 = Literal(5)
    lit_abc = Literal("abc")
    ident_xx = Identifier("xx")
    expressions_lengths = [
        (lit_5, 1, "5"),
        (lit_abc, 5, "'abc'"),
        (ident_xx, 2, "xx"),
        (Call("func", lit_5, lit_abc), 14, "func(5, 'abc')"),
        (ListExpression(elements=[lit_5, lit_abc, ident_xx]), 14, "[5, 'abc', xx]"),
        (SetExpression(elements=[lit_5, lit_abc, ident_xx]), 14, "{5, 'abc', xx}"),
        (TupleExpression(elements=[lit_5, lit_abc, ident_xx]), 14, "(5, 'abc', xx)"),
        (
            DictExpression(entries={lit_5: lit_abc, ident_xx: lit_5}),
            17,
            "{5: 'abc', xx: 5}",
        ),
        (
            Operation(operator="+", operands=(lit_5, lit_abc, ident_xx)),
            14,
            "5 + 'abc' + xx",
        ),
    ]

    for expression, expected_length, expected_str in expressions_lengths:
        representation = _TextualForm(expression)
        print(f'"{expression}"')
        assert len(representation) == expected_length
        assert str(representation) == expected_str
        assert (
            len(PythonExpressionFormatter(single_line=True).to_text(expression))
            == expected_length
        )


def test_expression_operators() -> None:
    a, b = Identifier("a"), Identifier("b")
    assert a + b == Operation("+", operands=[a, b])
    assert a - b == Operation("-", operands=(a, b))
    assert a * b == Operation("*", operands=(a, b))
    assert a @ b == Operation("@", operands=(a, b))
    assert a / b == Operation("/", operands=(a, b))
    assert a // b == Operation("//", operands=(a, b))
    assert a % b == Operation("%", operands=(a, b))
    assert a ** b == Operation("**", operands=(a, b))
    assert a << b == Operation("<<", operands=(a, b))
    assert a >> b == Operation(">>", operands=(a, b))
    assert a & b == Operation("&", operands=(a, b))
    assert a ^ b == Operation("^", operands=(a, b))
    assert a | b == Operation("|", operands=(a, b))
    assert -a == UnaryOperation("-", operand=a)
    assert +a == UnaryOperation("+", operand=a)
    assert ~a == UnaryOperation("~", operand=a)


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

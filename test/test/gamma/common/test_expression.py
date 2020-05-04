import logging

from gamma.common.expression import (
    Call,
    DictExpression,
    Expression,
    Identifier,
    ListExpression,
    Literal,
    Operation,
    SetExpression,
    TupleExpression,
    UnaryOperation,
)

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

    rep = (e + e + e - e * e).representation()
    assert len(rep) == len(rep.to_string(multiline=False))

    assert (
        str(rep)
        == """f((1 | 2) >> 'x' % x, abc=-5)
+ f((1 | 2) >> 'x' % x, abc=-5)
+ f((1 | 2) >> 'x' % x, abc=-5)
- f((1 | 2) >> 'x' % x, abc=-5) * f((1 | 2) >> 'x' % x, abc=-5)"""
    )

    # expression 2, generated with from_value

    assert (
        str(Expression.from_value([1, 2, {3: 4, 5: e}]))
        == "[1, 2, {3: 4, 5: f((1 | 2) >> 'x' % x, abc=-5)}]"
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
        representation = expression.representation()
        print(f'"{expression}"')
        assert len(representation) == expected_length
        assert str(representation) == expected_str
        assert len(representation.to_string(multiline=False)) == expected_length


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

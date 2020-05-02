import logging

from gamma.common.expression import Call, Expression, Identifier, Literal

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
    expressions_lengths = [(Literal(5), 1), (Literal("abc"), 5)]
    for expression, expected_length in expressions_lengths:
        representation = expression.representation()
        assert len(representation) == expected_length
        assert len(representation.to_string(multiline=False)) == expected_length

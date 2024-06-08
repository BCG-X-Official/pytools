"""
Tests for the ``repr`` module.
"""

from pytools.expression import freeze
from pytools.expression.composite import (
    DictLiteral,
    ListLiteral,
    SetLiteral,
    TupleLiteral,
)
from pytools.expression.repr import (
    DictWithExpressionRepr,
    ListWithExpressionRepr,
    SetWithExpressionRepr,
    TupleWithExpressionRepr,
)


def test_list_repr() -> None:
    """
    Test the representation of a list.
    """
    list_with_repr = ListWithExpressionRepr([1, 2, 3])
    assert freeze(list_with_repr.to_expression()) == freeze(ListLiteral(1, 2, 3))
    assert repr(list_with_repr) == "[1, 2, 3]"
    assert str(list_with_repr) == "[1, 2, 3]"


def test_set_repr() -> None:
    """
    Test the representation of a set.
    """
    set_with_repr = SetWithExpressionRepr([1, 2, 3])
    assert freeze(set_with_repr.to_expression()) == freeze(SetLiteral(1, 2, 3))
    assert repr(set_with_repr) == "{1, 2, 3}"
    assert str(set_with_repr) == "{1, 2, 3}"

    # Empty sets should be represented as `set()`.
    assert repr(SetWithExpressionRepr([])) == "set()"
    assert str(SetWithExpressionRepr([])) == "set()"


def test_tuple_repr() -> None:
    """
    Test the representation of a tuple.
    """
    tuple_with_repr: TupleWithExpressionRepr[int, int, int] = TupleWithExpressionRepr(
        (1, 2, 3)
    )
    assert freeze(tuple_with_repr.to_expression()) == freeze(TupleLiteral(1, 2, 3))
    assert repr(tuple_with_repr) == "(1, 2, 3)"
    assert str(tuple_with_repr) == "(1, 2, 3)"


def test_dict_repr() -> None:
    """
    Test the representation of a dict.
    """
    dict_with_repr = DictWithExpressionRepr({1: 2, 3: 4})
    assert freeze(dict_with_repr.to_expression()) == freeze(DictLiteral((1, 2), (3, 4)))
    assert repr(dict_with_repr) == "{1: 2, 3: 4}"
    assert str(dict_with_repr) == "{1: 2, 3: 4}"

"""
Basic utilities for constructing expressions and rendering them as multi-line strings
with indentation; useful for generating representations of complex Python objects.
"""
from ._expression import (
    Expression,
    ExpressionAlias,
    ExpressionFormatter,
    FrozenExpression,
    HasExpressionRepr,
    freeze,
    make_expression,
)
from ._text import *

_expression.default.validate_imported(globals())

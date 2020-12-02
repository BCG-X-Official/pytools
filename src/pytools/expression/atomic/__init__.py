"""
Atomic expressions.

Atomic expressions comprise identifiers, literal values, and the empty expression.
"""
from .. import _expression

# noinspection PyUnresolvedReferences
from .._expression import Epsilon, Id, Lit

_expression.atomic.validate_imported(globals())
del _expression

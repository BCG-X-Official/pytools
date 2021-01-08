"""
Implementation of :mod:`pytools.expression.composite.base`.
"""
import logging
from typing import Any

from ... import Expression
from ...atomic import Epsilon, Id
from ...base import SimplePrefixExpression
from ...operator import BinaryOperator, UnaryOperator
from pytools.api import AllTracker, inheritdoc

log = logging.getLogger(__name__)


#
# Exported names
#

__all__ = [
    "KeywordArgument",
    "DictEntry",
    "LambdaDefinition",
]


#
# Ensure all symbols introduced below are included in __all__
#

__tracker = AllTracker(globals())


#
# Class definitions
#


@inheritdoc(match="[see superclass]")
class KeywordArgument(SimplePrefixExpression):
    """
    A keyword argument, used by functions.
    """

    _PRECEDENCE = BinaryOperator.EQ.precedence

    def __init__(self, name: str, value: Any):
        """
        :param name: the name of the keyword
        :param value: the value for the keyword
        """
        super().__init__(prefix=Id(name), body=value)
        self._name = name

    @property
    def name_(self) -> str:
        """
        The name of this keyword argument.
        """
        return self._name

    @property
    def separator_(self) -> str:
        """[see superclass]"""
        return "="

    @property
    def value_(self) -> Expression:
        """
        The name of this keyword argument.
        """
        return self.body_

    @property
    def precedence_(self) -> int:
        """[see superclass]"""
        return self._PRECEDENCE


@inheritdoc(match="[see superclass]")
class DictEntry(SimplePrefixExpression):
    """
    Two expressions separated by a colon, used in dictionaries.
    """

    _PRECEDENCE = BinaryOperator.COLON.precedence

    def __init__(self, key: Any, value: Any):
        """
        :param key: the key of the dictionary entry
        :param value: the value of the dictionary entry
        """
        super().__init__(prefix=key, body=value)

    @property
    def key_(self) -> Expression:
        """
        The key of this dictionary entry; identical with the expression prefix.
        """
        return self.prefix_

    @property
    def separator_(self) -> str:
        """A ``:``, followed by a space."""
        return ": "

    @property
    def value_(self) -> Expression:
        """
        The value of this dictionary entry; identical with the expression body.
        """
        return self.body_

    @property
    def precedence_(self) -> int:
        """[see superclass]"""
        return DictEntry._PRECEDENCE


@inheritdoc(match="[see superclass]")
class LambdaDefinition(SimplePrefixExpression):
    """
    Function parameters and body separated by a colon, used inside lambda expressions.
    """

    _PRECEDENCE = UnaryOperator.LAMBDA.precedence

    def __init__(self, *params: Id, body: Any):
        """
        :param params: the parameters of the lambda expression
        :param body: the body of the lambda expression
        """
        if not params:
            params_expression = Epsilon()
        elif len(params) == 1:
            params_expression = params[0]
        else:
            from .. import BinaryOperation

            params_expression = BinaryOperation(BinaryOperator.COMMA, *params)
        super().__init__(prefix=params_expression, body=body)

    @property
    def params_(self) -> Expression:
        """
        The parameters of the lambda expression.
        """
        return self.prefix_

    @property
    def separator_(self) -> str:
        """A ``:``, followed by a space."""
        return ": "

    @property
    def precedence_(self) -> int:
        """[see superclass]"""
        return LambdaDefinition._PRECEDENCE

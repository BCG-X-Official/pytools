"""
String representations of expressions
"""

import logging
from abc import ABCMeta, abstractmethod
from typing import *

from gamma.common import AllTracker
from gamma.common.expression._expression import (
    AtomicExpression,
    BracketedExpression,
    Expression,
    ExpressionFormatter,
    InfixExpression,
    PrefixExpression,
)

log = logging.getLogger(__name__)

__all__ = ["PythonExpressionFormatter"]


#
# Private helper classes
#


class FormattingConfig(NamedTuple):
    """
    The parameters to use for formatting an expression
    """

    max_width: int = 80
    """maximum line width"""
    indent_width: int = 4
    """number of spaces in one indentation"""
    single_line: bool = False
    """if `True`, always produce a single line regardless of width"""


class IndentedLine(NamedTuple):
    """
    An indented line of text
    """

    indent: int
    text: str


class TextualForm:
    """
    A hierarchical textual representation of an expression
    """

    @staticmethod
    def from_expression(expression: Expression) -> "TextualForm":
        """
        Generate a textual form for the given expression
        :param expression: the expression to be transformed
        :return: the resulting textual form
        """
        if isinstance(expression, AtomicExpression):
            return AtomicForm(expression)
        elif isinstance(expression, BracketedExpression):
            return BracketedForm.from_bracketed_expression(expression)
        elif isinstance(expression, InfixExpression):
            return InfixForm.from_infix_expression(expression)
        else:
            assert isinstance(expression, PrefixExpression)
            return PrefixedForm.from_prefix_expression(expression)

    def to_text(self, config: FormattingConfig) -> str:
        """
        Render this textual form as a string
        :param config: the formatting configuration to use
        :return: the resulting string
        """

        if config.single_line:

            return self._to_single_line()

        else:

            def _spacing(indent: int) -> str:
                return " " * (config.indent_width * indent)

            return "\n".join(
                f"{_spacing(indent)}{text}"
                for indent, text in self._to_lines(config=config)
            )

    @abstractmethod
    def _to_lines(
        self,
        config: FormattingConfig,
        indent: int = 0,
        leading_characters: int = 0,
        trailing_characters: int = 0,
    ) -> List[IndentedLine]:
        pass

    @abstractmethod
    def _to_single_line(self) -> str:
        """
        Convert this representation to a single-line string
        :return: the resulting string
        """
        pass

    @property
    def brackets(self) -> Optional[Tuple[str, str]]:
        """
        The brackets enclosing this form
        :return: a tuple of opening and closing brackets, or `None` for no brackets
        """
        return None

    @property
    def opening_bracket(self) -> str:
        """
        The opening bracket of this expression.
        """
        return self.brackets[0] if self.brackets else ""

    @property
    def closing_bracket(self) -> str:
        """
        The closing bracket of this expression.
        """
        return self.brackets[1] if self.brackets else ""

    def encapsulate_if(self, condition: bool) -> "BracketedForm":
        """
        If condition is met, return this form encapsulated in round parentheses,
        otherwise return this form unchanged.
        :param condition: if `True`, the condition is met
        :return: the resulting form depending on the condition
        """
        return BracketedForm(brackets=("(", ")"), subform=self) if condition else self

    @abstractmethod
    def __len__(self) -> int:
        pass

    def __repr__(self) -> str:
        # noinspection PyProtectedMember
        return self.to_text(config=_DEFAULT_PYTHON_EXPRESSION_FORMATTER.config)


class AtomicForm(TextualForm):
    """
    A textual representation of an atomic expression
    """

    def __init__(self, expression: AtomicExpression) -> None:
        self.text = expression.text

    def _to_lines(
        self,
        config: FormattingConfig,
        indent: int = 0,
        leading_characters: int = 0,
        trailing_characters: int = 0,
    ) -> List[IndentedLine]:
        """[see superclass]"""

        return [IndentedLine(indent=indent, text=self._to_single_line())]

    def _to_single_line(self) -> str:
        """[see superclass]"""

        return self.text

    def __len__(self) -> int:
        return len(self.text)


class ComplexForm(TextualForm, metaclass=ABCMeta):
    """
    Base class of non-atomic forms.
    """

    def __init__(self, length: int) -> None:
        """
        :param length: the length of the single-line representation of this form
        """

        self._len = length

    def _to_lines(
        self,
        config: FormattingConfig,
        indent: int = 0,
        leading_characters: int = 0,
        trailing_characters: int = 0,
    ) -> List[IndentedLine]:
        """[see superclass]"""

        if (
            leading_characters
            + len(self)
            + indent * config.indent_width
            + trailing_characters
            > config.max_width
        ):
            if indent == 0 and not self.brackets:
                # we add parentheses if we have multiple lines at indent level 0,
                # and there is no existing bracketing
                return BracketedForm(
                    brackets=("(", ")"), subform=self
                )._to_multiple_lines(
                    config=config,
                    indent=0,
                    leading_characters=leading_characters,
                    trailing_characters=trailing_characters,
                )

            return self._to_multiple_lines(
                config=config,
                indent=indent,
                leading_characters=leading_characters,
                trailing_characters=trailing_characters,
            )
        else:
            return [IndentedLine(indent=indent, text=self._to_single_line())]

    @abstractmethod
    def _to_multiple_lines(
        self,
        config: FormattingConfig,
        indent: int,
        leading_characters: int,
        trailing_characters: int,
    ) -> List[IndentedLine]:
        """
        Convert this representation to multiple lines
        :param indent: global indent of this expression
        :param leading_characters: leading space to reserve in first line
        :param trailing_characters: trailing space to reserve in last line
        :return: resulting lines
        """
        pass

    def __len__(self) -> int:
        return self._len


class BracketedForm(ComplexForm):
    """
    A hierarchical textual representation of a complex expression
    """

    def __init__(self, brackets: Tuple[str, str], subform: TextualForm) -> None:
        """
        :param brackets: the brackets surrounding the subform(s)
        """
        assert len(brackets) == 2, "brackets is a pair"

        super().__init__(
            length=(len(brackets[0]) + len(brackets[1]) if brackets else 0)
            + len(subform)
        )

        self._brackets = brackets
        self.subform = subform

    @staticmethod
    def from_bracketed_expression(expression: BracketedExpression) -> "BracketedForm":
        return BracketedForm(
            brackets=expression.brackets,
            subform=TextualForm.from_expression(expression.subexpression),
        )

    @property
    def brackets(self) -> Tuple[str, str]:
        """[see superclass]"""
        return self._brackets

    brackets.__doc__ = TextualForm.brackets.__doc__

    def _to_single_line(self) -> str:
        return (
            self.opening_bracket + self.subform._to_single_line() + self.closing_bracket
        )

    def _to_multiple_lines(
        self,
        config: FormattingConfig,
        indent: int,
        leading_characters: int,
        trailing_characters: int,
    ) -> List[IndentedLine]:
        return [
            IndentedLine(indent=indent, text=self.opening_bracket),
            *self.subform._to_lines(
                config=config,
                indent=indent + 1,
                leading_characters=leading_characters,
                trailing_characters=trailing_characters,
            ),
            IndentedLine(indent=indent, text=self.closing_bracket),
        ]


class PrefixedForm(ComplexForm):
    """
    A hierarchical textual representation of a complex expression
    """

    def __init__(self, prefix: TextualForm, subform: TextualForm) -> None:
        """
        :param prefix: the prefix form
        :param subform: the subform
        """
        super().__init__(length=len(prefix) + len(subform))

        self.prefix = prefix
        self.subform = subform

    @staticmethod
    def from_prefix_expression(expression: PrefixExpression) -> TextualForm:
        """
        Create a prefixed form from the given prefix expression
        """

        prefix = expression.prefix
        subexpression = expression.subexpression
        return PrefixedForm(
            prefix=(
                TextualForm.from_expression(prefix).encapsulate_if(
                    condition=prefix.precedence > expression.precedence
                )
            ),
            subform=(
                TextualForm.from_expression(subexpression).encapsulate_if(
                    condition=subexpression.precedence > expression.precedence
                )
            ),
        )

    def _to_single_line(self) -> str:
        """[see superclass]"""

        return self.prefix._to_single_line() + self.subform._to_single_line()

    def _to_multiple_lines(
        self,
        config: FormattingConfig,
        indent: int,
        leading_characters: int,
        trailing_characters: int,
    ) -> List[IndentedLine]:

        result: List[IndentedLine]

        result = self.prefix._to_lines(
            config=config,
            indent=indent,
            leading_characters=leading_characters,
            trailing_characters=0,
        )

        last_prefix_line = result[-1]
        subform_lines = self.subform._to_lines(
            config=config,
            indent=indent,
            leading_characters=len(last_prefix_line),
            trailing_characters=trailing_characters,
        )

        result[-1] = IndentedLine(
            indent=last_prefix_line.indent,
            text=last_prefix_line.text + subform_lines[0].text,
        )
        result.extend(subform_lines[1:])

        return result


class InfixForm(ComplexForm):
    """
    A hierarchical textual representation of a complex expression
    """

    PADDING_NONE = "none"
    PADDING_RIGHT = "right"
    PADDING_BOTH = "both"

    __PADDING_SPACES = {PADDING_NONE: 0, PADDING_RIGHT: 1, PADDING_BOTH: 2}

    def __init__(
        self,
        infix: str = "",
        infix_padding: str = PADDING_BOTH,
        subforms: Tuple[TextualForm, ...] = (),
    ) -> None:
        """
        :param infix: the infix operator separating the subforms
        :param infix_padding: the padding mode for the infix operator
        :param subforms: the subforms
        """
        super().__init__(
            length=(
                sum(len(inner_representation) for inner_representation in subforms)
                + max(len(subforms) - 1, 0)
                * (len(infix) + (InfixForm.__PADDING_SPACES[infix_padding]))
            )
        )
        self.infix = infix
        self.infix_padding = infix_padding
        self.subforms = subforms

    @staticmethod
    def from_infix_expression(expression: InfixExpression) -> TextualForm:
        """
        Create a infix form from the given infix expression
        :param expression:
        :return:
        """

        subexpressions = expression.subexpressions
        if len(subexpressions) == 1:
            return TextualForm.from_expression(subexpressions[0])

        subforms = tuple(
            TextualForm.from_expression(subexpression).encapsulate_if(
                condition=(
                    subexpression.precedence
                    > expression.precedence - (0 if pos == 0 else 1)
                )
            )
            for pos, subexpression in enumerate(subexpressions)
        )

        infix = expression.infix

        infix_padding = (
            InfixForm.PADDING_RIGHT
            if infix in [",", ":"]
            else InfixForm.PADDING_NONE
            if infix in [".", ""]
            else InfixForm.PADDING_BOTH
        )

        return InfixForm(infix=infix, infix_padding=infix_padding, subforms=subforms)

    def _to_single_line(self) -> str:

        if self.infix:
            infix_padding = self.infix_padding
            if infix_padding is InfixForm.PADDING_NONE:
                infix = self.infix
            elif infix_padding is InfixForm.PADDING_RIGHT:
                infix = f"{self.infix} "
            else:
                assert (
                    infix_padding is InfixForm.PADDING_BOTH
                ), "known infix padding mode"
                infix = f" {self.infix} "
        else:
            infix = ""

        return infix.join(subform._to_single_line() for subform in self.subforms)

    def _to_multiple_lines(
        self,
        config: FormattingConfig,
        indent: int,
        leading_characters: int,
        trailing_characters: int,
    ) -> List[IndentedLine]:
        """
        Convert this representation to multiple lines
        :param indent: global indent of this expression
        :param leading_characters: leading space to reserve in first line
        :param trailing_characters: trailing space to reserve in last line
        :return: resulting lines
        """

        subforms: Tuple[TextualForm, ...] = self.subforms
        result: List[IndentedLine] = []

        if len(subforms) == 1:

            result.extend(
                subforms[0]._to_lines(
                    config=config,
                    indent=indent,
                    leading_characters=leading_characters,
                    trailing_characters=trailing_characters,
                )
            )

        else:

            last_idx = len(subforms) - 1
            infix = self.infix

            if self.infix_padding is InfixForm.PADDING_RIGHT:
                len_infix = len(infix)
                for idx, inner_representation in enumerate(subforms):
                    lines = inner_representation._to_lines(
                        config=config,
                        indent=indent,
                        leading_characters=(leading_characters if idx == 0 else 0),
                        trailing_characters=(
                            len_infix if idx < last_idx else trailing_characters
                        ),
                    )

                    if idx != last_idx:
                        # append infix to last line,
                        # except we're in the last representation
                        lines[-1] = IndentedLine(
                            indent=indent, text=f"{lines[-1].text}{infix}"
                        )

                    result.extend(lines)
            else:
                if self.infix_padding is InfixForm.PADDING_BOTH:
                    infix = f"{infix} "

                len_infix = len(infix)
                for idx, inner_representation in enumerate(subforms):
                    lines = inner_representation._to_lines(
                        config=config,
                        indent=indent,
                        leading_characters=leading_characters
                        if idx == 0
                        else len_infix,
                        trailing_characters=(
                            trailing_characters if idx == last_idx else 0
                        ),
                    )
                    if idx != 0:
                        # prepend infix to first line,
                        # except we're in the first representation
                        lines[0] = IndentedLine(
                            indent=indent, text=f"{infix}{lines[0].text}"
                        )

                    result.extend(lines)

        return result


#
# Public classes
#

__tracker = AllTracker(globals())


class PythonExpressionFormatter(ExpressionFormatter):
    """
    Formats expression objects as Python expressions, in line with the `black` style
    """

    def __init__(
        self, max_width: int = 80, indent_width: int = 4, single_line: bool = False
    ):
        """
        :param max_width: the maximum line width (ignored when enforcing single-line \
            text (default: 80)
        :param indent_width: the width of one indentation in spaces (default: 4)
        :param single_line: if `False`, include line breaks to keep the width within \
            maximum bounds (default: `False`)
        """
        self.config = FormattingConfig(
            max_width=max_width, indent_width=indent_width, single_line=single_line
        )

    def to_text(self, expression: Expression) -> str:
        """[see superclass]"""

        return TextualForm.from_expression(expression).to_text(self.config)

    to_text.__doc__ = ExpressionFormatter.to_text.__doc__


# Register class PythonExpressionFormat as the default display form
_DEFAULT_PYTHON_EXPRESSION_FORMATTER = PythonExpressionFormatter()
# noinspection PyProtectedMember
ExpressionFormatter._register_default_format(_DEFAULT_PYTHON_EXPRESSION_FORMATTER)

__tracker.validate()

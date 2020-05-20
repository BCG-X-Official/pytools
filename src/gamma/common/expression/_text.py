"""
String representations of expressions
"""

import logging
from abc import abstractmethod
from typing import *

from gamma.common import AllTracker
from gamma.common.expression._expression import (
    AtomicExpression,
    ComplexExpression,
    Expression,
    ExpressionFormatter,
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
    def from_expression(
        expression: Expression, encapsulate: bool = False
    ) -> "TextualForm":
        """
        Generate a textual form for the given expression
        :param expression: the expression to be transformed
        :param encapsulate: if `True`, encapsulate the expression in parentheses
        :return: the resulting textual form
        """
        if isinstance(expression, AtomicExpression):
            return AtomicForm(expression)
        else:
            expression: ComplexExpression
            return ComplexForm(expression, encapsulate=encapsulate)

    @abstractmethod
    def __len__(self) -> int:
        pass

    def __repr__(self) -> str:
        # noinspection PyProtectedMember
        return _DEFAULT_PYTHON_EXPRESSION_FORMATTER._form_to_text(self)


class AtomicForm(TextualForm):
    """
    A textual representation of an atomic expression
    """

    def __init__(self, expression: AtomicExpression) -> None:
        self.text = expression.text

    def __len__(self) -> int:
        return len(self.text)


class ComplexForm(TextualForm):
    """
    A hierarchical textual representation of a complex expression
    """

    PADDING_NONE = "none"
    PADDING_RIGHT = "right"
    PADDING_BOTH = "both"

    __PADDING_SPACES = {PADDING_NONE: 0, PADDING_RIGHT: 1, PADDING_BOTH: 2}

    def __init__(
        self, expression: ComplexExpression, encapsulate: bool = False
    ) -> None:
        subexpressions = expression.subexpressions

        subforms = tuple(
            TextualForm.from_expression(
                subexpression,
                encapsulate=(
                    len(subexpressions) > 1
                    and subexpression.precedence()
                    > expression.precedence() - (0 if pos == 0 else 1)
                ),
            )
            for pos, subexpression in enumerate(subexpressions)
        )

        brackets = expression.brackets
        assert brackets is None or len(brackets) == 2, "brackets is None or a pair"

        first_subform = subforms[0] if subforms else None

        if (
            not brackets
            and isinstance(first_subform, ComplexForm)
            and len(subforms) == 1
            and not first_subform.prefix
        ):
            # promote inner brackets to top level if inner is a bracketed singleton

            _inner_single = first_subform
            brackets = _inner_single.brackets
            infix = _inner_single.infix
            infix_padding = _inner_single.infix_padding
            subforms = _inner_single.inner

        else:
            infix = expression.infix
            infix_padding = (
                ComplexForm.PADDING_RIGHT
                if infix in [",", ":"]
                else ComplexForm.PADDING_NONE
                if infix in [".", ""]
                else ComplexForm.PADDING_BOTH
            )

        if encapsulate and not brackets:
            brackets = ("(", ")")

        self.prefix = prefix = (
            TextualForm.from_expression(expression.prefix)
            if expression.prefix
            else None
        )

        self.brackets = brackets
        self.infix = infix
        self.infix_padding = infix_padding
        self.inner = subforms

        self.__len = (
            (len(prefix) if prefix else 0)
            + (len(brackets[0]) + len(brackets[1]) if brackets else 0)
            + sum(len(inner_representation) for inner_representation in subforms)
            + max(len(subforms) - 1, 0)
            * (len(infix) + (ComplexForm.__PADDING_SPACES[infix_padding]))
        )

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

    def __len__(self) -> int:
        return self.__len


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

        return self._form_to_text(TextualForm.from_expression(expression))

    def _form_to_text(self, form: TextualForm) -> str:
        # render a textual form as a string

        config = self.config
        if config.single_line:

            return self._to_single_line(form=form)

        else:

            def _spacing(indent: int) -> str:
                return " " * (config.indent_width * indent)

            return "\n".join(
                f"{_spacing(indent)}{text}"
                for indent, text in self._to_lines(form=form, config=config)
            )

    to_text.__doc__ = ExpressionFormatter.to_text.__doc__

    def _to_lines(
        self,
        form: TextualForm,
        config: FormattingConfig,
        indent: int = 0,
        leading_characters: int = 0,
        trailing_characters: int = 0,
    ) -> List[IndentedLine]:
        """
        Convert this representation to as few lines as possible without exceeding
        maximum line length
        :param indent: global indent of this expression
        :param leading_characters: leading space to reserve in first line
        :param trailing_characters: trailing space to reserve in last line
        :return: resulting lines
        """

        if (
            isinstance(form, ComplexForm)
            and leading_characters
            + len(form)
            + indent * config.indent_width
            + trailing_characters
            > config.max_width
        ):
            return self._to_multiple_lines(
                form=form,
                config=config,
                indent=indent,
                leading_characters=leading_characters,
                trailing_characters=trailing_characters,
            )
        else:
            return [IndentedLine(indent=indent, text=self._to_single_line(form=form))]

    def _to_single_line(self, form: TextualForm) -> str:
        """
        Convert this representation to a single-line string
        :return: the resulting string
        """
        if isinstance(form, AtomicForm):
            return form.text

        assert isinstance(form, ComplexForm), f"form is not complex: {type(form)}"

        if form.infix:
            infix_padding = form.infix_padding
            if infix_padding is ComplexForm.PADDING_NONE:
                infix = form.infix
            elif infix_padding is ComplexForm.PADDING_RIGHT:
                infix = f"{form.infix} "
            elif infix_padding is ComplexForm.PADDING_BOTH:
                infix = f" {form.infix} "
            else:
                raise ValueError(f"unknown infix padding: {infix_padding}")
        else:
            infix = ""

        inner = infix.join(
            self._to_single_line(form=subexpression_form)
            for subexpression_form in form.inner
        )

        line_inner = f"{form.opening_bracket}{inner}{form.closing_bracket}"

        prefix = form.prefix
        if prefix:
            return f"{self._to_single_line(form=prefix)}{line_inner}"
        else:
            return line_inner

    def _to_multiple_lines(
        self,
        form: ComplexForm,
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

        result: List[IndentedLine]

        prefix = form.prefix
        inner: Tuple[ComplexForm, ...] = form.inner

        # we add parentheses if there is no existing bracketing, and either
        # - there is a prefix, or
        # - we are at indentation level 0 and have more than one inner element
        parenthesize = not form.brackets and (
            prefix or (indent == 0 and len(inner) > 1)
        )

        if parenthesize:
            opening_bracket = f"("
        else:
            opening_bracket = f"{form.opening_bracket}"

        if isinstance(prefix, str):
            result = [IndentedLine(indent=indent, text=prefix)]
        elif prefix:
            result = self._to_lines(
                form=prefix,
                config=config,
                indent=indent,
                leading_characters=leading_characters,
                trailing_characters=len(opening_bracket),
            )
        else:
            result = []

        if opening_bracket:
            if prefix:
                prefix_last_line = result[-1]
                result[-1] = IndentedLine(
                    indent=prefix_last_line.indent,
                    text=prefix_last_line.text + opening_bracket,
                )
            else:
                result.append(IndentedLine(indent=indent, text=opening_bracket))
            inner_indent = indent + 1
        else:
            inner_indent = indent

        if len(inner) == 1:
            inner_single = inner[0]

            result.extend(
                self._to_lines(
                    form=inner_single,
                    config=config,
                    indent=inner_indent,
                    leading_characters=leading_characters,
                    trailing_characters=trailing_characters,
                )
            )

        elif inner:

            last_idx = len(inner) - 1
            infix = form.infix

            if form.infix_padding is ComplexForm.PADDING_RIGHT:
                len_infix = len(infix)
                for idx, inner_representation in enumerate(inner):
                    lines = self._to_lines(
                        form=inner_representation,
                        config=config,
                        indent=inner_indent,
                        leading_characters=(leading_characters if idx == 0 else 0),
                        trailing_characters=(
                            len_infix if idx < last_idx else trailing_characters
                        ),
                    )

                    if idx != last_idx:
                        # append infix to last line,
                        # except we're in the last representation
                        lines[-1] = IndentedLine(
                            indent=inner_indent, text=f"{lines[-1].text}{infix}"
                        )

                    result.extend(lines)
            else:
                if form.infix_padding is ComplexForm.PADDING_BOTH:
                    infix = f"{infix} "

                len_infix = len(infix)
                for idx, inner_representation in enumerate(inner):
                    lines = self._to_lines(
                        form=inner_representation,
                        config=config,
                        indent=inner_indent,
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
                            indent=inner_indent, text=f"{infix}{lines[0].text}"
                        )

                    result.extend(lines)

        if parenthesize:
            closing_bracket = f")"
        else:
            closing_bracket = f"{form.closing_bracket}"

        if closing_bracket:
            result.append(IndentedLine(indent=indent, text=closing_bracket))

        return result


# Register class PythonExpressionFormat as the default display form
_DEFAULT_PYTHON_EXPRESSION_FORMATTER = PythonExpressionFormatter()
# noinspection PyProtectedMember
ExpressionFormatter._register_default_format(_DEFAULT_PYTHON_EXPRESSION_FORMATTER)

__tracker.validate()

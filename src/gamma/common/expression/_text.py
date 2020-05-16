"""
String representations of expressions
"""

import logging
from typing import *

from gamma.common import AllTracker
from gamma.common.expression._expression import Expression, ExpressionFormatter

log = logging.getLogger(__name__)


__all__ = ["PythonExpressionFormatter"]
__tracker = AllTracker(globals())


class _IndentedLine(NamedTuple):
    """
    An indented line of text
    """

    indent: int
    text: str


class _TextualForm:
    """
    A hierarchical textual representation of an expression
    """

    PADDING_NONE = "none"
    PADDING_RIGHT = "right"
    PADDING_BOTH = "both"

    __PADDING_SPACES = {PADDING_NONE: 0, PADDING_RIGHT: 1, PADDING_BOTH: 2}

    def __init__(self, expression: Expression, encapsulate: bool = False) -> None:
        subexpressions = expression.subexpressions

        inner = tuple(
            _TextualForm(
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

        prefix = expression.prefix

        if not brackets and len(inner) == 1 and not inner[0].prefix:
            # promote inner brackets to top level if inner is a bracketed singleton

            _inner_single = inner[0]
            brackets = _inner_single.brackets
            infix = _inner_single.infix
            infix_padding = _inner_single.infix_padding
            inner = _inner_single.inner

        else:
            infix = expression.infix
            infix_padding = (
                _TextualForm.PADDING_RIGHT
                if infix in [",", ":"]
                else _TextualForm.PADDING_NONE
                if infix == "."
                else _TextualForm.PADDING_BOTH
            )

        if encapsulate and not brackets:
            brackets = ("(", ")")

        self.prefix = prefix
        self.brackets = brackets
        self.infix = infix
        self.infix_padding = infix_padding
        self.inner = inner

        self.__len = (
            len(prefix)
            + (len(brackets[0]) + len(brackets[1]) if brackets else 0)
            + sum(len(inner_representation) for inner_representation in inner)
            + max(len(inner) - 1, 0)
            * (len(infix) + (_TextualForm.__PADDING_SPACES[infix_padding]))
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

    def __repr__(self) -> str:
        # noinspection PyProtectedMember
        return _DEFAULT_PYTHON_EXPRESSION_FORMATTER._form_to_text(self)

    def __len__(self) -> int:
        return self.__len


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
        self.max_width = max_width
        self.indent_width = indent_width
        self.single_line = single_line

    def to_text(self, expression: "Expression") -> str:
        """[see superclass]"""

        return self._form_to_text(_TextualForm(expression))

    def _form_to_text(self, form: _TextualForm) -> str:
        # render a textual form as a string

        if self.single_line:

            return self._to_single_line(form=form)

        else:

            def _spacing(indent: int) -> str:
                return " " * (self.indent_width * indent)

            return "\n".join(
                f"{_spacing(indent)}{text}" for indent, text in self._to_lines(form)
            )

    to_text.__doc__ = ExpressionFormatter.to_text.__doc__

    def _to_lines(
        self,
        form: _TextualForm,
        indent: int = 0,
        leading_characters: int = 0,
        trailing_characters: int = 0,
    ) -> List[_IndentedLine]:
        """
        Convert this representation to as few lines as possible without exceeding
        maximum line length
        :param indent: global indent of this expression
        :param leading_characters: leading space to reserve in first line
        :param trailing_characters: trailing space to reserve in last line
        :return: resulting lines
        """

        if (
            leading_characters
            + len(form)
            + indent * self.indent_width
            + trailing_characters
            > self.max_width
        ):
            return self._to_multiple_lines(
                form=form,
                indent=indent,
                leading_characters=leading_characters,
                trailing_characters=trailing_characters,
            )
        else:
            return [_IndentedLine(indent=indent, text=self._to_single_line(form=form))]

    def _to_single_line(self, form: _TextualForm) -> str:
        """
        Convert this representation to a single-line string
        :return: the resulting string
        """
        if form.infix:
            infix_padding = form.infix_padding
            if infix_padding is _TextualForm.PADDING_NONE:
                infix = form.infix
            elif infix_padding is _TextualForm.PADDING_RIGHT:
                infix = f"{form.infix} "
            elif infix_padding is _TextualForm.PADDING_BOTH:
                infix = f" {form.infix} "
            else:
                raise ValueError(f"unknown infix padding: {infix_padding}")
        else:
            infix = ""
        inner = infix.join(
            self._to_single_line(form=subexpression_form)
            for subexpression_form in form.inner
        )
        return f"{form.prefix}{form.opening_bracket}{inner}{form.closing_bracket}"

    def _to_multiple_lines(
        self,
        form: _TextualForm,
        indent: int,
        leading_characters: int,
        trailing_characters: int,
    ) -> List[_IndentedLine]:
        """
        Convert this representation to multiple lines
        :param indent: global indent of this expression
        :param leading_characters: leading space to reserve in first line
        :param trailing_characters: trailing space to reserve in last line
        :return: resulting lines
        """

        result: List[_IndentedLine] = []

        inner: Tuple[_TextualForm, ...] = form.inner

        # we add parentheses if there is no existing bracketing, and either
        # - there is a prefix, or
        # - we are at indentation level 0 and have more than one inner element
        parenthesize = not form.brackets and (
            form.prefix or (indent == 0 and len(inner) > 1)
        )

        if parenthesize:
            opening_bracket = f"{form.prefix}("
        else:
            opening_bracket = f"{form.prefix}{form.opening_bracket}"

        if opening_bracket:
            result.append(_IndentedLine(indent=indent, text=opening_bracket))
            inner_indent = indent + 1
        else:
            inner_indent = indent

        if len(inner) == 1:
            inner_single = inner[0]

            result.extend(
                self._to_lines(
                    form=inner_single,
                    indent=inner_indent,
                    leading_characters=leading_characters,
                    trailing_characters=trailing_characters,
                )
            )

        elif inner:

            last_idx = len(inner) - 1
            infix = form.infix

            if form.infix_padding is _TextualForm.PADDING_RIGHT:
                len_infix = len(infix)
                for idx, inner_representation in enumerate(inner):
                    lines = self._to_lines(
                        form=inner_representation,
                        indent=inner_indent,
                        leading_characters=(leading_characters if idx == 0 else 0),
                        trailing_characters=(
                            len_infix if idx < last_idx else trailing_characters
                        ),
                    )

                    if idx != last_idx:
                        # append infix to last line,
                        # except we're in the last representation
                        lines[-1] = _IndentedLine(
                            indent=inner_indent, text=f"{lines[-1].text}{infix}"
                        )

                    result.extend(lines)
            else:
                if form.infix_padding is _TextualForm.PADDING_BOTH:
                    infix = f"{infix} "

                len_infix = len(infix)
                for idx, inner_representation in enumerate(inner):
                    lines = self._to_lines(
                        form=inner_representation,
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
                        lines[0] = _IndentedLine(
                            indent=inner_indent, text=f"{infix}{lines[0].text}"
                        )

                    result.extend(lines)

        if parenthesize:
            closing_bracket = f")"
        else:
            closing_bracket = f"{form.closing_bracket}"

        if closing_bracket:
            result.append(_IndentedLine(indent=indent, text=closing_bracket))

        return result


# Register class PythonExpressionFormat as the default display form
_DEFAULT_PYTHON_EXPRESSION_FORMATTER = PythonExpressionFormatter()
# noinspection PyProtectedMember
ExpressionFormatter._register_default_format(_DEFAULT_PYTHON_EXPRESSION_FORMATTER)

__tracker.validate()

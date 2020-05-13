"""
String representations of expressions
"""

import logging
from typing import *


log = logging.getLogger(__name__)

INDENT_WIDTH = 4
MAX_LINE_LENGTH = 80

__all__ = ["IndentedLine", "ExpressionRepresentation"]


class IndentedLine(NamedTuple):
    """
    An indented line of text
    """

    indent: int
    text: str


class ExpressionRepresentation:
    """
    A hierarchical string representation of an expression
    """

    PADDING_NONE = "none"
    PADDING_RIGHT = "right"
    PADDING_BOTH = "both"

    __PADDING_SPACES = {PADDING_NONE: 0, PADDING_RIGHT: 1, PADDING_BOTH: 2}

    def __init__(
        self,
        prefix: str = "",
        *,
        brackets: Optional[str] = None,
        infix: str = "",
        infix_padding: str = PADDING_BOTH,
        inner: Tuple["ExpressionRepresentation", ...] = (),
    ):
        """
        :param prefix: the start of the expression
        :param infix: separator for subexpressions nested inside the expression
        :param infix_padding: where to pad the infix withspaces. Permissible values \
            are `none`. `right`, snd `both` (default: `both`)
        :param inner: list of representations of the subexpressions nested inside the \
            expression
        """

        if brackets and len(brackets) != 2:
            raise ValueError(
                f"arg brackets must have exactly 2 characters but is {brackets}"
            )

        # promote inner brackets to top level if inner is a bracketed singleton
        if not brackets and len(inner) == 1:
            inner_single = inner[0]
            if not inner_single.prefix:
                brackets = inner_single.brackets
                inner = inner_single.inner

        def validate_padding(permitted: Iterable[str]) -> str:
            for option in permitted:
                if infix_padding == option:
                    return option
            raise ValueError(f"illegal value for arg infix_padding: {infix_padding}")

        self.prefix = prefix
        self.brackets = brackets
        self.infix = infix
        self.infix_padding = validate_padding(self.__PADDING_SPACES.keys())
        self.inner = inner

        self.__len = (
            len(prefix)
            + (len(brackets) if brackets else 0)
            + sum(len(inner_representation) for inner_representation in inner)
            + max(len(inner) - 1, 0)
            * (len(infix) + (ExpressionRepresentation.__PADDING_SPACES[infix_padding]))
        )

    def to_string(self, multiline: bool = True) -> str:
        """
        Convert this representation to a string
        :param multiline: if `True`, include line breaks to keep the width within \
            maximum bounds (default: `True`)
        :return: this representation rendered as a string
        """

        if multiline:

            def _spacing(indent: int) -> str:
                return " " * (INDENT_WIDTH * indent)

            return "\n".join(
                f"{_spacing(indent)}{text}" for indent, text in self._to_lines()
            )

        else:
            return self._to_single_line()

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

    def _to_lines(
        self, indent: int = 0, leading_characters: int = 0, trailing_characters: int = 0
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
            leading_characters + len(self) + indent * INDENT_WIDTH + trailing_characters
            > MAX_LINE_LENGTH
        ):
            return self._to_multiple_lines(
                indent=indent,
                leading_characters=leading_characters,
                trailing_characters=trailing_characters,
            )
        else:
            return [IndentedLine(indent=indent, text=self._to_single_line())]

    def _to_single_line(self) -> str:
        """
        Convert this representation to a single-line string
        :return: the resulting string
        """
        if self.infix:
            infix_padding = self.infix_padding
            if infix_padding is ExpressionRepresentation.PADDING_NONE:
                infix = self.infix
            elif infix_padding is ExpressionRepresentation.PADDING_RIGHT:
                infix = f"{self.infix} "
            elif infix_padding is ExpressionRepresentation.PADDING_BOTH:
                infix = f" {self.infix} "
            else:
                raise ValueError(f"unknown infix padding: {infix_padding}")
        else:
            infix = ""
        inner = infix.join(
            subexpression_representation._to_single_line()
            for subexpression_representation in self.inner
        )
        return f"{self.prefix}{self.opening_bracket}{inner}{self.closing_bracket}"

    def _to_multiple_lines(
        self, indent: int, leading_characters: int, trailing_characters: int
    ) -> List[IndentedLine]:
        """
        Convert this representation to multiple lines
        :param indent: global indent of this expression
        :param leading_characters: leading space to reserve in first line
        :param trailing_characters: trailing space to reserve in last line
        :return: resulting lines
        """

        result: List[IndentedLine] = []

        inner: Tuple[ExpressionRepresentation, ...] = self.inner

        # we add parentheses if there is no existing bracketing, and either
        # - there is a prefix, or
        # - we are at indentation level 0 and have more than one inner element
        parenthesize = not self.brackets and (
            self.prefix or (indent == 0 and len(inner) > 1)
        )

        if parenthesize:
            opening_bracket = f"{self.prefix}("
        else:
            opening_bracket = f"{self.prefix}{self.opening_bracket}"

        if opening_bracket:
            result.append(IndentedLine(indent=indent, text=opening_bracket))
            inner_indent = indent + 1
        else:
            inner_indent = indent

        if len(inner) == 1:
            inner_single = inner[0]

            result.extend(
                inner_single._to_lines(
                    indent=inner_indent,
                    leading_characters=leading_characters,
                    trailing_characters=trailing_characters,
                )
            )

        elif inner:

            last_idx = len(inner) - 1
            infix = self.infix

            if self.infix_padding is ExpressionRepresentation.PADDING_RIGHT:
                len_infix = len(infix)
                for idx, inner_representation in enumerate(inner):
                    lines = inner_representation._to_lines(
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
                if self.infix_padding is ExpressionRepresentation.PADDING_BOTH:
                    infix = f"{infix} "

                len_infix = len(infix)
                for idx, inner_representation in enumerate(inner):
                    lines = inner_representation._to_lines(
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
            closing_bracket = f"{self.closing_bracket}"

        if closing_bracket:
            result.append(IndentedLine(indent=indent, text=closing_bracket))

        return result

    def __repr__(self) -> str:
        return self.to_string()

    def __len__(self) -> int:
        return self.__len

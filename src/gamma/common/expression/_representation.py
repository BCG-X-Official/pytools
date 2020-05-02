"""
String representations of expressions
"""

from __future__ import annotations

import itertools
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

    def __init__(
        self,
        prefix: str = "",
        *,
        infix: str = "",
        infix_spacing: bool = True,
        infix_keep_with_left: bool = False,
        inner: Tuple[ExpressionRepresentation, ...] = (),
        suffix: str = "",
    ):
        """
        :param prefix: the start of the expression
        :param infix: separator for subexpressions nested inside the expression
        :param infix_spacing: if `True`, insert spaces between infix and operands
        :param infix_keep_with_left: if `True`, always keep the infix operator \
            with the left operand and never insert a space left of the infix
        :param inner: list of representations of the subexpressions nested inside the \
            expression
        :param suffix: the end of the expression
        """

        self.prefix = prefix
        self.infix = infix
        self.infix_spacing = infix_spacing
        self.infix_keep_with_left = infix_keep_with_left
        self.inner = inner
        self.suffix = suffix
        infix_length = len(infix) + (1 if infix_keep_with_left else 2)
        self.__len = (
            len(prefix)
            + sum(len(inner_representation) for inner_representation in inner)
            + max(len(inner) - 1, 0) * infix_length
            + len(suffix)
        )

    def with_wrapper(self, prefix: str, suffix: str) -> ExpressionRepresentation:
        """
        Construct a copy of this representation with a new prefix and suffix
        :param prefix: the new prefix
        :param suffix: the new suffix
        :return: the new representation
        """
        return ExpressionRepresentation(
            prefix=prefix,
            infix=self.infix,
            infix_keep_with_left=self.infix_keep_with_left,
            inner=self.inner,
            suffix=suffix,
        )

    def to_string(self, multiline: bool = True) -> str:
        """
        Convert this representation to a string
        :param multiline: if `True`, include line breaks to keep the width within \
            maximum bounds (default: `True`)
        :return: this representation rendered as a string
        """

        def _spacing(indent: int) -> str:
            return " " * (INDENT_WIDTH * indent)

        lines: List[IndentedLine] = self._to_lines()
        if multiline:
            return "\n".join(f"{_spacing(indent)}{text}" for indent, text in lines)
        else:
            if len(lines) == 1:
                return lines[0].text
            else:
                return "".join(
                    f"{text} " if indent == next_indent else text
                    for (indent, text), next_indent in itertools.zip_longest(
                        lines, (indent for indent, _ in lines[1:])
                    )
                )

    def _to_lines(
        self, indent: int = 0, leading_space: int = 0, trailing_space: int = 0
    ) -> List[IndentedLine]:
        """
        Convert this representation to as few lines as possible without exceeding
        maximum line length
        :param indent: global indent of this expression
        :param leading_space: leading space to reserve in first line
        :param trailing_space: trailing space to reserve in last line
        :return: resulting lines
        """
        log.warning(
            (
                self._to_single_line(),
                indent * INDENT_WIDTH,
                leading_space,
                len(self),
                trailing_space,
            )
        )

        if (
            leading_space + len(self) + indent * INDENT_WIDTH + trailing_space
            > MAX_LINE_LENGTH
        ):
            return self._to_multiple_lines(
                indent=indent,
                leading_space=leading_space,
                trailing_space=trailing_space,
            )
        else:
            return [IndentedLine(indent=indent, text=self._to_single_line())]

    def _to_single_line(self) -> str:
        """
        Convert this representation to a single-line string
        :return: the resulting string
        """
        if self.infix:
            if not self.infix_spacing:
                infix = self.infix
            elif self.infix_keep_with_left:
                infix = f"{self.infix} "
            else:
                infix = f" {self.infix} "
        else:
            infix = ""
        inner = infix.join(
            subexpression_representation._to_single_line()
            for subexpression_representation in self.inner
        )
        return f"{self.prefix}{inner}{self.suffix}"

    def _to_multiple_lines(
        self, indent: int, leading_space: int, trailing_space: int
    ) -> List[IndentedLine]:
        """
        Convert this representation to multiple lines
        :param indent: global indent of this expression
        :param leading_space: leading space to reserve in first line
        :param trailing_space: trailing space to reserve in last line
        :return: resulting lines
        """
        result: List[IndentedLine] = []
        if self.prefix:
            result.append(IndentedLine(indent=indent, text=self.prefix))
            inner_indent = indent + 1
        else:
            inner_indent = indent

        inner = self.inner
        if inner:

            last_idx = len(inner) - 1
            infix = self.infix

            if self.infix_keep_with_left:
                len_infix = len(infix)
                for idx, inner_representation in enumerate(inner):
                    lines = inner_representation._to_lines(
                        indent=inner_indent,
                        leading_space=(leading_space if idx == 0 else 0),
                        trailing_space=len_infix if idx < last_idx else trailing_space,
                    )

                    if idx != last_idx:
                        # append infix to last line,
                        # except we're in the last representation
                        lines[-1] = IndentedLine(
                            indent=inner_indent, text=f"{lines[-1].text}{infix}"
                        )

                    result.extend(lines)
            else:
                if self.infix_spacing:
                    infix = f"{infix} "

                len_infix = len(infix)
                for idx, inner_representation in enumerate(inner):
                    lines = inner_representation._to_lines(
                        indent=inner_indent,
                        leading_space=leading_space if idx == 0 else len_infix,
                        trailing_space=(trailing_space if idx == last_idx else 0),
                    )
                    if idx != 0:
                        # prepend infix to first line,
                        # except we're in the first representation
                        lines[0] = IndentedLine(
                            indent=inner_indent, text=f"{infix}{lines[0].text}"
                        )

                    result.extend(lines)

        if self.suffix:
            result.append(IndentedLine(indent=indent, text=self.suffix))
        return result

    def __str__(self) -> str:
        return self.to_string()

    def __len__(self) -> int:
        return self.__len

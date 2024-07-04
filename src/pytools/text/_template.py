"""
Implementation of TextTemplate.
"""

from __future__ import annotations

import logging
import string
from collections.abc import Iterable, Sized
from typing import Any

from pytools.api import as_set, inheritdoc
from pytools.expression import (
    Expression,
    HasExpressionRepr,
    expression_from_init_params,
)

log = logging.getLogger(__name__)

__all__ = [
    "TextTemplate",
]


#
# Class declarations
#


@inheritdoc(match="""[see superclass]""")
class TextTemplate(HasExpressionRepr):
    """
    A template for generating text by substituting format keys in a format string with
    actual values.

    The format string must contain the required formatting keys, and no unexpected keys.

    Method :meth:`format_with_attributes` formats the text by substituting the format
    keys with the given attributes passed as keyword arguments.

    If the template is `strict`, an error is raised if not all attributes have a
    corresponding key in the format string. If the template is not strict, attributes
    must be provided to substitute all keys in the format string, but attributes not
    present in the formatting keys will be ignored.
    """

    #: A format string with formatting keys that will be substituted with values.
    format_string: str

    #: The formatting keys used in the format string.
    formatting_keys: set[str]

    #: If ``False``, an error is raised if the format string contains keys other than
    # the required keys; if ``True``, additional keys are allowed.
    allow_additional_keys: bool

    #: If ``False```, the template is strict and an error is raised if not all
    #: attributes have a corresponding key in the format string; if ``True``, attributes
    #: not present in the formatting keys will be ignored.
    ignore_unmatched_attributes: bool

    def __init__(
        self,
        *,
        format_string: str,
        required_keys: Iterable[str],
        allow_additional_keys: bool = False,
        ignore_unmatched_attributes: bool = False,
    ) -> None:
        """
        :param format_string: a format string with formatting keys that will be
            substituted with values
        :param required_keys: the names of the formatting keys required in the format
            string
        :param allow_additional_keys: if ``False``, an error is raised if the format
            string contains keys other than the required keys; if ``True``, additional
            keys are allowed (default: ``False``)
        :param ignore_unmatched_attributes: if ``False``, the template is strict and an
            error is raised if not all attributes have a corresponding key in the format
            string; if ``True``, attributes not present in the format string will be
            ignored (default: ``False``)
        """
        super().__init__()
        required_keys = as_set(
            required_keys,
            element_type=str,
            arg_name="formatting_keys",
        )
        self.formatting_keys = _validate_format_string(
            format_string,
            required_keys=required_keys,
            allow_additional_keys=allow_additional_keys,
        )

        self.format_string = format_string
        self.allow_additional_keys = allow_additional_keys
        self.ignore_unmatched_attributes = ignore_unmatched_attributes

    def format_with_attributes(self, **attributes: Any) -> str:
        """
        Formats the text using the format string and the given attributes passed as
        keyword arguments.

        :param attributes: the keyword arguments to use for formatting
        :return: the formatted text
        """

        if not self.ignore_unmatched_attributes:
            # We run in strict mode: ensure that the attribute keys match the formatting
            # keys
            if set(attributes) != self.formatting_keys:
                raise ValueError(
                    f"Provided attributes must have the same keys as formatting keys "
                    f"{self.formatting_keys!r}, but got {attributes!r}"
                )

        else:
            # We run in non-strict mode: ignore attributes not present in the formatting
            # keys but ensure that all formatting keys are present in the attributes
            missing_attributes = self.formatting_keys - set(attributes)
            if missing_attributes:
                raise ValueError(
                    f"No values provided for formatting key"
                    f"{_plural(missing_attributes)}: "
                    + ", ".join(map(repr, sorted(missing_attributes)))
                )

        return self.format_string.format(**attributes)

    def to_expression(self) -> Expression:
        """[see superclass]"""
        return expression_from_init_params(self)


def _validate_format_string(
    format_string: str, *, required_keys: Iterable[str], allow_additional_keys: bool
) -> set[str]:
    """
    Validate that the given format string contains the required keys, and that it does
    not contain any unexpected keys.

    :param format_string: the format string to validate
    :param required_keys: the required keys
    :param allow_additional_keys: if ``False``, an error is raised if the format string
        contains keys other than the required keys; if ``True``, additional keys are
        allowed
    :return: all formatting keys in the format string
    :raises TypeError: if the given format string is not a string
    """

    if not isinstance(format_string, str):
        raise TypeError(f"Format string must be a string, but got: {format_string!r}")

    # ensure arg expected_keys is a set
    required_keys = as_set(required_keys, element_type=str, arg_name="required_keys")

    # get all keys from the format string
    actual_keys = {
        field_name
        for _, field_name, _, _ in string.Formatter().parse(format_string)
        if field_name is not None
    }

    # check that the format string contains the required keys
    missing_keys = required_keys - actual_keys
    if missing_keys:
        raise ValueError(
            f"Format string is missing required key{_plural(missing_keys)}: "
            + ", ".join(map(repr, sorted(missing_keys)))
        )

    if not allow_additional_keys:
        # check that the format string does not contain unexpected keys
        unexpected_keys = actual_keys - required_keys
        if unexpected_keys:
            raise ValueError(
                f"Format string contains unexpected key{_plural(unexpected_keys)}: "
                + ", ".join(map(repr, sorted(unexpected_keys)))
            )

    return actual_keys


def _plural(items: Sized) -> str:
    return "" if len(items) == 1 else "s"

"""
Unit tests for class ``TextTemplate``
"""

import pytest

from pytools.expression import freeze
from pytools.expression.atomic import Id
from pytools.text import TextTemplate


def test_text_template_strict() -> None:

    with pytest.raises(
        TypeError,
        match=r"^Format string must be a string, but got: 42$",
    ):
        TextTemplate(format_string=42, required_keys=[])  # type: ignore[arg-type]

    with pytest.raises(
        ValueError,
        match=r"^Format string is missing required key: 'not_in_template'$",
    ):
        TextTemplate(
            format_string="Hello, {name}!",
            required_keys=["name", "not_in_template"],
        )
    with pytest.raises(
        ValueError,
        match=r"^Format string contains unexpected key: 'not_required'$",
    ):
        TextTemplate(
            format_string="Hello, {name}{not_required}!",
            required_keys=["name"],
        )

    template_strict = TextTemplate(
        format_string="Hello, {name}!",
        required_keys=["name"],
    )

    with pytest.raises(
        ValueError,
        match=(
            r"^Provided attributes must have the same keys as formatting keys "
            r"{'name'}, but got {'nickname': 'Jack'}$"
        ),
    ):
        template_strict.format_with_attributes(nickname="Jack")

    with pytest.raises(
        ValueError,
        match=(
            r"^Provided attributes must have the same keys as formatting keys "
            r"{'name'}, but got {'name': 'Jacob', 'nickname': 'Jack'}$"
        ),
    ):
        template_strict.format_with_attributes(name="Jacob", nickname="Jack")

    assert template_strict.format_with_attributes(name="Jacob") == "Hello, Jacob!"


def test_text_template_relaxed() -> None:

    with pytest.raises(
        ValueError,
        match=r"^Format string is missing required key: 'not_in_template'$",
    ):
        TextTemplate(
            format_string="Hello, {name}!",
            required_keys=["name", "not_in_template"],
            ignore_unmatched_attributes=True,
        )

    with pytest.raises(
        ValueError,
        match=r"^Format string contains unexpected key: 'not_required'$",
    ):
        TextTemplate(
            format_string="Hello, {name}{not_required}!",
            required_keys=["name"],
            ignore_unmatched_attributes=True,
        )

    template = TextTemplate(
        format_string="Hello, {name}{not_required}!",
        required_keys=["name"],
        allow_additional_keys=True,
        ignore_unmatched_attributes=True,
    )

    with pytest.raises(
        ValueError,
        match=r"^No values provided for formatting key: 'not_required'$",
    ):
        template.format_with_attributes(name="Jacob")

    template = TextTemplate(
        format_string="Hello, {name}!",
        required_keys=["name"],
        ignore_unmatched_attributes=True,
    )

    with pytest.raises(
        ValueError,
        match=r"^No values provided for formatting key: 'name'$",
    ):
        template.format_with_attributes(nickname="Jack")

    assert (
        template.format_with_attributes(name="Jacob", nickname="Jack")
        == "Hello, Jacob!"
    )

    assert freeze(template.to_expression()) == freeze(
        Id(TextTemplate)(
            format_string="Hello, {name}!", ignore_unmatched_attributes=True
        )
    )

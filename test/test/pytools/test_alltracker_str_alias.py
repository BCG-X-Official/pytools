"""
Test that the AllTracker evaluates type aliases defined as strings.
"""

import importlib
from collections.abc import Sequence
from typing import get_type_hints

import pytest


@pytest.mark.parametrize(
    argnames="module_name",
    argvalues=["alias_future", "alias_plain", "alias_exported"],
)
def test_string_alias(module_name: str) -> None:
    module = importlib.import_module(f"test.pytools.{module_name}")

    assert module.StrAlias == int | str
    assert get_type_hints(module.Holder)["x"] == (
        int | str | Sequence[int | str] | None
    )

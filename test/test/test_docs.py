"""
Test docstrings.
"""

from pytools.api import DocValidator


def test_docstrings() -> None:
    assert DocValidator(root_dir="src").validate_doc(), "docstrings are valid"

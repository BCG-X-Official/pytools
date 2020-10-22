"""
Test the pytools.viz module
"""


def test_imports() -> None:
    from pytools.viz import colors, dendrogram, distribution, matrix, text, util
    from pytools.viz.dendrogram import base as dendrogram_base

    # we need this assertion to prevent an "unused imports" error during linting
    assert all(
        module is not None
        for module in [
            colors,
            dendrogram,
            dendrogram_base,
            distribution,
            matrix,
            text,
            util,
        ]
    )
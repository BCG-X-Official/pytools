"""
Test the pytools.viz module
"""


def test_imports() -> None:
    from pytools.viz import color, dendrogram, distribution, matrix, util
    from pytools.viz.dendrogram import base as dendrogram_base

    # we need this assertion to prevent an "unused imports" error during linting
    assert all(
        module is not None
        for module in [
            color,
            dendrogram,
            dendrogram_base,
            distribution,
            matrix,
            util,
        ]
    )

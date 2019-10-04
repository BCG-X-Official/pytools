"""
Tests for package gamma.viz.dendrogram
"""

# noinspection PyPackageRequirements
import hashlib
import logging
from io import StringIO

import numpy as np

# noinspection PyPackageRequirements
import pytest

# noinspection PyPackageRequirements
from scipy.cluster.hierarchy import linkage

from gamma.viz.dendrogram import DendrogramDrawer, DendrogramReportStyle, LinkageTree

log = logging.getLogger(__name__)


@pytest.fixture
def linkage_tree() -> LinkageTree:
    """Create a linkage tree for drawing tests."""
    x = np.array([[i] for i in [2, 8, 0, 4, 1, 9, 9, 0]])
    return LinkageTree(
        scipy_linkage_matrix=linkage(x),
        leaf_labels=list("ABCDEFGH"),
        leaf_weights=[(w + 1) / 36 for w in range(8)],
    )


def test_dendrogram_drawer_text(linkage_tree: LinkageTree) -> None:
    checksum_dendrogram_report = "aa90a5bd6ba5750a44c3718854f1ac83"

    with pytest.raises(ValueError) as value_error:
        DendrogramDrawer(
            title="Test", linkage=linkage_tree, style=DendrogramReportStyle()
        )
    assert value_error.value.args == (
        "arg max_distance=1.0 must be equal to or greater than arg "
        "linkage.root.children_distance=4.0",
    )

    with StringIO() as out:

        dd = DendrogramDrawer(
            title="Test",
            linkage=linkage_tree,
            style=DendrogramReportStyle(out=out),
            max_distance=10.0,
        )

        dd.draw()

        report_str = str(out.getvalue())

        log.debug(f"\n{report_str}")

        assert (
            hashlib.md5(str(report_str).encode("utf-8")).hexdigest()
        ) == checksum_dendrogram_report

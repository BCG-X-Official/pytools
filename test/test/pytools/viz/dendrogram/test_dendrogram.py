"""
Tests for package pytools.viz.dendrogram
"""

# noinspection PyPackageRequirements
import hashlib
import logging
from io import StringIO

import numpy as np

# noinspection PyPackageRequirements
import pytest

# noinspection PyPackageRequirements
import scipy.cluster.hierarchy as hc

from pytools.viz.dendrogram import DendrogramDrawer, DendrogramReportStyle, LinkageTree

log = logging.getLogger(__name__)


@pytest.fixture
def linkage_matrix() -> np.ndarray:
    """Create a linkage matrix."""
    x = np.array([[i] for i in [2, 8, 0, 4, 1, 9, 9, 0]])
    return hc.linkage(x)


@pytest.fixture
def linkage_tree(linkage_matrix: np.ndarray) -> LinkageTree:
    """Create a linkage tree for drawing tests."""
    return LinkageTree(
        scipy_linkage_matrix=linkage_matrix,
        leaf_names=list("ABCDEFGH"),
        leaf_weights=[(w + 1) / 36 for w in range(8)],
    )


def test_dendrogram_drawer_text(linkage_matrix: np.ndarray) -> None:
    checksum_dendrogram_report = "2d94fe5966d1fb77b4216c16e9845da6"
    leaf_names = list("ABCDEFGH")
    leaf_weights = [(w + 1) / 36 for w in range(8)]

    with pytest.raises(ValueError) as value_error:
        LinkageTree(
            scipy_linkage_matrix=linkage_matrix,
            leaf_names=leaf_names,
            leaf_weights=leaf_weights,
            max_distance=1,
        )
    assert value_error.value.args == (
        "arg max_distance=1 must be equal to or greater than the maximum distance "
        "(= 4.0) in the linkage tree",
    )

    linkage_tree = LinkageTree(
        scipy_linkage_matrix=linkage_matrix,
        leaf_names=leaf_names,
        leaf_weights=[(w + 1) / 36 for w in range(8)],
        distance_label="distance",
        leaf_label="label",
        weight_label="weight",
    )

    with StringIO() as out:
        dd = DendrogramDrawer(style=DendrogramReportStyle(out=out))
        dd.draw(data=linkage_tree, title="Test")
        report_str = str(out.getvalue())
        log.debug(f"\n{report_str}")
        assert (
            hashlib.md5(str(report_str).encode("utf-8")).hexdigest()
        ) == checksum_dendrogram_report

"""
Tests for package pytools.viz.dendrogram
"""

import logging
from io import StringIO

import numpy as np
import pytest
import scipy.cluster.hierarchy as hc

from pytools.data import LinkageTree
from pytools.viz.dendrogram import DendrogramDrawer, DendrogramReportStyle

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
        dd.draw(data=linkage_tree.sort_by_weight(), title="Test")
        report_str = str(out.getvalue())
        log.debug(f"\n{report_str}")

        print(report_str)
    report_str_expected = (
        r"""
===================================== Test =====================================

G 19% \_________________
F 17% /                 \------------------------------------------------------\
B  6% ------------------/                                                      |
H 22% \_________________                                                       |
C  8% /                 \_________________                                     |
E 14% ------------------/                 \------------------------------------/
A  3% ------------------/                 |
D 11% ------------------------------------/

"""
    )[1:]
    assert report_str == report_str_expected

    linkage_tree = LinkageTree(
        scipy_linkage_matrix=linkage_matrix,
        leaf_names=leaf_names,
        leaf_weights=[(w + 1) / 36 for w in range(8)],
        max_distance=5.0,
        distance_label="distance",
        leaf_label="label",
        weight_label="weight",
    )

    with StringIO() as out:
        dd = DendrogramDrawer(style=DendrogramReportStyle(out=out))
        dd.draw(data=linkage_tree.sort_by_weight(), title="Test")
        report_str = str(out.getvalue())
        log.debug(f"\n{report_str}")

        print(report_str)
    report_str_expected = (
        r"""
===================================== Test =====================================

G 19% \_____________
F 17% /             \--------------------------------------------\
B  6% --------------/                                            |
H 22% \_____________                                             |_____________
C  8% /             \______________                              |
E 14% --------------/              \-----------------------------/
A  3% --------------/              |
D 11% -----------------------------/

"""
    )[1:]
    assert report_str == report_str_expected

"""
Utilities for creating simulated data sets.
"""
import logging
from typing import List
from urllib import request
from xml.etree import ElementTree

from packaging.version import Version
from ..api import AllTracker


__all__ = ["validate_release_version"]


log = logging.getLogger(__name__)


__tracker = AllTracker(globals())


def validate_release_version(*, package: str, version: str) -> None:
    """
    Validate that the given version id can be used for the next release
    of the given package.

    :param package: name of the package to be released on PyPi
    :param version: version to be released
    """
    log.info(f"Testing package version: {package} {version}")

    version: Version = Version(version)

    releases_uri = f"https://pypi.org/rss/project/{package}/releases.xml"

    with request.urlopen(releases_uri) as response:
        assert response.getcode() == 200, "Error getting releases from PyPi"
        releases_xml = response.read()

    tree = ElementTree.fromstring(releases_xml)
    releases_nodes = tree.findall(path=".//channel//item//title")

    released_versions: List[Version] = sorted(
        Version(r) for r in [r.text for r in releases_nodes]
    )

    log.info(f"Releases found on PyPi: {', '.join(map(str, released_versions))}")

    assert (
        version not in released_versions
    ), f"{package} {version} must not yet be released on PyPi"

    if version.micro == 0 and not version.is_prerelease:
        # we have a major or minor release: need a release candidate
        release_candidates = [
            v
            for v in released_versions
            if v.pre and v.pre[0] == "rc" and v.release == version.release
        ]

        assert release_candidates, (
            f"Release of major or minor version {version} "
            f"requires at least one release candidate, e.g., "
            f"{version.release[0]}.{version.release[1]}.rc0"
        )

        log.info(
            f"Release candidates {release_candidates} exist; "
            f"release of major/minor version {version} approved"
        )


__tracker.validate()

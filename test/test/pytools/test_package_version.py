import logging
import re
from os import environ
from urllib import request
from xml.etree import ElementTree

from pytest import mark

import pytools

log = logging.getLogger(__name__)

ENV_RUN_PACKAGE_VERSION_TEST = "RUN_PACKAGE_VERSION_TEST"


@mark.skipif(
    condition=environ.get(ENV_RUN_PACKAGE_VERSION_TEST, "") != pytools.__name__,
    reason="Parent build is not primarily for pytools.",
)
def test_package_version() -> None:
    dev_version = pytools.__version__

    log.info(f"Test package version – version set to: {dev_version}")
    assert re.match(
        r"^(\d)+\.(\d)+\.(\d)+(rc\d+)?$", dev_version
    ), "pytools.__version__ is not in MAJOR.MINOR.PATCH[rcN] format."

    releases_uri = "https://pypi.org/rss/project/gamma-pytools/releases.xml"

    with request.urlopen(releases_uri) as response:
        assert response.getcode() == 200, "Error getting releases from PyPi"
        releases_xml = response.read()

    tree = ElementTree.fromstring(releases_xml)
    releases_nodes = tree.findall(path=".//channel//item//title")
    releases = [r.text for r in releases_nodes]

    log.info(f"Releases found on PyPi: {', '.join(releases)}")

    if dev_version not in releases:
        log.warning(f"Current package version {dev_version} is already on PyPi")

    is_minor_or_major_release = dev_version.endswith(".0")

    if is_minor_or_major_release:
        pre_releases = [
            version
            for version in releases
            if re.match(f"{dev_version}rc\\d+$", version)
        ]

        assert pre_releases, (
            f"Release of major or minor version {dev_version} "
            f"requires at least one pre-release, e.g. {dev_version}rc0"
        )

        log.info(
            f"Pre-releases {pre_releases} exist(s) – "
            f"release of major/minor version {dev_version} allowed"
        )

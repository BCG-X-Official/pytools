import logging
import re
from xml.etree import ElementTree

import requests

import pytools

log = logging.getLogger(__name__)


def test_package_version():
    dev_version = pytools.__version__

    log.info(f"Test package version – version set to: {dev_version}")
    assert re.match(
        r"^(\d)+\.(\d)+\.(\d)+(rc\d)?$", dev_version
    ), "pytools.__version__ is not in MAJOR.MINOR.PATCH[rcN] format."

    releases_uri = "https://pypi.org/rss/project/gamma-pytools/releases.xml"
    releases_xml = requests.get(releases_uri)
    assert releases_xml.status_code == 200, "Error getting releases from PyPi"

    tree = ElementTree.fromstring(releases_xml.text)
    releases_nodes = tree.findall(path=".//channel//item//title")
    releases = [r.text for r in releases_nodes]

    log.info(f"Found these releases on PyPi:{releases}")

    assert (
        dev_version not in releases
    ), f"Current package version {dev_version} already on PyPi"

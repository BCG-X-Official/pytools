import logging
from os import environ

from pytest import mark

import pytools
from pytools.build import validate_release_version

log = logging.getLogger(__name__)


PACKAGE_VERSION = pytools.__version__
MODULE_NAME = pytools.__name__
PACKAGE_NAME = "gamma-pytools"


@mark.skipif(
    condition=environ.get("RUN_PACKAGE_VERSION_TEST", "") != MODULE_NAME,
    reason=f"build is not for a {PACKAGE_NAME} release",
)
def test_package_version() -> None:
    validate_release_version(package=PACKAGE_NAME, version=PACKAGE_VERSION)

import os

import pytest
import rsa

from gamma.common import licensing

# noinspection PyProtectedMember
from gamma.common.licensing._licensing import (
    LICENSE_KEY_SIG_ENV,
    LICENSEE_ENV,
    safe_dumps,
)


@pytest.fixture(scope="function")
def clear_environment() -> None:
    os.environ[LICENSEE_ENV] = ""
    os.environ[LICENSE_KEY_SIG_ENV] = ""
    yield


def test_no_license_warns(clear_environment) -> None:
    with pytest.warns(expected_warning=UserWarning):
        # have to ensure it's not cached already
        licensing.check_license()


def test_valid_license(clear_environment, monkeypatch) -> None:
    from gamma.common.licensing._licensing import LICENSED_FOR

    licensing.check_license()
    assert LICENSED_FOR == "UNLICENSED"
    (pubkey, privkey) = rsa.newkeys(512)

    client = "bcg client"
    signature = rsa.sign(client.encode("ASCII"), privkey, "SHA-1")

    # activate the test-license through the environment
    # os.environ[LICENSE_KEY_ENV] = safe_dumps(pubkey)
    os.environ[LICENSE_KEY_SIG_ENV] = safe_dumps(signature)
    os.environ[LICENSEE_ENV] = client

    monkeypatch.setattr(
        licensing._licensing, name="LICENSE_KEY", value=safe_dumps(pubkey)
    )

    # test license retrieval on the other end:
    ret_key, ret_sig, ret_client = licensing._licensing.retrieve_license()

    # assert client name is equal
    assert ret_client == client
    assert ret_key == pubkey
    assert ret_sig == signature

    licensing.check_license()

    # noinspection PyProtectedMember
    from gamma.common.licensing._licensing import LICENSED_FOR

    assert LICENSED_FOR == client

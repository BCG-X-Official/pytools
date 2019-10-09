import os
import pytest
import rsa
from gamma.common import licensing
from gamma.common.licensing import (
    LICENSEE_ENV,
    LICENSE_KEY_ENV,
    LICENSE_KEY_SIG_ENV,
    retrieve_license,
    safe_dumps,
)


def test_no_license_warns() -> None:
    with pytest.warns(expected_warning=UserWarning):
        # have to ensure it's not cached already
        licensing.check_license()


def test_valid_license() -> None:
    from gamma.common.licensing import LICENSED_FOR

    licensing.check_license()
    assert LICENSED_FOR == "UNLICENSED"
    (pubkey, privkey) = rsa.newkeys(512)
    client = "bcg client"
    signature = rsa.sign(client.encode("ASCII"), privkey, "SHA-1")

    # activate the test-license through the environment
    os.environ[LICENSE_KEY_ENV] = safe_dumps(pubkey)
    os.environ[LICENSE_KEY_SIG_ENV] = safe_dumps(signature)
    os.environ[LICENSEE_ENV] = client

    # test license retrieval on the other end:
    ret_key, ret_sig, ret_client = retrieve_license()

    # assert client name is equal
    assert ret_client == client
    assert ret_key == pubkey
    assert ret_sig == signature

    licensing.check_license()
    from gamma.common.licensing import LICENSED_FOR

    assert LICENSED_FOR == client

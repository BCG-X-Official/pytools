import base64
import logging
import os
import pickle
import warnings
from typing import Any, Tuple

import rsa
from rsa import PublicKey

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

LICENSE_KEY_ENV = "GAMMA_ALPHA_KEY"
LICENSE_KEY_SIG_ENV = "GAMMA_ALPHA_LICENSE_SIGNATURE"
LICENSEE_ENV = "GAMMA_ALPHA_LICENSEE"

WARNING_MESSAGE = """
NOT FOR CLIENT USE!

This is a pre-release library under development. Handling of IP rights is still
being investigated. To avoid causing any potential IP disputes or issues, DO NOT USE
ANY OF THIS CODE ON A CLIENT PROJECT, not even in modified form.

Please direct any queries to any of:
- Jan Ittner
- Jörg Schneider
- Florent Martin
"""

LICENSED_FOR = "UNLICENSED"


def var_in_env(var: str) -> bool:
    """ Checks if a variable is in the environment and not empty. """
    return var in os.environ and os.environ[var].strip() != ""


def safe_load(pickled_string: str) -> Any:
    """ Loads a pickled string safely escaping control/reserved characters. """
    return pickle.loads(base64.decodebytes(pickled_string.encode("ASCII")))


def safe_dumps(obj: Any) -> str:
    """ Dumps an object safely to a pickled string. """
    return base64.encodebytes(pickle.dumps(obj)).decode("ASCII")


def retrieve_license() -> Tuple[PublicKey, str, str]:
    """ Retrieves the license from the environment."""
    return (
        safe_load(os.environ[LICENSE_KEY_ENV]),
        safe_load(os.environ[LICENSE_KEY_SIG_ENV]),
        os.environ[LICENSEE_ENV],
    )


def check_license() -> str:
    """ Checks if library is licensed and if-so, returns licensee name in clear-text."""
    if (
        not var_in_env(LICENSE_KEY_SIG_ENV)
        or not var_in_env(LICENSEE_ENV)
        or not var_in_env(LICENSE_KEY_ENV)
    ):
        warnings.warn(message=WARNING_MESSAGE, category=UserWarning)
    else:
        rsa_public_key, rsa_sig_hash, client_name = retrieve_license()

        license_verified = rsa.verify(
            client_name.encode("ASCII"), rsa_sig_hash, rsa_public_key
        )

        if not license_verified:
            raise EnvironmentError(
                f"Supplied license for client {client_name} is invalid!"
                f"Please check ENV variables: "
                f"{LICENSE_KEY_ENV},{LICENSE_KEY_SIG_ENV},{LICENSEE_ENV}"
            )
        else:
            global LICENSED_FOR
            LICENSED_FOR = client_name
            logger.info(f"alpha library successfully licensed for: {LICENSED_FOR}")

    return LICENSED_FOR

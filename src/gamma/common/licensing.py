"""
License checking for gamma packages.
"""
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

LICENSE_KEY = """gANjcnNhLmtleQpQdWJsaWNLZXkKcQApgXEBiwECAABJ2G9TBoEQgz4BclMzK4VJ0glO6ae9Fcto
9EIzJxLCfkavTrOqgP9fim8h7ihH+KwI9m3EcV/JLm/0IP/lLVQQE/h2CmbGGZ1RXqrx/SnbLtCk
eD15fn9V6cdV8COei+iW/RynyvisOlUO9ruwt72XJFlhbU6tD8MFLcJM3DHxiv3A1mQxUo/1N8bP
4wp2SBNjjtJTX8M4PAhV90nyQhL0aeD8fcuCzIQ0cRUQjgpPtAhL6Nhsgw3r9Zcp1ICwSrwjeIbA
5sSRdIBCHokLBUyc+WtolzNxfodgRzc7/4XJc8Yheosw+eYWTcTJIQX4a/45Kv3iKnO9/J0xGfYd
myHS3sJX6E2QMb5Kf0I3IlNlBkzbfm5zJyTw9nunbNorHr2c1YXk9BudhjN5/AH01jnkZ/5hIRbd
JlpXJ8sAqYrHIcPlw8gT3PcykrOQ5R9PJfy4fk3HQb1Mb+Qj8Nwc/MWrgJElaiHReTrYWvbqQlP6
TrwVR/L4U9VgSifHmB3AsGe0//42Vzmh7kFYnQ2JnZQDdtk/tu4t/dp+Qtcf0z/86rdj1Om8hsVG
OEYMsNqF3iTbFQSHN8deQU0cKy2rbW3ex8xbREQJKmVV1814Alzhtdc0AFV55p8NPJ93cjdR1yqa
AcZNdYQo+G/1qdCScv132osYXYXjkXrMZts3VaPupwBKAQABAIZxAmIu"""

LICENSE_KEY_SIG_ENV = "GAMMA_ALPHA_LICENSE_SIGNATURE"
LICENSEE_ENV = "GAMMA_ALPHA_LICENSEE"

WARNING_MESSAGE = """
NOT FOR CLIENT USE!

This is a early release library under development. Handling of IP rights is still
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
        safe_load(LICENSE_KEY),
        safe_load(os.environ[LICENSE_KEY_SIG_ENV]),
        os.environ[LICENSEE_ENV],
    )


def check_license() -> str:
    """ Checks if library is licensed and if so, returns licensee name in clear-text."""
    if not var_in_env(LICENSE_KEY_SIG_ENV) or not var_in_env(LICENSEE_ENV):
        warnings.warn(message=WARNING_MESSAGE, category=UserWarning, stacklevel=2)
    else:
        rsa_public_key, rsa_sig_hash, client_name = retrieve_license()

        license_verified = rsa.verify(
            client_name.encode("ASCII"), rsa_sig_hash, rsa_public_key
        )

        if not license_verified:
            raise EnvironmentError(
                f"Supplied license for client {client_name} is invalid!"
                f"Please check ENV variables: "
                f"{LICENSE_KEY_SIG_ENV} and {LICENSEE_ENV}"
            )
        else:
            global LICENSED_FOR
            LICENSED_FOR = client_name
            logger.info(f"alpha library successfully licensed for: {LICENSED_FOR}")

    return LICENSED_FOR

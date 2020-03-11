"""
Core implementation of :mod:`gamma.common.licensing`
"""

import base64
import logging
import os
import pickle
import sys
from typing import Any, Tuple

import rsa
from rsa import PublicKey

logger = logging.getLogger(__name__)

#
# exported names
#

__all__ = ["check_license"]


#
# Constants
#

# noinspection SpellCheckingInspection
LICENSE_KEY = (
    "gANjcnNhLmtleQpQdWJsaWNLZXkKcQApgXEBiwECAABJ2G9TBoEQgz4BclMzK4VJ0glO6ae9Fcto\n"
    "9EIzJxLCfkavTrOqgP9fim8h7ihH+KwI9m3EcV/JLm/0IP/lLVQQE/h2CmbGGZ1RXqrx/SnbLtCk\n"
    "eD15fn9V6cdV8COei+iW/RynyvisOlUO9ruwt72XJFlhbU6tD8MFLcJM3DHxiv3A1mQxUo/1N8bP\n"
    "4wp2SBNjjtJTX8M4PAhV90nyQhL0aeD8fcuCzIQ0cRUQjgpPtAhL6Nhsgw3r9Zcp1ICwSrwjeIbA\n"
    "5sSRdIBCHokLBUyc+WtolzNxfodgRzc7/4XJc8Yheosw+eYWTcTJIQX4a/45Kv3iKnO9/J0xGfYd\n"
    "myHS3sJX6E2QMb5Kf0I3IlNlBkzbfm5zJyTw9nunbNorHr2c1YXk9BudhjN5/AH01jnkZ/5hIRbd\n"
    "JlpXJ8sAqYrHIcPlw8gT3PcykrOQ5R9PJfy4fk3HQb1Mb+Qj8Nwc/MWrgJElaiHReTrYWvbqQlP6\n"
    "TrwVR/L4U9VgSifHmB3AsGe0//42Vzmh7kFYnQ2JnZQDdtk/tu4t/dp+Qtcf0z/86rdj1Om8hsVG\n"
    "OEYMsNqF3iTbFQSHN8deQU0cKy2rbW3ex8xbREQJKmVV1814Alzhtdc0AFV55p8NPJ93cjdR1yqa\n"
    "AcZNdYQo+G/1qdCScv132osYXYXjkXrMZts3VaPupwBKAQABAIZxAmIu"
)

LICENSE_KEY_SIG_ENV = "GAMMA_ALPHA_LICENSE_SIGNATURE"
LICENSEE_ENV = "GAMMA_ALPHA_LICENSEE"

WARNING_MESSAGE = "No license in place for package {}"
WARNING_MESSAGE_LONG = (
    "\n"
    "ALPHA (c) 2019, 2020 Boston Consulting Group\n"
    "Modules from the ALPHA suite need to be licensed for commercial use.\n"
    "Please contact the ALPHA team for support with this.\n"
    "\n"
    f"{WARNING_MESSAGE}"
)

licensee = "UNLICENSED"
checked_packages = set()

#
# local helper functions
#


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


def print_license_warning(package_name) -> None:
    """
    Issue a license warning for the given package.
    Warn only once per package.
    The first warning is more verbose than warnings for subsequent packages.
    :param package_name: name of the unlicensed package
    """

    if package_name not in checked_packages:

        if len(checked_packages) == 0:
            # first time round our warning message will be more verbose ...
            message = WARNING_MESSAGE_LONG
        else:
            # ... followed by brief messages for subsequent unlicensed packages
            message = WARNING_MESSAGE

        checked_packages.add(package_name)

        print(message.format(package_name), file=sys.stderr)


#
# main function
#


def check_license(package_name: str) -> str:
    """
    Check if library is licensed and if so, returns licensee name in clear-text
    :param package_name: name of the package to license
    :return: the name of the licensee
    """

    global licensee

    if not var_in_env(LICENSE_KEY_SIG_ENV) or not var_in_env(LICENSEE_ENV):

        print_license_warning(package_name=package_name)

    else:

        rsa_public_key, rsa_sig_hash, client_name = retrieve_license()

        license_verified = rsa.verify(
            client_name.encode("ASCII"), rsa_sig_hash, rsa_public_key
        )

        if not license_verified:

            print_license_warning(package_name=package_name)

            raise EnvironmentError(
                f"Supplied license for client {client_name} is invalid. "
                f"Please check environment variables "
                f"{LICENSE_KEY_SIG_ENV} and {LICENSEE_ENV}"
            )

        else:

            licensee = client_name
            logger.info(
                f"alpha package {package_name} successfully licensed to: {licensee}"
            )

    return licensee

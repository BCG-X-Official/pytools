"""
Implementation of ``fetch_url``.
"""

from __future__ import annotations

import http.client
import logging
import urllib.parse

log = logging.getLogger(__name__)

__all__ = [
    "fetch_url",
]


def fetch_url(url: str) -> bytes:
    """
    Fetch the contents of a URL.

    :param url: the URL to fetch
    :return: the contents of the URL
    :raises ValueError: if the request fails
    """
    # Parse the URL
    parsed_url = urllib.parse.urlparse(url)

    # Determine the connection type based on the URL scheme
    if parsed_url.scheme == "http":
        conn = http.client.HTTPConnection(parsed_url.netloc)
    elif parsed_url.scheme == "https":
        conn = http.client.HTTPSConnection(parsed_url.netloc)
    else:
        raise ValueError("Unsupported URL scheme")

    # Send a GET request
    path = parsed_url.path if parsed_url.path else "/"
    conn.request("GET", path)

    # Get the response
    response = conn.getresponse()

    # Read the response body
    data = response.read()

    # Get the response code
    status_code = response.status

    # If the response code is not OK, raise an error
    if status_code != http.client.OK:
        raise http.client.HTTPException(
            f"Request failed with status code {status_code}: {url}"
        )

    # Close the connection
    conn.close()

    return data

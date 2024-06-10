"""
Tests of the flow.util module.
"""

import http.client
import logging
from unittest.mock import Mock, patch

import pytest

from pytools.http import fetch_url

log = logging.getLogger(__name__)


# noinspection HttpUrlsUsage
def test_fetch_url() -> None:
    # Example URL
    example_url = "http://www.example.com/my_test"

    with patch("http.client.HTTPConnection") as MockHTTPConnection:
        # Mock the response object
        mock_response = Mock()
        mock_response.read.return_value = b"<!doctype html><html>...</html>\n"
        mock_response.status = http.client.OK

        # Set up the mock connection object
        mock_conn = Mock()
        mock_conn.getresponse.return_value = mock_response
        MockHTTPConnection.return_value = mock_conn

        # Configure the mock connection to return the mock response based on the URL
        def mock_request() -> Mock | None:
            if mock_conn.request.call_args[0][1] == "/my_test":
                return mock_response
            else:
                return None

        mock_conn.getresponse.side_effect = mock_request

        # Call fetch_url and run assertion on returned data
        data = fetch_url(example_url)
        assert data is not None
        assert len(data) > 0
        assert data.startswith(b"<!doctype html>")
        assert data.endswith(b"</html>\n")


# noinspection HttpUrlsUsage
def test_fetch_url_403() -> None:
    # Non-existent example URL
    example_url = "http://example.com/nonexistent"

    with patch("http.client.HTTPConnection") as MockHTTPConnection:
        # Create a mock HTTPConnection instance
        mock_conn = MockHTTPConnection.return_value

        # Create a mock response with status code 403
        mock_response = Mock()
        mock_response.status = 403

        # Configure the mock to return the mock response based on the URL
        def mock_request() -> Mock | None:
            if mock_conn.request.call_args[0][1] == "/nonexistent":
                return mock_response
            else:
                return None

        mock_conn.getresponse.side_effect = mock_request

        # Assert that the HTTPException is raised with the correct message
        with pytest.raises(
            http.client.HTTPException,
            match=(
                r"^Request failed with status code 403: http://example\.com/"
                r"nonexistent$"
            ),
        ):
            fetch_url(example_url)

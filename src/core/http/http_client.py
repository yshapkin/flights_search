"""HTTP requests with shared timeouts and per-request status validation."""

import logging
from urllib import parse

import requests

from core.http import http_client_parameters
from core.http import request_parameters

logger = logging.getLogger(__name__)


class HttpClient:
    """A synchronous HTTP client with configurable response expectations."""

    def __init__(
        self, parameters: http_client_parameters.HttpClientParameters
    ) -> None:
        """Initializes the shared client settings.

        Args:
            parameters: Base URL and request timeout in seconds.
        """
        self._parameters = parameters

    def get(
        self, parameters: request_parameters.RequestParameters
    ) -> requests.Response:
        """Sends a GET request and validates its response status.

        Args:
            parameters: URL, headers, query values, and acceptable statuses.

        Returns:
            The original response when its status is accepted.

        Raises:
            requests.HTTPError: The response status is not accepted.
            requests.RequestException: The HTTP request fails.
        """
        logger.info("HTTP GET started", extra={"http.request.method": "GET"})
        try:
            response = requests.get(
                parse.urljoin(self._parameters.base_url, parameters.url),
                headers=parameters.headers,
                params=parameters.params,
                timeout=self._parameters.timeout,
            )
        except requests.RequestException as error:
            error_type = type(error).__name__
            logger.error(
                "HTTP GET failed (%s)",
                error_type,
                extra={"error.type": error_type},
            )
            raise

        if response.status_code not in parameters.expected_status_codes:
            logger.error(
                "HTTP GET returned unexpected status %s",
                response.status_code,
                extra={"http.response.status_code": response.status_code},
            )
            raise requests.HTTPError(
                f"Unexpected HTTP status code: {response.status_code}",
                response=response,
            )

        logger.info(
            "HTTP GET completed with status %s",
            response.status_code,
            extra={"http.response.status_code": response.status_code},
        )
        return response

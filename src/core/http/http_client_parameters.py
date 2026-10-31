"""Shared base URL and timeout settings for HTTP requests."""


class HttpClientParameters:
    """Read-only connection settings shared across requests."""

    def __init__(self, url: str, timeout: int) -> None:
        """Initializes the connection settings.

        Args:
            url: Base URL used to resolve relative request URLs.
            timeout: Request timeout in seconds.
        """
        self._url = url
        self._timeout = timeout

    @property
    def base_url(self) -> str:
        """The base URL used to resolve relative request URLs."""
        return self._url

    @property
    def timeout(self) -> int:
        """The request timeout in seconds."""
        return self._timeout

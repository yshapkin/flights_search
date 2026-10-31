"""RapidAPI host and authentication settings."""


class RapidApiParameters:
    """Read-only credentials for a RapidAPI service."""

    def __init__(self, host: str, key: str) -> None:
        """Initializes the service credentials.

        Args:
            host: Service host sent in the RapidAPI host header.
            key: API key sent in the RapidAPI authentication header.
        """
        self._host = host
        self._key = key

    @property
    def host(self) -> str:
        """The RapidAPI service host."""
        return self._host

    @property
    def key(self) -> str:
        """The API key; this value must not be logged."""
        return self._key

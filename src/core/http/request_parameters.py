"""Per-request HTTP arguments and acceptable response statuses."""

from collections.abc import Mapping, Sequence


class RequestParameters:
    """Read-only request settings with a snapshot of expected statuses."""

    def __init__(
        self,
        url: str,
        headers: Mapping[str, str] | None = None,
        params: Mapping[str, str] | None = None,
        expected_status_codes: Sequence[int] | None = None,
    ) -> None:
        """Initializes the request settings.

        Args:
            url: Relative or absolute request URL.
            headers: Optional request headers, retained by reference.
            params: Optional query values, retained by reference.
            expected_status_codes: Accepted statuses, copied to a tuple. None
                accepts all 2xx statuses; an empty sequence rejects every status.
        """
        self._url = url
        self._headers = headers
        self._params = params
        self._exp_status_codes = tuple(
            range(200, 300)
            if expected_status_codes is None
            else expected_status_codes
        )

    @property
    def url(self) -> str:
        """The relative or absolute request URL."""
        return self._url

    @property
    def headers(self) -> Mapping[str, str] | None:
        """The optional request headers."""
        return self._headers

    @property
    def params(self) -> Mapping[str, str] | None:
        """The optional query values."""
        return self._params

    @property
    def expected_status_codes(self) -> tuple[int, ...]:
        """The immutable snapshot of accepted response statuses."""
        return self._exp_status_codes

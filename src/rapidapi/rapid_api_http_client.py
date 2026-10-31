"""RapidAPI flight endpoints backed by the shared HTTP client."""

from collections.abc import Mapping
from typing import Any

from core.http import http_client
from core.http import request_parameters
from rapidapi import rapid_api_parameters


class RapidApiHttpClient:
    """A flight API client using injected HTTP transport and credentials."""

    def __init__(
        self,
        transport: http_client.HttpClient,
        parameters: rapid_api_parameters.RapidApiParameters,
    ) -> None:
        """Initializes the RapidAPI wrapper.

        Args:
            transport: HTTP client configured with the flight API base URL.
            parameters: RapidAPI host and authentication key.
        """
        self._http_client = transport
        self._parameters = parameters

    def get_flights_airports(self) -> Any:
        """Returns the airport endpoint's decoded JSON payload unchanged.

        Raises:
            requests.RequestException: The request fails or returns a non-200
                status, or its response cannot be decoded as JSON.
        """
        parameters = request_parameters.RequestParameters(
            url="/flights/airports",
            headers={
                "x-rapidapi-host": self._parameters.host,
                "x-rapidapi-key": self._parameters.key,
            },
            expected_status_codes=[200],
        )
        response = self._http_client.get(parameters)
        return response.json()

    def get_flights_search_roundtrip(
        self, from_entity_id: str, params: Mapping[str, str]
    ) -> Any:
        """Returns the round-trip search endpoint's decoded JSON payload.

        Args:
            from_entity_id: Departure entity identifier.
            params: Search query values, excluding fromEntityId.

        Raises:
            requests.RequestException: The request fails, returns a non-2xx
                status, or its response cannot be decoded as JSON.
        """
        parameters = request_parameters.RequestParameters(
            url="/flights/search-roundtrip",
            headers={
                "x-rapidapi-host": self._parameters.host,
                "x-rapidapi-key": self._parameters.key,
            },
            params={**params, "fromEntityId": from_entity_id},
        )
        response = self._http_client.get(parameters)
        return response.json()

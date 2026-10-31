from typing import Any
from unittest import mock

import pytest
import requests

from core.http import http_client
from rapidapi import rapid_api_http_client
from rapidapi import rapid_api_parameters


def test_rapid_api_parameters_store_host_and_key() -> None:
    parameters = rapid_api_parameters.RapidApiParameters(
        "flights-sky.p.rapidapi.com", "test-key"
    )

    assert parameters.host == "flights-sky.p.rapidapi.com"
    assert parameters.key == "test-key"


@pytest.mark.parametrize("payload", [{"data": [{"code": "FRA"}]}, [], None])
def test_get_flights_airports_sends_headers_and_returns_json(
    payload: Any,
) -> None:
    transport = mock.Mock(spec=http_client.HttpClient)
    transport.get.return_value.json.return_value = payload
    client = rapid_api_http_client.RapidApiHttpClient(
        transport=transport,
        parameters=rapid_api_parameters.RapidApiParameters(
            "flights-sky.p.rapidapi.com", "test-key"
        ),
    )

    assert client.get_flights_airports() is payload

    transport.get.assert_called_once()
    parameters = transport.get.call_args.args[0]
    assert parameters.url == "/flights/airports"
    assert parameters.headers == {
        "x-rapidapi-host": "flights-sky.p.rapidapi.com",
        "x-rapidapi-key": "test-key",
    }
    assert parameters.params is None
    assert parameters.expected_status_codes == (200,)
    transport.get.return_value.json.assert_called_once_with()


@pytest.mark.parametrize("error_type", [requests.Timeout, requests.HTTPError])
def test_get_flights_airports_propagates_http_errors(
    error_type: type[requests.RequestException],
) -> None:
    error = error_type("request failed")
    transport = mock.Mock(spec=http_client.HttpClient)
    transport.get.side_effect = error
    client = rapid_api_http_client.RapidApiHttpClient(
        transport,
        rapid_api_parameters.RapidApiParameters(
            "flights-sky.p.rapidapi.com", "test-key"
        ),
    )

    with pytest.raises(error_type) as failure:
        client.get_flights_airports()

    assert failure.value is error


def test_get_flights_search_roundtrip_forwards_query_and_returns_json() -> None:
    payload = {"data": []}
    transport = mock.Mock(spec=http_client.HttpClient)
    transport.get.return_value.json.return_value = payload
    client = rapid_api_http_client.RapidApiHttpClient(
        transport,
        rapid_api_parameters.RapidApiParameters("test-host", "test-key"),
    )
    query = {
        "originSkyId": "FRA",
        "travelDate": "2023-10-05",
        "currency": "EUR",
    }

    assert client.get_flights_search_roundtrip("PARI", query) is payload

    transport.get.assert_called_once()
    parameters = transport.get.call_args.args[0]
    assert parameters.url == "/flights/search-roundtrip"
    assert parameters.headers == {
        "x-rapidapi-host": "test-host",
        "x-rapidapi-key": "test-key",
    }
    assert parameters.params == {**query, "fromEntityId": "PARI"}
    assert parameters.expected_status_codes == tuple(range(200, 300))
    assert "fromEntityId" not in query
    transport.get.return_value.json.assert_called_once_with()


def test_get_flights_airports_propagates_invalid_json() -> None:
    error = requests.exceptions.JSONDecodeError("Invalid JSON", "", 0)
    transport = mock.Mock(spec=http_client.HttpClient)
    transport.get.return_value.json.side_effect = error
    client = rapid_api_http_client.RapidApiHttpClient(
        transport,
        rapid_api_parameters.RapidApiParameters(
            "flights-sky.p.rapidapi.com", "test-key"
        ),
    )

    with pytest.raises(requests.exceptions.JSONDecodeError) as failure:
        client.get_flights_airports()

    assert failure.value is error

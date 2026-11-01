import inspect
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


def test_get_config_has_no_endpoint_arguments_and_returns_any() -> None:
    signature = inspect.signature(
        rapid_api_http_client.RapidApiHttpClient.get_config
    )

    assert tuple(signature.parameters) == ("self",)
    assert signature.return_annotation is Any


@pytest.mark.parametrize(
    "payload",
    [
        {"config": {"currencies": ["EUR"], "enabled": False}},
        ["EUR", {"locale": "en-GB"}],
        None,
        {},
        [],
        True,
        "EUR",
        0,
    ],
    ids=[
        "dict",
        "list",
        "null",
        "empty-dict",
        "empty-list",
        "bool",
        "string",
        "number",
    ],
)
def test_get_config_sends_headers_and_returns_json(
    payload: Any,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level("DEBUG")
    transport = mock.Mock(spec=http_client.HttpClient)
    transport.get.return_value.json.return_value = payload
    client = rapid_api_http_client.RapidApiHttpClient(
        transport=transport,
        parameters=rapid_api_parameters.RapidApiParameters(
            "custom-config-host.invalid", "dummy-custom-config-key"
        ),
    )

    assert client.get_config() is payload

    transport.get.assert_called_once()
    parameters = transport.get.call_args.args[0]
    assert parameters.url == "/get-config"
    assert parameters.headers == {
        "x-rapidapi-host": "custom-config-host.invalid",
        "x-rapidapi-key": "dummy-custom-config-key",
    }
    assert parameters.params is None
    assert parameters.expected_status_codes == (200,)
    transport.get.return_value.json.assert_called_once_with()
    transport.get.return_value.raise_for_status.assert_not_called()
    assert "dummy-custom-config-key" not in caplog.text


@pytest.mark.parametrize("error_type", [requests.Timeout, requests.HTTPError])
def test_get_config_propagates_http_errors(
    error_type: type[requests.RequestException],
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level("DEBUG")
    error = error_type("request failed")
    transport = mock.Mock(spec=http_client.HttpClient)
    transport.get.side_effect = error
    client = rapid_api_http_client.RapidApiHttpClient(
        transport,
        rapid_api_parameters.RapidApiParameters(
            "custom-config-host.invalid", "dummy-custom-config-key"
        ),
    )

    with pytest.raises(error_type) as failure:
        client.get_config()

    assert failure.value is error
    transport.get.assert_called_once()
    transport.get.return_value.json.assert_not_called()
    assert "dummy-custom-config-key" not in caplog.text


def test_get_config_propagates_invalid_json(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level("DEBUG")
    error = requests.exceptions.JSONDecodeError("Invalid JSON", "", 0)
    transport = mock.Mock(spec=http_client.HttpClient)
    transport.get.return_value.json.side_effect = error
    client = rapid_api_http_client.RapidApiHttpClient(
        transport,
        rapid_api_parameters.RapidApiParameters(
            "custom-config-host.invalid", "dummy-custom-config-key"
        ),
    )

    with pytest.raises(requests.exceptions.JSONDecodeError) as failure:
        client.get_config()

    assert failure.value is error
    transport.get.assert_called_once()
    transport.get.return_value.json.assert_called_once_with()
    assert "dummy-custom-config-key" not in caplog.text


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


@pytest.mark.parametrize("payload", [{"data": [{"skyId": "FRA"}]}, [], None])
def test_get_flights_sky_id_list_sends_headers_and_returns_json(
    payload: Any,
) -> None:
    transport = mock.Mock(spec=http_client.HttpClient)
    transport.get.return_value.json.return_value = payload
    client = rapid_api_http_client.RapidApiHttpClient(
        transport,
        rapid_api_parameters.RapidApiParameters("test-host", "test-key"),
    )

    assert client.get_flights_sky_id_list() is payload

    transport.get.assert_called_once()
    parameters = transport.get.call_args.args[0]
    assert parameters.url == "/flights/skyId-list"
    assert parameters.headers == {
        "x-rapidapi-host": "test-host",
        "x-rapidapi-key": "test-key",
    }
    assert parameters.params is None
    assert parameters.expected_status_codes == (200,)
    transport.get.return_value.json.assert_called_once_with()


@pytest.mark.parametrize("error_type", [requests.Timeout, requests.HTTPError])
def test_get_flights_sky_id_list_propagates_http_errors(
    error_type: type[requests.RequestException],
) -> None:
    error = error_type("request failed")
    transport = mock.Mock(spec=http_client.HttpClient)
    transport.get.side_effect = error
    client = rapid_api_http_client.RapidApiHttpClient(
        transport,
        rapid_api_parameters.RapidApiParameters("test-host", "test-key"),
    )

    with pytest.raises(error_type) as failure:
        client.get_flights_sky_id_list()

    assert failure.value is error
    transport.get.return_value.json.assert_not_called()


def test_get_flights_sky_id_list_propagates_invalid_json() -> None:
    error = requests.exceptions.JSONDecodeError("Invalid JSON", "", 0)
    transport = mock.Mock(spec=http_client.HttpClient)
    transport.get.return_value.json.side_effect = error
    client = rapid_api_http_client.RapidApiHttpClient(
        transport,
        rapid_api_parameters.RapidApiParameters("test-host", "test-key"),
    )

    with pytest.raises(requests.exceptions.JSONDecodeError) as failure:
        client.get_flights_sky_id_list()

    assert failure.value is error

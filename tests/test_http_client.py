import logging
import types
from unittest import mock

import pytest
import requests

from core.http import http_client
from core.http import http_client_parameters
from core.http import request_parameters


@pytest.mark.parametrize("status_code", [200, 201, 204, 299])
def test_get_accepts_default_success_codes(
    monkeypatch: pytest.MonkeyPatch, status_code: int
) -> None:
    response = requests.Response()
    response.status_code = status_code
    get = mock.Mock(return_value=response)
    monkeypatch.setattr(requests, "get", get)
    client = http_client.HttpClient(
        http_client_parameters.HttpClientParameters(
            "https://example.com/api/", 30
        )
    )
    parameters = request_parameters.RequestParameters(
        "flights",
        headers={"Accept": "application/json"},
        params={"origin": "FRA"},
    )

    assert client.get(parameters) is response
    get.assert_called_once_with(
        "https://example.com/api/flights",
        headers=parameters.headers,
        params=parameters.params,
        timeout=30,
    )


def test_custom_expected_status_codes_are_copied(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected_codes = [404]
    parameters = request_parameters.RequestParameters(
        "/flights", expected_status_codes=expected_codes
    )
    expected_codes.append(500)
    assert parameters.expected_status_codes == (404,)
    response = requests.Response()
    response.status_code = 404
    monkeypatch.setattr(requests, "get", mock.Mock(return_value=response))

    client = http_client.HttpClient(
        http_client_parameters.HttpClientParameters("https://example.com", 30)
    )
    assert client.get(parameters) is response


def test_expected_status_codes_are_per_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    response = requests.Response()
    response.status_code = 404
    monkeypatch.setattr(requests, "get", mock.Mock(return_value=response))
    client = http_client.HttpClient(
        http_client_parameters.HttpClientParameters("https://example.com", 30)
    )

    assert (
        client.get(
            request_parameters.RequestParameters(
                "/flights", expected_status_codes=[404]
            )
        )
        is response
    )
    with pytest.raises(requests.HTTPError):
        client.get(request_parameters.RequestParameters("/flights"))


def test_empty_expected_status_codes_reject_all_responses(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    response = requests.Response()
    response.status_code = 200
    monkeypatch.setattr(requests, "get", mock.Mock(return_value=response))
    client = http_client.HttpClient(
        http_client_parameters.HttpClientParameters("https://example.com", 30)
    )

    with pytest.raises(requests.HTTPError):
        client.get(
            request_parameters.RequestParameters(
                "/flights", expected_status_codes=[]
            )
        )


@pytest.mark.parametrize("status_code", [302, 400, 500])
def test_unexpected_status_raises_http_error(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    status_code: int,
) -> None:
    response = requests.Response()
    response.status_code = status_code
    monkeypatch.setattr(requests, "get", mock.Mock(return_value=response))
    client = http_client.HttpClient(
        http_client_parameters.HttpClientParameters("https://example.com", 30)
    )

    with pytest.raises(requests.HTTPError) as failure:
        client.get(request_parameters.RequestParameters("/flights"))

    assert failure.value.response is response
    assert "unexpected status" in caplog.text


@pytest.mark.parametrize(
    "error_type", [requests.Timeout, requests.ConnectionError]
)
def test_network_errors_are_logged_and_reraised(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    error_type: type[requests.RequestException],
) -> None:
    error = error_type("sensitive-url?api_key=secret")
    monkeypatch.setattr(requests, "get", mock.Mock(side_effect=error))
    client = http_client.HttpClient(
        http_client_parameters.HttpClientParameters("https://example.com", 30)
    )

    with pytest.raises(error_type) as failure:
        client.get(request_parameters.RequestParameters("/flights"))

    assert failure.value is error
    assert error_type.__name__ in caplog.text
    assert "secret" not in caplog.text


def test_success_logging_does_not_expose_request_values(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    response = requests.Response()
    response.status_code = 200
    monkeypatch.setattr(requests, "get", mock.Mock(return_value=response))
    client = http_client.HttpClient(
        http_client_parameters.HttpClientParameters("https://example.com", 30)
    )
    with caplog.at_level(logging.INFO):
        client.get(
            request_parameters.RequestParameters(
                "/flights?key=secret", headers={"Key": "secret"}
            )
        )

    assert "HTTP GET completed" in caplog.text
    assert "secret" not in caplog.text


def test_request_parameters_accept_mappings_and_sequences() -> None:
    headers = types.MappingProxyType({"Accept": "application/json"})
    query = types.MappingProxyType({"origin": "FRA"})
    parameters = request_parameters.RequestParameters(
        "/flights",
        headers=headers,
        params=query,
        expected_status_codes=(200, 204),
    )

    assert parameters.headers is headers
    assert parameters.params is query
    assert parameters.expected_status_codes == (200, 204)

from unittest import mock

import pytest
import requests

import main


def test_main_searches_through_rapid_api_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RAPID_API_HOST", "test-host")
    monkeypatch.setenv("RAPID_API_KEY", "test-key")
    monkeypatch.setattr(main.dotenv, "load_dotenv", mock.Mock())
    payload = {"data": []}
    response = mock.Mock(status_code=200)
    response.json.return_value = payload
    get = mock.Mock(return_value=response)
    monkeypatch.setattr(requests, "get", get)
    logger = mock.Mock()
    monkeypatch.setattr(main, "logger", logger)
    wrapper = mock.Mock(wraps=main.rapid_api_http_client.RapidApiHttpClient)
    monkeypatch.setattr(
        main.rapid_api_http_client, "RapidApiHttpClient", wrapper
    )

    main.main()

    wrapper.assert_called_once()
    get.assert_called_once_with(
        "https://flights-sky.p.rapidapi.com/flights/search-roundtrip",
        headers={"x-rapidapi-host": "test-host", "x-rapidapi-key": "test-key"},
        params={
            "originSkyId": "FRA",
            "travelDate": "2023-10-05",
            "currency": "EUR",
            "fromEntityId": "PARI",
        },
        timeout=30,
    )
    logger.info.assert_called_once_with("Flight search response: %s", payload)

import copy
import csv
import inspect
import logging
import pathlib
import runpy
import typing
from unittest import mock

import dotenv
import pytest
import requests

import main
from core.http import http_client
from core.http import http_client_parameters
from core.utils import json_utils
from rapidapi import rapid_api_http_client
from rapidapi import rapid_api_parameters

MAIN_SOURCE = pathlib.Path(main.__file__).resolve()


@pytest.fixture(autouse=True)
def isolated_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RAPID_API_HOST", "test-config-host.invalid")
    monkeypatch.setenv("RAPID_API_KEY", "dummy-config-key-not-a-secret")
    monkeypatch.setattr(dotenv, "load_dotenv", mock.Mock())
    monkeypatch.setattr(
        requests.sessions.Session,
        "request",
        mock.Mock(side_effect=AssertionError("Live requests are forbidden")),
    )


@pytest.fixture(autouse=True)
def fake_repository(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> pathlib.Path:
    repository = (tmp_path / "repository").resolve()
    source = repository / "src" / "main.py"
    source.parent.mkdir(parents=True)
    monkeypatch.setattr(main, "__file__", str(source))
    monkeypatch.chdir(tmp_path)
    real_exporter = json_utils.json_to_csv

    def export_in_temporary_repository(
        records: list[dict[str, object]],
        output_folder: pathlib.Path,
        filename: str,
    ) -> pathlib.Path:
        assert pathlib.Path(output_folder).resolve() == repository / "data"
        assert filename == "get-config_data.csv"
        return real_exporter(records, output_folder, filename)

    monkeypatch.setattr(
        json_utils,
        "json_to_csv",
        mock.Mock(side_effect=export_in_temporary_repository),
    )
    return repository


@pytest.fixture
def andorra_record() -> dict[str, object]:
    return {
        "country": "Andorra",
        "market": "AD",
        "locale": "es-ES",
        "currencyTitle": "Euro",
        "currency": "EUR",
        "currencySymbol": "\u20ac",
        "site": "www.skyscanner.net",
    }


@pytest.fixture
def entrypoint_mocks(
    monkeypatch: pytest.MonkeyPatch, andorra_record: dict[str, object]
) -> dict[str, mock.Mock]:
    client = mock.Mock(spec=rapid_api_http_client.RapidApiHttpClient)
    client.get_config.return_value = {
        "status": "response-only-marker",
        "data": [andorra_record],
    }
    transport = mock.Mock(spec=http_client.HttpClient)
    constructors = {
        "credentials": mock.Mock(wraps=rapid_api_parameters.RapidApiParameters),
        "settings": mock.Mock(
            wraps=http_client_parameters.HttpClientParameters
        ),
        "transport": mock.Mock(return_value=transport),
        "wrapper": mock.Mock(return_value=client),
        "client": client,
    }
    monkeypatch.setattr(
        rapid_api_parameters,
        "RapidApiParameters",
        constructors["credentials"],
    )
    monkeypatch.setattr(
        http_client_parameters,
        "HttpClientParameters",
        constructors["settings"],
    )
    monkeypatch.setattr(http_client, "HttpClient", constructors["transport"])
    monkeypatch.setattr(
        rapid_api_http_client, "RapidApiHttpClient", constructors["wrapper"]
    )
    return constructors


def _read_rows(path: pathlib.Path) -> list[list[str]]:
    with path.open(encoding="utf-8", newline="") as csv_file:
        return list(csv.reader(csv_file))


def _assert_entrypoint_flow(constructors: dict[str, mock.Mock]) -> None:
    dotenv.load_dotenv.assert_called_once_with()
    constructors["credentials"].assert_called_once_with(
        host="test-config-host.invalid", key="dummy-config-key-not-a-secret"
    )
    constructors["settings"].assert_called_once_with(
        "https://flights-sky.p.rapidapi.com", timeout=30
    )
    constructors["transport"].assert_called_once()
    settings = constructors["transport"].call_args.args[0]
    assert settings.base_url == "https://flights-sky.p.rapidapi.com"
    assert settings.timeout == 30
    constructors["wrapper"].assert_called_once()
    credentials = constructors["wrapper"].call_args.kwargs["parameters"]
    assert credentials.host == "test-config-host.invalid"
    assert credentials.key == "dummy-config-key-not-a-secret"
    constructors["wrapper"].assert_called_once_with(
        transport=constructors["transport"].return_value,
        parameters=credentials,
    )
    assert constructors["client"].mock_calls == [mock.call.get_config()]


def test_main_and_save_config_have_module_level_no_self_contracts() -> None:
    assert inspect.isfunction(main.main)
    assert inspect.isfunction(main._save_config)
    assert tuple(inspect.signature(main.main).parameters) == ()
    assert tuple(inspect.signature(main._save_config).parameters) == ("client",)
    assert typing.get_type_hints(main.main)["return"] is type(None)
    annotations = typing.get_type_hints(main._save_config)
    assert annotations["client"] is rapid_api_http_client.RapidApiHttpClient
    assert annotations["return"] is type(None)


def test_save_config_fetches_and_exports_same_unchanged_data_once(
    fake_repository: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
    andorra_record: dict[str, object],
) -> None:
    records = [andorra_record, {"arbitrary": [{"enabled": True}]}]
    payload = {"status": True, "data": records, "metadata": "not a column"}
    original_payload = copy.deepcopy(payload)
    client = mock.Mock(spec=rapid_api_http_client.RapidApiHttpClient)
    client.get_config.return_value = payload
    exporter = mock.Mock(return_value=fake_repository / "ignored-return.csv")
    monkeypatch.setattr(json_utils, "json_to_csv", exporter)

    assert main._save_config(client) is None

    assert client.mock_calls == [mock.call.get_config()]
    exporter.assert_called_once_with(
        records,
        output_folder=fake_repository / "data",
        filename="get-config_data.csv",
    )
    assert exporter.call_args.args[0] is records
    assert payload == original_payload


@pytest.mark.parametrize("existing_file", [False, True])
def test_save_config_exports_exact_andorra_csv_and_overwrites(
    fake_repository: pathlib.Path,
    andorra_record: dict[str, object],
    existing_file: bool,
) -> None:
    destination = fake_repository / "data" / "get-config_data.csv"
    if existing_file:
        destination.parent.mkdir()
        destination.write_text("old,long,content\n" * 100, encoding="utf-8")
    else:
        assert not destination.parent.exists()
    client = mock.Mock(spec=rapid_api_http_client.RapidApiHttpClient)
    client.get_config.return_value = {
        "status": True,
        "timestamp": 123,
        "data": [andorra_record],
    }

    assert main._save_config(client) is None

    assert _read_rows(destination) == [
        [
            "country",
            "market",
            "locale",
            "currencyTitle",
            "currency",
            "currencySymbol",
            "site",
        ],
        [
            "Andorra",
            "AD",
            "es-ES",
            "Euro",
            "EUR",
            "\u20ac",
            "www.skyscanner.net",
        ],
    ]
    assert "\u20ac".encode("utf-8") in destination.read_bytes()
    assert list(destination.parent.iterdir()) == [destination]


def test_save_config_preserves_all_countries_and_rows_beyond_235(
    fake_repository: pathlib.Path,
) -> None:
    countries = ["Andorra", "France", "Japan"]
    records = [
        {
            "country": countries[index % 3],
            "market": f"M{index}",
            "sequence": index,
        }
        for index in range(240)
    ]
    records.append(
        {
            "country": "Final sentinel",
            "market": "ZZ",
            "sequence": 240,
            "last": "last record",
        }
    )
    client = mock.Mock(spec=rapid_api_http_client.RapidApiHttpClient)
    client.get_config.return_value = {"data": records, "total": 235}

    main._save_config(client)

    expected_rows = [
        [countries[index % 3], f"M{index}", str(index), ""]
        for index in range(240)
    ]
    assert _read_rows(fake_repository / "data" / "get-config_data.csv") == [
        ["country", "market", "sequence", "last"],
        *expected_rows,
        ["Final sentinel", "ZZ", "240", "last record"],
    ]


def test_save_config_preserves_union_header_empty_rows_and_json_cells(
    fake_repository: pathlib.Path,
) -> None:
    records = [
        {},
        {
            "country": "Andorra",
            "note": 'comma, quote" and\r\nnewline',
            "nested": {"symbol": "\u20ac", "list": [1, False, None]},
            "enabled": False,
            "count": 17,
            "rate": 1.25,
            "null": None,
        },
        {
            "country": "Japan",
            "late": ["\u6771\u4eac", True, None],
            "enabled": True,
        },
        {},
    ]
    client = mock.Mock(spec=rapid_api_http_client.RapidApiHttpClient)
    client.get_config.return_value = {"data": records, "outer": "excluded"}

    main._save_config(client)

    destination = fake_repository / "data" / "get-config_data.csv"
    assert _read_rows(destination) == [
        [
            "country",
            "note",
            "nested",
            "enabled",
            "count",
            "rate",
            "null",
            "late",
        ],
        ["", "", "", "", "", "", "", ""],
        [
            "Andorra",
            'comma, quote" and\r\nnewline',
            '{"symbol": "\u20ac", "list": [1, false, null]}',
            "false",
            "17",
            "1.25",
            "null",
            "",
        ],
        ["Japan", "", "", "true", "", "", "", '["\u6771\u4eac", true, null]'],
        ["", "", "", "", "", "", "", ""],
    ]
    assert b'"comma, quote"" and\r\nnewline"' in destination.read_bytes()


def test_save_config_resolves_source_symlink_independently_of_cwd(
    fake_repository: pathlib.Path,
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    source_link = outside / "linked-main.py"
    source_link.symlink_to(fake_repository / "src" / "main.py")
    monkeypatch.setattr(main, "__file__", str(source_link))
    monkeypatch.chdir(outside)
    client = mock.Mock(spec=rapid_api_http_client.RapidApiHttpClient)
    client.get_config.return_value = {"data": [{"country": "Japan"}]}

    main._save_config(client)

    destination = fake_repository / "data" / "get-config_data.csv"
    assert _read_rows(destination) == [["country"], ["Japan"]]
    json_utils.json_to_csv.assert_called_once_with(
        client.get_config.return_value["data"],
        output_folder=fake_repository / "data",
        filename="get-config_data.csv",
    )
    assert not (outside / "data").exists()
    assert not (tmp_path / "data").exists()


@pytest.mark.parametrize("existing_file", [False, True])
def test_save_config_empty_data_creates_or_truncates_zero_byte_file(
    fake_repository: pathlib.Path, existing_file: bool
) -> None:
    destination = fake_repository / "data" / "get-config_data.csv"
    if existing_file:
        destination.parent.mkdir()
        destination.write_text("stale header\nold record\n", encoding="utf-8")
    else:
        assert not destination.parent.exists()
    client = mock.Mock(spec=rapid_api_http_client.RapidApiHttpClient)
    client.get_config.return_value = {"data": []}

    assert main._save_config(client) is None

    assert destination.is_file()
    assert destination.read_bytes() == b""


def test_save_config_missing_data_raises_native_key_error_without_export(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)
    client = mock.Mock(spec=rapid_api_http_client.RapidApiHttpClient)
    client.get_config.return_value = {"metadata": "synthetic-payload-marker"}
    exporter = mock.Mock()
    monkeypatch.setattr(json_utils, "json_to_csv", exporter)

    with pytest.raises(KeyError) as failure:
        main._save_config(client)

    assert failure.value.args == ("data",)
    assert client.mock_calls == [mock.call.get_config()]
    exporter.assert_not_called()
    assert "synthetic-payload-marker" not in caplog.text


@pytest.mark.parametrize(
    "error",
    [
        requests.Timeout("synthetic timeout"),
        requests.HTTPError("synthetic HTTP failure"),
        requests.exceptions.JSONDecodeError("synthetic JSON failure", "{", 1),
    ],
    ids=["timeout", "http-error", "json-error"],
)
def test_save_config_fetch_errors_propagate_unchanged_without_export(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    error: requests.RequestException,
) -> None:
    caplog.set_level(logging.DEBUG)
    client = mock.Mock(spec=rapid_api_http_client.RapidApiHttpClient)
    client.get_config.side_effect = error
    exporter = mock.Mock()
    monkeypatch.setattr(json_utils, "json_to_csv", exporter)

    with pytest.raises(type(error)) as failure:
        main._save_config(client)

    assert failure.value is error
    assert client.mock_calls == [mock.call.get_config()]
    exporter.assert_not_called()
    assert str(error) not in caplog.text


@pytest.mark.parametrize(
    "error",
    [OSError("synthetic filesystem failure"), PermissionError("write denied")],
    ids=["os-error", "permission-error"],
)
def test_save_config_export_errors_propagate_unchanged(
    fake_repository: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
    error: OSError,
) -> None:
    records = [{"country": "Andorra"}]
    client = mock.Mock(spec=rapid_api_http_client.RapidApiHttpClient)
    client.get_config.return_value = {"data": records}
    exporter = mock.Mock(side_effect=error)
    monkeypatch.setattr(json_utils, "json_to_csv", exporter)

    with pytest.raises(type(error)) as failure:
        main._save_config(client)

    assert failure.value is error
    assert client.mock_calls == [mock.call.get_config()]
    exporter.assert_called_once_with(
        records,
        output_folder=fake_repository / "data",
        filename="get-config_data.csv",
    )
    assert exporter.call_args.args[0] is records
    assert not (fake_repository / "data").exists()


def test_main_loads_synthetic_environment_and_exports_without_extra_calls(
    fake_repository: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
    entrypoint_mocks: dict[str, mock.Mock],
    caplog: pytest.LogCaptureFixture,
    capsys: pytest.CaptureFixture[str],
) -> None:
    caplog.set_level(logging.DEBUG)
    monkeypatch.delenv("RAPID_API_HOST")
    monkeypatch.delenv("RAPID_API_KEY")

    def load_synthetic_environment() -> bool:
        monkeypatch.setenv("RAPID_API_HOST", "test-config-host.invalid")
        monkeypatch.setenv("RAPID_API_KEY", "dummy-config-key-not-a-secret")
        return True

    dotenv.load_dotenv.side_effect = load_synthetic_environment
    helper = mock.Mock(wraps=main._save_config)
    monkeypatch.setattr(main, "_save_config", helper)

    assert main.main() is None

    _assert_entrypoint_flow(entrypoint_mocks)
    helper.assert_called_once_with(entrypoint_mocks["client"])
    assert _read_rows(fake_repository / "data" / "get-config_data.csv")[1] == [
        "Andorra",
        "AD",
        "es-ES",
        "Euro",
        "EUR",
        "\u20ac",
        "www.skyscanner.net",
    ]
    captured = capsys.readouterr()
    for marker in (
        "Andorra",
        "dummy-config-key-not-a-secret",
        "response-only-marker",
    ):
        assert marker not in caplog.text
        assert marker not in captured.out + captured.err


def test_execution_guard_runs_main_with_only_mocked_dependencies(
    monkeypatch: pytest.MonkeyPatch,
    entrypoint_mocks: dict[str, mock.Mock],
    tmp_path: pathlib.Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.DEBUG)
    exporter = mock.Mock(return_value=tmp_path / "ignored-return.csv")
    monkeypatch.setattr(json_utils, "json_to_csv", exporter)
    configure_logging = mock.Mock()
    monkeypatch.setattr(logging, "basicConfig", configure_logging)

    namespace = runpy.run_path(str(MAIN_SOURCE), run_name="__main__")

    assert namespace["__name__"] == "__main__"
    _assert_entrypoint_flow(entrypoint_mocks)
    configure_logging.assert_called_once_with(level=logging.INFO)
    records = entrypoint_mocks["client"].get_config.return_value["data"]
    exporter.assert_called_once_with(
        records,
        output_folder=MAIN_SOURCE.parents[1] / "data",
        filename="get-config_data.csv",
    )
    assert exporter.call_args.args[0] is records
    assert "Andorra" not in caplog.text
    assert "dummy-config-key-not-a-secret" not in caplog.text

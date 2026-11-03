"""Independent offline acceptance tests for the RapidAPI stdio MCP server."""

import copy
import io
import json
import os
import pathlib
import runpy
import selectors
import subprocess
import sys
import time
from typing import Any
from unittest import mock

import anyio
import dotenv
import mcp.client
import mcp.server
import mcp.shared.exceptions
import mcp.types
import pytest
import requests

import rapid_api_mcp_server
from core.http import http_client
from core.utils import json_utils
from mcp_server import rapid_api_server
from rapidapi import rapid_api_http_client
from rapidapi import rapid_api_parameters

TOOL_NAMES = (
    "get_config",
    "get_flights_airports",
    "get_flights_sky_id_list",
    "get_flights_search_roundtrip",
)
LAUNCHER = pathlib.Path(rapid_api_mcp_server.__file__).resolve()
CHILD_PROGRAM = """
import runpy
import sys
from unittest import mock
sys.path.insert(0, sys.argv[1])
with (
    mock.patch('requests.sessions.Session.request',
               side_effect=AssertionError('Network forbidden')),
    mock.patch('core.utils.json_utils.json_to_csv',
               side_effect=AssertionError('CSV forbidden')),
):
    runpy.run_path(sys.argv[2], run_name='__main__')
"""
SENSITIVE_MARKERS = (
    "synthetic-key-do-not-disclose",
    "synthetic-host.invalid",
    "x-rapidapi-key",
    "Authorization",
    "query-private-value",
    "raw-exception-private-value",
)
PAYLOADS = [
    None,
    {},
    [],
    False,
    True,
    0,
    -17,
    1.25,
    "",
    "plain text",
    "\u6771\u4eac \u00e9 \u2708",
    {"status": False, "data": [], "error": "upstream application status"},
    [None, [], False, {"nested": ["x", 0, "\u20ac"]}],
]


@pytest.fixture(autouse=True)
def isolated_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("RAPID_API_HOST", raising=False)
    monkeypatch.delenv("RAPID_API_KEY", raising=False)
    monkeypatch.delenv("PYTHON_DOTENV_DISABLED", raising=False)
    monkeypatch.setattr(
        requests.sessions.Session,
        "request",
        mock.Mock(side_effect=AssertionError("Live requests are forbidden")),
    )
    monkeypatch.setattr(
        json_utils,
        "json_to_csv",
        mock.Mock(side_effect=AssertionError("CSV export is forbidden")),
    )


def _arguments(name: str) -> dict[str, Any]:
    if name == "get_flights_search_roundtrip":
        return {
            "from_entity_id": "explicit-origin",
            "params": {"arbitrary": "query-private-value"},
        }
    return {}


def _assert_json_identical(actual: Any, expected: Any) -> None:
    assert type(actual) is type(expected)
    assert actual == expected
    if isinstance(expected, dict):
        for key, value in expected.items():
            _assert_json_identical(actual[key], value)
    elif isinstance(expected, list):
        for actual_item, expected_item in zip(actual, expected, strict=True):
            _assert_json_identical(actual_item, expected_item)


def _assert_success(result: mcp.types.CallToolResult, payload: Any) -> None:
    wire = result.model_dump(by_alias=True, exclude_none=True)
    assert not wire.get("isError", False)
    _assert_json_identical(wire["structuredContent"], {"result": payload})
    assert len(wire["content"]) == 1
    assert wire["content"][0]["type"] == "text"
    _assert_json_identical(
        json.loads(wire["content"][0]["text"]), {"result": payload}
    )


def _call_tool(
    client: rapid_api_http_client.RapidApiHttpClient,
    name: str,
    arguments: dict[str, Any],
) -> mcp.types.CallToolResult:
    async def invoke() -> mcp.types.CallToolResult:
        with anyio.fail_after(10):
            async with mcp.client.Client(
                rapid_api_server.create_server(client), mode="legacy"
            ) as session:
                return await session.call_tool(name, arguments)

    return anyio.run(invoke)


def test_handshake_discovery_and_factory_are_inert() -> None:
    client = mock.Mock(spec=rapid_api_http_client.RapidApiHttpClient)
    application = rapid_api_server.create_server(client)
    assert isinstance(application, mcp.server.MCPServer)
    assert client.mock_calls == []

    async def discover() -> None:
        with anyio.fail_after(10):
            async with mcp.client.Client(application, mode="legacy") as session:
                assert session.server_info.name == "RapidAPI_mcp_server"
                tools = await session.list_tools()
                assert {tool.name for tool in tools.tools} == set(TOOL_NAMES)
                assert len(tools.tools) == 4
                schemas = {tool.name: tool.input_schema for tool in tools.tools}
                for name in TOOL_NAMES[:3]:
                    assert not schemas[name].get("properties")
                    assert not schemas[name].get("required")
                roundtrip = schemas[TOOL_NAMES[3]]
                assert set(roundtrip["required"]) == {
                    "from_entity_id",
                    "params",
                }
                properties = roundtrip["properties"]
                assert set(properties) == {"from_entity_id", "params"}
                assert properties["from_entity_id"]["type"] == "string"
                assert properties["params"]["type"] == "object"
                assert properties["params"]["additionalProperties"] == {
                    "type": "string"
                }

    anyio.run(discover)
    assert client.mock_calls == []


@pytest.mark.parametrize("name", TOOL_NAMES)
@pytest.mark.parametrize("payload", PAYLOADS)
def test_tools_delegate_once_and_preserve_every_json_value(
    name: str, payload: Any
) -> None:
    client = mock.Mock(spec=rapid_api_http_client.RapidApiHttpClient)
    getattr(client, name).return_value = payload
    arguments = _arguments(name)
    before = copy.deepcopy(arguments)

    result = _call_tool(client, name, arguments)

    _assert_success(result, payload)
    assert arguments == before
    expected_args = (
        (arguments["from_entity_id"], arguments["params"]) if arguments else ()
    )
    assert client.mock_calls == [getattr(mock.call, name)(*expected_args)]


@pytest.mark.parametrize(
    ("origin", "query"),
    [
        ("", {}),
        ("", {"fromEntityId": "conflicting", "": ""}),
        ("explicit", {"fromEntityId": "conflicting"}),
        (
            "origin",
            {
                "empty_object": "{}",
                "object": '{"value":"text"}',
                "array": "[]",
                "null": "null",
                "boolean": "true",
                "number": "0",
            },
        ),
        (
            " \u6771\u4eac ",
            {
                "arbitrary": "not-a-date&?=",
                "negative": "-1",
                "travelDate": "",
                "unicode": "\u00e9\u20ac",
            },
        ),
    ],
)
def test_roundtrip_preserves_query_and_existing_client_precedence(
    origin: str, query: dict[str, str]
) -> None:
    transport = mock.Mock(spec=http_client.HttpClient)
    transport.get.return_value.json.return_value = {"data": []}
    client = rapid_api_http_client.RapidApiHttpClient(
        transport,
        rapid_api_parameters.RapidApiParameters("test-host", "test-key"),
    )
    original_query = copy.deepcopy(query)

    result = _call_tool(
        client,
        "get_flights_search_roundtrip",
        {"from_entity_id": origin, "params": query},
    )

    _assert_success(result, {"data": []})
    assert query == original_query
    transport.get.assert_called_once()
    request = transport.get.call_args.args[0]
    assert request.url == "/flights/search-roundtrip"
    assert request.params == {**original_query, "fromEntityId": origin}
    transport.get.return_value.json.assert_called_once_with()


@pytest.mark.parametrize(
    "arguments",
    [
        {},
        {"from_entity_id": "origin"},
        {"params": {}},
        {"from_entity_id": None, "params": {}},
        {"from_entity_id": 0, "params": {}},
        {"from_entity_id": False, "params": {}},
        {"from_entity_id": True, "params": {}},
        {"from_entity_id": 1.25, "params": {}},
        {"from_entity_id": [], "params": {}},
        {"from_entity_id": {}, "params": {}},
        {"from_entity_id": "origin", "params": None},
        {"from_entity_id": "origin", "params": "query"},
        {"from_entity_id": "origin", "params": ""},
        {"from_entity_id": "origin", "params": "{}"},
        {"from_entity_id": "origin", "params": '{"value":"text"}'},
        {"from_entity_id": "origin", "params": 0},
        {"from_entity_id": "origin", "params": 1.25},
        {"from_entity_id": "origin", "params": False},
        {"from_entity_id": "origin", "params": True},
        {"from_entity_id": "origin", "params": []},
        {"from_entity_id": "origin", "params": ["value"]},
        {"from_entity_id": "origin", "params": {"value": 0}},
        {"from_entity_id": "origin", "params": {"value": 1.25}},
        {"from_entity_id": "origin", "params": {"value": False}},
        {"from_entity_id": "origin", "params": {"value": None}},
        {"from_entity_id": "origin", "params": {"value": []}},
        {"from_entity_id": "origin", "params": {"value": {}}},
    ],
)
def test_sdk_rejects_missing_or_wrong_type_arguments_before_client_call(
    arguments: dict[str, Any],
) -> None:
    client = mock.Mock(spec=rapid_api_http_client.RapidApiHttpClient)
    before = copy.deepcopy(arguments)
    try:
        result = _call_tool(client, "get_flights_search_roundtrip", arguments)
    except mcp.shared.exceptions.MCPError:
        pass
    else:
        assert result.is_error is True
    assert client.mock_calls == []
    assert arguments == before


@pytest.mark.parametrize("name", TOOL_NAMES)
@pytest.mark.parametrize(
    "error_kind", ["timeout", "connection", "http", "json", "unexpected"]
)
def test_dependency_failures_are_sanitized_and_next_call_recovers(
    name: str,
    error_kind: str,
    caplog: pytest.LogCaptureFixture,
    capsys: pytest.CaptureFixture[str],
) -> None:
    caplog.set_level("DEBUG")
    message = " ".join(SENSITIVE_MARKERS)
    errors = {
        "timeout": requests.Timeout(message),
        "connection": requests.ConnectionError(message),
        "http": requests.HTTPError(message),
        "json": requests.exceptions.JSONDecodeError(message, message, 0),
        "unexpected": RuntimeError(message),
    }
    client = mock.Mock(spec=rapid_api_http_client.RapidApiHttpClient)
    getattr(client, name).side_effect = [
        errors[error_kind],
        {"recovered": True},
    ]
    arguments = _arguments(name)

    async def fail_then_recover() -> None:
        with anyio.fail_after(10):
            async with mcp.client.Client(
                rapid_api_server.create_server(client), mode="legacy"
            ) as session:
                failure = await session.call_tool(name, arguments)
                assert failure.is_error is True
                wire = failure.model_dump(by_alias=True, exclude_none=True)
                assert "result" not in wire.get("structuredContent", {})
                assert wire["content"]
                assert all(item["type"] == "text" for item in wire["content"])
                assert any(item["text"].strip() for item in wire["content"])
                captured = capsys.readouterr()
                diagnostic = (
                    json.dumps(wire) + caplog.text + captured.out + captured.err
                )
                for marker in SENSITIVE_MARKERS:
                    assert marker not in diagnostic
                assert "Traceback" not in diagnostic
                _assert_success(
                    await session.call_tool(name, arguments),
                    {"recovered": True},
                )

    anyio.run(fail_then_recover)
    expected_args = (
        (arguments["from_entity_id"], arguments["params"]) if arguments else ()
    )
    assert client.mock_calls == [getattr(mock.call, name)(*expected_args)] * 2


def test_import_and_factory_need_no_credentials_or_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    forbidden = mock.Mock(side_effect=AssertionError("Startup is forbidden"))
    monkeypatch.setattr(dotenv, "load_dotenv", forbidden)
    monkeypatch.setattr(http_client, "HttpClient", forbidden)
    monkeypatch.setattr(rapid_api_parameters, "RapidApiParameters", forbidden)
    monkeypatch.setattr(mcp.server.MCPServer, "run", forbidden)

    imported = runpy.run_path(str(LAUNCHER), run_name="inert_launcher_import")
    client = mock.Mock(spec=rapid_api_http_client.RapidApiHttpClient)
    application = rapid_api_server.create_server(client)

    assert callable(imported["main"])
    assert isinstance(application, mcp.server.MCPServer)
    assert client.mock_calls == []
    forbidden.assert_not_called()


def _startup_mocks(monkeypatch: pytest.MonkeyPatch) -> dict[str, mock.Mock]:
    client = mock.Mock(spec=rapid_api_http_client.RapidApiHttpClient)
    constructors = {
        "credentials": mock.Mock(wraps=rapid_api_parameters.RapidApiParameters),
        "transport": mock.Mock(spec=http_client.HttpClient),
        "wrapper": mock.Mock(return_value=client),
        "factory": mock.Mock(),
        "client": client,
    }
    monkeypatch.setattr(
        rapid_api_parameters, "RapidApiParameters", constructors["credentials"]
    )
    monkeypatch.setattr(http_client, "HttpClient", constructors["transport"])
    monkeypatch.setattr(
        rapid_api_http_client, "RapidApiHttpClient", constructors["wrapper"]
    )
    monkeypatch.setattr(
        rapid_api_server, "create_server", constructors["factory"]
    )
    return constructors


def _dotenv_fallback(monkeypatch: pytest.MonkeyPatch) -> mock.Mock:
    real_loader = dotenv.load_dotenv

    def load_fallback(**kwargs: Any) -> bool:
        return real_loader(
            stream=io.StringIO(
                "RAPID_API_HOST=dotenv-host.invalid\n"
                "RAPID_API_KEY=dotenv-synthetic-key\n"
            ),
            **kwargs,
        )

    loader = mock.Mock(side_effect=load_fallback)
    monkeypatch.setattr(dotenv, "load_dotenv", loader)
    return loader


@pytest.mark.parametrize(
    ("inherited_host", "inherited_key"),
    [
        (None, None),
        (" inherited-host.invalid ", None),
        (None, " inherited-key "),
        (" inherited-host.invalid ", " inherited-key "),
    ],
)
def test_guarded_startup_uses_dotenv_fallback_and_existing_client_settings(
    monkeypatch: pytest.MonkeyPatch,
    inherited_host: str | None,
    inherited_key: str | None,
    capsys: pytest.CaptureFixture[str],
) -> None:
    if inherited_host is not None:
        monkeypatch.setenv("RAPID_API_HOST", inherited_host)
    if inherited_key is not None:
        monkeypatch.setenv("RAPID_API_KEY", inherited_key)
    loader = _dotenv_fallback(monkeypatch)
    constructors = _startup_mocks(monkeypatch)

    runpy.run_path(str(LAUNCHER), run_name="__main__")

    loader.assert_called_once_with(override=False)
    constructors["credentials"].assert_called_once_with(
        host=inherited_host or "dotenv-host.invalid",
        key=inherited_key or "dotenv-synthetic-key",
    )
    constructors["transport"].assert_called_once()
    settings = constructors["transport"].call_args.args[0]
    assert settings.base_url == "https://flights-sky.p.rapidapi.com"
    assert settings.timeout == 30
    credentials = constructors["credentials"].return_value
    credentials = constructors["wrapper"].call_args.kwargs["parameters"]
    assert credentials.host == (inherited_host or "dotenv-host.invalid")
    assert credentials.key == (inherited_key or "dotenv-synthetic-key")
    constructors["wrapper"].assert_called_once_with(
        transport=constructors["transport"].return_value,
        parameters=credentials,
    )
    constructors["factory"].assert_called_once_with(constructors["client"])
    constructors["factory"].return_value.run.assert_called_once_with(
        transport="stdio"
    )
    assert constructors["client"].mock_calls == []
    assert capsys.readouterr().out == ""


@pytest.mark.parametrize("credential", ["RAPID_API_HOST", "RAPID_API_KEY"])
@pytest.mark.parametrize("value", [None, "", " ", "\t\n"])
def test_invalid_credentials_stop_before_construction(
    monkeypatch: pytest.MonkeyPatch,
    credential: str,
    value: str | None,
    caplog: pytest.LogCaptureFixture,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("RAPID_API_HOST", SENSITIVE_MARKERS[1])
    monkeypatch.setenv("RAPID_API_KEY", SENSITIVE_MARKERS[0])
    if value is None:
        monkeypatch.delenv(credential)
    else:
        monkeypatch.setenv(credential, value)
    loader = mock.Mock()
    monkeypatch.setattr(dotenv, "load_dotenv", loader)
    constructors = _startup_mocks(monkeypatch)

    with pytest.raises(SystemExit) as failure:
        rapid_api_mcp_server.main()

    assert isinstance(failure.value.code, int)
    assert failure.value.code != 0
    loader.assert_called_once_with(override=False)
    for constructor in constructors.values():
        constructor.assert_not_called()
    captured = capsys.readouterr()
    assert captured.out == ""
    diagnostic = captured.err + caplog.text
    assert diagnostic.strip()
    assert "Traceback" not in diagnostic
    for marker in SENSITIVE_MARKERS:
        assert marker not in diagnostic


@pytest.mark.parametrize("credential", ["RAPID_API_HOST", "RAPID_API_KEY"])
@pytest.mark.parametrize("value", ["", " ", "\t\n"])
def test_inherited_invalid_credential_is_not_replaced_by_dotenv(
    monkeypatch: pytest.MonkeyPatch, credential: str, value: str
) -> None:
    monkeypatch.setenv(credential, value)
    loader = _dotenv_fallback(monkeypatch)
    constructors = _startup_mocks(monkeypatch)

    with pytest.raises(SystemExit) as failure:
        rapid_api_mcp_server.main()

    assert failure.value.code != 0
    assert os.environ[credential] == value
    loader.assert_called_once_with(override=False)
    for constructor in constructors.values():
        constructor.assert_not_called()


def _child_environment() -> dict[str, str]:
    return {
        "PATH": os.defpath,
        "PYTHON_DOTENV_DISABLED": "1",
        "RAPID_API_HOST": SENSITIVE_MARKERS[1],
        "RAPID_API_KEY": SENSITIVE_MARKERS[0],
    }


def _child_command() -> list[str]:
    return [
        sys.executable,
        "-c",
        CHILD_PROGRAM,
        str(LAUNCHER.parent),
        str(LAUNCHER),
    ]


@pytest.mark.parametrize("credential", ["RAPID_API_HOST", "RAPID_API_KEY"])
@pytest.mark.parametrize("value", [None, "", " ", "\t\n"])
def test_subprocess_invalid_credentials_exit_nonzero_with_safe_stderr(
    credential: str, value: str | None, tmp_path: pathlib.Path
) -> None:
    environment = _child_environment()
    if value is None:
        environment.pop(credential)
    else:
        environment[credential] = value

    completed = subprocess.run(
        _child_command(),
        input=b"",
        capture_output=True,
        cwd=tmp_path,
        env=environment,
        timeout=15,
        check=False,
    )

    assert completed.returncode != 0
    assert completed.stdout == b""
    diagnostic = completed.stderr.decode("utf-8")
    assert diagnostic.strip()
    assert "Traceback" not in diagnostic
    assert "Network forbidden" not in diagnostic
    assert "CSV forbidden" not in diagnostic
    for marker in SENSITIVE_MARKERS:
        assert marker not in diagnostic


def test_subprocess_stdio_handshake_discovery_and_protocol_only_stdout(
    tmp_path: pathlib.Path,
) -> None:
    messages: list[dict[str, Any]] = []
    pending = b""
    with subprocess.Popen(
        _child_command(),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=tmp_path,
        env=_child_environment(),
    ) as process:
        assert process.stdin is not None
        assert process.stdout is not None

        def send(message: dict[str, Any]) -> None:
            process.stdin.write(json.dumps(message).encode("utf-8") + b"\n")
            process.stdin.flush()

        def receive_response(identifier: int) -> dict[str, Any]:
            nonlocal pending
            deadline = time.monotonic() + 15
            with selectors.DefaultSelector() as selector:
                selector.register(process.stdout, selectors.EVENT_READ)
                while True:
                    remaining = deadline - time.monotonic()
                    assert remaining > 0, "MCP response timed out"
                    assert selector.select(remaining), "MCP response timed out"
                    chunk = os.read(process.stdout.fileno(), 65536)
                    assert chunk, "MCP server exited before responding"
                    pending += chunk
                    while b"\n" in pending:
                        line, pending = pending.split(b"\n", 1)
                        message = json.loads(line)
                        assert message["jsonrpc"] == "2.0"
                        messages.append(message)
                        if message.get("id") == identifier:
                            return message

        try:
            send(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2026-07-28",
                        "capabilities": {},
                        "clientInfo": {
                            "name": "independent-tester",
                            "version": "1",
                        },
                    },
                }
            )
            handshake = receive_response(1)
            assert "error" not in handshake
            assert handshake["result"]["serverInfo"]["name"] == (
                "RapidAPI_mcp_server"
            )
            send({"jsonrpc": "2.0", "method": "notifications/initialized"})
            send({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
            discovery = receive_response(2)
            assert "error" not in discovery
            tools = discovery["result"]["tools"]
            assert len(tools) == 4
            assert {tool["name"] for tool in tools} == set(TOOL_NAMES)
            stdout, stderr = process.communicate(timeout=15)
        finally:
            if process.poll() is None:
                process.kill()
                process.communicate(timeout=15)

    assert process.returncode == 0
    assert not pending.strip()
    for line in stdout.splitlines():
        message = json.loads(line)
        assert message["jsonrpc"] == "2.0"
        messages.append(message)
    assert {message.get("id") for message in messages} >= {1, 2}
    diagnostic = stderr.decode("utf-8")
    assert "Traceback" not in diagnostic
    assert "Network forbidden" not in diagnostic
    assert "CSV forbidden" not in diagnostic
    for marker in SENSITIVE_MARKERS:
        assert marker not in diagnostic
    assert list(tmp_path.iterdir()) == []

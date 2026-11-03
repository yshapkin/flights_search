"""MCP tools backed by an injected RapidAPI flight client."""

import json
from collections.abc import Callable, Mapping
from typing import Any

import mcp.server
import mcp.server.context
import mcp.types

from rapidapi import rapid_api_http_client


def _call_client(
    method: Callable[..., Any], *args: Any
) -> mcp.types.CallToolResult:
    """Calls the client and converts its response without leaking failures."""
    try:
        envelope = {"result": method(*args)}
        return mcp.types.CallToolResult(
            content=[
                mcp.types.TextContent(type="text", text=json.dumps(envelope))
            ],
            structured_content=envelope,
        )
    except Exception:
        return mcp.types.CallToolResult(
            content=[
                mcp.types.TextContent(
                    type="text",
                    text="Unable to complete the RapidAPI request.",
                )
            ],
            is_error=True,
        )


async def _validate_roundtrip_arguments(
    ctx: mcp.server.context.ServerRequestContext[Any],
    call_next: mcp.server.context.CallNext,
) -> mcp.server.context.HandlerResult:
    """Rejects raw input types before the SDK's JSON string preprocessing."""
    if (
        ctx.method == "tools/call"
        and ctx.params is not None
        and ctx.params.get("name") == "get_flights_search_roundtrip"
    ):
        arguments = ctx.params.get("arguments")
        params = (
            arguments.get("params") if isinstance(arguments, Mapping) else None
        )
        if (
            not isinstance(arguments, Mapping)
            or not isinstance(arguments.get("from_entity_id"), str)
            or not isinstance(params, Mapping)
            or any(
                not isinstance(key, str) or not isinstance(value, str)
                for key, value in params.items()
            )
        ):
            return mcp.types.CallToolResult(
                content=[
                    mcp.types.TextContent(
                        type="text", text="Invalid round-trip search arguments."
                    )
                ],
                is_error=True,
            )
    return await call_next(ctx)


def create_server(
    client: rapid_api_http_client.RapidApiHttpClient,
) -> mcp.server.MCPServer:
    """Creates an MCP server exposing the injected client's flight endpoints.

    Args:
        client: RapidAPI client used for all tool calls.

    Returns:
        A fresh server with four synchronous tools and no startup I/O.
    """
    server = mcp.server.MCPServer(
        "RapidAPI_mcp_server", middleware=[_validate_roundtrip_arguments]
    )

    @server.tool()
    def get_config() -> mcp.types.CallToolResult:
        """Returns the RapidAPI configuration in a result envelope."""
        return _call_client(client.get_config)

    @server.tool()
    def get_flights_airports() -> mcp.types.CallToolResult:
        """Returns the flight airports in a result envelope."""
        return _call_client(client.get_flights_airports)

    @server.tool()
    def get_flights_sky_id_list() -> mcp.types.CallToolResult:
        """Returns the flight Sky ID list in a result envelope."""
        return _call_client(client.get_flights_sky_id_list)

    @server.tool()
    def get_flights_search_roundtrip(
        from_entity_id: str, params: Mapping[str, str]
    ) -> mcp.types.CallToolResult:
        """Returns round-trip search results in a result envelope.

        Args:
            from_entity_id: Departure entity identifier.
            params: Search query values passed unchanged to the client.
        """
        return _call_client(
            client.get_flights_search_roundtrip, from_entity_id, params
        )

    return server

"""Launches the RapidAPI flight tools as a standalone stdio MCP server."""

import logging
import os
import sys

import dotenv

from core.http import http_client
from core.http import http_client_parameters
from mcp_server import rapid_api_server
from rapidapi import rapid_api_http_client
from rapidapi import rapid_api_parameters

logger = logging.getLogger(__name__)


def main() -> None:
    """Loads credentials and runs the RapidAPI MCP server over stdio.

    Raises:
        SystemExit: Either required credential is missing or blank.
    """
    logging.basicConfig(level=logging.INFO, stream=sys.stderr)
    dotenv.load_dotenv(override=False)
    host = os.environ.get("RAPID_API_HOST")
    key = os.environ.get("RAPID_API_KEY")
    if not host or not host.strip() or not key or not key.strip():
        logger.error(
            "RAPID_API_HOST and RAPID_API_KEY must be set and non-blank."
        )
        raise SystemExit(1)

    configuration = rapid_api_parameters.RapidApiParameters(host=host, key=key)
    transport = http_client.HttpClient(
        http_client_parameters.HttpClientParameters(
            "https://flights-sky.p.rapidapi.com", timeout=30
        )
    )
    client = rapid_api_http_client.RapidApiHttpClient(
        transport=transport, parameters=configuration
    )
    rapid_api_server.create_server(client).run(transport="stdio")


if __name__ == "__main__":
    main()

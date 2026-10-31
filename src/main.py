"""Runs a flight search using RapidAPI credentials from the environment."""

import logging
import os

import dotenv

from core.http import http_client
from core.http import http_client_parameters
from rapidapi import rapid_api_http_client
from rapidapi import rapid_api_parameters

logger = logging.getLogger(__name__)


def main() -> None:
    """Loads credentials, performs a round-trip search, and logs its JSON.

    Raises:
        KeyError: A required RapidAPI environment variable is missing.
        requests.RequestException: The request fails, returns an unexpected
            status, or its response cannot be decoded as JSON.
    """
    dotenv.load_dotenv()
    configuration = rapid_api_parameters.RapidApiParameters(
        host=os.environ["RAPID_API_HOST"],
        key=os.environ["RAPID_API_KEY"],
    )
    transport = http_client.HttpClient(
        http_client_parameters.HttpClientParameters(
            "https://flights-sky.p.rapidapi.com", timeout=30
        )
    )
    client = rapid_api_http_client.RapidApiHttpClient(
        transport=transport, parameters=configuration
    )
    payload = client.get_flights_sky_id_list()
    logger.info("Flight search response: %s", payload)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()

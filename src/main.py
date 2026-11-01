"""Exports RapidAPI configuration records to a repository-local CSV file."""

import logging
import os
import pathlib

import dotenv

from core.http import http_client
from core.http import http_client_parameters
from core.utils import json_utils
from rapidapi import rapid_api_http_client
from rapidapi import rapid_api_parameters

logger = logging.getLogger(__name__)


def main() -> None:
    """Loads credentials and exports the RapidAPI configuration to CSV.

    Raises:
        KeyError: A required RapidAPI environment variable or data key is missing.
        requests.RequestException: The request fails, returns an unexpected
            status, or its response cannot be decoded as JSON.
        OSError: Creating the output directory or writing the CSV fails.
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
    _save_config(client)
    # payload = client.get_flights_sky_id_list()
    # logger.info("Flight search response: %s", payload)


def _save_config(client: rapid_api_http_client.RapidApiHttpClient) -> None:
    """Exports configuration data to the repository's data directory.

    Args:
        client: RapidAPI client used to fetch the configuration payload.

    Raises:
        KeyError: The configuration payload has no data key.
        requests.RequestException: The request fails, returns an unexpected
            status, or its response cannot be decoded as JSON.
        OSError: Creating the output directory or writing the CSV fails.
    """
    payload = client.get_config()
    output_folder = pathlib.Path(__file__).resolve().parents[1] / "data"
    json_utils.json_to_csv(
        payload["data"],
        output_folder=output_folder,
        filename="get-config_data.csv",
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()

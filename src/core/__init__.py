"""HTTP modules for shared connection settings and per-request behavior."""

from core.http import http_client
from core.http import http_client_parameters
from core.http import request_parameters

__all__ = ["http_client", "http_client_parameters", "request_parameters"]

"""Configuration for the Snark MCP server.

The server is a thin client over the Snark REST API. Point it at a running
instance with the ``SNARK_API_URL`` environment variable (same convention as
the ``snark`` CLI). Defaults to a local dev stack.
"""

import os

DEFAULT_API_URL = "http://localhost:8100"
API_PREFIX = "v1/wit"
REQUEST_TIMEOUT = 15.0  # seconds; a thin wrapper must never hang on the API
MAX_RESPONSE_CHARS = 4000  # cap upstream text to keep tool output bounded


def api_base_url() -> str:
    """Return the configured Snark API base URL with no trailing slash."""
    return os.environ.get("SNARK_API_URL", DEFAULT_API_URL).rstrip("/")

import importlib

from snark_mcp import config


def test_default_api_base_url(monkeypatch):
    monkeypatch.delenv("SNARK_API_URL", raising=False)
    assert config.api_base_url() == "http://localhost:8100"


def test_api_base_url_from_env_strips_trailing_slash(monkeypatch):
    monkeypatch.setenv("SNARK_API_URL", "https://snark.example.com/")
    assert config.api_base_url() == "https://snark.example.com"


def test_constants_present():
    assert config.API_PREFIX == "v1/wit"
    assert config.REQUEST_TIMEOUT > 0
    assert config.MAX_RESPONSE_CHARS > 0
    importlib.import_module("snark_mcp")  # package imports cleanly

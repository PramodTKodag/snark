import pytest
from wit import pricing
from wit.management.commands.update_pricing import extract


class TestExtract:
    def test_keeps_only_wanted_providers_with_numeric_rates(self):
        raw = {
            "groq/llama-3.3-70b-versatile": {
                "litellm_provider": "groq",
                "input_cost_per_token": 5e-7,
                "output_cost_per_token": 8e-7,
            },
            "gpt-4o": {  # openai, unwanted -> dropped
                "litellm_provider": "openai",
                "input_cost_per_token": 1e-6,
                "output_cost_per_token": 2e-6,
            },
            "claude-haiku-4-5": {
                "litellm_provider": "anthropic",
                "input_cost_per_token": 1e-6,
                "output_cost_per_token": 5e-6,
            },
            "gemini-broken": {  # wanted provider but non-numeric -> dropped
                "litellm_provider": "gemini",
                "input_cost_per_token": "n/a",
                "output_cost_per_token": 1e-6,
            },
            "sample_spec": "not-a-dict",  # non-dict entry -> skipped
        }
        out = extract(raw)
        assert out["groq/llama-3.3-70b-versatile"] == {"input": 5e-7, "output": 8e-7}
        assert "claude-haiku-4-5" in out
        assert "gpt-4o" not in out
        assert "gemini-broken" not in out
        assert "sample_spec" not in out

    def test_matches_on_key_prefix_even_without_litellm_provider(self):
        raw = {
            "gemini-2.0-flash": {
                "litellm_provider": "vertex_ai",
                "input_cost_per_token": 1e-7,
                "output_cost_per_token": 4e-7,
            },
        }
        out = extract(raw)
        assert out["gemini-2.0-flash"] == {"input": 1e-7, "output": 4e-7}


PROVIDERS_FILE = """\
default: local
fallback: [local]
providers:
  local:
    type: openai_compatible
    url: http://localhost:11434/v1
    model: m
    free: true
  claude:
    type: openai_compatible
    url: https://llm.example.test/v1
    model: claude-haiku
    price: [1, 3]
"""

UNPRICED_FILE = """\
default: plain
fallback: [plain]
providers:
  plain:
    type: openai_compatible
    url: http://localhost:11434/v1
    model: m
"""

PRICED_ONLY_FILE = """\
default: claude
fallback: [claude]
providers:
  claude:
    type: openai_compatible
    url: https://llm.example.test/v1
    model: claude-haiku
    price: [1, 3]
"""

FREE_ONLY_FILE = """\
default: local
fallback: [local]
providers:
  local:
    type: openai_compatible
    url: http://localhost:11434/v1
    model: m
    free: true
"""

NO_VENDORED_PRICES = {}


class TestGetRates:
    def test_free_provider_costs_zero(self, monkeypatch, use_providers_file):
        use_providers_file(PROVIDERS_FILE)
        # A vendored entry for the same model must not make a free provider cost.
        monkeypatch.setattr(
            pricing, "_price_map", lambda: {"m": {"input": 9.9, "output": 9.9}}
        )
        assert pricing.get_rates("local", "m") == (0.0, 0.0)

    def test_price_converts_per_million_to_per_token(
        self, monkeypatch, use_providers_file
    ):
        use_providers_file(PROVIDERS_FILE)
        monkeypatch.setattr(pricing, "_price_map", lambda: NO_VENDORED_PRICES)
        rates = pricing.get_rates("claude", "claude-haiku")
        assert rates == pytest.approx((1e-6, 3e-6))

    def test_price_beats_vendored_map(self, monkeypatch, use_providers_file):
        use_providers_file(PROVIDERS_FILE)
        monkeypatch.setattr(
            pricing,
            "_price_map",
            lambda: {"claude-haiku": {"input": 9.9, "output": 9.9}},
        )
        rates = pricing.get_rates("claude", "claude-haiku")
        assert rates == pytest.approx((1e-6, 3e-6))

    def test_provider_without_price_uses_vendored_map(
        self, monkeypatch, use_providers_file
    ):
        use_providers_file(UNPRICED_FILE)
        monkeypatch.setattr(
            pricing, "_price_map", lambda: {"m": {"input": 5e-7, "output": 8e-7}}
        )
        assert pricing.get_rates("plain", "m") == (5e-7, 8e-7)

    def test_unknown_provider_falls_back_to_vendored_map(
        self, monkeypatch, use_providers_file
    ):
        # Historic log rows may name a provider that was removed from the file.
        use_providers_file(PROVIDERS_FILE)
        monkeypatch.setattr(
            pricing,
            "_price_map",
            lambda: {"removed/model": {"input": 5e-7, "output": 8e-7}},
        )
        assert pricing.get_rates("removed", "model") == (5e-7, 8e-7)

    def test_resolves_bare_model_key(self, monkeypatch, use_providers_file):
        use_providers_file(UNPRICED_FILE)
        monkeypatch.setattr(
            pricing,
            "_price_map",
            lambda: {"gemini-2.0-flash": {"input": 1e-7, "output": 4e-7}},
        )
        assert pricing.get_rates("plain", "gemini-2.0-flash") == (1e-7, 4e-7)

    def test_nothing_known_returns_zero(self, monkeypatch, use_providers_file):
        use_providers_file(UNPRICED_FILE)
        monkeypatch.setattr(pricing, "_price_map", lambda: NO_VENDORED_PRICES)
        assert pricing.get_rates("plain", "nope") == (0.0, 0.0)
        assert pricing.get_rates("removed", "nope") == (0.0, 0.0)


class TestRequestCost:
    def test_uses_split_rates(self, use_providers_file):
        use_providers_file(PROVIDERS_FILE)
        # $1/1M input + $3/1M output over 1M tokens each -> 1 + 3 = 4.0
        assert pricing.request_cost("claude", "m", 1_000_000, 1_000_000) == 4.0

    def test_none_tokens_treated_as_zero(self, use_providers_file):
        use_providers_file(PROVIDERS_FILE)
        assert pricing.request_cost("claude", "m", None, None) == 0.0

    def test_unknown_provider_is_zero(self, monkeypatch, use_providers_file):
        use_providers_file(PROVIDERS_FILE)
        monkeypatch.setattr(pricing, "_price_map", lambda: NO_VENDORED_PRICES)
        assert pricing.request_cost("nope", "m", 100, 100) == 0.0


class TestHasPricing:
    def test_true_with_vendored_map_only(self, monkeypatch, use_providers_file):
        use_providers_file(UNPRICED_FILE)
        monkeypatch.setattr(
            pricing, "_price_map", lambda: {"m": {"input": 1e-7, "output": 1e-7}}
        )
        assert pricing.has_pricing() is True

    def test_true_with_only_a_yaml_price(self, monkeypatch, use_providers_file):
        use_providers_file(PRICED_ONLY_FILE)
        monkeypatch.setattr(pricing, "_price_map", lambda: NO_VENDORED_PRICES)
        assert pricing.has_pricing() is True

    def test_false_with_only_a_free_provider(self, monkeypatch, use_providers_file):
        """A free provider is a known zero, not a source of pricing data."""
        use_providers_file(FREE_ONLY_FILE)
        monkeypatch.setattr(pricing, "_price_map", lambda: NO_VENDORED_PRICES)
        assert pricing.has_pricing() is False

    def test_false_when_nothing_is_priced(self, monkeypatch, use_providers_file):
        use_providers_file(UNPRICED_FILE)
        monkeypatch.setattr(pricing, "_price_map", lambda: NO_VENDORED_PRICES)
        assert pricing.has_pricing() is False

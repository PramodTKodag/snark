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


class TestGetRates:
    def test_resolves_known_model_from_map(self, monkeypatch, settings):
        settings.PROVIDER_TOKEN_COST = ""
        monkeypatch.setattr(
            pricing,
            "_price_map",
            lambda: {"groq/llama-3.3-70b-versatile": {"input": 5e-7, "output": 8e-7}},
        )
        assert pricing.get_rates("groq", "llama-3.3-70b-versatile") == (5e-7, 8e-7)

    def test_resolves_bare_model_key(self, monkeypatch, settings):
        settings.PROVIDER_TOKEN_COST = ""
        monkeypatch.setattr(
            pricing,
            "_price_map",
            lambda: {"gemini-2.0-flash": {"input": 1e-7, "output": 4e-7}},
        )
        assert pricing.get_rates("gemini", "gemini-2.0-flash") == (1e-7, 4e-7)

    def test_unknown_returns_zero(self, monkeypatch, settings):
        settings.PROVIDER_TOKEN_COST = ""
        monkeypatch.setattr(pricing, "_price_map", lambda: {})
        assert pricing.get_rates("groq", "nope") == (0.0, 0.0)

    def test_env_override_input_output_wins(self, monkeypatch, settings):
        settings.PROVIDER_TOKEN_COST = "claude:1:3"
        monkeypatch.setattr(
            pricing,
            "_price_map",
            lambda: {"claude-haiku": {"input": 9.9, "output": 9.9}},
        )
        # $1/1M input, $3/1M output -> per-token; override beats the map.
        rates = pricing.get_rates("claude", "claude-haiku")
        assert rates == pytest.approx((1e-6, 3e-6))

    def test_legacy_blended_override(self, settings):
        settings.PROVIDER_TOKEN_COST = "claude:2"
        assert pricing.get_rates("claude", "any") == pytest.approx((2e-6, 2e-6))

    def test_legacy_dict_override(self, settings):
        settings.PROVIDER_TOKEN_COST = {"claude": 1.5}
        assert pricing.get_rates("claude", "any") == pytest.approx((1.5e-6, 1.5e-6))


class TestHasPricing:
    def test_true_when_map_non_empty(self, monkeypatch, settings):
        settings.PROVIDER_TOKEN_COST = ""
        monkeypatch.setattr(
            pricing, "_price_map", lambda: {"x": {"input": 1, "output": 1}}
        )
        assert pricing.has_pricing() is True

    def test_false_when_map_empty_and_no_override(self, monkeypatch, settings):
        settings.PROVIDER_TOKEN_COST = ""
        monkeypatch.setattr(pricing, "_price_map", lambda: {})
        assert pricing.has_pricing() is False

    def test_true_when_only_override(self, monkeypatch, settings):
        settings.PROVIDER_TOKEN_COST = "claude:1:3"
        monkeypatch.setattr(pricing, "_price_map", lambda: {})
        assert pricing.has_pricing() is True

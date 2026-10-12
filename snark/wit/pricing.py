"""Per-model token pricing for the cost estimate.

A provider's `price` or `free` setting in the AI providers file wins, so
operators can set or correct prices without a redeploy. Otherwise rates come
from a vendored copy of LiteLLM's community-maintained pricing map
(pricing_data.json, MIT-licensed, refreshable via `manage.py update_pricing`).
All rates are dollars per single token.
"""

import json
from functools import lru_cache
from pathlib import Path

from .providers import ProviderRegistry

_DATA = Path(__file__).resolve().parent / "pricing_data.json"
_TOKENS_PER_PRICE_UNIT = 1_000_000


@lru_cache(maxsize=1)
def _price_map() -> dict:
    try:
        return json.loads(_DATA.read_text())
    except (OSError, ValueError):
        return {}


def get_rates(provider: str, model: str) -> tuple:
    """Return (input_per_token, output_per_token) for a provider/model.

    The provider's configured `free`/`price` wins, then the vendored map.
    (0, 0) if unknown."""
    spec = ProviderRegistry.spec(provider)
    if spec is not None:
        if spec.free:
            return 0.0, 0.0
        if spec.price is not None:
            in_price, out_price = spec.price
            return (
                in_price / _TOKENS_PER_PRICE_UNIT,
                out_price / _TOKENS_PER_PRICE_UNIT,
            )
    data = _price_map()
    for key in (model, f"{provider}/{model}"):
        entry = data.get(key)
        if entry:
            return entry.get("input", 0.0), entry.get("output", 0.0)
    return 0.0, 0.0


def request_cost(
    provider: str, model: str, input_tokens: int, output_tokens: int
) -> float:
    """Estimated USD cost for a single request from its split token counts."""
    in_rate, out_rate = get_rates(provider, model)
    return round((input_tokens or 0) * in_rate + (output_tokens or 0) * out_rate, 6)


def has_pricing() -> bool:
    return bool(_price_map()) or any(
        spec.free or spec.price is not None
        for spec in ProviderRegistry.specs().values()
    )

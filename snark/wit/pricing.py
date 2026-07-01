"""Per-model token pricing for the cost estimate.

Rates come from a vendored copy of LiteLLM's community-maintained pricing map
(pricing_data.json, MIT-licensed, refreshable via `manage.py update_pricing`).
The PROVIDER_TOKEN_COST env override wins per provider so operators can tune or
correct prices without a redeploy. All rates are dollars per single token.
"""

import json
import logging
from functools import lru_cache
from pathlib import Path

from django.conf import settings

logger = logging.getLogger(__name__)

_DATA = Path(__file__).resolve().parent / "pricing_data.json"


@lru_cache(maxsize=1)
def _price_map() -> dict:
    try:
        return json.loads(_DATA.read_text())
    except (OSError, ValueError):
        return {}


def _env_overrides() -> dict:
    """PROVIDER_TOKEN_COST -> {provider: (input_per_token, output_per_token)}.

    Accepts "provider:in:out" (input/output $ per 1M) or legacy "provider:blended"
    (applied to both). Values are per-1M; converted to per-token here.
    """
    raw = getattr(settings, "PROVIDER_TOKEN_COST", "") or ""
    if isinstance(raw, dict):  # already-parsed legacy {provider: blended_per_1M}
        return {p: (v / 1_000_000, v / 1_000_000) for p, v in raw.items()}
    out = {}
    for part in str(raw).split(","):
        bits = [b.strip() for b in part.split(":")]
        try:
            if len(bits) == 2 and bits[0]:
                rate = float(bits[1]) / 1_000_000
                out[bits[0]] = (rate, rate)
            elif len(bits) == 3 and bits[0]:
                out[bits[0]] = (
                    float(bits[1]) / 1_000_000,
                    float(bits[2]) / 1_000_000,
                )
        except ValueError:
            # A misconfigured override must not crash the dashboard at render
            # time; skip the bad entry and keep the rest.
            logger.warning("Ignoring malformed PROVIDER_TOKEN_COST entry: %r", part)
    return out


def get_rates(provider: str, model: str) -> tuple:
    """Return (input_per_token, output_per_token) for a provider/model.

    (0, 0) if unknown."""
    override = _env_overrides().get(provider)
    if override:
        return override
    data = _price_map()
    for key in (model, f"{provider}/{model}"):
        entry = data.get(key)
        if entry:
            return entry.get("input", 0.0), entry.get("output", 0.0)
    return 0.0, 0.0


def has_pricing() -> bool:
    return bool(_price_map()) or bool(_env_overrides())

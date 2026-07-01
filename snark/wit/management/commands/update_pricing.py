import json
import urllib.request
from pathlib import Path

from django.core.management.base import BaseCommand

URL = (
    "https://raw.githubusercontent.com/BerriAI/litellm/main/"
    "model_prices_and_context_window.json"
)
WANT_PROVIDERS = {"groq", "gemini", "vertex_ai", "anthropic"}
OUT = Path(__file__).resolve().parents[2] / "pricing_data.json"


def extract(raw: dict) -> dict:
    result = {}
    for key, entry in raw.items():
        if not isinstance(entry, dict):
            continue
        prov = entry.get("litellm_provider", "")
        prefix = key.split("/")[0]
        if prov in WANT_PROVIDERS or prefix in {"groq", "gemini", "claude", "anthropic"}:
            i = entry.get("input_cost_per_token")
            o = entry.get("output_cost_per_token")
            if isinstance(i, (int, float)) and isinstance(o, (int, float)):
                result[key] = {"input": i, "output": o}
    return result


class Command(BaseCommand):
    help = "Refresh wit/pricing_data.json from LiteLLM's model cost map (MIT)."

    def handle(self, *args, **options):
        with urllib.request.urlopen(URL, timeout=30) as resp:
            raw = json.loads(resp.read().decode("utf-8"))
        data = extract(raw)
        OUT.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
        self.stdout.write(self.style.SUCCESS(f"Wrote {len(data)} price rows to {OUT}."))

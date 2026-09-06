"""Prometheus counters for generation reliability.

Labels are deliberately low-cardinality (provider + boolean outcomes) so the
metric stays cheap. High-cardinality context (persona, model) lives in the
structured logs, not in labels. Works under gunicorn multiprocess mode via
PROMETHEUS_MULTIPROC_DIR.
"""

from prometheus_client import Counter

GENERATIONS_TOTAL = Counter(
    "snark_generations_total",
    "Total generation attempts recorded at the reliability choke point.",
    ["provider", "success", "fell_back", "content_filtered"],
)

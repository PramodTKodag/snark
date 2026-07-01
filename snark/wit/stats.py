"""Read-only aggregation helpers for the /stats endpoint and admin dashboard.

Single source of truth for usage numbers so the API and the admin never drift.
Provider status/cost are derived from settings/env only — no DB-backed provider
config. Every function here is a read-only query; none mutate state.
"""

from datetime import timedelta

from django.conf import settings
from django.db.models import Avg, Count, Max, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone

from .models import Persona, ResponseLog


def usage_stats() -> dict:
    """Totals + top personas — the shape the public /stats endpoint returns."""
    agg = ResponseLog.objects.aggregate(total=Count("id"), tokens=Sum("tokens_used"))
    top = (
        ResponseLog.objects.values("persona__slug", "persona__name")
        .annotate(count=Count("id"))
        .order_by("-count")[:10]
    )
    return {
        "total_responses": agg["total"] or 0,
        "total_tokens": agg["tokens"] or 0,
        "personas": [
            {
                "slug": row["persona__slug"],
                "name": row["persona__name"],
                "count": row["count"],
            }
            for row in top
        ],
    }


def active_persona_counts() -> dict:
    total = Persona.objects.count()
    active = Persona.objects.filter(is_active=True).count()
    return {"total": total, "active": active}


def dashboard_kpis() -> dict:
    agg = ResponseLog.objects.aggregate(
        total=Count("id"), tokens=Sum("tokens_used"), avg_latency=Avg("latency_ms")
    )
    last_24h = ResponseLog.objects.filter(
        created_at__gte=timezone.now() - timedelta(hours=24)
    ).count()
    personas = active_persona_counts()
    return {
        "total_responses": agg["total"] or 0,
        "total_tokens": agg["tokens"] or 0,
        "avg_latency": round(agg["avg_latency"] or 0),
        "last_24h": last_24h,
        "active_personas": personas["active"],
        "total_personas": personas["total"],
    }


def _percentile(sorted_values: list, q: float) -> int:
    """Nearest-rank percentile over an already-sorted list (0 when empty)."""
    if not sorted_values:
        return 0
    idx = min(len(sorted_values) - 1, int(round(q * (len(sorted_values) - 1))))
    return sorted_values[idx]


def latency_stats(sample: int = 1000) -> dict:
    """avg/max over all rows; p50/p95/p99 over the most recent ``sample`` rows."""
    agg = ResponseLog.objects.aggregate(avg=Avg("latency_ms"), max=Max("latency_ms"))
    latencies = sorted(
        ResponseLog.objects.order_by("-created_at").values_list(
            "latency_ms", flat=True
        )[:sample]
    )
    return {
        "avg": round(agg["avg"] or 0),
        "p50": _percentile(latencies, 0.50),
        "p95": _percentile(latencies, 0.95),
        "p99": _percentile(latencies, 0.99),
        "max": agg["max"] or 0,
        "sample": len(latencies),
    }


def provider_breakdown() -> list:
    total = ResponseLog.objects.count()
    rows = (
        ResponseLog.objects.values("provider_name")
        .annotate(
            count=Count("id"), avg_latency=Avg("latency_ms"), tokens=Sum("tokens_used")
        )
        .order_by("-count")
    )
    result = []
    for row in rows:
        result.append(
            {
                "provider": row["provider_name"] or "unknown",
                "count": row["count"],
                "share": round(100 * row["count"] / total, 1) if total else 0,
                "avg_latency": round(row["avg_latency"] or 0),
                "tokens": row["tokens"] or 0,
            }
        )
    return result


def model_usage(limit: int = 10) -> list:
    rows = (
        ResponseLog.objects.values("model_name")
        .annotate(count=Count("id"))
        .order_by("-count")[:limit]
    )
    return [{"model": r["model_name"] or "unknown", "count": r["count"]} for r in rows]


def responses_over_time(days: int = 14) -> list:
    """Per-day response count + tokens for the last ``days`` days, gaps filled."""
    start = (timezone.now() - timedelta(days=days - 1)).date()
    rows = (
        ResponseLog.objects.filter(created_at__date__gte=start)
        .annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(count=Count("id"), tokens=Sum("tokens_used"))
        .order_by("day")
    )
    by_day = {r["day"]: r for r in rows}
    series = []
    for i in range(days):
        day = start + timedelta(days=i)
        row = by_day.get(day)
        series.append(
            {
                "day": day.isoformat(),
                "count": row["count"] if row else 0,
                "tokens": (row["tokens"] or 0) if row else 0,
            }
        )
    return series


def top_personas(limit: int = 10) -> list:
    rows = (
        ResponseLog.objects.values("persona__slug", "persona__name")
        .annotate(
            count=Count("id"),
            avg_latency=Avg("latency_ms"),
            avg_tokens=Avg("tokens_used"),
        )
        .order_by("-count")[:limit]
    )
    return [
        {
            "slug": r["persona__slug"],
            "name": r["persona__name"],
            "count": r["count"],
            "avg_latency": round(r["avg_latency"] or 0),
            "avg_tokens": round(r["avg_tokens"] or 0),
        }
        for r in rows
    ]


def unused_personas() -> list:
    return list(
        Persona.objects.filter(is_active=True, response_logs__isnull=True)
        .values("slug", "name")
        .order_by("name")
    )


def recent_activity(limit: int = 15) -> list:
    return list(
        ResponseLog.objects.order_by("-created_at").values(
            "persona__slug",
            "provider_name",
            "model_name",
            "latency_ms",
            "tokens_used",
            "created_at",
        )[:limit]
    )


def provider_status() -> list:
    """Which providers are configured, in fallback order, default flagged."""
    from .providers import ProviderRegistry

    default = getattr(settings, "AI_DEFAULT_PROVIDER", "groq")
    order = list(getattr(settings, "AI_PROVIDER_FALLBACK_ORDER", ["groq"]))
    if default not in order:
        order.append(default)
    result = []
    for name in order:
        try:
            configured = ProviderRegistry.get(name).is_available()
        except Exception:
            configured = False
        result.append(
            {"name": name, "configured": configured, "is_default": name == default}
        )
    return result


def system_health() -> dict:
    from django.core.cache import cache
    from django.db import connection

    database = "healthy"
    try:
        connection.ensure_connection()
    except Exception:
        database = "unhealthy"
    redis = "healthy"
    try:
        cache.set("dash_health_check", "ok", 5)
        redis = "healthy" if cache.get("dash_health_check") == "ok" else "unhealthy"
    except Exception:
        redis = "unhealthy"
    return {"database": database, "redis": redis}


def cost_estimate() -> dict:
    """Estimated USD spend from token counts x per-provider PROVIDER_TOKEN_COST."""
    pricing = getattr(settings, "PROVIDER_TOKEN_COST", {}) or {}
    rows = ResponseLog.objects.values("provider_name").annotate(
        tokens=Sum("tokens_used")
    )
    per_provider = []
    total = 0.0
    for row in rows:
        name = row["provider_name"] or "unknown"
        tokens = row["tokens"] or 0
        price = pricing.get(name, 0) or 0
        cost = tokens / 1_000_000 * price
        total += cost
        per_provider.append(
            {"provider": name, "tokens": tokens, "cost": round(cost, 4)}
        )
    per_provider.sort(key=lambda item: item["cost"], reverse=True)
    return {
        "total": round(total, 2),
        "per_provider": per_provider,
        "configured": any(bool(v) for v in pricing.values()),
    }


def cost_by_persona(limit: int = 10) -> list:
    """Estimated USD spend per persona = sum over providers of tokens * rate.

    Segments the existing token/provider data by persona so operators can see
    which personas drive spend, not just the aggregate bill.
    """
    pricing = getattr(settings, "PROVIDER_TOKEN_COST", {}) or {}
    rows = ResponseLog.objects.values(
        "persona__slug", "persona__name", "provider_name"
    ).annotate(tokens=Sum("tokens_used"))
    by_persona = {}
    for row in rows:
        slug = row["persona__slug"]
        entry = by_persona.setdefault(
            slug,
            {"slug": slug, "name": row["persona__name"], "tokens": 0, "cost": 0.0},
        )
        tokens = row["tokens"] or 0
        rate = pricing.get(row["provider_name"], 0) or 0
        entry["tokens"] += tokens
        entry["cost"] += tokens / 1_000_000 * rate
    result = sorted(by_persona.values(), key=lambda entry: entry["cost"], reverse=True)
    for entry in result:
        entry["cost"] = round(entry["cost"], 4)
    return result[:limit]

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

from . import pricing
from .models import GenerationEvent, Persona, ResponseLog


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
            count=Count("id"),
            avg_latency=Avg("latency_ms"),
            tokens=Sum("tokens_used"),
            input_tokens=Sum("input_tokens"),
            output_tokens=Sum("output_tokens"),
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
                "input_tokens": row["input_tokens"] or 0,
                "output_tokens": row["output_tokens"] or 0,
            }
        )
    return result


def reliability_stats() -> dict:
    """Error / provider-fallback / content-filter rates over all events."""
    from django.db.models import Q

    agg = GenerationEvent.objects.aggregate(
        total=Count("id"),
        errors=Count("id", filter=Q(success=False)),
        fallbacks=Count("id", filter=Q(fell_back=True)),
        filtered=Count("id", filter=Q(content_filtered=True)),
    )
    total = agg["total"] or 0

    def rate(n):
        return round(100 * n / total, 1) if total else 0.0

    return {
        "total": total,
        "errors": agg["errors"] or 0,
        "fallbacks": agg["fallbacks"] or 0,
        "filtered": agg["filtered"] or 0,
        "error_rate": rate(agg["errors"] or 0),
        "fallback_rate": rate(agg["fallbacks"] or 0),
        "content_filter_rate": rate(agg["filtered"] or 0),
    }


def provider_error_breakdown() -> list:
    """Per-provider count of failed generation events, most failures first."""
    rows = (
        GenerationEvent.objects.filter(success=False)
        .values("provider_name")
        .annotate(errors=Count("id"))
        .order_by("-errors")
    )
    return [{"provider": r["provider_name"], "errors": r["errors"]} for r in rows]


def recent_failures(limit: int = 10) -> list:
    """Most recent failed generation events (provider, why, when)."""
    return list(
        GenerationEvent.objects.filter(success=False)
        .order_by("-created_at")
        .values(
            "provider_name", "error_code", "error_detail", "streamed", "created_at"
        )[:limit]
    )


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
    """Estimated USD spend from split input/output tokens x per-model rates.

    Rates are resolved per (provider, model) group from the vendored pricing map
    (with the PROVIDER_TOKEN_COST env override), then rolled up to per-provider
    totals for display. Streamed and non-streamed responses both log split
    token usage, so both contribute to the estimate.
    """
    rows = ResponseLog.objects.values("provider_name", "model_name").annotate(
        input_tokens=Sum("input_tokens"),
        output_tokens=Sum("output_tokens"),
        tokens=Sum("tokens_used"),
    )
    per_provider: dict = {}
    total = 0.0
    for row in rows:
        name = row["provider_name"] or "unknown"
        in_rate, out_rate = pricing.get_rates(name, row["model_name"] or "")
        cost = (row["input_tokens"] or 0) * in_rate + (row["output_tokens"] or 0) * (
            out_rate
        )
        total += cost
        entry = per_provider.setdefault(
            name, {"provider": name, "tokens": 0, "cost": 0.0}
        )
        entry["tokens"] += row["tokens"] or 0
        entry["cost"] += cost
    ordered = sorted(per_provider.values(), key=lambda item: item["cost"], reverse=True)
    for entry in ordered:
        entry["cost"] = round(entry["cost"], 4)
    return {
        "total": round(total, 2),
        "per_provider": ordered,
        "configured": pricing.has_pricing(),
    }


def cost_by_persona(limit: int = 10) -> list:
    """Estimated USD spend per persona from split tokens x per-model rates.

    Segments the token data by (persona, provider, model) so operators can see
    which personas drive spend, not just the aggregate bill.
    """
    rows = ResponseLog.objects.values(
        "persona__slug", "persona__name", "provider_name", "model_name"
    ).annotate(
        input_tokens=Sum("input_tokens"),
        output_tokens=Sum("output_tokens"),
        tokens=Sum("tokens_used"),
    )
    by_persona: dict = {}
    for row in rows:
        slug = row["persona__slug"]
        entry = by_persona.setdefault(
            slug,
            {"slug": slug, "name": row["persona__name"], "tokens": 0, "cost": 0.0},
        )
        in_rate, out_rate = pricing.get_rates(
            row["provider_name"] or "", row["model_name"] or ""
        )
        entry["tokens"] += row["tokens"] or 0
        entry["cost"] += (row["input_tokens"] or 0) * in_rate + (
            row["output_tokens"] or 0
        ) * out_rate
    result = sorted(by_persona.values(), key=lambda entry: entry["cost"], reverse=True)
    for entry in result:
        entry["cost"] = round(entry["cost"], 4)
    return result[:limit]

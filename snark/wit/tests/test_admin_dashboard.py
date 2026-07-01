from datetime import timedelta

import pytest
from base.admin import snark_admin_site
from django.contrib.auth import get_user_model
from django.test import RequestFactory
from django.utils import timezone
from wit import stats
from wit.models import ResponseLog


@pytest.fixture
def admin_urls():
    """Register the admin URLconf for the duration of a test.

    The session-scoped conftest fixture builds ``base.urls`` with
    ``ADMIN_ENABLED=False`` (no admin namespace), so the default admin index
    would raise ``NoReverseMatch`` while building the app list. Enable the admin
    route here, then restore the disabled state afterwards so other routing
    tests still see /admin/ as unregistered.
    """
    import importlib

    import base.urls as urls
    from django.conf import settings as dj_settings
    from django.urls import clear_url_caches

    original = dj_settings.ADMIN_ENABLED
    dj_settings.ADMIN_ENABLED = True
    importlib.reload(urls)
    clear_url_caches()
    try:
        yield
    finally:
        dj_settings.ADMIN_ENABLED = original
        importlib.reload(urls)
        clear_url_caches()


def _log(
    persona,
    provider="groq",
    model="m",
    tokens=10,
    latency=100,
    age_days=0,
    input_tokens=0,
    output_tokens=0,
):
    log = ResponseLog.objects.create(
        persona=persona,
        response_text="hi",
        tokens_used=tokens,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        latency_ms=latency,
        provider_name=provider,
        model_name=model,
    )
    if age_days:
        ResponseLog.objects.filter(pk=log.pk).update(
            created_at=timezone.now() - timedelta(days=age_days)
        )
    return log


@pytest.mark.django_db
def test_dashboard_kpis(persona_no):
    _log(persona_no, tokens=5, latency=100)
    _log(persona_no, tokens=7, latency=200)
    k = stats.dashboard_kpis()
    assert k["total_responses"] == 2
    assert k["total_tokens"] == 12
    assert k["avg_latency"] == 150
    assert k["last_24h"] == 2
    assert k["active_personas"] == 1
    assert k["total_personas"] == 1


@pytest.mark.django_db
def test_provider_breakdown_shares(persona_no):
    _log(persona_no, provider="groq")
    _log(persona_no, provider="groq")
    _log(persona_no, provider="claude")
    rows = stats.provider_breakdown()
    groq = next(r for r in rows if r["provider"] == "groq")
    assert groq["count"] == 2
    assert groq["share"] == pytest.approx(66.7, abs=0.1)


@pytest.mark.django_db
def test_provider_breakdown_sums_input_output_tokens(persona_no):
    _log(persona_no, provider="claude", input_tokens=100, output_tokens=40, tokens=140)
    _log(persona_no, provider="claude", input_tokens=10, output_tokens=5, tokens=15)
    claude = next(
        r for r in stats.provider_breakdown() if r["provider"] == "claude"
    )
    assert claude["input_tokens"] == 110
    assert claude["output_tokens"] == 45


@pytest.mark.django_db
def test_latency_stats(persona_no):
    for ms in (100, 200, 300, 400):
        _log(persona_no, latency=ms)
    lat = stats.latency_stats()
    assert lat["avg"] == 250
    assert lat["max"] == 400
    assert lat["p95"] >= 300
    # percentiles are monotonic and bounded by max
    assert lat["p50"] <= lat["p95"] <= lat["p99"] <= lat["max"]
    assert lat["p99"] == 400


@pytest.mark.django_db
def test_responses_over_time_fills_gaps(persona_no):
    _log(persona_no, age_days=0)
    series = stats.responses_over_time(days=7)
    assert len(series) == 7  # every day present, gaps filled with 0
    assert series[-1]["count"] == 1
    assert all("day" in row and "count" in row and "tokens" in row for row in series)


@pytest.mark.django_db
def test_unused_personas(persona_no, persona_roast):
    _log(persona_no)  # persona_no used, persona_roast unused
    unused = stats.unused_personas()
    slugs = [p["slug"] for p in unused]
    assert "roast" in slugs
    assert "say-no" not in slugs


@pytest.mark.django_db
def test_cost_estimate(persona_no, settings):
    # claude override: input $1/1M, output $3/1M. groq unpriced (model "m").
    settings.PROVIDER_TOKEN_COST = "claude:1:3"
    _log(
        persona_no,
        provider="claude",
        tokens=2_000_000,
        input_tokens=1_000_000,
        output_tokens=1_000_000,
    )
    _log(persona_no, provider="groq", tokens=500_000, input_tokens=500_000)
    cost = stats.cost_estimate()
    # 1M input * $1/1M + 1M output * $3/1M = $4.00; groq (model "m") = $0.
    assert cost["total"] == pytest.approx(4.0, abs=0.001)
    assert cost["configured"] is True
    claude = next(r for r in cost["per_provider"] if r["provider"] == "claude")
    assert claude["cost"] == pytest.approx(4.0, abs=0.001)


@pytest.mark.django_db
def test_cost_by_persona(persona_no, persona_roast, settings):
    settings.PROVIDER_TOKEN_COST = "claude:1:3"
    _log(
        persona_no,
        provider="claude",
        tokens=2_000_000,
        input_tokens=1_000_000,
        output_tokens=1_000_000,
    )  # $4.00
    _log(persona_roast, provider="groq", tokens=500_000, input_tokens=500_000)  # $0.00
    rows = stats.cost_by_persona()
    top = rows[0]
    assert top["slug"] == "say-no"
    assert top["cost"] == pytest.approx(4.0, abs=0.001)
    assert top["tokens"] == 2_000_000
    roast = next(r for r in rows if r["slug"] == "roast")
    assert roast["cost"] == 0.0


@pytest.mark.django_db
def test_dashboard_index_injects_full_context(persona_no, admin_urls):
    _log(persona_no)
    admin_user = get_user_model().objects.create_superuser(
        "root", "root@example.com", "supersecret123"
    )
    request = RequestFactory().get("/")
    request.user = admin_user
    response = snark_admin_site.index(request)
    ctx = response.context_data
    for key in (
        "kpis",
        "cost",
        "providers",
        "provider_breakdown",
        "model_usage",
        "latency",
        "top_personas",
        "unused_personas",
        "recent",
        "health",
        "over_time",
        "cost_by_persona",
    ):
        assert key in ctx, f"missing dashboard context key: {key}"


@pytest.mark.django_db
def test_stats_endpoint_still_works(api_client, persona_no):
    _log(persona_no, tokens=3)
    resp = api_client.get("/v1/wit/stats/")
    assert resp.status_code == 200
    assert resp.data["total_responses"] == 1
    assert resp.data["total_tokens"] == 3


@pytest.mark.django_db
def test_admin_index_requires_login(admin_urls, client):
    resp = client.get("/admin/", SERVER_NAME="localhost")
    assert resp.status_code == 302
    assert "/login" in resp["Location"]


@pytest.mark.django_db
def test_dashboard_persona_chart_payload(persona_no, persona_roast, admin_urls):
    _log(persona_no)
    _log(persona_no)
    _log(persona_roast)
    admin_user = get_user_model().objects.create_superuser(
        "root3", "root3@example.com", "supersecret123"
    )
    request = RequestFactory().get("/")
    request.user = admin_user
    chart = snark_admin_site.index(request).context_data["chart_personas"]
    assert set(chart) == {"labels", "counts"}
    assert sum(chart["counts"]) == 3
    # Ordered by request count desc: say-no (2 requests) before roast (1).
    assert chart["counts"][0] == 2
    assert chart["labels"][0] == persona_no.name

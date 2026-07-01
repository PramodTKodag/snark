"""Custom admin site for snark.

Subclasses Django's AdminSite. The ``index`` override surfaces an interactive
operations dashboard (KPIs, provider/latency/model analytics, a configurable
cost estimate, unused-persona detection, recent activity and system health)
rendered by ``templates/admin/index.html`` with Chart.js. Model admins register
to ``snark_admin_site`` (see ``wit/admin.py``); the site is routed only when
``ADMIN_ENABLED`` is true.
"""

from django.contrib import admin


class SnarkAdminSite(admin.AdminSite):
    site_header = "Snark administration"
    site_title = "Snark admin"
    index_title = "Dashboard"

    def index(self, request, extra_context=None):
        from wit import stats

        over_time = stats.responses_over_time(14)
        breakdown = stats.provider_breakdown()
        top_personas = stats.top_personas(10)
        extra = dict(extra_context or {})
        extra.update(
            {
                "kpis": stats.dashboard_kpis(),
                "reliability": stats.reliability_stats(),
                "provider_errors": stats.provider_error_breakdown(),
                "recent_failures": stats.recent_failures(10),
                "cost": stats.cost_estimate(),
                "cost_by_persona": stats.cost_by_persona(10),
                "providers": stats.provider_status(),
                "provider_breakdown": breakdown,
                "model_usage": stats.model_usage(),
                "latency": stats.latency_stats(),
                "top_personas": top_personas,
                "unused_personas": stats.unused_personas(),
                "recent": stats.recent_activity(15),
                "health": stats.system_health(),
                "over_time": over_time,
                # Chart.js data payloads (rendered via json_script in the template).
                "chart_over_time": {
                    "labels": [row["day"] for row in over_time],
                    "responses": [row["count"] for row in over_time],
                    "tokens": [row["tokens"] for row in over_time],
                },
                "chart_providers": {
                    "labels": [row["provider"] for row in breakdown],
                    "counts": [row["count"] for row in breakdown],
                },
                "chart_personas": {
                    "labels": [row["name"] for row in top_personas],
                    "counts": [row["count"] for row in top_personas],
                },
            }
        )
        return super().index(request, extra_context=extra)


snark_admin_site = SnarkAdminSite(name="snark_admin")

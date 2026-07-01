"""Custom admin site for snark.

Subclasses Django's AdminSite so the index page can surface a stats dashboard
and read-only provider status. Model admins register to ``snark_admin_site``
(see ``wit/admin.py``); the site is routed only when ``ADMIN_ENABLED`` is true.
"""

from django.contrib import admin


class SnarkAdminSite(admin.AdminSite):
    site_header = "Snark administration"
    site_title = "Snark admin"
    index_title = "Dashboard"

    def index(self, request, extra_context=None):
        # Import lazily so importing this module never triggers ORM/provider work.
        from wit.stats import (
            active_persona_counts,
            per_day_counts,
            provider_status,
            recent_activity,
            usage_stats,
        )

        extra = dict(extra_context or {})
        extra.update(
            {
                "snark_stats": usage_stats(),
                "snark_personas": active_persona_counts(),
                "snark_providers": provider_status(),
                "snark_recent": recent_activity(10),
                "snark_daily": per_day_counts(7),
            }
        )
        return super().index(request, extra_context=extra)


snark_admin_site = SnarkAdminSite(name="snark_admin")

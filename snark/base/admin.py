"""Custom admin site for snark.

Subclasses Django's AdminSite. The stats-dashboard task adds an ``index``
override that surfaces usage stats + provider status; until then this is a
plain custom site. Model admins register to ``snark_admin_site`` (see
``wit/admin.py``); the site is routed only when ``ADMIN_ENABLED`` is true.
"""

from django.contrib import admin


class SnarkAdminSite(admin.AdminSite):
    site_header = "Snark administration"
    site_title = "Snark admin"
    index_title = "Dashboard"


snark_admin_site = SnarkAdminSite(name="snark_admin")

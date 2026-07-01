from django.conf import settings
from django.contrib import (  # noqa: F401  (ensures admin is imported)
    admin as django_admin,
)
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from wit.views import HealthStatusView, LivenessView, ReadinessView

# All routes hang off the single API mount point defined in settings, so the
# version/namespace can be changed in one place (settings.API_PREFIX).
_PREFIX = f"{settings.API_PREFIX}/"


def build_admin_patterns():
    """Return the admin route only when ADMIN_ENABLED; otherwise nothing.

    Read at import time so a disabled deployment exposes no admin URL at all.
    """
    if not settings.ADMIN_ENABLED:
        return []
    from base.admin import snark_admin_site

    return [path(settings.ADMIN_URL, snark_admin_site.urls)]


urlpatterns = [
    path(f"{_PREFIX}health/live/", LivenessView.as_view(), name="health-live"),
    path(f"{_PREFIX}health/ready/", ReadinessView.as_view(), name="health-ready"),
    path(f"{_PREFIX}health/status/", HealthStatusView.as_view(), name="health-status"),
    path(f"{_PREFIX}schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        f"{_PREFIX}swagger/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        f"{_PREFIX}redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
    # Business endpoints live in wit/urls.py — add new wit paths there.
    path(_PREFIX, include("wit.urls")),
]

urlpatterns += build_admin_patterns()

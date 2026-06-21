from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from wit.views import HealthStatusView, LivenessView, ReadinessView

urlpatterns = [
    path("v1/wit/health/live/", LivenessView.as_view(), name="health-live"),
    path("v1/wit/health/ready/", ReadinessView.as_view(), name="health-ready"),
    path("v1/wit/health/status/", HealthStatusView.as_view(), name="health-status"),
    path("v1/wit/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "v1/wit/swagger/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "v1/wit/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
    path("v1/wit/", include("wit.urls")),
]

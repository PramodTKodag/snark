"""Bearer-token-guarded Prometheus metrics endpoint.

/metrics is served on the same public port as the API, where an IP allowlist is
unreliable: Docker's published-port NAT rewrites external source IPs to the
private bridge gateway, and X-Forwarded-For is spoofable on a directly-reachable
port. So access is gated by a shared bearer token compared in constant time.
When the token is unset the endpoint does not exist (404), keeping it off by
default. Network isolation remains the recommended primary control.
"""

import hmac

from django.conf import settings
from django.http import Http404
from django_prometheus.exports import ExportToDjangoView

_BEARER_PREFIX = "Bearer "


def metrics_view(request):
    token = settings.METRICS_AUTH_TOKEN
    if not token:
        raise Http404

    header = request.META.get("HTTP_AUTHORIZATION", "")
    provided = (
        header[len(_BEARER_PREFIX) :] if header.startswith(_BEARER_PREFIX) else ""
    )

    if not (provided and hmac.compare_digest(provided, token)):
        raise Http404

    return ExportToDjangoView(request)

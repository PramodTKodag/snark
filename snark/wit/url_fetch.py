"""SSRF-safe fetcher for the roast-url endpoint.

Fetches a user-supplied public URL using only the Python standard library. The
network path is hardened against Server-Side Request Forgery: only http/https on
ports 80/443 are allowed, every resolved IP is screened against internal ranges,
the socket is pinned to the screened IP (defeating DNS rebinding), and redirects
are followed manually with the full screen re-applied on each hop.
"""

import http.client
import ipaddress
import logging
import socket
import ssl
from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit

logger = logging.getLogger(__name__)

_ALLOWED_SCHEMES = frozenset({"http", "https"})
_ALLOWED_PORTS = frozenset({80, 443})
_REDIRECT_CODES = frozenset({301, 302, 303, 307, 308})

TIMEOUT = 5  # seconds, per connect/read
MAX_BYTES = 512 * 1024  # cap on response body read
MAX_REDIRECTS = 3
_USER_AGENT = "snark-api"

# Networks that must never be fetched, beyond what ``is_global`` covers on every
# supported Python version. CGNAT (100.64.0.0/10) is only classified private
# from Python 3.13 onward, so it is listed explicitly for 3.12.
_EXTRA_DENY_NETWORKS = (
    ipaddress.ip_network("100.64.0.0/10"),  # CGNAT (RFC 6598)
    ipaddress.ip_network("192.0.0.0/24"),  # IETF protocol assignments
    ipaddress.ip_network("198.18.0.0/15"),  # benchmarking
)


class UrlFetchError(Exception):
    """Base class for URL fetch failures."""


class UnsafeUrlError(UrlFetchError):
    """The URL targets a disallowed scheme, port, or internal/non-global IP."""


class UrlUnreachableError(UrlFetchError):
    """The URL could not be retrieved (DNS failure, timeout, bad status, size)."""


@dataclass(frozen=True)
class FetchedPage:
    """A successfully fetched page: its HTML and the final (post-redirect) URL."""

    html: str
    final_url: str


def _screen_ip(raw_ip: str) -> None:
    """Raise UnsafeUrlError unless ``raw_ip`` is a safe, globally-routable host."""
    ip = ipaddress.ip_address(raw_ip)

    # Collapse IPv6 tunnelling/mapping so the embedded IPv4 is screened directly.
    if isinstance(ip, ipaddress.IPv6Address):
        mapped = ip.ipv4_mapped or ip.sixtofour
        if mapped is not None:
            ip = mapped

    unsafe = (
        not ip.is_global
        or ip.is_loopback
        or ip.is_private
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
        or any(ip in net for net in _EXTRA_DENY_NETWORKS)
    )
    if unsafe:
        raise UnsafeUrlError("URL resolves to a non-public address")


def _resolve_and_screen(host: str, port: int) -> str:
    """Resolve ``host``, screen every address, and return one safe IP to pin to."""
    try:
        infos = socket.getaddrinfo(host, port, proto=socket.IPPROTO_TCP)
    except socket.gaierror as exc:
        raise UrlUnreachableError(f"DNS resolution failed for {host}") from exc
    if not infos:
        raise UrlUnreachableError(f"No addresses for {host}")
    for info in infos:
        _screen_ip(info[4][0])
    return infos[0][4][0]


def _request(scheme: str, host: str, ip: str, port: int, path: str):
    """Perform a single GET against the screened ``ip`` while presenting ``host``.

    Returns ``(status, body, location)``. The socket is pinned to ``ip`` so the
    connection cannot be re-pointed at an internal host after screening. For
    https, TLS SNI and certificate validation still target ``host``.
    """
    raw = socket.create_connection((ip, port), timeout=TIMEOUT)
    if scheme == "https":
        context = ssl.create_default_context()
        sock = context.wrap_socket(raw, server_hostname=host)
    else:
        sock = raw

    conn = http.client.HTTPConnection(host, port, timeout=TIMEOUT)
    conn.sock = sock
    try:
        conn.request(
            "GET",
            path,
            headers={"User-Agent": _USER_AGENT, "Accept": "text/html"},
        )
        resp = conn.getresponse()
        location = (
            resp.getheader("Location") if resp.status in _REDIRECT_CODES else None
        )
        body = resp.read(MAX_BYTES).decode("utf-8", errors="replace")
        return resp.status, body, location
    finally:
        conn.close()


def _validate_target(url: str):
    """Validate scheme/port and return ``(scheme, host, port, path)`` for ``url``."""
    parts = urlsplit(url)
    if parts.scheme not in _ALLOWED_SCHEMES:
        raise UnsafeUrlError(f"Unsupported scheme: {parts.scheme or '(none)'}")
    host = parts.hostname
    if not host:
        raise UnsafeUrlError("URL has no host")
    port = parts.port or (443 if parts.scheme == "https" else 80)
    if port not in _ALLOWED_PORTS:
        raise UnsafeUrlError(f"Disallowed port: {port}")
    path = parts.path or "/"
    if parts.query:
        path = f"{path}?{parts.query}"
    return parts.scheme, host, port, path


def fetch_url(url: str) -> FetchedPage:
    """Fetch a public URL safely, following redirects with per-hop re-screening.

    Raises UnsafeUrlError for disallowed targets and UrlUnreachableError for
    network failures, non-2xx responses, or exceeding the redirect budget.
    """
    current = url
    for _ in range(MAX_REDIRECTS + 1):
        scheme, host, port, path = _validate_target(current)
        ip = _resolve_and_screen(host, port)
        try:
            status, body, location = _request(scheme, host, ip, port, path)
        except (OSError, http.client.HTTPException) as exc:
            raise UrlUnreachableError(f"Fetch failed: {exc}") from exc

        if status in _REDIRECT_CODES and location:
            current = urljoin(current, location)
            continue
        if not 200 <= status < 300:
            raise UrlUnreachableError(f"HTTP {status}")
        logger.info("Fetched %s (%s)", host, status)
        return FetchedPage(html=body, final_url=current)

    raise UrlUnreachableError("Too many redirects")

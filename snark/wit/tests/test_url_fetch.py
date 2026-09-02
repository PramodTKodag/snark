"""Tests for the SSRF-safe URL fetcher (wit.url_fetch).

The security-critical behaviour (scheme/port allowlists, private-IP screening,
DNS-rebinding defence, redirect re-validation, and resource caps) is exercised
here with loopback stubs and patched DNS resolution — never real external hosts.
"""

import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from unittest.mock import patch

import pytest
from wit.url_fetch import (
    MAX_BYTES,
    FetchedPage,
    UnsafeUrlError,
    UrlUnreachableError,
    _request,
    fetch_url,
)


def _addrinfo(ip):
    """Build a socket.getaddrinfo-shaped result resolving to a single IP."""
    family = 10 if ":" in ip else 2  # AF_INET6 / AF_INET
    return [(family, 1, 6, "", (ip, 80))]


class TestSchemeAndPortScreening:
    @pytest.mark.parametrize(
        "url", ["ftp://example.com", "file:///etc/passwd", "gopher://x"]
    )
    def test_rejects_non_http_scheme(self, url):
        with pytest.raises(UnsafeUrlError):
            fetch_url(url)

    def test_rejects_missing_scheme(self):
        with pytest.raises(UnsafeUrlError):
            fetch_url("example.com/path")

    def test_rejects_non_web_port(self):
        with pytest.raises(UnsafeUrlError):
            fetch_url("http://example.com:8080/")


class TestPrivateIpScreening:
    @pytest.mark.parametrize(
        "ip",
        [
            "127.0.0.1",  # loopback
            "10.0.0.5",  # RFC1918
            "192.168.1.1",  # RFC1918
            "172.16.0.1",  # RFC1918
            "169.254.169.254",  # link-local / cloud metadata
            "100.64.0.1",  # CGNAT
            "0.0.0.0",  # unspecified
            "::1",  # IPv6 loopback
            "fc00::1",  # IPv6 ULA
            "::ffff:127.0.0.1",  # IPv4-mapped loopback
        ],
    )
    def test_rejects_internal_targets(self, ip):
        with patch("wit.url_fetch.socket.getaddrinfo", return_value=_addrinfo(ip)):
            with pytest.raises(UnsafeUrlError):
                fetch_url("http://internal.example.com/")

    def test_dns_failure_is_unreachable_not_unsafe(self):
        import socket

        with patch("wit.url_fetch.socket.getaddrinfo", side_effect=socket.gaierror):
            with pytest.raises(UrlUnreachableError):
                fetch_url("http://nonexistent.example.com/")


class _StubHandler(BaseHTTPRequestHandler):
    body = b"<html><head><title>hi</title></head></html>"
    status = 200

    def do_GET(self):
        self.send_response(self.status)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(self.body)

    def log_message(self, *args):
        pass  # silence test server logging


class _stub_server:
    """Context manager yielding (ip, port) for a loopback HTTP stub."""

    def __init__(self, body=None, status=200):
        self._body = body
        self._status = status

    def __enter__(self):
        handler = type("H", (_StubHandler,), {})
        if self._body is not None:
            handler.body = self._body
        handler.status = self._status
        self._srv = HTTPServer(("127.0.0.1", 0), handler)
        self._thread = threading.Thread(target=self._srv.serve_forever, daemon=True)
        self._thread.start()
        return self._srv.server_address  # (ip, port)

    def __exit__(self, *exc):
        self._srv.shutdown()
        self._srv.server_close()


class TestTransport:
    """_request performs the pinned HTTP GET; tested against a loopback stub.

    Returns (status, body, location); location is the Location header or None.
    """

    def test_returns_status_and_body(self):
        with _stub_server(body=b"<p>hello</p>") as (ip, port):
            status, body, location = _request("http", "127.0.0.1", ip, port, "/")
        assert status == 200
        assert body == "<p>hello</p>"
        assert location is None

    def test_caps_response_body(self):
        oversized = b"x" * (MAX_BYTES + 5000)
        with _stub_server(body=oversized) as (ip, port):
            _status, body, _loc = _request("http", "127.0.0.1", ip, port, "/")
        assert len(body.encode()) <= MAX_BYTES


class TestFetchOrchestration:
    _PUBLIC = "93.184.216.34"

    def test_happy_path_returns_fetched_page(self):
        with patch(
            "wit.url_fetch.socket.getaddrinfo", return_value=_addrinfo(self._PUBLIC)
        ):
            with patch(
                "wit.url_fetch._request", return_value=(200, "<html>ok</html>", None)
            ):
                page = fetch_url("http://example.com/path")
        assert isinstance(page, FetchedPage)
        assert page.html == "<html>ok</html>"
        assert page.final_url == "http://example.com/path"

    def test_non_2xx_is_unreachable(self):
        with patch(
            "wit.url_fetch.socket.getaddrinfo", return_value=_addrinfo(self._PUBLIC)
        ):
            with patch("wit.url_fetch._request", return_value=(500, "err", None)):
                with pytest.raises(UrlUnreachableError):
                    fetch_url("http://example.com/")

    def test_follows_redirect_and_updates_final_url(self):
        with patch(
            "wit.url_fetch.socket.getaddrinfo", return_value=_addrinfo(self._PUBLIC)
        ):
            with patch(
                "wit.url_fetch._request",
                side_effect=[
                    (302, "", "http://example.com/final"),
                    (200, "<html>done</html>", None),
                ],
            ):
                page = fetch_url("http://example.com/start")
        assert page.final_url == "http://example.com/final"
        assert "done" in page.html

    def test_redirect_to_internal_is_blocked(self):
        def screen_by_host(host, port):
            if host == "169.254.169.254":
                raise UnsafeUrlError("blocked")

        with patch("wit.url_fetch._resolve_and_screen", side_effect=screen_by_host):
            with patch(
                "wit.url_fetch._request",
                return_value=(302, "", "http://169.254.169.254/latest/meta-data/"),
            ):
                with pytest.raises(UnsafeUrlError):
                    fetch_url("http://example.com/start")

    def test_redirect_cap_exceeded(self):
        with patch(
            "wit.url_fetch.socket.getaddrinfo", return_value=_addrinfo(self._PUBLIC)
        ):
            with patch(
                "wit.url_fetch._request",
                return_value=(302, "", "http://example.com/loop"),
            ):
                with pytest.raises(UrlUnreachableError):
                    fetch_url("http://example.com/start")

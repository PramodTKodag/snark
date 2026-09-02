"""Extract a compact page summary from HTML for the roast-url endpoint.

Uses only the Python standard library (``html.parser``), so no dependency is
added. Prefers Open Graph tags and falls back to ``<title>`` and the meta
description. All extracted text is treated as untrusted: control characters are
stripped and each field is length-capped before it reaches the model.
"""

import unicodedata
from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import urlsplit

TITLE_MAX = 200
DESCRIPTION_MAX = 500
SITE_NAME_MAX = 100
TYPE_MAX = 50


@dataclass(frozen=True)
class PageSummary:
    """Structured, sanitized metadata extracted from a page."""

    title: str
    description: str
    site_name: str
    type: str


class _MetaParser(HTMLParser):
    """Collect meta tags (first value wins) and the document title text."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.metas: dict[str, str] = {}
        self._in_title = False
        self._title_parts: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag == "meta":
            attr = dict(attrs)
            key = (attr.get("property") or attr.get("name") or "").lower()
            if key and "content" in attr and key not in self.metas:
                self.metas[key] = attr["content"] or ""
        elif tag == "title":
            self._in_title = True

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self._title_parts.append(data)

    @property
    def title_text(self) -> str:
        return "".join(self._title_parts)


def _clean(value: str, limit: int) -> str:
    """Strip control characters and trailing/leading whitespace, then cap length."""
    text = "".join(ch for ch in value if unicodedata.category(ch)[0] != "C").strip()
    return text[:limit]


def extract_summary(html: str) -> PageSummary:
    """Parse HTML into a sanitized PageSummary, degrading gracefully on garbage."""
    parser = _MetaParser()
    try:
        parser.feed(html)
    except Exception:  # pragma: no cover - html.parser is lenient; defensive only
        pass

    metas = parser.metas
    title = metas.get("og:title") or parser.title_text
    description = metas.get("og:description") or metas.get("description") or ""
    return PageSummary(
        title=_clean(title, TITLE_MAX),
        description=_clean(description, DESCRIPTION_MAX),
        site_name=_clean(metas.get("og:site_name") or "", SITE_NAME_MAX),
        type=_clean(metas.get("og:type") or "", TYPE_MAX),
    )


def build_roast_context(summary: PageSummary, final_url: str) -> str:
    """Turn a page summary into a compact roast prompt."""
    host = urlsplit(final_url).hostname or final_url
    parts = [f"URL: {final_url}", f"host: {host}"]
    if summary.site_name:
        parts.append(f"site: {summary.site_name}")
    if summary.title:
        parts.append(f"title: {summary.title}")
    if summary.description:
        parts.append(f"description: {summary.description}")
    if summary.type:
        parts.append(f"type: {summary.type}")
    return (
        "Roast this web page based on its public metadata. Be playful and clever "
        "about what it actually is. Details — " + ", ".join(parts) + "."
    )

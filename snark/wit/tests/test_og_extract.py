"""Tests for the pure HTML metadata extractor (wit.og_extract)."""

from wit.og_extract import (
    DESCRIPTION_MAX,
    TITLE_MAX,
    PageSummary,
    build_roast_context,
    extract_summary,
)


class TestExtractSummary:
    def test_prefers_open_graph_tags(self):
        html = """
        <html><head>
          <meta property="og:title" content="Cool Project">
          <meta property="og:description" content="A very cool thing">
          <meta property="og:site_name" content="ProductHunt">
          <meta property="og:type" content="website">
          <title>ignored when og:title present</title>
        </head></html>
        """
        summary = extract_summary(html)
        assert summary.title == "Cool Project"
        assert summary.description == "A very cool thing"
        assert summary.site_name == "ProductHunt"
        assert summary.type == "website"

    def test_falls_back_to_title_and_meta_description(self):
        html = """
        <html><head>
          <title>Plain Page</title>
          <meta name="description" content="Plain description">
        </head></html>
        """
        summary = extract_summary(html)
        assert summary.title == "Plain Page"
        assert summary.description == "Plain description"
        assert summary.site_name == ""
        assert summary.type == ""

    def test_decodes_html_entities(self):
        html = '<meta property="og:title" content="Tom &amp; Jerry">'
        assert extract_summary(html).title == "Tom & Jerry"

    def test_truncates_long_fields(self):
        long_title = "t" * (TITLE_MAX + 50)
        long_desc = "d" * (DESCRIPTION_MAX + 50)
        html = (
            f'<meta property="og:title" content="{long_title}">'
            f'<meta property="og:description" content="{long_desc}">'
        )
        summary = extract_summary(html)
        assert len(summary.title) == TITLE_MAX
        assert len(summary.description) == DESCRIPTION_MAX

    def test_strips_control_characters(self):
        html = '<meta property="og:title" content="a\x00b\x07c">'
        assert extract_summary(html).title == "abc"

    def test_malformed_html_degrades_gracefully(self):
        summary = extract_summary("<html><head><meta property=og:title")
        assert isinstance(summary, PageSummary)
        assert summary.title == ""


class TestBuildRoastContext:
    def test_includes_available_fields_and_host(self):
        summary = PageSummary(
            title="Cool Project",
            description="A very cool thing",
            site_name="ProductHunt",
            type="website",
        )
        ctx = build_roast_context(summary, "https://www.example.com/cool")
        assert "Cool Project" in ctx
        assert "A very cool thing" in ctx
        assert "example.com" in ctx
        assert "roast" in ctx.lower()

    def test_handles_empty_summary(self):
        ctx = build_roast_context(PageSummary("", "", "", ""), "https://example.com/")
        assert "example.com" in ctx
        assert "roast" in ctx.lower()

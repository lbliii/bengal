"""Tests for rendering-side page operation helpers."""

from __future__ import annotations

from pathlib import Path

from bengal.core.page import Page
from bengal.rendering.page_operations import extract_links, has_shortcode


def _page(content: str = "", html: str | None = None) -> Page:
    return Page(
        source_path=Path("content/docs/page.md"),
        _raw_content=content,
        _raw_metadata={"title": "Page"},
        html_content=html,
    )


def test_extract_links_ignores_markdown_inside_code() -> None:
    page = _page(
        "\n".join(
            [
                "[real](/real)",
                "`[inline](/inline)`",
                "```",
                "[code](/code)",
                "```",
                "[other](/other)",
            ]
        )
    )

    assert extract_links(page) == ["/real", "/other"]
    assert page.links == ["/real", "/other"]


def test_extract_links_uses_plugin_wikilinks_and_merges_directive_links() -> None:
    page = _page("[markdown](/markdown) [[docs/page]]", '<a href="/directive">Directive</a>')
    page._directive_links = ["/directive", "/markdown"]

    assert extract_links(page, plugin_links=["/resolved-wiki"]) == [
        "/markdown",
        "/resolved-wiki",
        "/directive",
    ]


def test_extract_links_falls_back_to_rendered_html() -> None:
    page = _page("", '<a href="/ok">OK</a><span class="broken-ref" data-ref="missing"></span>')

    assert extract_links(page) == ["/ok", "missing"]


def test_page_extract_links_shim_delegates_to_rendering_service() -> None:
    page = _page("[guide](/guide)")

    assert page.extract_links() == ["/guide"]


def test_page_has_shortcode_shim_delegates_to_rendering_service() -> None:
    page = _page("Text {{< tip >}}Hint{{< /tip >}}")

    assert has_shortcode(page, "tip") is True
    assert page.HasShortcode("tip") is True
    assert page.HasShortcode("audio") is False

"""Tests for rendered internal reference resolution."""

from __future__ import annotations

from bengal.rendering.reference_resolution import (
    base_url_from_page_url,
    resolve_internal_link,
    resolved_path_url_variants,
)


def test_directory_url_resolves_dot_slash_links_within_same_directory():
    assert (
        resolve_internal_link("/docs/get-started/", "./quickstart-writer")
        == "/docs/get-started/quickstart-writer"
    )


def test_file_style_url_resolves_relative_links_against_parent():
    assert resolve_internal_link("/docs/page.html", "./next") == "/docs/next"


def test_markdown_source_links_normalize_to_clean_urls():
    assert resolve_internal_link("/docs/", "./guide.md") == "/docs/guide"
    assert resolve_internal_link("/docs/", "./reference/_index.md") == "/docs/reference"


def test_base_url_from_page_url_uses_browser_semantics():
    assert base_url_from_page_url("/docs/get-started/") == "/docs/get-started/"
    assert base_url_from_page_url("/docs/page.html") == "/docs/"


def test_resolved_path_url_variants_handles_root():
    assert resolved_path_url_variants("/") == ("/", "/", "/")

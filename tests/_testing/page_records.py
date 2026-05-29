"""Canonical immutable page-record fixtures for tests.

These helpers keep tests aligned with the Page migration adapters instead of
recreating mutable ``Page`` construction rules in each test module.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any

from bengal.cache.parsed_output import apply_parsed_page_to_page
from bengal.content.discovery.page_adapter import page_from_source_page
from bengal.core.records import (
    ParsedPage,
    RenderedPage,
    SourcePage,
    build_page_core,
    build_source_page,
    parsed_page_from_page_state,
    rendered_page_from_page_state,
)

if TYPE_CHECKING:
    from bengal.core.page import Page
    from bengal.core.page.page_core import PageCore


def make_page_core(**overrides: Any) -> PageCore:
    """Create a representative ``PageCore`` for unit tests."""
    metadata = {
        "title": "Hello World",
        "tags": ["python", "web"],
        "slug": "hello",
        "type": "post",
    }
    metadata.update(overrides.pop("metadata", {}))
    return build_page_core(
        overrides.pop("source_path", "content/posts/hello.md"),
        metadata,
        file_hash=overrides.pop("file_hash", "file123"),
        **overrides,
    )


def make_source_page(**overrides: Any) -> SourcePage:
    """Create a representative ``SourcePage`` for unit tests."""
    metadata = {
        "title": "Hello World",
        "tags": ["python", "web"],
        "slug": "hello",
        "type": "post",
    }
    metadata.update(overrides.pop("metadata", {}))
    translation_key = overrides.pop("translation_key", None)
    if translation_key is not None:
        metadata["translation_key"] = translation_key
    return build_source_page(
        source_path=overrides.pop("source_path", "content/posts/hello.md"),
        raw_content=overrides.pop("raw_content", "# Hello\n\nWorld"),
        metadata=metadata,
        content_hash=overrides.pop("content_hash", "body123"),
        file_hash=overrides.pop("file_hash", "file123"),
        is_virtual=overrides.pop("is_virtual", False),
        **overrides,
    )


def make_test_page(
    *,
    html_content: str | None = None,
    site: Any | None = None,
    section: Any | None = None,
    **overrides: Any,
) -> Page:
    """Create a Page compatibility object through the SourcePage adapter."""
    source_page = make_source_page(**overrides)
    page = page_from_source_page(source_page, site=site, section=section)
    if html_content is not None:
        apply_parsed_page_to_page(
            page,
            make_parsed_page(html_content=html_content),
            seed_plain_text=False,
        )
    return page


def make_parsed_page(**overrides: Any) -> ParsedPage:
    """Create a representative ``ParsedPage`` for unit tests."""
    page = SimpleNamespace(
        html_content=overrides.pop("html_content", "<h1>Hello</h1>"),
        toc=overrides.pop("toc", ""),
        excerpt=overrides.pop("excerpt", "Hello"),
        meta_description=overrides.pop("meta_description", "Hello"),
        description=overrides.pop("description", ""),
        plain_text=overrides.pop("plain_text", "Hello"),
        word_count=overrides.pop("word_count", 1),
        reading_time=overrides.pop("reading_time", 1),
        links=overrides.pop("links", ["/docs/"]),
        _ast_cache=overrides.pop("ast_cache", None),
    )
    return parsed_page_from_page_state(
        page,
        toc_items=overrides.pop("toc_items", ()),
        **overrides,
    )


def seed_parsed_page_state(
    page: Any,
    parsed_page: ParsedPage | None = None,
    **overrides: Any,
) -> ParsedPage:
    """Seed a page-like test object through the parsed-record adapter."""
    if parsed_page is not None and overrides:
        msg = "pass either parsed_page or parsed page overrides, not both"
        raise ValueError(msg)

    record = parsed_page or make_parsed_page(**overrides)
    apply_parsed_page_to_page(page, record)
    return record


def make_rendered_page(**overrides: Any) -> RenderedPage:
    """Create a representative ``RenderedPage`` for unit tests."""
    page = SimpleNamespace(
        source_path=overrides.pop("source_path", Path("content/posts/hello.md")),
        output_path=overrides.pop("output_path", Path("public/posts/hello/index.html")),
        rendered_html=overrides.pop("rendered_html", "<html>Hello</html>"),
        render_time_ms=overrides.pop("render_time_ms", 1.5),
    )
    return rendered_page_from_page_state(
        page,
        dependencies=overrides.pop("dependencies", ()),
        **overrides,
    )

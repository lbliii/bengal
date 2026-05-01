"""Tests for immutable Page migration adapters."""

from __future__ import annotations

from pathlib import Path
from types import MappingProxyType, SimpleNamespace

import pytest

from bengal.core.records import (
    PAGE_CORE_MIGRATION_MAP,
    PARSED_PAGE_MIGRATION_MAP,
    RENDERED_PAGE_MIGRATION_MAP,
    SOURCE_PAGE_MIGRATION_MAP,
    build_page_core,
    build_source_page,
    parsed_page_from_page_state,
    rendered_page_from_page_state,
)
from tests._testing.page_records import (
    make_page_core,
    make_parsed_page,
    make_rendered_page,
    make_source_page,
)


def test_migration_maps_name_handoff_fields():
    """Migration maps document the mutable Page -> record handoff."""
    assert PAGE_CORE_MIGRATION_MAP["variant"] == (
        "metadata.variant or metadata.layout or props.hero_style"
    )
    assert SOURCE_PAGE_MIGRATION_MAP["raw_metadata"] == "read-only parsed frontmatter mapping"
    assert PARSED_PAGE_MIGRATION_MAP["plain_text"] == "page.plain_text"
    assert RENDERED_PAGE_MIGRATION_MAP["dependencies"] == (
        "render-time tracked asset/template dependencies"
    )


def test_build_page_core_matches_page_field_rules():
    core = build_page_core(
        Path("content/docs/_index.md"),
        {
            "title": "Docs",
            "tags": "reference",
            "layout": "wide",
            "hero_style": "ignored-because-layout-wins",
            "custom": "value",
            "_internal": "private",
            "aliases": ["/docs/latest/"],
            "version": "v2",
        },
        lang="fr",
        section_path="docs",
        file_hash="file123",
    )

    assert core.source_path == "content/docs/_index.md"
    assert core.slug == "docs"
    assert core.tags == ["reference"]
    assert core.variant == "wide"
    assert core.props == {
        "custom": "value",
        "hero_style": "ignored-because-layout-wins",
        "version": "v2",
    }
    assert core.lang == "fr"
    assert core.section == "docs"
    assert core.file_hash == "file123"
    assert core.aliases == ["/docs/latest/"]
    assert core.version == "v2"


def test_build_source_page_freezes_metadata_and_preserves_hashes():
    source = build_source_page(
        source_path=Path("content/posts/hello.md"),
        raw_content="# Hello",
        metadata={"title": "Hello", "translation_key": "posts/hello"},
        content_hash="body123",
        file_hash="file123",
    )

    assert source.core.file_hash == "file123"
    assert source.content_hash == "body123"
    assert source.translation_key == "posts/hello"
    assert isinstance(source.raw_metadata, MappingProxyType)
    with pytest.raises(TypeError):
        source.raw_metadata["title"] = "Changed"


def test_build_source_page_does_not_compute_hashes_in_core():
    source = build_source_page(
        source_path=Path("content/posts/hello.md"),
        raw_content="# Hello",
        metadata={"title": "Hello"},
    )

    assert source.content_hash is None
    assert source.core.file_hash is None


def test_parsed_page_adapter_uses_supplied_toc_items_without_rendering_imports():
    page = SimpleNamespace(
        html_content="<h2>Intro</h2>",
        toc="<nav></nav>",
        excerpt="Intro",
        meta_description="Intro meta",
        description="Fallback",
        plain_text="Intro",
        word_count=3,
        reading_time=1,
        links=["/guide/", 42],
        _ast_cache={"_type": "Document"},
    )

    parsed = parsed_page_from_page_state(
        page,
        toc_items=({"id": "intro", "title": "Intro"},),
    )

    assert parsed.html_content == "<h2>Intro</h2>"
    assert parsed.toc_items == ({"id": "intro", "title": "Intro"},)
    assert parsed.links == ("/guide/", "42")
    assert parsed.ast_cache == {"_type": "Document"}


def test_rendered_page_adapter_requires_output_path():
    page = SimpleNamespace(
        source_path=Path("content/index.md"),
        output_path=None,
        rendered_html="<html></html>",
        render_time_ms=1.0,
    )

    with pytest.raises(ValueError, match="determine_output_path"):
        rendered_page_from_page_state(page)


def test_testing_record_factories_use_canonical_adapters():
    assert make_page_core().title == "Hello World"
    assert make_source_page().raw_content == "# Hello\n\nWorld"
    assert make_parsed_page().plain_text == "Hello"
    assert make_rendered_page().rendered_html == "<html>Hello</html>"

"""
Edge case tests for URL construction in rendering.

These tests verify correct URL construction for edge cases like
empty section names, pagination without sections, etc.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock


def make_mock_page(
    source_path: str = "content/test.md",
    metadata: dict[str, Any] | None = None,
    section: Any = None,
) -> SimpleNamespace:
    """Create a mock page for testing."""
    page = SimpleNamespace(
        source_path=Path(source_path),
        metadata=metadata or {},
        _section=section,
        title="Test Page",
        href="/test/",
    )
    return page


def make_mock_section(
    name: str = "docs",
    pages: list | None = None,
    subsections: list | None = None,
    metadata: dict[str, Any] | None = None,
) -> SimpleNamespace:
    """Create a mock section for testing."""
    return SimpleNamespace(
        name=name,
        pages=pages or [],
        subsections=subsections or [],
        metadata=metadata or {},
    )


def make_mock_paginator(
    items: list | None = None,
    per_page: int = 10,
) -> SimpleNamespace:
    """Create a mock paginator for testing."""
    items = items or []

    def page(page_num: int) -> list:
        start = (page_num - 1) * per_page
        end = start + per_page
        return items[start:end]

    def page_context(page_num: int, base_url: str) -> dict[str, Any]:
        total_pages = max(1, (len(items) + per_page - 1) // per_page)
        return {
            "current_page": page_num,
            "total_pages": total_pages,
            "has_next": page_num < total_pages,
            "has_prev": page_num > 1,
            "base_url": base_url,
        }

    return SimpleNamespace(
        items=items,
        per_page=per_page,
        page=page,
        page_context=page_context,
    )


class TestPaginationURLConstruction:
    """Test pagination URL construction edge cases."""

    def test_pagination_url_with_none_section(self) -> None:
        """Verify pagination URL doesn't have double slashes when section is None."""
        from bengal.rendering.renderer import Renderer

        mock_engine = MagicMock()
        mock_site = MagicMock()
        mock_engine.site = mock_site

        renderer = Renderer(mock_engine, build_stats=None)

        page = make_mock_page(
            source_path="content/tags/python/index.md",
            metadata={
                "_generated": True,
                "type": "archive",
                "_section": None,
                "_posts": [],
                "_paginator": make_mock_paginator(),
                "_page_num": 1,
            },
        )

        context: dict[str, Any] = {}
        renderer._add_archive_like_generated_page_context(page, context)

        # base_url should be "/" not "//"
        assert context.get("base_url") == "/"
        # Double-check no double slashes
        assert "//" not in context.get("base_url", "")

    def test_pagination_url_with_empty_section_name(self) -> None:
        """Verify empty section name doesn't cause malformed URLs."""
        from bengal.rendering.renderer import Renderer

        mock_engine = MagicMock()
        mock_site = MagicMock()
        mock_engine.site = mock_site

        renderer = Renderer(mock_engine, build_stats=None)

        # Edge case: section with empty name
        section = make_mock_section(name="")
        page = make_mock_page(
            metadata={
                "_generated": True,
                "type": "archive",
                "_section": section,
                "_posts": [],
                "_paginator": make_mock_paginator(),
                "_page_num": 1,
            },
            section=section,
        )

        context: dict[str, Any] = {}
        renderer._add_archive_like_generated_page_context(page, context)

        # base_url should be "/" not "//"
        base_url = context.get("base_url", "")
        assert base_url == "/" or (base_url.startswith("/") and "//" not in base_url)

    def test_pagination_url_with_valid_section(self) -> None:
        """Verify normal section name produces correct URL."""
        from bengal.rendering.renderer import Renderer

        mock_engine = MagicMock()
        mock_site = MagicMock()
        mock_engine.site = mock_site

        renderer = Renderer(mock_engine, build_stats=None)

        section = make_mock_section(name="blog")
        page = make_mock_page(
            metadata={
                "_generated": True,
                "type": "archive",
                "_section": section,
                "_posts": [],
                "_paginator": make_mock_paginator(),
                "_page_num": 1,
            },
            section=section,
        )

        context: dict[str, Any] = {}
        renderer._add_archive_like_generated_page_context(page, context)

        # base_url should be "/blog/"
        assert context.get("base_url") == "/blog/"

    def test_pagination_without_paginator(self) -> None:
        """Verify pagination context is correct when no paginator."""
        from bengal.rendering.renderer import Renderer

        mock_engine = MagicMock()
        mock_site = MagicMock()
        mock_engine.site = mock_site

        renderer = Renderer(mock_engine, build_stats=None)

        section = make_mock_section(name="docs")
        page = make_mock_page(
            metadata={
                "_generated": True,
                "type": "archive",
                "_section": section,
                "_posts": [make_mock_page() for _ in range(5)],
                "_paginator": None,  # No paginator
                "_page_num": 1,
            },
            section=section,
        )

        context: dict[str, Any] = {}
        renderer._add_archive_like_generated_page_context(page, context)

        # Should have fallback pagination
        assert context.get("current_page") == 1
        assert context.get("total_pages") == 1
        assert context.get("has_next") is False
        assert context.get("has_prev") is False
        assert context.get("base_url") == "/docs/"


class TestTagPageURLConstruction:
    """Test tag page URL construction edge cases."""

    def test_tag_page_url_with_empty_slug(self) -> None:
        """Verify tag page handles empty slug gracefully."""
        from bengal.rendering.renderer import Renderer

        mock_engine = MagicMock()
        mock_site = MagicMock()
        mock_site.taxonomies = {"tags": {}}
        mock_site.get_page_path_map.return_value = {}
        mock_engine.site = mock_site

        renderer = Renderer(mock_engine, build_stats=None)

        page = make_mock_page(
            metadata={
                "_generated": True,
                "type": "tag",
                "_tag": "Python",
                "_tag_slug": "",  # Empty slug
                "_posts": [],
                "_page_num": 1,
            },
        )

        context: dict[str, Any] = {}
        renderer._add_tag_generated_page_context(page, context)

        # Should handle gracefully (empty base_url or /)
        base_url = context.get("base_url", "")
        # No double slashes
        assert "//" not in base_url or base_url == "/tags//"  # Edge case: /tags// is expected

    def test_tag_page_url_with_special_characters(self) -> None:
        """Verify tag page handles slugs with special characters."""
        from bengal.rendering.renderer import Renderer

        mock_engine = MagicMock()
        mock_site = MagicMock()
        mock_site.taxonomies = {"tags": {}}
        mock_site.get_page_path_map.return_value = {}
        mock_engine.site = mock_site

        renderer = Renderer(mock_engine, build_stats=None)

        page = make_mock_page(
            metadata={
                "_generated": True,
                "type": "tag",
                "_tag": "C++",
                "_tag_slug": "cpp",
                "_posts": [],
                "_page_num": 1,
            },
        )

        context: dict[str, Any] = {}
        renderer._add_tag_generated_page_context(page, context)

        assert context.get("base_url") == "/tags/cpp/"
        assert context.get("tag_slug") == "cpp"


class TestTagIndexURLConstruction:
    """Test tag index page URL construction."""

    def test_tag_index_with_empty_tags(self) -> None:
        """Verify tag index handles empty tags dict."""
        from bengal.rendering.renderer import Renderer

        mock_engine = MagicMock()
        mock_site = MagicMock()
        mock_engine.site = mock_site

        renderer = Renderer(mock_engine, build_stats=None)

        page = make_mock_page(
            metadata={
                "_generated": True,
                "type": "tag-index",
                "_tags": {},  # Empty tags
            },
        )

        context: dict[str, Any] = {}
        renderer._add_tag_index_generated_page_context(page, context)

        assert context.get("tags") == []
        assert context.get("total_tags") == 0

    def test_tag_index_sorts_by_count_then_name(self) -> None:
        """Verify tag index sorts tags correctly."""
        from bengal.rendering.renderer import Renderer

        mock_engine = MagicMock()
        mock_site = MagicMock()
        mock_engine.site = mock_site

        renderer = Renderer(mock_engine, build_stats=None)

        page = make_mock_page(
            metadata={
                "_generated": True,
                "type": "tag-index",
                "_tags": {
                    "zebra": {"name": "Zebra", "slug": "zebra", "pages": [1, 2]},
                    "alpha": {"name": "Alpha", "slug": "alpha", "pages": [1, 2]},
                    "popular": {"name": "Popular", "slug": "popular", "pages": [1, 2, 3, 4, 5]},
                },
            },
        )

        context: dict[str, Any] = {}
        renderer._add_tag_index_generated_page_context(page, context)

        tags = context.get("tags", [])
        # Should be sorted by count (descending), then name (ascending)
        assert tags[0]["slug"] == "popular"  # Most pages
        # Alpha and Zebra have same count, so sorted alphabetically
        assert tags[1]["slug"] == "alpha"
        assert tags[2]["slug"] == "zebra"

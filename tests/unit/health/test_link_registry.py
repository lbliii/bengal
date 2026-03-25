"""Tests for the shared LinkRegistry.

Tests bengal/health/link_registry.py:
- build_link_registry: builds immutable registry from site
- LinkRegistry: frozen dataclass with correct fields
- Anchor population from toc_items
- Auxiliary URL generation
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from bengal.health.link_registry import LinkRegistry, build_link_registry


@pytest.fixture
def mock_site(tmp_path):
    """Create a mock site with pages that have toc_items."""
    site = MagicMock()
    site.root_path = tmp_path
    site.config = {}

    # Create content directory structure for content_key resolution
    content_dir = tmp_path / "content"
    content_dir.mkdir()
    (content_dir / "docs").mkdir()
    (content_dir / "docs" / "_index.md").touch()
    (content_dir / "about.md").touch()

    page1 = MagicMock()
    page1.href = "/docs/"
    page1._path = "/docs/"
    page1.permalink = None
    page1.source_path = Path("content/docs/_index.md")
    page1.toc_items = [
        {"id": "introduction", "title": "Introduction", "level": 1},
        {"id": "getting-started", "title": "Getting Started", "level": 1},
        {"id": "advanced-usage", "title": "Advanced Usage", "level": 2},
    ]
    page1.links = []

    page2 = MagicMock()
    page2.href = "/about/"
    page2._path = "/about/"
    page2.permalink = None
    page2.source_path = Path("content/about.md")
    page2.toc_items = [
        {"id": "team", "title": "Team", "level": 1},
    ]
    page2.links = []

    page3 = MagicMock()
    page3.href = "/empty/"
    page3._path = "/empty/"
    page3.permalink = None
    page3.source_path = Path("content/empty.md")
    page3.toc_items = []
    page3.links = []

    site.pages = [page1, page2, page3]
    return site


class TestBuildLinkRegistry:
    """Tests for build_link_registry()."""

    def test_returns_frozen_dataclass(self, mock_site):
        """Registry is immutable."""
        registry = build_link_registry(mock_site)
        assert isinstance(registry, LinkRegistry)
        with pytest.raises(AttributeError):
            registry.page_urls = frozenset()  # type: ignore[misc]

    def test_page_urls_include_slash_variants(self, mock_site):
        """Page URLs include both with and without trailing slash."""
        registry = build_link_registry(mock_site)
        assert "/docs/" in registry.page_urls
        assert "/docs" in registry.page_urls
        assert "/about/" in registry.page_urls
        assert "/about" in registry.page_urls

    def test_source_paths_populated(self, mock_site):
        """Source paths are collected from pages."""
        registry = build_link_registry(mock_site)
        assert len(registry.source_paths) > 0

    def test_anchors_populated_from_toc_items(self, mock_site):
        """Anchors are extracted from page.toc_items."""
        registry = build_link_registry(mock_site)

        # Check docs page anchors (indexed by _path)
        docs_anchors = registry.anchors_by_url.get("/docs/")
        assert docs_anchors is not None
        assert "introduction" in docs_anchors
        assert "getting-started" in docs_anchors
        assert "advanced-usage" in docs_anchors

        # Check about page anchors
        about_anchors = registry.anchors_by_url.get("/about/")
        assert about_anchors is not None
        assert "team" in about_anchors

    def test_no_anchors_for_empty_toc(self, mock_site):
        """Pages with empty toc_items have no anchor entry."""
        registry = build_link_registry(mock_site)
        # /empty/ has no toc_items, so no entry in anchors_by_url
        assert registry.anchors_by_url.get("/empty/") is None

    def test_anchors_indexed_by_slash_variants(self, mock_site):
        """Anchors are accessible with and without trailing slash."""
        registry = build_link_registry(mock_site)
        assert registry.anchors_by_url.get("/docs/") is not None
        assert registry.anchors_by_url.get("/docs") is not None

    def test_auxiliary_urls_empty_when_llm_txt_disabled(self, mock_site):
        """No auxiliary URLs when output_formats not configured."""
        registry = build_link_registry(mock_site)
        assert len(registry.auxiliary_urls) == 0

    def test_auxiliary_urls_populated_when_llm_txt_enabled(self, mock_site):
        """index.txt URLs generated when llm_txt enabled."""
        mock_site.config = {"output_formats": {"enabled": True, "per_page": ["llm_txt"]}}
        registry = build_link_registry(mock_site)
        assert "/docs/index.txt" in registry.auxiliary_urls
        assert "/about/index.txt" in registry.auxiliary_urls

    def test_permalink_included(self, mock_site):
        """Permalinks are included in page_urls."""
        mock_site.pages[0].permalink = "/custom-docs/"
        registry = build_link_registry(mock_site)
        assert "/custom-docs/" in registry.page_urls
        assert "/custom-docs" in registry.page_urls


class TestLinkRegistryImmutability:
    """Tests that LinkRegistry fields are truly immutable."""

    def test_page_urls_is_frozenset(self, mock_site):
        registry = build_link_registry(mock_site)
        assert isinstance(registry.page_urls, frozenset)

    def test_source_paths_is_frozenset(self, mock_site):
        registry = build_link_registry(mock_site)
        assert isinstance(registry.source_paths, frozenset)

    def test_auxiliary_urls_is_frozenset(self, mock_site):
        registry = build_link_registry(mock_site)
        assert isinstance(registry.auxiliary_urls, frozenset)

    def test_anchors_values_are_frozensets(self, mock_site):
        registry = build_link_registry(mock_site)
        for anchors in registry.anchors_by_url.values():
            assert isinstance(anchors, frozenset)

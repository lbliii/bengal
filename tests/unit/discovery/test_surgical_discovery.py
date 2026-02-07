"""
Tests for surgical discovery cache handling.

These tests verify that surgical discovery (incremental builds with caching):
- Returns PageProxy on cache hit
- Returns None on cache miss (signaling caller to parse)
- Doesn't double-parse pages
- Handles executor vs non-executor paths correctly
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from bengal.content.discovery.content_discovery import ContentDiscovery
from bengal.core.page import Page, PageProxy
from bengal.core.page.page_core import PageCore


def make_page_core(source_path: str | Path, title: str, *, weight: int | None = None) -> PageCore:
    """Helper to create a PageCore for testing."""
    return PageCore(
        source_path=str(source_path),
        title=title,
        weight=weight,
    )


@pytest.fixture
def content_dir(tmp_path: Path) -> Path:
    """Create a temporary content directory with test files."""
    content_dir = tmp_path / "content"
    content_dir.mkdir()

    # Create some content files
    (content_dir / "index.md").write_text("---\ntitle: Home\n---\n# Home")

    docs_dir = content_dir / "docs"
    docs_dir.mkdir()
    (docs_dir / "_index.md").write_text("---\ntitle: Docs\nweight: 1\n---\n# Docs")
    (docs_dir / "getting-started.md").write_text(
        "---\ntitle: Getting Started\nweight: 1\n---\n# Getting Started"
    )
    (docs_dir / "advanced.md").write_text("---\ntitle: Advanced\nweight: 2\n---\n# Advanced")

    return content_dir


@pytest.fixture
def mock_cache() -> MagicMock:
    """Create a mock cache with configurable responses."""
    cache = MagicMock()
    cache.pages = {}
    return cache


class TestSurgicalDiscoveryCacheHit:
    """Tests for cache hit scenarios in surgical discovery."""

    def test_cache_hit_returns_page_proxy(self, content_dir: Path, mock_cache: MagicMock) -> None:
        """When cache has metadata, should return PageProxy without parsing."""
        file_path = content_dir / "docs" / "getting-started.md"
        mock_cache.get_metadata.return_value = make_page_core(file_path, "Cached Title", weight=1)

        discovery = ContentDiscovery(content_dir)

        result = discovery._create_page_surgical(file_path, mock_cache)

        assert result is not None
        assert isinstance(result, PageProxy)
        assert result.title == "Cached Title"

    def test_cache_hit_does_not_read_file(self, content_dir: Path, mock_cache: MagicMock) -> None:
        """Cache hit should not read the file from disk."""
        file_path = content_dir / "docs" / "getting-started.md"
        mock_cache.get_metadata.return_value = make_page_core(file_path, "Cached")

        discovery = ContentDiscovery(content_dir)

        with patch("builtins.open") as mock_open:
            result = discovery._create_page_surgical(file_path, mock_cache)

            # File should not be opened for reading
            mock_open.assert_not_called()
            assert isinstance(result, PageProxy)

    def test_cache_hit_preserves_section_reference(
        self, content_dir: Path, mock_cache: MagicMock
    ) -> None:
        """PageProxy from cache hit should have section set by discovery."""
        file_path = content_dir / "docs" / "getting-started.md"
        str(content_dir / "docs")
        mock_cache.get_metadata.return_value = make_page_core(file_path, "Test")

        from bengal.core.section import Section

        section = Section(name="docs", path=content_dir / "docs")

        discovery = ContentDiscovery(content_dir)

        result = discovery._create_page_surgical(file_path, mock_cache, section=section)

        assert result is not None
        assert isinstance(result, PageProxy)
        # Section is set as the section object by discovery
        assert result._section is section or result._section_path is not None


class TestSurgicalDiscoveryCacheMiss:
    """Tests for cache miss scenarios in surgical discovery."""

    def test_cache_miss_returns_none_when_executor_exists(
        self, content_dir: Path, mock_cache: MagicMock
    ) -> None:
        """When cache misses and executor exists, should return None."""
        mock_cache.get_metadata.return_value = None  # Cache miss

        discovery = ContentDiscovery(content_dir)
        discovery._executor = ThreadPoolExecutor(max_workers=1)

        try:
            file_path = content_dir / "docs" / "getting-started.md"
            result = discovery._create_page_surgical(file_path, mock_cache)

            assert result is None
        finally:
            discovery._executor.shutdown(wait=True)

    def test_cache_miss_without_executor_returns_none(
        self, content_dir: Path, mock_cache: MagicMock
    ) -> None:
        """When cache misses without executor, should also return None."""
        mock_cache.get_metadata.return_value = None

        discovery = ContentDiscovery(content_dir)
        discovery._executor = None  # No executor

        file_path = content_dir / "docs" / "getting-started.md"
        result = discovery._create_page_surgical(file_path, mock_cache)

        # Now returns None to signal caller should handle
        assert result is None


class TestSurgicalDiscoveryNoDoubleParsing:
    """Tests to verify pages aren't parsed twice."""

    def test_walk_directory_surgical_no_double_parsing(
        self, content_dir: Path, mock_cache: MagicMock
    ) -> None:
        """Files should only be parsed once, not double-parsed."""
        # Cache miss for all files
        mock_cache.get_metadata.return_value = None

        discovery = ContentDiscovery(content_dir)

        # Track how many times _create_page is called
        create_page_calls: list[Path] = []
        original_create_page = discovery._create_page

        def tracking_create_page(
            file_path: Path,
            current_lang: str | None = None,
            section: Any = None,
        ) -> Page:
            create_page_calls.append(file_path)
            return original_create_page(file_path, current_lang, section)

        with patch.object(discovery, "_create_page", side_effect=tracking_create_page):
            discovery._discover_surgical(mock_cache)

        # Each file should only be parsed once
        assert len(create_page_calls) == len(set(create_page_calls)), (
            f"Some files were parsed multiple times: {create_page_calls}"
        )

    def test_mixed_cache_hits_and_misses(self, content_dir: Path, mock_cache: MagicMock) -> None:
        """Discovery should handle mix of cache hits and misses."""

        # Set up cache to hit for some files, miss for others
        def get_metadata(path: Path) -> PageCore | None:
            if "getting-started" in str(path):
                return make_page_core(path, "Cached Getting Started")
            return None  # Cache miss for others

        mock_cache.get_metadata.side_effect = get_metadata

        discovery = ContentDiscovery(content_dir)

        # Track parsing
        parsed_files: list[Path] = []
        original_create_page = discovery._create_page

        def tracking_create_page(
            file_path: Path,
            current_lang: str | None = None,
            section: Any = None,
        ) -> Page:
            parsed_files.append(file_path)
            return original_create_page(file_path, current_lang, section)

        with patch.object(discovery, "_create_page", side_effect=tracking_create_page):
            _sections, _pages = discovery._discover_surgical(mock_cache)

        # getting-started should NOT be in parsed_files (cache hit)
        assert not any("getting-started" in str(f) for f in parsed_files)

        # Other files should be parsed
        assert len(parsed_files) > 0


class TestSurgicalDiscoveryExplicitlyChangedFiles:
    """Tests for handling explicitly changed files (hot reload scenario)."""

    def test_explicitly_changed_file_bypasses_cache(
        self, content_dir: Path, mock_cache: MagicMock
    ) -> None:
        """Files marked as changed should be re-parsed even if cached."""
        mock_cache.get_metadata.return_value = {"title": "Stale Cache"}

        # Create a mock site with changed_sources
        mock_site = MagicMock()
        mock_options = MagicMock()
        changed_file = content_dir / "docs" / "getting-started.md"
        mock_options.changed_sources = [changed_file]
        mock_site._last_build_options = mock_options
        mock_site.root_path = content_dir.parent

        discovery = ContentDiscovery(content_dir, site=mock_site)
        discovery._executor = ThreadPoolExecutor(max_workers=1)

        try:
            result = discovery._create_page_surgical(changed_file, mock_cache)

            # Should return None (needs re-parsing) despite cache hit
            assert result is None
        finally:
            discovery._executor.shutdown(wait=True)


class TestSurgicalDiscoveryPageProxyLoader:
    """Tests for PageProxy lazy loading behavior."""

    def test_page_proxy_loader_creates_full_page(
        self, content_dir: Path, mock_cache: MagicMock
    ) -> None:
        """PageProxy loader should create a full Page when called."""
        file_path = content_dir / "docs" / "getting-started.md"
        mock_cache.get_metadata.return_value = make_page_core(file_path, "Cached")

        discovery = ContentDiscovery(content_dir)

        proxy = discovery._create_page_surgical(file_path, mock_cache)

        assert isinstance(proxy, PageProxy)

        # Force load by accessing content (triggers _ensure_loaded)
        proxy._ensure_loaded()
        full_page = proxy._full_page

        assert isinstance(full_page, Page)
        assert full_page.title == "Getting Started"  # From actual file, not cache

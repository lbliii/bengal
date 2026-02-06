"""
Unit tests for bengal.build.provenance.filter.

Tests ProvenanceFilter for incremental filtering and thread safety.
"""

from __future__ import annotations

import threading
from pathlib import Path
from unittest.mock import MagicMock, PropertyMock

import pytest

from bengal.build.contracts.keys import CacheKey
from bengal.build.provenance.filter import ProvenanceFilter, ProvenanceFilterResult
from bengal.build.provenance.store import ProvenanceCache
from bengal.build.provenance.types import ContentHash, Provenance


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def cache_dir(tmp_path: Path) -> Path:
    """Create temp cache directory."""
    return tmp_path / ".bengal" / "provenance"


@pytest.fixture
def provenance_cache(cache_dir: Path) -> ProvenanceCache:
    """Create ProvenanceCache instance."""
    return ProvenanceCache(cache_dir=cache_dir)


@pytest.fixture
def mock_site(tmp_path: Path) -> MagicMock:
    """Create mock Site."""
    site = MagicMock()
    site.root_path = tmp_path / "site"
    site.root_path.mkdir(parents=True)
    site.config = {"title": "Test Site"}
    return site


@pytest.fixture
def provenance_filter(mock_site: MagicMock, provenance_cache: ProvenanceCache) -> ProvenanceFilter:
    """Create ProvenanceFilter instance."""
    return ProvenanceFilter(site=mock_site, cache=provenance_cache)


# =============================================================================
# Basic Filter Tests
# =============================================================================


class TestProvenanceFilterBasics:
    """Basic tests for ProvenanceFilter."""

    def test_creates_with_site_and_cache(
        self, mock_site: MagicMock, provenance_cache: ProvenanceCache
    ) -> None:
        """Filter initializes with site and cache."""
        pf = ProvenanceFilter(site=mock_site, cache=provenance_cache)

        assert pf.site == mock_site
        assert pf.cache == provenance_cache

    def test_filter_empty_pages_returns_empty(self, provenance_filter: ProvenanceFilter) -> None:
        """Filtering empty page list returns empty result."""
        result = provenance_filter.filter(pages=[], assets=[])

        assert result.pages_to_build == []
        assert result.assets_to_process == []
        assert result.pages_skipped == []

    def test_non_incremental_returns_all_pages(
        self, provenance_filter: ProvenanceFilter, mock_site: MagicMock
    ) -> None:
        """Non-incremental mode returns all pages as needing build."""
        page = MagicMock()
        page.source_path = mock_site.root_path / "content" / "about.md"
        page.source_path.parent.mkdir(parents=True, exist_ok=True)
        page.source_path.write_text("# About")
        page.metadata = {}

        result = provenance_filter.filter(
            pages=[page],
            assets=[],
            incremental=False,
        )

        assert len(result.pages_to_build) == 1
        assert result.cache_hits == 0


# =============================================================================
# Cache Hit/Miss Tests
# =============================================================================


class TestCacheHitMiss:
    """Tests for cache hit and miss detection."""

    def test_forced_changed_always_rebuilds(
        self, provenance_filter: ProvenanceFilter, mock_site: MagicMock
    ) -> None:
        """Page in forced_changed set always rebuilds."""
        page = MagicMock()
        page.source_path = mock_site.root_path / "content" / "about.md"
        page.source_path.parent.mkdir(parents=True, exist_ok=True)
        page.source_path.write_text("# About")
        page.metadata = {}
        page._virtual = False

        result = provenance_filter.filter(
            pages=[page],
            assets=[],
            forced_changed={page.source_path},
        )

        assert len(result.pages_to_build) == 1
        assert page.source_path in result.changed_page_paths

    def test_new_page_is_cache_miss(
        self, provenance_filter: ProvenanceFilter, mock_site: MagicMock
    ) -> None:
        """Page not in cache is a cache miss."""
        page = MagicMock()
        page.source_path = mock_site.root_path / "content" / "new.md"
        page.source_path.parent.mkdir(parents=True, exist_ok=True)
        page.source_path.write_text("# New Page")
        page.metadata = {}
        page._virtual = False

        result = provenance_filter.filter(pages=[page], assets=[])

        assert len(result.pages_to_build) == 1
        assert result.cache_misses == 1


# =============================================================================
# File Hash Caching Tests
# =============================================================================


class TestFileHashCaching:
    """Tests for file hash session caching."""

    def test_file_hash_cached_within_session(
        self, provenance_filter: ProvenanceFilter, mock_site: MagicMock
    ) -> None:
        """File hash is computed once and cached within session."""
        page = MagicMock()
        page.source_path = mock_site.root_path / "content" / "about.md"
        page.source_path.parent.mkdir(parents=True, exist_ok=True)
        page.source_path.write_text("# About")
        page.metadata = {}
        page._virtual = False

        # First call computes hash
        hash1 = provenance_filter._get_file_hash(page.source_path)

        # Second call should return cached value
        hash2 = provenance_filter._get_file_hash(page.source_path)

        assert hash1 == hash2
        assert page.source_path in provenance_filter._file_hashes


# =============================================================================
# OSError Handling Tests
# =============================================================================


class TestOSErrorHandling:
    """Tests for OSError handling in file operations."""

    def test_missing_file_returns_none_for_fast_provenance(
        self, provenance_filter: ProvenanceFilter, mock_site: MagicMock
    ) -> None:
        """Missing file returns None from _compute_provenance_fast."""
        page = MagicMock()
        page.source_path = mock_site.root_path / "content" / "nonexistent.md"
        page.metadata = {}
        page._virtual = False

        result = provenance_filter._compute_provenance_fast(page)

        assert result is None

    def test_asset_change_detection_handles_missing_file(
        self, provenance_filter: ProvenanceFilter, mock_site: MagicMock
    ) -> None:
        """Asset change detection returns True for missing file."""
        asset = MagicMock()
        asset.source_path = mock_site.root_path / "static" / "missing.css"

        result = provenance_filter._is_asset_changed(asset)

        assert result is True


# =============================================================================
# Thread Safety Tests
# =============================================================================


class TestProvenanceFilterThreadSafety:
    """Tests for thread safety in ProvenanceFilter."""

    def test_concurrent_file_hash_computation(
        self, provenance_filter: ProvenanceFilter, mock_site: MagicMock
    ) -> None:
        """Concurrent file hash computations are thread-safe."""
        # Create test files
        content_dir = mock_site.root_path / "content"
        content_dir.mkdir(parents=True, exist_ok=True)

        paths = []
        for i in range(10):
            path = content_dir / f"page{i}.md"
            path.write_text(f"# Page {i}")
            paths.append(path)

        results: dict[int, ContentHash] = {}
        errors: list[Exception] = []

        def compute_hash(idx: int, path: Path) -> None:
            try:
                # Each thread computes the same file's hash multiple times
                for _ in range(5):
                    hash_val = provenance_filter._get_file_hash(path)
                    if idx not in results:
                        results[idx] = hash_val
                    else:
                        # Verify consistent results
                        assert results[idx] == hash_val
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=compute_hash, args=(i, paths[i % len(paths)]))
            for i in range(20)
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert not errors, f"Thread errors: {errors}"

    def test_concurrent_provenance_computation(
        self, provenance_filter: ProvenanceFilter, mock_site: MagicMock
    ) -> None:
        """Concurrent provenance computations are thread-safe."""
        # Create test pages
        content_dir = mock_site.root_path / "content"
        content_dir.mkdir(parents=True, exist_ok=True)

        pages = []
        for i in range(5):
            path = content_dir / f"page{i}.md"
            path.write_text(f"# Page {i}")

            page = MagicMock()
            page.source_path = path
            page.metadata = {}
            page._virtual = False
            pages.append(page)

        results: dict[int, Provenance] = {}
        errors: list[Exception] = []

        def compute_provenance(idx: int, page: MagicMock) -> None:
            try:
                prov = provenance_filter._compute_provenance(page)
                results[idx] = prov
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=compute_provenance, args=(i, pages[i % len(pages)]))
            for i in range(20)
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert not errors, f"Thread errors: {errors}"


# =============================================================================
# Virtual Page Tests
# =============================================================================


class TestVirtualPages:
    """Tests for virtual page handling."""

    def test_virtual_page_fast_path_returns_none(
        self, provenance_filter: ProvenanceFilter, mock_site: MagicMock
    ) -> None:
        """Virtual pages return None from fast path."""
        page = MagicMock()
        page.source_path = mock_site.root_path / "_generated" / "tags" / "python.md"
        page.metadata = {"_generated": True}
        page._virtual = True

        result = provenance_filter._compute_provenance_fast(page)

        assert result is None

    def test_virtual_page_uses_full_provenance(
        self, provenance_filter: ProvenanceFilter, mock_site: MagicMock
    ) -> None:
        """Virtual pages use full provenance computation."""
        page = MagicMock()
        page.source_path = mock_site.root_path / "_generated" / "tags" / "python.md"
        page.metadata = {"_generated": True, "template": "tag.html", "title": "Python"}
        page._virtual = True

        prov = provenance_filter._compute_provenance(page)

        # Should have at least config input
        assert prov.input_count >= 1


# =============================================================================
# Result Properties Tests
# =============================================================================


class TestProvenanceFilterResult:
    """Tests for ProvenanceFilterResult dataclass."""

    def test_hit_rate_calculation(self) -> None:
        """hit_rate is calculated correctly."""
        result = ProvenanceFilterResult(
            pages_to_build=[],
            assets_to_process=[],
            pages_skipped=[MagicMock(), MagicMock(), MagicMock()],
            total_pages=10,
            cache_hits=3,
            cache_misses=7,
        )

        assert result.hit_rate == 30.0

    def test_hit_rate_zero_pages(self) -> None:
        """hit_rate returns 0 for zero pages."""
        result = ProvenanceFilterResult(
            pages_to_build=[],
            assets_to_process=[],
            pages_skipped=[],
            total_pages=0,
            cache_hits=0,
            cache_misses=0,
        )

        assert result.hit_rate == 0.0

    def test_is_skip_true_when_nothing_to_build(self) -> None:
        """is_skip is True when no pages or assets need building."""
        result = ProvenanceFilterResult(
            pages_to_build=[],
            assets_to_process=[],
            pages_skipped=[MagicMock()],
        )

        assert result.is_skip is True

    def test_is_skip_false_when_pages_to_build(self) -> None:
        """is_skip is False when pages need building."""
        result = ProvenanceFilterResult(
            pages_to_build=[MagicMock()],
            assets_to_process=[],
            pages_skipped=[],
        )

        assert result.is_skip is False


# =============================================================================
# Cascade Provenance Tests
# =============================================================================


class TestCascadeProvenance:
    """Tests for cascade source tracking in provenance."""

    def test_get_cascade_sources_returns_empty_for_page_without_section(
        self, provenance_filter: ProvenanceFilter, mock_site: MagicMock
    ) -> None:
        """Page without _section returns empty cascade sources."""
        page = MagicMock()
        page.source_path = mock_site.root_path / "content" / "about.md"
        page._section = None

        sources = provenance_filter._get_cascade_sources(page)

        assert sources == []

    def test_get_cascade_sources_returns_index_page_path(
        self, provenance_filter: ProvenanceFilter, mock_site: MagicMock
    ) -> None:
        """Page with section returns section's _index.md path."""
        # Create the index file on disk
        content_dir = mock_site.root_path / "content" / "docs"
        content_dir.mkdir(parents=True, exist_ok=True)
        index_path = content_dir / "_index.md"
        index_path.write_text("---\ncascade:\n  type: doc\n---\n# Docs")

        # Create mock section with index page
        index_page = MagicMock()
        index_page.source_path = index_path

        section = MagicMock()
        section.index_page = index_page
        section.parent = None

        page = MagicMock()
        page.source_path = content_dir / "intro.md"
        page._section = section

        sources = provenance_filter._get_cascade_sources(page)

        assert len(sources) == 1
        assert sources[0] == index_path

    def test_get_cascade_sources_traverses_parent_hierarchy(
        self, provenance_filter: ProvenanceFilter, mock_site: MagicMock
    ) -> None:
        """Page in nested section returns all parent _index.md paths."""
        # Create index files on disk
        docs_dir = mock_site.root_path / "content" / "docs"
        guides_dir = docs_dir / "guides"
        guides_dir.mkdir(parents=True, exist_ok=True)

        docs_index = docs_dir / "_index.md"
        docs_index.write_text("---\ncascade:\n  type: doc\n---\n# Docs")

        guides_index = guides_dir / "_index.md"
        guides_index.write_text("---\ncascade:\n  layout: guide\n---\n# Guides")

        # Create mock parent section
        docs_index_page = MagicMock()
        docs_index_page.source_path = docs_index

        parent_section = MagicMock()
        parent_section.index_page = docs_index_page
        parent_section.parent = None

        # Create mock child section
        guides_index_page = MagicMock()
        guides_index_page.source_path = guides_index

        child_section = MagicMock()
        child_section.index_page = guides_index_page
        child_section.parent = parent_section

        page = MagicMock()
        page.source_path = guides_dir / "intro.md"
        page._section = child_section

        sources = provenance_filter._get_cascade_sources(page)

        # Should return child first, then parent (ordered from immediate to root)
        assert len(sources) == 2
        assert sources[0] == guides_index
        assert sources[1] == docs_index

    def test_cascade_change_changes_provenance_hash(
        self, provenance_filter: ProvenanceFilter, mock_site: MagicMock
    ) -> None:
        """Changing _index.md content changes page provenance hash."""
        # Create content files
        docs_dir = mock_site.root_path / "content" / "docs"
        docs_dir.mkdir(parents=True, exist_ok=True)

        index_path = docs_dir / "_index.md"
        index_path.write_text("---\ncascade:\n  type: doc\n---\n# Docs")

        page_path = docs_dir / "intro.md"
        page_path.write_text("# Introduction")

        # Create mock section
        index_page = MagicMock()
        index_page.source_path = index_path

        section = MagicMock()
        section.index_page = index_page
        section.parent = None

        page = MagicMock()
        page.source_path = page_path
        page.metadata = {}
        page._virtual = False
        page._section = section

        # Compute initial provenance
        prov1 = provenance_filter._compute_provenance(page)
        hash1 = prov1.combined_hash

        # Clear session cache to force recomputation
        provenance_filter._file_hashes.clear()
        provenance_filter._computed_provenance.clear()

        # Change the _index.md content
        index_path.write_text("---\ncascade:\n  type: reference\n---\n# Docs")

        # Compute provenance again
        prov2 = provenance_filter._compute_provenance(page)
        hash2 = prov2.combined_hash

        # Hashes should be different
        assert hash1 != hash2

    def test_fast_path_includes_cascade_sources(
        self, provenance_filter: ProvenanceFilter, mock_site: MagicMock
    ) -> None:
        """Fast path provenance includes cascade source hashes."""
        # Create content files
        docs_dir = mock_site.root_path / "content" / "docs"
        docs_dir.mkdir(parents=True, exist_ok=True)

        index_path = docs_dir / "_index.md"
        index_path.write_text("---\ncascade:\n  type: doc\n---\n# Docs")

        page_path = docs_dir / "intro.md"
        page_path.write_text("# Introduction")

        # Create mock section
        index_page = MagicMock()
        index_page.source_path = index_path

        section = MagicMock()
        section.index_page = index_page
        section.parent = None

        page = MagicMock()
        page.source_path = page_path
        page.metadata = {}
        page._virtual = False
        page._section = section

        # Compute fast-path provenance
        prov = provenance_filter._compute_provenance_fast(page)

        assert prov is not None
        # Should have at least 3 inputs: content, cascade_0, config
        assert prov.input_count >= 3

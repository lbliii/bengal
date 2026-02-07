"""
Tests for AutodocTracker functionality.

Tests the autodoc source file → page dependency tracking used for
selective incremental rebuilds of autodoc pages.
"""

from __future__ import annotations

from pathlib import Path

from bengal.cache.build_cache import BuildCache

DUMMY_HASH = "deadbeef"
DUMMY_MTIME = 1.0


def add_dep(cache: BuildCache, source: str, page: str) -> None:
    cache.autodoc_tracker.add_autodoc_dependency(
        source,
        page,
        source_hash=DUMMY_HASH,
        source_mtime=DUMMY_MTIME,
    )


class TestAutodocTracker:
    """Test autodoc dependency tracking in BuildCache."""

    def test_add_autodoc_dependency(self) -> None:
        """Test registering a dependency between source file and autodoc page."""
        cache = BuildCache()

        add_dep(cache, "bengal/core/page.py", "python/api/bengal/core/page.md")

        assert "bengal/core/page.py" in cache.autodoc_tracker.autodoc_dependencies
        assert (
            "python/api/bengal/core/page.md"
            in cache.autodoc_tracker.autodoc_dependencies["bengal/core/page.py"]
        )

    def test_add_multiple_dependencies_same_source(self) -> None:
        """Test adding multiple pages from the same source file."""
        cache = BuildCache()

        add_dep(cache, "bengal/core/page.py", "python/api/bengal/core/page.md")
        add_dep(cache, "bengal/core/page.py", "python/api/bengal/core/page/proxy.md")

        deps = cache.autodoc_tracker.autodoc_dependencies["bengal/core/page.py"]
        assert len(deps) == 2
        assert "python/api/bengal/core/page.md" in deps
        assert "python/api/bengal/core/page/proxy.md" in deps

    def test_get_affected_autodoc_pages(self) -> None:
        """Test retrieving pages affected by a source file change."""
        cache = BuildCache()

        add_dep(cache, "bengal/core/page.py", "python/api/page.md")
        add_dep(cache, "bengal/core/site.py", "python/api/site.md")

        affected = cache.autodoc_tracker.get_affected_autodoc_pages("bengal/core/page.py")

        assert affected == {"python/api/page.md"}

    def test_get_affected_autodoc_pages_empty(self) -> None:
        """Test getting affected pages for untracked source file."""
        cache = BuildCache()

        affected = cache.autodoc_tracker.get_affected_autodoc_pages("unknown/file.py")

        assert affected == set()

    def test_get_autodoc_source_files(self) -> None:
        """Test getting all tracked source files."""
        cache = BuildCache()

        add_dep(cache, "bengal/core/page.py", "python/api/page.md")
        add_dep(cache, "bengal/core/site.py", "python/api/site.md")

        sources = cache.autodoc_tracker.get_autodoc_source_files()

        assert sources == {"bengal/core/page.py", "bengal/core/site.py"}

    def test_clear_autodoc_dependencies(self) -> None:
        """Test clearing all autodoc dependencies."""
        cache = BuildCache()

        add_dep(cache, "bengal/core/page.py", "python/api/page.md")
        cache.autodoc_tracker.clear_autodoc_dependencies()

        assert cache.autodoc_tracker.autodoc_dependencies == {}

    def test_remove_autodoc_source(self) -> None:
        """Test removing a source file and getting its pages."""
        cache = BuildCache()

        add_dep(cache, "bengal/core/page.py", "python/api/page.md")
        add_dep(cache, "bengal/core/page.py", "python/api/page/proxy.md")

        removed_pages = cache.autodoc_tracker.remove_autodoc_source("bengal/core/page.py")

        assert "bengal/core/page.py" not in cache.autodoc_tracker.autodoc_dependencies
        assert removed_pages == {"python/api/page.md", "python/api/page/proxy.md"}

    def test_remove_autodoc_source_not_found(self) -> None:
        """Test removing a source file that doesn't exist."""
        cache = BuildCache()

        removed_pages = cache.autodoc_tracker.remove_autodoc_source("unknown/file.py")

        assert removed_pages == set()

    def test_autodoc_dependencies_in_stats(self) -> None:
        """Test that autodoc stats are included in get_stats()."""
        cache = BuildCache()

        add_dep(cache, "bengal/core/page.py", "python/api/page.md")
        add_dep(cache, "bengal/core/page.py", "python/api/page/proxy.md")
        add_dep(cache, "bengal/core/site.py", "python/api/site.md")

        stats = cache.get_stats()

        assert stats["autodoc_source_files"] == 2
        assert stats["autodoc_pages_tracked"] == 3


class TestAutodocDependencySerialization:
    """Test autodoc dependencies survive save/load cycle."""

    def test_save_and_load_preserves_dependencies(self, tmp_path: Path) -> None:
        """Test that autodoc dependencies are persisted."""
        cache = BuildCache()
        cache_path = tmp_path / "cache.json"

        add_dep(cache, "bengal/core/page.py", "python/api/page.md")
        add_dep(cache, "bengal/core/site.py", "python/api/site.md")
        cache.save(cache_path, use_lock=False)

        loaded_cache = BuildCache.load(cache_path, use_lock=False)

        assert "bengal/core/page.py" in loaded_cache.autodoc_tracker.autodoc_dependencies
        assert (
            "python/api/page.md"
            in loaded_cache.autodoc_tracker.autodoc_dependencies["bengal/core/page.py"]
        )
        assert "bengal/core/site.py" in loaded_cache.autodoc_tracker.autodoc_dependencies

    def test_load_cache_without_autodoc_dependencies(self, tmp_path: Path) -> None:
        """Test loading a cache that was saved before autodoc tracking was added."""
        cache_path = tmp_path / "cache.json"

        # Save a minimal cache without autodoc_dependencies
        import json

        data = {
            "version": 5,
            "file_hashes": {},
            "file_fingerprints": {},
            "dependencies": {},
            "output_sources": {},
            "taxonomy_deps": {},
            "page_tags": {},
            "tag_to_pages": {},
            "known_tags": [],
            "parsed_content": {},
            "validation_results": {},
            "config_hash": None,
            "last_build": None,
        }
        cache_path.write_text(json.dumps(data))

        loaded_cache = BuildCache.load(cache_path, use_lock=False)

        assert loaded_cache.autodoc_tracker.autodoc_dependencies == {}

    def test_clear_includes_autodoc_dependencies(self) -> None:
        """Test that clear() also clears autodoc dependencies."""
        cache = BuildCache()

        add_dep(cache, "bengal/core/page.py", "python/api/page.md")
        cache.clear()

        assert cache.autodoc_tracker.autodoc_dependencies == {}

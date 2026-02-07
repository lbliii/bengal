"""
Unit tests for IncrementalBuildDebugger taxonomy logic.

Verifies that simulate_change correctly identifies which pages would rebuild
based on taxonomy relationships, without over-reporting unrelated pages.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from bengal.debug import IncrementalBuildDebugger


class TestSimulateChangeTaxonomy:
    """simulate_change must only return related pages, not all taxonomy pages."""

    @pytest.fixture
    def mock_cache_with_taxonomy(self) -> MagicMock:
        """Create mock cache with taxonomy dependencies."""
        cache = MagicMock()
        cache.file_fingerprints = {
            "content/post-a.md": "hash1",
            "content/post-b.md": "hash2",
            "content/post-c.md": "hash3",
            "content/post-d.md": "hash4",
        }
        cache.dependencies = {}
        # post-a and post-b share "python" tag
        # post-c has "rust" tag
        # post-d has both "python" and "rust" tags
        cache.taxonomy_index.taxonomy_deps = {
            "tags/python": ["content/post-a.md", "content/post-b.md", "content/post-d.md"],
            "tags/rust": ["content/post-c.md", "content/post-d.md"],
        }
        return cache

    def test_only_related_taxonomy_pages_returned(
        self,
        mock_cache_with_taxonomy: MagicMock,
    ) -> None:
        """Changing a page should only affect pages sharing its taxonomy terms.

        This test would have failed with the buggy implementation that added
        ALL pages from ALL taxonomy terms unconditionally.
        """
        debugger = IncrementalBuildDebugger(cache=mock_cache_with_taxonomy)

        # Changing post-a should affect:
        # - post-a itself (the changed file)
        # - post-b (shares "python" tag)
        # - post-d (shares "python" tag)
        # Should NOT affect:
        # - post-c (only has "rust" tag, no shared terms with post-a)
        affected = debugger.simulate_change("content/post-a.md")

        assert "content/post-a.md" in affected, "Changed file should rebuild"
        assert "content/post-b.md" in affected, "post-b shares 'python' tag"
        assert "content/post-d.md" in affected, "post-d shares 'python' tag"
        assert "content/post-c.md" not in affected, "post-c has no shared tags with post-a"

    def test_changing_rust_page_only_affects_rust_pages(
        self,
        mock_cache_with_taxonomy: MagicMock,
    ) -> None:
        """Changing post-c (rust only) should not affect python-only pages."""
        debugger = IncrementalBuildDebugger(cache=mock_cache_with_taxonomy)

        affected = debugger.simulate_change("content/post-c.md")

        assert "content/post-c.md" in affected, "Changed file should rebuild"
        assert "content/post-d.md" in affected, "post-d shares 'rust' tag"
        assert "content/post-a.md" not in affected, "post-a has no 'rust' tag"
        assert "content/post-b.md" not in affected, "post-b has no 'rust' tag"

    def test_changing_multi_tag_page_affects_all_related(
        self,
        mock_cache_with_taxonomy: MagicMock,
    ) -> None:
        """Changing post-d (has both tags) should affect all pages sharing either tag."""
        debugger = IncrementalBuildDebugger(cache=mock_cache_with_taxonomy)

        affected = debugger.simulate_change("content/post-d.md")

        # post-d has both python and rust tags, so all pages should be affected
        assert "content/post-d.md" in affected
        assert "content/post-a.md" in affected, "shares 'python' tag"
        assert "content/post-b.md" in affected, "shares 'python' tag"
        assert "content/post-c.md" in affected, "shares 'rust' tag"


class TestSimulateChangeNonContentFiles:
    """Test simulate_change behavior for non-content files."""

    @pytest.fixture
    def mock_cache_with_template_deps(self) -> MagicMock:
        """Create mock cache with template dependencies."""
        cache = MagicMock()
        cache.file_fingerprints = {
            "content/page.md": "hash1",
            "content/other.md": "hash2",
            "templates/base.html": "hash3",
        }
        cache.dependencies = {
            "content/page.md": {"templates/base.html", "templates/page.html"},
            "content/other.md": {"templates/base.html"},
        }
        cache.taxonomy_index.taxonomy_deps = {
            "tags/python": ["content/page.md"],
        }
        return cache

    def test_template_change_skips_taxonomy_logic(
        self,
        mock_cache_with_template_deps: MagicMock,
    ) -> None:
        """Changing a template should NOT trigger taxonomy-based rebuilds.

        Only content files should trigger taxonomy-related rebuilds.
        Templates affect pages through direct dependencies.
        """
        debugger = IncrementalBuildDebugger(cache=mock_cache_with_template_deps)

        affected = debugger.simulate_change("templates/base.html")

        # Should find pages via direct dependencies
        assert "content/page.md" in affected
        assert "content/other.md" in affected

        # Should NOT double-count via taxonomy (only 2 pages, not more)
        assert len(affected) == 2

    def test_non_content_file_does_not_add_taxonomy_pages(
        self,
        mock_cache_with_template_deps: MagicMock,
    ) -> None:
        """Non-md files should not trigger taxonomy-based rebuilds."""
        debugger = IncrementalBuildDebugger(cache=mock_cache_with_template_deps)

        # Change a template file (not .md)
        affected = debugger.simulate_change("templates/page.html")

        # Only pages that directly depend on this template
        assert "content/page.md" in affected
        # other.md doesn't depend on page.html, only base.html
        assert "content/other.md" not in affected


class TestSimulateChangeEmptyTaxonomy:
    """Test behavior when page has no taxonomy terms."""

    def test_page_without_tags_returns_only_self(self) -> None:
        """A page with no tags should only rebuild itself."""
        cache = MagicMock()
        cache.file_fingerprints = {
            "content/standalone.md": "hash1",
            "content/tagged.md": "hash2",
        }
        cache.dependencies = {}
        cache.taxonomy_index.taxonomy_deps = {
            "tags/python": ["content/tagged.md"],
            # standalone.md is not in any taxonomy
        }

        debugger = IncrementalBuildDebugger(cache=cache)
        affected = debugger.simulate_change("content/standalone.md")

        # Only the changed file itself
        assert affected == ["content/standalone.md"]

    def test_empty_taxonomy_deps(self) -> None:
        """Handle cache with no taxonomy dependencies."""
        cache = MagicMock()
        cache.file_fingerprints = {"content/page.md": "hash1"}
        cache.dependencies = {}
        cache.taxonomy_index.taxonomy_deps = {}  # Empty

        debugger = IncrementalBuildDebugger(cache=cache)
        affected = debugger.simulate_change("content/page.md")

        assert affected == ["content/page.md"]


class TestSimulateChangeNoDuplicates:
    """Ensure no duplicate pages in results."""

    def test_no_duplicates_with_overlapping_taxonomy(self) -> None:
        """Pages appearing in multiple terms should only appear once."""
        cache = MagicMock()
        cache.file_fingerprints = {
            "content/post.md": "hash1",
            "content/related.md": "hash2",
        }
        cache.dependencies = {}
        # Both pages share multiple tags
        cache.taxonomy_index.taxonomy_deps = {
            "tags/python": ["content/post.md", "content/related.md"],
            "tags/tutorial": ["content/post.md", "content/related.md"],
            "tags/beginner": ["content/post.md", "content/related.md"],
        }

        debugger = IncrementalBuildDebugger(cache=cache)
        affected = debugger.simulate_change("content/post.md")

        # Count occurrences - each page should appear exactly once
        assert affected.count("content/post.md") == 1
        assert affected.count("content/related.md") == 1


class TestSimulateChangeDirectDependencies:
    """Test direct dependency detection (non-taxonomy)."""

    def test_direct_dependencies_found(self) -> None:
        """Pages with direct file dependencies should rebuild."""
        cache = MagicMock()
        cache.file_fingerprints = {
            "content/page.md": "hash1",
            "data/config.yaml": "hash2",
        }
        cache.dependencies = {
            "content/page.md": {"data/config.yaml"},
        }
        cache.taxonomy_index.taxonomy_deps = {}

        debugger = IncrementalBuildDebugger(cache=cache)
        affected = debugger.simulate_change("data/config.yaml")

        assert "content/page.md" in affected

    def test_combines_direct_and_taxonomy_deps(self) -> None:
        """Should combine direct dependencies and taxonomy dependencies."""
        cache = MagicMock()
        cache.file_fingerprints = {
            "content/post-a.md": "hash1",
            "content/post-b.md": "hash2",
            "content/post-c.md": "hash3",
        }
        # post-c directly depends on post-a
        cache.dependencies = {
            "content/post-c.md": {"content/post-a.md"},
        }
        # post-a and post-b share a tag
        cache.taxonomy_index.taxonomy_deps = {
            "tags/python": ["content/post-a.md", "content/post-b.md"],
        }

        debugger = IncrementalBuildDebugger(cache=cache)
        affected = debugger.simulate_change("content/post-a.md")

        # Should include: post-a (itself), post-b (taxonomy), post-c (direct dep)
        assert "content/post-a.md" in affected
        assert "content/post-b.md" in affected
        assert "content/post-c.md" in affected

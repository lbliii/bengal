"""Tests for PageCacheManager path key consistency.

Regression test for get_page_path_map: map keys use str(p.source_path).
Renderer/taxonomy lookups use str(tax_page.source_path). Both must produce
the same string for resolution to succeed. This test documents the contract
and would fail if path formats diverge.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from bengal.core.page_cache import PageCacheManager


def _make_mock_page(source_path: Path | str) -> MagicMock:
    """Create mock page with source_path."""
    p = MagicMock()
    p.source_path = Path(source_path) if isinstance(source_path, str) else source_path
    p.metadata = {}
    p.in_listings = True
    return p


class TestGetPagePathMapPathKeys:
    """Tests for get_page_path_map path key consistency."""

    def test_map_keys_match_str_source_path(self) -> None:
        """Map keys are str(source_path); lookup with str(path) succeeds."""
        rel_path = "content/blog/post.md"
        page = _make_mock_page(Path(rel_path))
        cache = PageCacheManager(pages_fn=lambda: [page])

        path_map = cache.get_page_path_map()

        assert rel_path in path_map
        assert path_map[rel_path] is page
        # Renderer lookup: str(tax_page.source_path)
        assert path_map.get(str(page.source_path)) is page

    def test_tag_page_resolution_when_path_formats_match(self) -> None:
        """Tag/taxonomy page resolution works when map and lookup use same format."""
        # Simulate: pages from discovery have Path source_path
        # Taxonomy stores same pages; lookup uses str(tax_page.source_path)
        rel_path = "content/docs/guide.md"
        page = _make_mock_page(Path(rel_path))
        cache = PageCacheManager(pages_fn=lambda: [page])

        path_map = cache.get_page_path_map()
        # Simulate taxonomy page (same path, could be from cached data)
        tax_page = _make_mock_page(Path(rel_path))
        resolved = path_map.get(str(tax_page.source_path))

        assert resolved is page
        assert resolved is not None

    def test_path_and_str_key_equivalence(self) -> None:
        """Path('content/x.md') and 'content/x.md' produce same map key."""
        page = _make_mock_page(Path("content/about.md"))
        cache = PageCacheManager(pages_fn=lambda: [page])
        path_map = cache.get_page_path_map()

        # Both lookup styles should work (str(Path) == path string)
        assert path_map.get("content/about.md") is page
        assert path_map.get(str(Path("content/about.md"))) is page

    def test_mixed_path_formats_miss_regression_guard(self, tmp_path: Path) -> None:
        """Documents: map uses str(source_path); absolute vs relative = different keys.

        When taxonomy stores member with absolute path and map has relative (or vice
        versa), lookup fails. This test guards against regressions if we add
        content_key normalization to get_page_path_map.
        """
        # Map built from discovery (relative paths)
        rel_path = Path("content/docs/guide.md")
        page = _make_mock_page(rel_path)
        cache = PageCacheManager(pages_fn=lambda: [page])
        path_map = cache.get_page_path_map()

        # Simulate taxonomy member with absolute path (e.g. from cached/watcher data)
        abs_path = tmp_path / "content" / "docs" / "guide.md"
        tax_member = _make_mock_page(abs_path)

        # Lookup with absolute path string - misses (map key is relative)
        resolved = path_map.get(str(tax_member.source_path))
        assert resolved is None  # Current behavior: format mismatch = miss

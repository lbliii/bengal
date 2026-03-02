"""
Boundary tests for cache path key normalization.

Validates that content_key produces consistent lookup regardless of path dialect
(absolute from watcher, relative from discovery).
"""

from bengal.build.contracts.keys import content_key
from bengal.cache.build_cache import BuildCache


class TestContentKeyContract:
    """Validate content_key produces canonical keys for different path formats."""

    def test_absolute_and_relative_produce_same_key(self, tmp_path):
        """Absolute and relative paths to same file produce identical keys."""
        site_root = tmp_path / "site"
        site_root.mkdir()
        content_file = site_root / "content" / "docs" / "_index.md"
        content_file.parent.mkdir(parents=True)

        abs_key = content_key(content_file.resolve(), site_root)
        rel_key = content_key(site_root / "content/docs/_index.md", site_root)

        assert str(abs_key) == str(rel_key)
        assert str(abs_key) == "content/docs/_index.md"

    def test_watcher_absolute_matches_discovery_relative(self, tmp_path):
        """Path from watcher (absolute) matches path from discovery (relative)."""
        site_root = tmp_path / "site"
        site_root.mkdir()
        (site_root / "content").mkdir()
        md_file = site_root / "content" / "about.md"
        md_file.write_text("# About")

        watcher_path = md_file.resolve()  # Simulate watchfiles
        discovery_path = site_root / "content/about.md"  # Discovery path (site_root-relative)

        assert content_key(watcher_path, site_root) == content_key(discovery_path, site_root)


class TestBuildCacheKeyNormalization:
    """Validate BuildCache uses normalized keys for cache hits across path dialects."""

    def test_seed_relative_lookup_absolute_hits(self, tmp_path):
        """Cache seeded with relative path, lookup with absolute path hits."""
        site_root = tmp_path / "site"
        site_root.mkdir()
        (site_root / "content").mkdir()
        md_file = site_root / "content" / "page.md"
        md_file.write_text("# Page")

        cache = BuildCache()
        cache.site_root = site_root

        # Seed from discovery (path relative to site_root)
        cache.update_file(site_root / "content/page.md")

        # Lookup from watcher (absolute)
        assert cache.is_changed(md_file.resolve()) is False

    def test_seed_absolute_lookup_relative_hits(self, tmp_path):
        """Cache seeded from watcher (absolute), lookup from discovery (relative) hits."""
        site_root = tmp_path / "site"
        site_root.mkdir()
        (site_root / "content").mkdir()
        md_file = site_root / "content" / "page.md"
        md_file.write_text("# Page")

        cache = BuildCache()
        cache.site_root = site_root

        # Seed from watcher (absolute)
        cache.update_file(md_file.resolve())

        # Lookup from discovery (path relative to site_root)
        assert cache.is_changed(site_root / "content/page.md") is False

    def test_get_affected_pages_cross_dialect(self, tmp_path):
        """get_affected_pages finds pages when changed path uses different dialect."""
        site_root = tmp_path / "site"
        site_root.mkdir()
        (site_root / "content").mkdir()
        (site_root / "templates").mkdir()
        page_file = site_root / "content" / "page.md"
        template_file = site_root / "templates" / "base.html"
        page_file.write_text("# Page")
        template_file.write_text("<html></html>")

        cache = BuildCache()
        cache.site_root = site_root

        # Add dependency: page depends on template (use normalized keys)
        cache.add_dependency(page_file, template_file)

        # Invalidate from watcher path (absolute)
        affected = cache.get_affected_pages(template_file.resolve())
        assert str(content_key(page_file, site_root)) in affected

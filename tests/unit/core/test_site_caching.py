"""
Tests for Site property caching optimizations.

Verifies that expensive properties like regular_pages are cached
to prevent O(n²) performance issues.
"""

from bengal.core.page import Page
from bengal.core.site import Site


def test_regular_pages_caching(tmp_path):
    """Test that regular_pages is cached after first access."""
    site = Site(root_path=tmp_path)

    # Add some pages
    regular_page_1 = Page(source_path=tmp_path / "page1.md", metadata={"title": "Page 1"})
    regular_page_2 = Page(source_path=tmp_path / "page2.md", metadata={"title": "Page 2"})
    generated_page = Page(
        source_path=tmp_path / "tags" / "python.md",
        metadata={"title": "Python Tag", "_generated": True},
    )

    site.pages = [regular_page_1, regular_page_2, generated_page]

    # First access should compute and cache
    assert site._regular_pages_cache is None
    regular = site.regular_pages
    assert len(regular) == 2
    assert regular_page_1 in regular
    assert regular_page_2 in regular
    assert generated_page not in regular

    # Cache should now be populated
    assert site._regular_pages_cache is not None
    assert len(site._regular_pages_cache) == 2

    # Second access should use cache (same object reference)
    regular2 = site.regular_pages
    assert regular2 is site._regular_pages_cache


def test_regular_pages_cache_invalidation(tmp_path):
    """Test that regular_pages cache is invalidated when pages change."""
    site = Site(root_path=tmp_path)

    # Add initial pages
    regular_page = Page(source_path=tmp_path / "page1.md", metadata={"title": "Page 1"})
    site.pages = [regular_page]

    # Access to populate cache
    regular = site.regular_pages
    assert len(regular) == 1
    assert site._regular_pages_cache is not None

    # Invalidate cache
    site.invalidate_regular_pages_cache()
    assert site._regular_pages_cache is None

    # Add a generated page
    generated_page = Page(
        source_path=tmp_path / "tags" / "python.md",
        metadata={"title": "Python Tag", "_generated": True},
    )
    site.pages.append(generated_page)

    # Access again should recompute
    regular2 = site.regular_pages
    assert len(regular2) == 1  # Still only 1 regular page
    assert generated_page not in regular2


def test_regular_pages_empty_site(tmp_path):
    """Test regular_pages with no pages."""
    site = Site(root_path=tmp_path)
    site.pages = []

    regular = site.regular_pages
    assert regular == []
    assert site._regular_pages_cache == []


def test_regular_pages_all_generated(tmp_path):
    """Test regular_pages when all pages are generated."""
    site = Site(root_path=tmp_path)

    generated1 = Page(
        source_path=tmp_path / "tags" / "python.md",
        metadata={"title": "Python Tag", "_generated": True},
    )
    generated2 = Page(
        source_path=tmp_path / "tags" / "django.md",
        metadata={"title": "Django Tag", "_generated": True},
    )

    site.pages = [generated1, generated2]

    regular = site.regular_pages
    assert regular == []
    assert site._regular_pages_cache == []


def test_regular_pages_cache_performance(tmp_path):
    """Test that caching provides O(1) subsequent access."""
    import time

    site = Site(root_path=tmp_path)

    # Add many pages
    for i in range(1000):
        is_generated = i % 10 == 0  # Every 10th page is generated
        page = Page(
            source_path=tmp_path / f"page{i}.md",
            metadata={"title": f"Page {i}", "_generated": is_generated},
        )
        site.pages.append(page)

    # First access (should filter all pages)
    start = time.time()
    regular1 = site.regular_pages
    first_time = time.time() - start
    assert len(regular1) == 900  # 900 regular, 100 generated

    # Second access (should use cache)
    start = time.time()
    regular2 = site.regular_pages
    second_time = time.time() - start

    # Cached access should be MUCH faster (at least 10x)
    assert second_time < first_time / 10
    assert regular2 is site._regular_pages_cache


def test_regular_pages_cache_across_multiple_accesses(tmp_path):
    """Test that cache remains valid across many accesses."""
    site = Site(root_path=tmp_path)

    # Add pages
    for i in range(100):
        page = Page(source_path=tmp_path / f"page{i}.md", metadata={"title": f"Page {i}"})
        site.pages.append(page)

    # Access multiple times
    for _ in range(10):
        regular = site.regular_pages
        assert len(regular) == 100
        assert regular is site._regular_pages_cache


# =============================================================================
# Tests for Site runtime caches (Phase B: Formalized from dynamic injection)
# =============================================================================


class TestSiteRuntimeCaches:
    """Tests for Site runtime cache management."""

    def test_asset_fallback_lock_initialized(self, tmp_path):
        """Verify thread lock is initialized automatically in __post_init__."""
        import threading

        site = Site(root_path=tmp_path)

        assert site._asset_manifest_fallbacks_lock is not None
        assert isinstance(site._asset_manifest_fallbacks_lock, type(threading.Lock()))

    def test_asset_fallback_set_initialized(self, tmp_path):
        """Verify fallback set is initialized as empty set."""
        site = Site(root_path=tmp_path)

        assert site._asset_manifest_fallbacks_global is not None
        assert isinstance(site._asset_manifest_fallbacks_global, set)
        assert len(site._asset_manifest_fallbacks_global) == 0

    def test_runtime_caches_default_to_none(self, tmp_path):
        """Verify template environment caches default to None."""
        site = Site(root_path=tmp_path)

        assert site._bengal_theme_chain_cache is None
        assert site._bengal_template_dirs_cache is None
        assert site._bengal_template_metadata_cache is None
        assert site._discovery_breakdown_ms is None
        assert site._asset_manifest_previous is None

    def test_reset_ephemeral_clears_runtime_caches(self, tmp_path):
        """Verify reset_ephemeral_state clears Phase B fields."""
        from bengal.rendering.pipeline.thread_local import get_created_dirs

        site = Site(root_path=tmp_path)

        # Set some caches
        site._bengal_theme_chain_cache = {"key": "test", "chain": ["default"]}
        site._bengal_template_dirs_cache = {"key": "test", "template_dirs": ["/tmp"]}
        site._bengal_template_metadata_cache = {"key": "test", "metadata": {"engine": "test"}}
        site._discovery_breakdown_ms = {"pages": 100.0, "total": 150.0}
        site._asset_manifest_fallbacks_global.add("test.css")

        # Set created dirs cache
        get_created_dirs().add_if_new("/some/dir")

        # Reset
        site.reset_ephemeral_state()

        # Verify caches cleared
        assert site._bengal_theme_chain_cache is None
        assert site._bengal_template_dirs_cache is None
        assert site._bengal_template_metadata_cache is None
        assert site._discovery_breakdown_ms is None
        assert len(site._asset_manifest_fallbacks_global) == 0

        # Verify created dirs cleared
        assert "/some/dir" not in get_created_dirs()

    def test_reset_ephemeral_preserves_asset_manifest_previous(self, tmp_path):
        """Verify reset_ephemeral_state preserves _asset_manifest_previous for incremental builds."""
        site = Site(root_path=tmp_path)

        # Set asset manifest previous (needed for incremental)
        site._asset_manifest_previous = {"some": "manifest"}

        # Reset
        site.reset_ephemeral_state()

        # _asset_manifest_previous should NOT be reset (needed for incremental asset comparison)
        assert site._asset_manifest_previous == {"some": "manifest"}

    def test_reset_ephemeral_preserves_lock(self, tmp_path):
        """Verify reset_ephemeral_state preserves the thread lock."""
        import threading

        site = Site(root_path=tmp_path)
        original_lock = site._asset_manifest_fallbacks_lock

        # Reset
        site.reset_ephemeral_state()

        # Lock should still be the same object (not reset)
        assert site._asset_manifest_fallbacks_lock is original_lock
        assert isinstance(site._asset_manifest_fallbacks_lock, type(threading.Lock()))

    def test_fallback_set_thread_safe_usage(self, tmp_path):
        """Verify fallback set can be used with lock for thread safety."""
        site = Site(root_path=tmp_path)

        # Simulate thread-safe usage pattern
        with site._asset_manifest_fallbacks_lock:
            site._asset_manifest_fallbacks_global.add("css/style.css")
            site._asset_manifest_fallbacks_global.add("js/main.js")

        assert "css/style.css" in site._asset_manifest_fallbacks_global
        assert "js/main.js" in site._asset_manifest_fallbacks_global
        assert len(site._asset_manifest_fallbacks_global) == 2

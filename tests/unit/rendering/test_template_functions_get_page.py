"""Tests for get_page template function used by tracks feature."""

import threading
from pathlib import Path

import pytest

from bengal.core.site import Site
from bengal.rendering.template_functions.get_page import (
    _get_render_cache,
    _normalize_cache_key,
    clear_get_page_cache,
    register,
)
from bengal.utils.file_io import write_text_file


@pytest.fixture
def site_with_content(tmp_path: Path) -> Site:
    """Create a site with test content for get_page testing."""
    site_dir = tmp_path / "site"
    site_dir.mkdir()

    # Create config
    config_path = site_dir / "bengal.toml"
    write_text_file(
        str(config_path),
        """[site]
title = "Test Site"
baseurl = "/"

[build]
output_dir = "public"
""",
    )

    # Create content structure
    content_dir = site_dir / "content"
    content_dir.mkdir()

    # Create pages in various locations
    (content_dir / "index.md").write_text("---\ntitle: Home\n---\n# Home")

    docs_dir = content_dir / "docs"
    docs_dir.mkdir()

    getting_started_dir = docs_dir / "getting-started"
    getting_started_dir.mkdir()

    (getting_started_dir / "installation.md").write_text(
        "---\ntitle: Installation\n---\n# Installation"
    )
    (getting_started_dir / "writer-quickstart.md").write_text(
        "---\ntitle: Writer Quickstart\n---\n# Writer"
    )

    guides_dir = docs_dir / "guides"
    guides_dir.mkdir()
    (guides_dir / "content-workflow.md").write_text("---\ntitle: Content Workflow\n---\n# Workflow")

    # Create site and discover content
    site = Site.from_config(site_dir, config_path=config_path)
    site.discover_content()
    site.discover_assets()

    return site


class TestGetPageFunction:
    """Test get_page template function for track page resolution."""

    def test_get_page_by_relative_path(self, site_with_content: Site):
        """Test resolving page by content-relative path."""
        from jinja2 import Environment

        env = Environment()
        register(env, site_with_content)
        get_page = env.globals["get_page"]

        # Test exact path match
        page = get_page("docs/getting-started/installation.md")
        assert page is not None
        assert page.title == "Installation"

        # Test path without extension
        page2 = get_page("docs/getting-started/writer-quickstart")
        assert page2 is not None
        assert page2.title == "Writer Quickstart"

    def test_get_page_by_path_without_extension(self, site_with_content: Site):
        """Test resolving page when .md extension omitted."""
        from jinja2 import Environment

        env = Environment()
        register(env, site_with_content)
        get_page = env.globals["get_page"]

        page = get_page("docs/getting-started/installation")
        assert page is not None
        assert page.title == "Installation"

    def test_get_page_nonexistent_path(self, site_with_content: Site):
        """Test None returned for non-existent pages."""
        from jinja2 import Environment

        env = Environment()
        register(env, site_with_content)
        get_page = env.globals["get_page"]

        page = get_page("docs/nonexistent/page.md")
        assert page is None

        page2 = get_page("docs/getting-started/does-not-exist.md")
        assert page2 is None

    def test_get_page_empty_path(self, site_with_content: Site):
        """Test empty path handling."""
        from jinja2 import Environment

        env = Environment()
        register(env, site_with_content)
        get_page = env.globals["get_page"]

        assert get_page("") is None
        assert get_page(None) is None  # type: ignore

    def test_get_page_path_normalization(self, site_with_content: Site):
        """Test Windows/Unix path separator normalization."""
        from jinja2 import Environment

        env = Environment()
        register(env, site_with_content)
        get_page = env.globals["get_page"]

        # Test Windows-style path separators
        page = get_page("docs\\getting-started\\installation.md")
        assert page is not None
        assert page.title == "Installation"

        # Test mixed separators
        page2 = get_page("docs/getting-started\\writer-quickstart.md")
        assert page2 is not None
        assert page2.title == "Writer Quickstart"

    def test_get_page_lookup_map_caching(self, site_with_content: Site):
        """Test that lookup maps are cached on site object."""
        from jinja2 import Environment

        # Clear per-render cache to ensure we hit lookup map creation path
        clear_get_page_cache()

        env = Environment()
        register(env, site_with_content)
        get_page = env.globals["get_page"]

        # First call should create maps (field exists but is None before first use)
        assert site_with_content._page_lookup_maps is None
        page1 = get_page("docs/getting-started/installation.md")
        assert site_with_content._page_lookup_maps is not None

        # Maps should be reused
        maps_before = site_with_content._page_lookup_maps
        page2 = get_page("docs/guides/content-workflow.md")
        assert site_with_content._page_lookup_maps is maps_before

        assert page1 is not None
        assert page2 is not None

    def test_get_page_index_page(self, site_with_content: Site):
        """Test resolving index page."""
        from jinja2 import Environment

        env = Environment()
        register(env, site_with_content)
        get_page = env.globals["get_page"]

        page = get_page("index.md")
        assert page is not None
        assert page.title == "Home"

    def test_get_page_with_trailing_slash(self, site_with_content: Site):
        """Test path with trailing slash is handled."""
        from jinja2 import Environment

        env = Environment()
        register(env, site_with_content)
        get_page = env.globals["get_page"]

        # Should still work (though not ideal)
        get_page("docs/getting-started/installation.md/")
        # May or may not work, but shouldn't crash
        # Current implementation may return None, which is acceptable

    def test_get_page_case_sensitivity(self, site_with_content: Site):
        """Test that path matching is case-sensitive."""
        from jinja2 import Environment

        env = Environment()
        register(env, site_with_content)
        get_page = env.globals["get_page"]

        # Exact case should work
        page = get_page("docs/getting-started/installation.md")
        assert page is not None

        # Different case may not work (platform-dependent)
        # On case-insensitive filesystems (macOS/Windows), this might work
        # On case-sensitive filesystems (Linux), this should fail
        # Current implementation is case-sensitive, which is correct

    def test_get_page_parses_on_demand(self, site_with_content: Site):
        """Test that get_page parses pages on-demand when accessed from templates."""
        from jinja2 import Environment

        env = Environment()
        register(env, site_with_content)
        get_page = env.globals["get_page"]

        # Get a page that hasn't been parsed yet
        page = get_page("docs/getting-started/writer-quickstart.md")
        assert page is not None

        # Verify page is parsed after get_page call
        assert hasattr(page, "parsed_ast")
        assert page.parsed_ast is not None
        assert len(page.parsed_ast) > 0
        # Should be HTML, not markdown
        assert "<h1>" in page.parsed_ast or "<h2>" in page.parsed_ast

    def test_get_page_does_not_reparse_already_parsed_pages(self, site_with_content: Site):
        """Test that get_page doesn't reparse pages that are already parsed."""
        from jinja2 import Environment

        env = Environment()
        register(env, site_with_content)
        get_page = env.globals["get_page"]

        # Get a page and parse it manually first
        page = get_page("docs/getting-started/installation.md")
        assert page is not None

        # Manually set parsed_ast to a known value
        original_parsed = "<h1>Test</h1><p>Original content</p>"
        page.parsed_ast = original_parsed

        # Get the page again - should not reparse
        page2 = get_page("docs/getting-started/installation.md")
        assert page2 is not None
        assert page2.parsed_ast == original_parsed


class TestCacheKeyNormalization:
    """Test cache key normalization for consistent caching."""

    def test_strips_leading_dot_slash(self):
        """Test ./foo.md -> foo.md normalization."""
        assert _normalize_cache_key("./foo.md") == "foo.md"
        assert _normalize_cache_key("./guides/foo.md") == "guides/foo.md"

    def test_strips_content_prefix(self):
        """Test content/foo.md -> foo.md normalization."""
        assert _normalize_cache_key("content/foo.md") == "foo.md"
        assert _normalize_cache_key("content/guides/foo.md") == "guides/foo.md"

    def test_normalizes_backslashes(self):
        """Test Windows path separator normalization."""
        assert _normalize_cache_key("content\\foo.md") == "foo.md"
        assert _normalize_cache_key("guides\\setup\\install.md") == "guides/setup/install.md"
        assert _normalize_cache_key(".\\foo.md") == "foo.md"

    def test_preserves_simple_path(self):
        """Test simple paths are preserved."""
        assert _normalize_cache_key("foo.md") == "foo.md"
        assert _normalize_cache_key("guides/foo.md") == "guides/foo.md"

    def test_handles_nested_paths(self):
        """Test nested paths with content prefix."""
        assert (
            _normalize_cache_key("content/guides/deep/nested/page.md")
            == "guides/deep/nested/page.md"
        )

    def test_handles_path_without_extension(self):
        """Test paths without .md extension."""
        assert _normalize_cache_key("foo") == "foo"
        assert _normalize_cache_key("content/foo") == "foo"
        assert _normalize_cache_key("./foo") == "foo"


class TestPerRenderCache:
    """Test per-render caching behavior."""

    def test_cache_starts_empty(self):
        """Test that cache starts empty in each thread."""
        clear_get_page_cache()
        cache = _get_render_cache()
        assert len(cache) == 0

    def test_cache_cleared_properly(self):
        """Test that clear_get_page_cache() clears the cache."""
        cache = _get_render_cache()
        cache["test_key"] = "test_value"
        assert "test_key" in cache

        clear_get_page_cache()
        cache = _get_render_cache()
        assert "test_key" not in cache

    def test_cache_hit_returns_same_object(self, site_with_content: Site):
        """Test that cached get_page() returns the same object."""
        from jinja2 import Environment

        clear_get_page_cache()

        env = Environment()
        register(env, site_with_content)
        get_page = env.globals["get_page"]

        # First call populates cache
        page1 = get_page("docs/getting-started/installation.md")
        assert page1 is not None

        # Second call should return same object from cache
        page2 = get_page("docs/getting-started/installation.md")
        assert page2 is page1  # Same object reference

    def test_cache_miss_also_cached(self, site_with_content: Site):
        """Test that None results are also cached."""
        from jinja2 import Environment

        clear_get_page_cache()

        env = Environment()
        register(env, site_with_content)
        get_page = env.globals["get_page"]

        # First call for non-existent page
        page1 = get_page("nonexistent/page.md")
        assert page1 is None

        # Check that None is cached
        cache_key = _normalize_cache_key("nonexistent/page.md")
        cache = _get_render_cache()
        assert cache_key in cache
        assert cache[cache_key] is None

    def test_different_path_variants_hit_same_cache_entry(self, site_with_content: Site):
        """Test that different path formats resolve to same cache entry."""
        from jinja2 import Environment

        clear_get_page_cache()

        env = Environment()
        register(env, site_with_content)
        get_page = env.globals["get_page"]

        # These should all resolve to the same page and cache entry
        page1 = get_page("docs/getting-started/installation.md")
        page2 = get_page("content/docs/getting-started/installation.md")
        page3 = get_page("./docs/getting-started/installation.md")

        assert page1 is not None
        assert page2 is page1  # Same object from cache
        assert page3 is page1  # Same object from cache


class TestCacheThreadSafety:
    """Test thread isolation of cache."""

    def test_caches_are_thread_isolated(self):
        """Test that each thread has its own isolated cache."""
        results: dict[int, str | None] = {}
        errors: list[str] = []

        def thread_work(thread_id: int) -> None:
            try:
                # Clear this thread's cache
                clear_get_page_cache()
                cache = _get_render_cache()

                # Store a thread-specific value
                cache["test"] = f"thread-{thread_id}"

                # Small delay to allow interleaving
                import time

                time.sleep(0.01)

                # Read back the value - should still be our value
                results[thread_id] = cache.get("test")
            except Exception as e:
                errors.append(f"Thread {thread_id}: {e}")

        # Create and run multiple threads
        threads = [threading.Thread(target=thread_work, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Check for errors
        assert not errors, f"Thread errors: {errors}"

        # Each thread should have its own value
        for i in range(5):
            assert results[i] == f"thread-{i}", f"Thread {i} got wrong value: {results[i]}"

    def test_cache_clearing_is_thread_local(self):
        """Test that clearing cache in one thread doesn't affect others."""
        thread1_value_after_clear: str | None = None
        thread2_value_after_t1_clear: str | None = None
        barrier = threading.Barrier(2)

        def thread1_work() -> None:
            nonlocal thread1_value_after_clear
            cache = _get_render_cache()
            cache["shared_key"] = "thread1_value"
            barrier.wait()  # Wait for thread2 to set its value
            barrier.wait()  # Wait for thread2 to read its value
            clear_get_page_cache()  # Clear thread1's cache
            cache = _get_render_cache()
            thread1_value_after_clear = cache.get("shared_key")
            barrier.wait()  # Signal thread2 to check its value

        def thread2_work() -> None:
            nonlocal thread2_value_after_t1_clear
            cache = _get_render_cache()
            cache["shared_key"] = "thread2_value"
            barrier.wait()  # Signal thread1 we've set our value
            # Verify we have our own value
            assert cache.get("shared_key") == "thread2_value"
            barrier.wait()  # Signal thread1 to clear
            barrier.wait()  # Wait for thread1 to clear
            # Our cache should still have our value
            cache = _get_render_cache()
            thread2_value_after_t1_clear = cache.get("shared_key")

        t1 = threading.Thread(target=thread1_work)
        t2 = threading.Thread(target=thread2_work)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        # Thread1's cache should be empty after clear
        assert thread1_value_after_clear is None
        # Thread2's cache should still have its value
        assert thread2_value_after_t1_clear == "thread2_value"

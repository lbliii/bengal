"""
Unit tests for PageProxy lazy-loading mechanism.

Tests verify that:
- PageProxy stores and returns cached metadata instantly
- PageProxy lazy-loads full content on first access
- PageProxy behaves identically to normal Page objects
- Proxy state can be inspected for debugging
"""

from pathlib import Path

import pytest

from bengal.cache.page_discovery_cache import PageMetadata
from bengal.core.page import Page, PageProxy


@pytest.fixture
def sample_page():
    """Create a sample page for testing."""
    return Page(
        source_path=Path("content/blog/post.md"),
        _raw_content="# My Post\n\nContent here.",
        metadata={
            "title": "My Post",
            "date": "2025-01-15",
            "tags": ["python", "web"],
            "weight": 5,
        },
    )


@pytest.fixture
def cached_metadata():
    """Create cached metadata."""
    return PageMetadata(
        source_path="content/blog/post.md",
        title="My Post",
        date="2025-01-15",
        tags=["python", "web"],
        section="content/blog",
        slug="post",
        weight=5,
        lang="en",
    )


@pytest.fixture
def page_loader(sample_page):
    """Create a page loader function."""

    def loader(source_path):
        return sample_page

    return loader


class TestPageProxyMetadata:
    """Tests for metadata access (cached, instant)."""

    def test_proxy_stores_metadata_from_cache(self, cached_metadata, page_loader):
        """Verify proxy stores metadata from cache."""
        proxy = PageProxy(
            source_path=Path("content/blog/post.md"),
            metadata=cached_metadata,
            loader=page_loader,
        )

        assert proxy.title == "My Post"
        assert proxy.slug == "post"
        assert proxy.weight == 5
        assert proxy.lang == "en"
        assert proxy.tags == ["python", "web"]

    def test_proxy_parses_date_from_cache(self, cached_metadata, page_loader):
        """Verify proxy parses ISO date string."""
        proxy = PageProxy(
            source_path=Path("content/blog/post.md"),
            metadata=cached_metadata,
            loader=page_loader,
        )

        assert proxy.date is not None
        assert proxy.date.year == 2025
        assert proxy.date.month == 1
        assert proxy.date.day == 15

    def test_proxy_metadata_access_does_not_trigger_load(self, cached_metadata, page_loader):
        """Verify accessing cached metadata doesn't trigger lazy load."""
        proxy = PageProxy(
            source_path=Path("content/blog/post.md"),
            metadata=cached_metadata,
            loader=page_loader,
        )

        # Access all cached metadata fields
        _ = proxy.title
        _ = proxy.slug
        _ = proxy.date
        _ = proxy.tags

        # Proxy should still not be loaded
        assert not proxy._lazy_loaded


class TestPageProxyLazyLoading:
    """Tests for lazy-loading full content."""

    def test_proxy_lazy_loads_content_on_access(self, cached_metadata, page_loader):
        """Verify proxy loads full content on first .content access."""
        proxy = PageProxy(
            source_path=Path("content/blog/post.md"),
            metadata=cached_metadata,
            loader=page_loader,
        )

        assert not proxy._lazy_loaded

        # Access content property (should trigger load)
        content = proxy.content

        assert proxy._lazy_loaded
        assert content == "# My Post\n\nContent here."

    def test_proxy_lazy_loads_metadata_dict(self, cached_metadata, page_loader):
        """Verify proxy provides cached metadata WITHOUT triggering lazy load."""
        proxy = PageProxy(
            source_path=Path("content/blog/post.md"),
            metadata=cached_metadata,
            loader=page_loader,
        )

        assert not proxy._lazy_loaded

        # Access metadata dict (should NOT trigger load - comes from PageCore cache!)
        metadata = proxy.metadata

        assert not proxy._lazy_loaded  # Still not loaded!
        assert isinstance(metadata, dict)
        # Metadata should come from PageCore cache
        assert "type" in metadata or "tags" in metadata  # Has some cached fields

    def test_proxy_lazy_loads_only_once(self, cached_metadata, page_loader):
        """Verify proxy loads content only once, then caches it."""
        load_count = 0

        def counting_loader(source_path):
            nonlocal load_count
            load_count += 1
            return page_loader(source_path)

        proxy = PageProxy(
            source_path=Path("content/blog/post.md"),
            metadata=cached_metadata,
            loader=counting_loader,
        )

        # Access multiple times
        _ = proxy.content
        _ = proxy.content
        _ = proxy.metadata

        # Should have loaded exactly once
        assert load_count == 1
        assert proxy._lazy_loaded

    def test_proxy_lazy_loads_toc(self, cached_metadata, page_loader):
        """Verify accessing .toc triggers lazy load."""
        proxy = PageProxy(
            source_path=Path("content/blog/post.md"),
            metadata=cached_metadata,
            loader=page_loader,
        )

        # Access lazy property
        _ = proxy.toc

        assert proxy._lazy_loaded


class TestPageProxyEquality:
    """Tests for proxy equality and hashing."""

    def test_proxy_equality_with_same_source(self, cached_metadata, page_loader, sample_page):
        """Verify two proxies with same source are equal."""
        proxy1 = PageProxy(
            source_path=Path("content/blog/post.md"),
            metadata=cached_metadata,
            loader=page_loader,
        )

        proxy2 = PageProxy(
            source_path=Path("content/blog/post.md"),
            metadata=cached_metadata,
            loader=page_loader,
        )

        assert proxy1 == proxy2

    def test_proxy_equality_with_different_source(self, cached_metadata, page_loader):
        """Verify proxies with different sources are not equal."""
        proxy1 = PageProxy(
            source_path=Path("content/blog/post1.md"),
            metadata=cached_metadata,
            loader=page_loader,
        )

        proxy2 = PageProxy(
            source_path=Path("content/blog/post2.md"),
            metadata=cached_metadata,
            loader=page_loader,
        )

        assert proxy1 != proxy2

    def test_proxy_hashable(self, cached_metadata, page_loader):
        """Verify proxy can be hashed and used in sets."""
        proxy = PageProxy(
            source_path=Path("content/blog/post.md"),
            metadata=cached_metadata,
            loader=page_loader,
        )

        # Should be hashable
        h = hash(proxy)
        assert isinstance(h, int)

        # Should work in sets
        proxy_set = {proxy}
        assert len(proxy_set) == 1

    def test_proxy_in_dict(self, cached_metadata, page_loader):
        """Verify proxy can be used as dict key."""
        proxy = PageProxy(
            source_path=Path("content/blog/post.md"),
            metadata=cached_metadata,
            loader=page_loader,
        )

        mapping = {proxy: "value"}
        assert mapping[proxy] == "value"


class TestPageProxyRepresentation:
    """Tests for string representation."""

    def test_proxy_repr_before_load(self, cached_metadata, page_loader):
        """Verify repr shows proxy state."""
        proxy = PageProxy(
            source_path=Path("content/blog/post.md"),
            metadata=cached_metadata,
            loader=page_loader,
        )

        repr_str = repr(proxy)
        assert "proxy" in repr_str
        assert "My Post" in repr_str
        assert "post.md" in repr_str

    def test_proxy_repr_after_load(self, cached_metadata, page_loader):
        """Verify repr changes after load."""
        proxy = PageProxy(
            source_path=Path("content/blog/post.md"),
            metadata=cached_metadata,
            loader=page_loader,
        )

        # Trigger load
        _ = proxy.content

        repr_str = repr(proxy)
        assert "loaded" in repr_str


class TestPageProxyDebugging:
    """Tests for debugging and inspection."""

    def test_get_load_status_before_load(self, cached_metadata, page_loader):
        """Verify load status before loading."""
        proxy = PageProxy(
            source_path=Path("content/blog/post.md"),
            metadata=cached_metadata,
            loader=page_loader,
        )

        status = proxy.get_load_status()

        assert status["is_loaded"] is False
        assert status["title"] == "My Post"
        assert "post.md" in status["source_path"]

    def test_get_load_status_after_load(self, cached_metadata, page_loader):
        """Verify load status after loading."""
        proxy = PageProxy(
            source_path=Path("content/blog/post.md"),
            metadata=cached_metadata,
            loader=page_loader,
        )

        # Trigger load
        _ = proxy.content

        status = proxy.get_load_status()
        assert status["is_loaded"] is True
        assert status["has_full_page"] is True


class TestPageProxyFromPage:
    """Tests for creating proxy from existing page."""

    def test_create_proxy_from_page(self, sample_page, cached_metadata):
        """Verify can create proxy from existing page."""
        proxy = PageProxy.from_page(sample_page, cached_metadata)

        assert proxy.title == "My Post"
        assert proxy.source_path == sample_page.source_path

        # Should load immediately when accessing
        content = proxy.content
        assert content == sample_page.content


class TestPageProxyEdgeCases:
    """Tests for edge cases and error handling."""

    def test_proxy_with_none_date(self, page_loader):
        """Verify proxy handles None date gracefully."""
        metadata = PageMetadata(
            source_path="content/post.md",
            title="Post",
            date=None,
            tags=[],
            section=None,
            slug="post",
        )

        proxy = PageProxy(
            source_path=Path("content/post.md"),
            metadata=metadata,
            loader=page_loader,
        )

        assert proxy.date is None

    def test_proxy_with_invalid_date(self, page_loader):
        """Verify proxy handles invalid date gracefully."""
        metadata = PageMetadata(
            source_path="content/post.md",
            title="Post",
            date="invalid-date",
            tags=[],
            section=None,
            slug="post",
        )

        proxy = PageProxy(
            source_path=Path("content/post.md"),
            metadata=metadata,
            loader=page_loader,
        )

        # Should return None for invalid date
        assert proxy.date is None

    def test_proxy_with_empty_tags(self, page_loader):
        """Verify proxy handles empty tags."""
        metadata = PageMetadata(
            source_path="content/post.md",
            title="Post",
            date=None,
            tags=[],
            section=None,
            slug="post",
        )

        proxy = PageProxy(
            source_path=Path("content/post.md"),
            metadata=metadata,
            loader=page_loader,
        )

        assert proxy.tags == []

    def test_proxy_empty_content_access(self, page_loader):
        """Verify accessing empty properties returns empty values."""
        metadata = PageMetadata(
            source_path="content/post.md",
            title="Post",
            date=None,
            tags=[],
            section=None,
            slug="post",
        )

        def empty_loader(source_path):
            return None

        proxy = PageProxy(
            source_path=Path("content/post.md"),
            metadata=metadata,
            loader=empty_loader,
        )

        # Should handle None gracefully
        assert proxy.rendered_html == ""
        assert proxy.links == []


class TestPageProxyPlainText:
    """Tests for plain_text property (output formats contract).

    These tests ensure PageProxy exposes plain_text for output format generators
    (index.json, llm-full.txt, etc.) that read it during postprocessing.
    """

    def test_proxy_plain_text_exists_and_returns_string(self, cached_metadata, page_loader):
        """Verify plain_text property exists and returns str."""
        proxy = PageProxy(
            source_path=Path("content/blog/post.md"),
            metadata=cached_metadata,
            loader=page_loader,
        )

        result = proxy.plain_text

        assert isinstance(result, str)

    def test_proxy_plain_text_triggers_lazy_load(self, cached_metadata, page_loader):
        """Verify accessing plain_text triggers lazy load."""
        proxy = PageProxy(
            source_path=Path("content/blog/post.md"),
            metadata=cached_metadata,
            loader=page_loader,
        )

        assert not proxy._lazy_loaded

        # Access plain_text (should trigger load)
        _ = proxy.plain_text

        assert proxy._lazy_loaded

    def test_proxy_plain_text_returns_empty_when_loader_returns_none(self):
        """Verify plain_text returns empty string when loader returns None."""
        metadata = PageMetadata(
            source_path="content/post.md",
            title="Post",
            date=None,
            tags=[],
            section=None,
            slug="post",
        )

        def empty_loader(source_path):
            return None

        proxy = PageProxy(
            source_path=Path("content/post.md"),
            metadata=metadata,
            loader=empty_loader,
        )

        # Should handle None gracefully
        assert proxy.plain_text == ""

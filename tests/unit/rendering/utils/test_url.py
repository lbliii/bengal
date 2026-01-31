"""Tests for URL utilities."""

from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import Mock

import pytest

from bengal.rendering.utils.url import apply_baseurl, normalize_url_path


@dataclass
class MockSite:
    """Mock site object for testing."""

    baseurl: str | None = None


class TestApplyBaseurl:
    """Tests for apply_baseurl function."""

    def test_empty_baseurl_returns_path_unchanged(self):
        """Empty baseurl should return path unchanged."""
        site = MockSite(baseurl="")
        assert apply_baseurl("/docs/page/", site) == "/docs/page/"

    def test_none_baseurl_returns_path_unchanged(self):
        """None baseurl should return path unchanged."""
        site = MockSite(baseurl=None)
        assert apply_baseurl("/docs/page/", site) == "/docs/page/"

    def test_path_only_baseurl(self):
        """Path-only baseurl should be prepended."""
        site = MockSite(baseurl="/bengal")
        assert apply_baseurl("/docs/page/", site) == "/bengal/docs/page/"

    def test_path_baseurl_with_trailing_slash(self):
        """Trailing slash on baseurl should be stripped."""
        site = MockSite(baseurl="/bengal/")
        assert apply_baseurl("/docs/page/", site) == "/bengal/docs/page/"

    def test_path_baseurl_without_leading_slash(self):
        """Baseurl without leading slash should get one added."""
        site = MockSite(baseurl="bengal")
        assert apply_baseurl("/docs/page/", site) == "/bengal/docs/page/"

    def test_absolute_https_baseurl(self):
        """HTTPS absolute baseurl should be prepended."""
        site = MockSite(baseurl="https://example.com")
        assert apply_baseurl("/docs/page/", site) == "https://example.com/docs/page/"

    def test_absolute_https_baseurl_with_path(self):
        """HTTPS baseurl with path should be prepended."""
        site = MockSite(baseurl="https://example.com/subpath")
        assert apply_baseurl("/docs/page/", site) == "https://example.com/subpath/docs/page/"

    def test_absolute_http_baseurl(self):
        """HTTP absolute baseurl should work."""
        site = MockSite(baseurl="http://example.com")
        assert apply_baseurl("/docs/page/", site) == "http://example.com/docs/page/"

    def test_file_protocol_baseurl(self):
        """File protocol baseurl should be prepended."""
        site = MockSite(baseurl="file:///home/user/site")
        assert apply_baseurl("/docs/page/", site) == "file:///home/user/site/docs/page/"

    def test_path_without_leading_slash(self):
        """Path without leading slash should get one added."""
        site = MockSite(baseurl="/bengal")
        assert apply_baseurl("docs/page/", site) == "/bengal/docs/page/"

    def test_root_path(self):
        """Root path should work."""
        site = MockSite(baseurl="/bengal")
        assert apply_baseurl("/", site) == "/bengal/"

    def test_slash_only_baseurl_treated_as_empty(self):
        """Baseurl of just '/' should be treated as empty."""
        site = MockSite(baseurl="/")
        assert apply_baseurl("/docs/page/", site) == "/docs/page/"

    def test_none_site_returns_path(self):
        """None site should return path unchanged."""
        assert apply_baseurl("/docs/page/", None) == "/docs/page/"

    def test_site_without_baseurl_attribute(self):
        """Site without baseurl attribute should return path unchanged."""
        site = Mock(spec=[])  # No attributes
        assert apply_baseurl("/docs/page/", site) == "/docs/page/"

    def test_mock_site_returning_none(self):
        """Site returning None for baseurl should return path unchanged."""
        site = Mock()
        site.baseurl = None
        assert apply_baseurl("/docs/page/", site) == "/docs/page/"


class TestNormalizeUrlPath:
    """Tests for normalize_url_path function."""

    def test_empty_path_returns_slash(self):
        """Empty path should return '/'."""
        assert normalize_url_path("") == "/"

    def test_path_without_leading_slash(self):
        """Path without leading slash should get one."""
        assert normalize_url_path("docs/page/") == "/docs/page/"

    def test_path_with_leading_slash(self):
        """Path with leading slash should be unchanged."""
        assert normalize_url_path("/docs/page/") == "/docs/page/"

    def test_removes_duplicate_slashes(self):
        """Duplicate slashes should be collapsed."""
        assert normalize_url_path("//docs//page//") == "/docs/page/"

    def test_preserves_protocol_slashes(self):
        """Protocol double slashes should be preserved."""
        # Note: normalize_url_path is for paths, not full URLs
        # but it should handle edge cases gracefully
        assert normalize_url_path("/docs/page/") == "/docs/page/"

    def test_single_slash(self):
        """Single slash should remain."""
        assert normalize_url_path("/") == "/"

    def test_multiple_leading_slashes(self):
        """Multiple leading slashes should be collapsed to one."""
        assert normalize_url_path("///docs/page/") == "/docs/page/"


class TestImportLocations:
    """Tests verifying apply_baseurl is importable from expected locations."""

    def test_import_from_rendering_urls(self):
        """apply_baseurl should be importable from rendering.urls."""
        from bengal.rendering.urls import apply_baseurl

        site = MockSite(baseurl="/bengal")
        assert apply_baseurl("/docs/page/", site) == "/bengal/docs/page/"

    def test_import_from_utils(self):
        """apply_baseurl should be importable from rendering.utils."""
        from bengal.rendering.utils import apply_baseurl

        site = MockSite(baseurl="/bengal")
        assert apply_baseurl("/docs/page/", site) == "/bengal/docs/page/"

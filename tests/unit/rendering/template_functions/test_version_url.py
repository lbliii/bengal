"""
Tests for version URL template functions.

These functions compute pre-built fallback URLs for version switching,
enabling instant navigation without 404 errors.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from bengal.core.version import Version, VersionConfig
from bengal.rendering.template_functions.version_url import (
    _build_version_page_index,
    _construct_version_url,
    _get_section_index_url,
    _get_version_root_url,
    get_version_target_url,
    invalidate_version_page_index,
    page_exists_in_version,
)


@pytest.fixture
def mock_site():
    """Create a mock site with versioning enabled."""
    site = MagicMock()
    site.versioning_enabled = True

    # Set up version config
    v2 = Version(id="v2", latest=True, label="2.0")
    v1 = Version(id="v1", latest=False, label="1.0")
    version_config = VersionConfig(
        enabled=True,
        versions=[v2, v1],
        sections=["docs"],
    )
    site.version_config = version_config

    # Set up pages
    pages = []

    # v2 (latest) pages
    for url in ["/docs/", "/docs/guide/", "/docs/guide/advanced/", "/docs/api/"]:
        page = MagicMock()
        page.version = "v2"
        page.relative_url = url
        pages.append(page)

    # v1 (older) pages - note: /docs/guide/advanced/ doesn't exist in v1
    for url in ["/docs/", "/docs/guide/", "/docs/legacy/"]:
        page = MagicMock()
        page.version = "v1"
        # v1 pages have version prefix in URL when output
        page.relative_url = url.replace("/docs/", "/docs/v1/")
        pages.append(page)

    site.pages = pages

    # Clear cache before each test
    invalidate_version_page_index()

    return site


@pytest.fixture
def v2_dict():
    """Version 2 (latest) as dict for template."""
    return {"id": "v2", "label": "2.0", "latest": True, "url_prefix": ""}


@pytest.fixture
def v1_dict():
    """Version 1 (older) as dict for template."""
    return {"id": "v1", "label": "1.0", "latest": False, "url_prefix": "/v1"}


class TestGetVersionTargetUrl:
    """Tests for get_version_target_url function."""

    def test_same_version_returns_current_url(self, mock_site, v2_dict):
        """When target is same version, return current URL."""
        page = MagicMock()
        page.version = "v2"
        page.relative_url = "/docs/guide/"

        result = get_version_target_url(page, v2_dict, mock_site)

        assert result == "/docs/guide/"

    def test_exact_page_exists_returns_exact_url(self, mock_site, v1_dict):
        """When exact page exists in target version, return it."""
        page = MagicMock()
        page.version = "v2"
        page.relative_url = "/docs/guide/"

        result = get_version_target_url(page, v1_dict, mock_site)

        # /docs/guide/ exists in v1 as /docs/v1/guide/
        assert result == "/docs/v1/guide/"

    def test_page_missing_falls_back_to_section_index(self, mock_site, v1_dict):
        """When exact page missing, fall back to section index."""
        page = MagicMock()
        page.version = "v2"
        page.relative_url = "/docs/guide/advanced/"  # Doesn't exist in v1

        result = get_version_target_url(page, v1_dict, mock_site)

        # /docs/guide/advanced/ doesn't exist in v1, but /docs/v1/guide/ does
        assert result == "/docs/v1/guide/"

    def test_section_missing_falls_back_to_version_root(self, mock_site, v1_dict):
        """When section index also missing, fall back to version root."""
        page = MagicMock()
        page.version = "v2"
        page.relative_url = "/docs/api/"  # /docs/api/ doesn't exist in v1

        result = get_version_target_url(page, v1_dict, mock_site)

        # Neither /docs/api/ nor /docs/ parent index exist specifically for v1
        # Fall back to version root
        assert result == "/docs/v1/"

    def test_from_older_to_latest_version(self, mock_site, v2_dict):
        """Switching from older to latest version."""
        page = MagicMock()
        page.version = "v1"
        page.relative_url = "/docs/v1/guide/"

        result = get_version_target_url(page, v2_dict, mock_site)

        # /docs/guide/ exists in v2 (latest, no prefix)
        assert result == "/docs/guide/"

    def test_none_page_returns_root(self, mock_site, v1_dict):
        """None page returns root URL."""
        result = get_version_target_url(None, v1_dict, mock_site)
        assert result == "/"

    def test_none_version_returns_root(self, mock_site):
        """None version returns root URL."""
        page = MagicMock()
        page.relative_url = "/docs/guide/"

        result = get_version_target_url(page, None, mock_site)
        assert result == "/"

    def test_versioning_disabled_returns_current_url(self):
        """When versioning disabled, return current URL."""
        site = MagicMock()
        site.versioning_enabled = False

        page = MagicMock()
        page.relative_url = "/docs/guide/"

        result = get_version_target_url(page, {"id": "v1"}, site)
        assert result == "/docs/guide/"


class TestConstructVersionUrl:
    """Tests for URL construction between versions."""

    def test_latest_to_older(self, mock_site):
        """Convert latest URL to older version URL."""
        result = _construct_version_url(
            current_url="/docs/guide/",
            current_version_id="v2",
            target_version_id="v1",
            target_is_latest=False,
            site=mock_site,
        )
        assert result == "/docs/v1/guide/"

    def test_older_to_latest(self, mock_site):
        """Convert older version URL to latest."""
        result = _construct_version_url(
            current_url="/docs/v1/guide/",
            current_version_id="v1",
            target_version_id="v2",
            target_is_latest=True,
            site=mock_site,
        )
        assert result == "/docs/guide/"

    def test_older_to_older(self, mock_site):
        """Convert between two older versions."""
        # Add v3 config
        v3 = Version(id="v3", latest=False)
        mock_site.version_config.versions.append(v3)
        mock_site.version_config._version_map["v3"] = v3

        result = _construct_version_url(
            current_url="/docs/v1/guide/",
            current_version_id="v1",
            target_version_id="v3",
            target_is_latest=False,
            site=mock_site,
        )
        assert result == "/docs/v3/guide/"

    def test_non_versioned_url_unchanged(self, mock_site):
        """URLs outside versioned sections remain unchanged."""
        result = _construct_version_url(
            current_url="/about/",
            current_version_id="v2",
            target_version_id="v1",
            target_is_latest=False,
            site=mock_site,
        )
        assert result == "/about/"


class TestGetSectionIndexUrl:
    """Tests for section index URL extraction."""

    def test_deep_nested_path(self):
        """Get parent for deeply nested path."""
        result = _get_section_index_url("/docs/v1/guide/advanced/")
        assert result == "/docs/v1/guide/"

    def test_shallow_path(self):
        """Get parent for shallow path."""
        result = _get_section_index_url("/docs/guide/")
        assert result == "/docs/"

    def test_version_root_returns_none(self):
        """Version root has no parent."""
        result = _get_section_index_url("/docs/v1/")
        assert result == "/docs/"

    def test_root_returns_none(self):
        """Root path returns None."""
        result = _get_section_index_url("/")
        assert result is None

    def test_empty_returns_none(self):
        """Empty path returns None."""
        result = _get_section_index_url("")
        assert result is None


class TestGetVersionRootUrl:
    """Tests for version root URL generation."""

    def test_latest_version_root(self, mock_site):
        """Latest version root has no prefix."""
        result = _get_version_root_url("v2", is_latest=True, site=mock_site)
        assert result == "/docs/"

    def test_older_version_root(self, mock_site):
        """Older version root has version prefix."""
        result = _get_version_root_url("v1", is_latest=False, site=mock_site)
        assert result == "/docs/v1/"


class TestPageExistsInVersion:
    """Tests for page existence checks."""

    def test_page_exists(self, mock_site):
        """Page that exists returns True."""
        result = page_exists_in_version("/docs/v1/guide/", "v1", mock_site)
        assert result is True

    def test_page_not_exists(self, mock_site):
        """Page that doesn't exist returns False."""
        result = page_exists_in_version("/docs/v1/nonexistent/", "v1", mock_site)
        assert result is False

    def test_handles_trailing_slash_variants(self, mock_site):
        """Handles URLs with and without trailing slashes."""
        # With trailing slash
        result1 = page_exists_in_version("/docs/v1/guide/", "v1", mock_site)
        # Without trailing slash
        result2 = page_exists_in_version("/docs/v1/guide", "v1", mock_site)

        assert result1 is True
        assert result2 is True

    def test_versioning_disabled_returns_false(self):
        """When versioning disabled, always returns False."""
        site = MagicMock()
        site.versioning_enabled = False

        result = page_exists_in_version("/docs/guide/", "v1", site)
        assert result is False


class TestBuildVersionPageIndex:
    """Tests for version page index building."""

    def test_builds_index_by_version(self, mock_site):
        """Index groups pages by version."""
        index = _build_version_page_index(mock_site)

        assert "v2" in index
        assert "v1" in index
        assert "/docs/" in index["v2"]
        assert "/docs/v1/guide/" in index["v1"]

    def test_caches_result(self, mock_site):
        """Index is cached after first call."""
        # First call
        index1 = _build_version_page_index(mock_site)
        # Second call should return same object (cached)
        index2 = _build_version_page_index(mock_site)

        assert index1 is index2

    def test_invalidate_clears_cache(self, mock_site):
        """Invalidate clears the cache."""
        # Build index
        _build_version_page_index(mock_site)

        # Invalidate
        invalidate_version_page_index()

        # Rebuild - should work without error after invalidation
        result = _build_version_page_index(mock_site)

        # Verify the rebuilt index has expected structure
        assert "v2" in result
        assert "v1" in result


class TestIntegration:
    """Integration tests for version URL functions."""

    def test_fallback_cascade_complete(self, mock_site, v1_dict):
        """Test complete fallback cascade from deep page to version root."""
        # Page that doesn't exist anywhere in v1 except root
        page = MagicMock()
        page.version = "v2"
        page.relative_url = "/docs/api/deep/nested/page/"

        result = get_version_target_url(page, v1_dict, mock_site)

        # Should fall back all the way to version root
        assert result == "/docs/v1/"

    def test_round_trip_v2_to_v1_to_v2(self, mock_site, v1_dict, v2_dict):
        """Switching v2 → v1 → v2 should return to original (when page exists)."""
        page = MagicMock()
        page.version = "v2"
        page.relative_url = "/docs/guide/"

        # v2 → v1
        v1_url = get_version_target_url(page, v1_dict, mock_site)
        assert v1_url == "/docs/v1/guide/"

        # Create v1 page mock for return trip
        page_v1 = MagicMock()
        page_v1.version = "v1"
        page_v1.relative_url = v1_url

        # v1 → v2
        v2_url = get_version_target_url(page_v1, v2_dict, mock_site)
        assert v2_url == "/docs/guide/"

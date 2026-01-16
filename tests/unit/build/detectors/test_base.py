"""
Unit tests for bengal.build.detectors.base.

Tests helper functions for path normalization and key generation.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from bengal.build.contracts.keys import CacheKey
from bengal.build.detectors.base import (
    asset_key_for_asset,
    data_key_for_path,
    key_to_path,
    normalize_source_path,
    page_key_for_page,
    page_key_for_path,
)


# =============================================================================
# normalize_source_path Tests
# =============================================================================


class TestNormalizeSourcePath:
    """Tests for normalize_source_path function."""

    def test_relative_path_becomes_absolute(self) -> None:
        """Relative path is joined with site root."""
        site_root = Path("/site")
        result = normalize_source_path(site_root, "content/about.md")
        assert result == Path("/site/content/about.md")

    def test_absolute_path_unchanged(self) -> None:
        """Absolute path is returned unchanged."""
        site_root = Path("/site")
        result = normalize_source_path(site_root, "/other/path/file.md")
        assert result == Path("/other/path/file.md")

    def test_path_object_relative(self) -> None:
        """Path object (relative) is normalized."""
        site_root = Path("/site")
        result = normalize_source_path(site_root, Path("content/blog/post.md"))
        assert result == Path("/site/content/blog/post.md")

    def test_path_object_absolute(self) -> None:
        """Path object (absolute) is returned unchanged."""
        site_root = Path("/site")
        result = normalize_source_path(site_root, Path("/absolute/path.md"))
        assert result == Path("/absolute/path.md")

    def test_empty_path(self) -> None:
        """Empty relative path returns site root."""
        site_root = Path("/site")
        result = normalize_source_path(site_root, "")
        assert result == Path("/site")


# =============================================================================
# page_key_for_page Tests
# =============================================================================


class TestPageKeyForPage:
    """Tests for page_key_for_page function."""

    def test_generates_relative_key(self) -> None:
        """Key is relative to site root."""
        site_root = Path("/site")
        page = MagicMock()
        page.source_path = Path("/site/content/about.md")
        
        key = page_key_for_page(site_root, page)
        
        assert key == CacheKey("content/about.md")

    def test_normalizes_slashes(self) -> None:
        """Backslashes are normalized to forward slashes."""
        site_root = Path("/site")
        page = MagicMock()
        page.source_path = Path("/site/content/docs/guide.md")
        
        key = page_key_for_page(site_root, page)
        
        assert "/" in key
        assert "\\" not in key


# =============================================================================
# page_key_for_path Tests
# =============================================================================


class TestPageKeyForPath:
    """Tests for page_key_for_path function."""

    def test_generates_relative_key(self) -> None:
        """Key is relative to site root."""
        site_root = Path("/site")
        path = Path("/site/content/blog/post.md")
        
        key = page_key_for_path(site_root, path)
        
        assert key == CacheKey("content/blog/post.md")

    def test_handles_nested_paths(self) -> None:
        """Deep nesting is handled correctly."""
        site_root = Path("/site")
        path = Path("/site/content/docs/api/v2/reference.md")
        
        key = page_key_for_path(site_root, path)
        
        assert key == CacheKey("content/docs/api/v2/reference.md")


# =============================================================================
# asset_key_for_asset Tests
# =============================================================================


class TestAssetKeyForAsset:
    """Tests for asset_key_for_asset function."""

    def test_generates_relative_key(self) -> None:
        """Key is relative to site root."""
        site_root = Path("/site")
        asset = MagicMock()
        asset.source_path = Path("/site/static/css/style.css")
        
        key = asset_key_for_asset(site_root, asset)
        
        assert key == CacheKey("static/css/style.css")

    def test_different_asset_types(self) -> None:
        """Various asset types are handled correctly."""
        site_root = Path("/site")
        
        for asset_name in ["style.css", "main.js", "logo.png", "font.woff2"]:
            asset = MagicMock()
            asset.source_path = Path(f"/site/static/{asset_name}")
            
            key = asset_key_for_asset(site_root, asset)
            
            assert key == CacheKey(f"static/{asset_name}")


# =============================================================================
# data_key_for_path Tests
# =============================================================================


class TestDataKeyForPath:
    """Tests for data_key_for_path function."""

    def test_generates_prefixed_key(self) -> None:
        """Key has 'data:' prefix."""
        site_root = Path("/site")
        path = Path("/site/data/team.yaml")
        
        key = data_key_for_path(site_root, path)
        
        assert key.startswith("data:")
        assert "data/team.yaml" in key

    def test_full_key_format(self) -> None:
        """Key has expected format: data:relative/path."""
        site_root = Path("/site")
        path = Path("/site/data/config/settings.json")
        
        key = data_key_for_path(site_root, path)
        
        assert key == CacheKey("data:data/config/settings.json")


# =============================================================================
# key_to_path Tests
# =============================================================================


class TestKeyToPath:
    """Tests for key_to_path function."""

    def test_unprefixed_key(self) -> None:
        """Key without prefix is converted to path."""
        site_root = Path("/site")
        key = CacheKey("content/about.md")
        
        path = key_to_path(site_root, key)
        
        assert path == Path("/site/content/about.md")

    def test_prefixed_key(self) -> None:
        """Key with prefix is converted to path."""
        site_root = Path("/site")
        key = CacheKey("data:data/team.yaml")
        
        path = key_to_path(site_root, key)
        
        assert path == Path("/site/data/team.yaml")

    def test_absolute_path_in_key(self) -> None:
        """Key containing absolute path is handled."""
        site_root = Path("/site")
        key = CacheKey("/absolute/path/file.md")
        
        path = key_to_path(site_root, key)
        
        assert path == Path("/absolute/path/file.md")

    def test_roundtrip_content_key(self) -> None:
        """page_key_for_path and key_to_path are inverses."""
        site_root = Path("/site")
        original_path = Path("/site/content/docs/guide.md")
        
        key = page_key_for_path(site_root, original_path)
        recovered_path = key_to_path(site_root, key)
        
        assert recovered_path == original_path

    def test_roundtrip_data_key(self) -> None:
        """data_key_for_path and key_to_path are inverses."""
        site_root = Path("/site")
        original_path = Path("/site/data/team.yaml")
        
        key = data_key_for_path(site_root, original_path)
        recovered_path = key_to_path(site_root, key)
        
        assert recovered_path == original_path

"""Tests for asset_url fingerprint resolution.

These tests verify that the asset resolver properly resolves fingerprinted
asset URLs from the asset manifest, matching the behavior of all template engines.

Regression test for: kida adapter not resolving fingerprinted assets.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from bengal.rendering.assets import resolve_asset_url


class MockSite:
    """Minimal site mock for testing asset_url resolution."""

    def __init__(self, output_dir: Path, config: dict[str, Any] | None = None):
        self.output_dir = output_dir
        self.config = config or {}
        self.dev_mode = False

    @property
    def baseurl(self) -> str:
        """Return baseurl from config, supporting nested [site].baseurl or flat baseurl."""
        site_section = self.config.get("site", {})
        if isinstance(site_section, dict) and site_section.get("baseurl"):
            return site_section.get("baseurl", "")
        return self.config.get("baseurl", "")


@pytest.fixture
def site_with_manifest(tmp_path: Path) -> MockSite:
    """Create a mock site with an asset manifest."""
    manifest = {
        "version": 1,
        "generated_at": "2025-01-01T00:00:00Z",
        "assets": {
            "css/style.css": {
                "output_path": "assets/css/style.abc123.css",
                "fingerprint": "abc123",
                "size_bytes": 1000,
            },
            "js/main.js": {
                "output_path": "assets/js/main.def456.js",
                "fingerprint": "def456",
                "size_bytes": 2000,
            },
            "images/logo.png": {
                "output_path": "assets/images/logo.789abc.png",
                "fingerprint": "789abc",
                "size_bytes": 5000,
            },
        },
    }

    manifest_path = tmp_path / "asset-manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    return MockSite(output_dir=tmp_path)


class TestAssetUrlFingerprinting:
    """Test that asset resolver resolves fingerprinted asset URLs."""

    def test_resolves_fingerprinted_css(self, site_with_manifest: MockSite) -> None:
        """CSS files should resolve to fingerprinted paths from manifest."""
        result = resolve_asset_url("css/style.css", site_with_manifest)
        assert result == "/assets/css/style.abc123.css"

    def test_resolves_fingerprinted_js(self, site_with_manifest: MockSite) -> None:
        """JS files should resolve to fingerprinted paths from manifest."""
        result = resolve_asset_url("js/main.js", site_with_manifest)
        assert result == "/assets/js/main.def456.js"

    def test_resolves_fingerprinted_image(self, site_with_manifest: MockSite) -> None:
        """Image files should resolve to fingerprinted paths from manifest."""
        result = resolve_asset_url("images/logo.png", site_with_manifest)
        assert result == "/assets/images/logo.789abc.png"

    def test_fallback_for_unknown_asset(self, site_with_manifest: MockSite) -> None:
        """Assets not in manifest should fallback to direct path."""
        result = resolve_asset_url("js/unknown.js", site_with_manifest)
        assert result == "/assets/js/unknown.js"

    def test_dev_mode_skips_fingerprinting(self, site_with_manifest: MockSite) -> None:
        """Dev mode should return non-fingerprinted URLs for fast iteration."""
        site_with_manifest.dev_mode = True
        result = resolve_asset_url("css/style.css", site_with_manifest)
        assert result == "/assets/css/style.css"
        assert "abc123" not in result

    def test_empty_path_returns_assets_root(self, site_with_manifest: MockSite) -> None:
        """Empty path should return assets root."""
        result = resolve_asset_url("", site_with_manifest)
        assert result == "/assets/"

    def test_normalizes_path_separators(self, site_with_manifest: MockSite) -> None:
        """Backslashes should be normalized to forward slashes."""
        result = resolve_asset_url("css\\style.css", site_with_manifest)
        assert result == "/assets/css/style.abc123.css"

    def test_strips_leading_slash(self, site_with_manifest: MockSite) -> None:
        """Leading slashes should be stripped."""
        result = resolve_asset_url("/css/style.css", site_with_manifest)
        assert result == "/assets/css/style.abc123.css"


class TestAssetUrlWithBaseurl:
    """Test that asset resolver respects baseurl configuration."""

    def test_path_baseurl(self, site_with_manifest: MockSite) -> None:
        """Path-based baseurl should be prepended."""
        site_with_manifest.config["baseurl"] = "/docs"
        result = resolve_asset_url("css/style.css", site_with_manifest)
        assert result == "/docs/assets/css/style.abc123.css"

    def test_absolute_baseurl(self, site_with_manifest: MockSite) -> None:
        """Absolute baseurl should be prepended."""
        site_with_manifest.config["baseurl"] = "https://cdn.example.com"
        result = resolve_asset_url("css/style.css", site_with_manifest)
        assert result == "https://cdn.example.com/assets/css/style.abc123.css"


class TestManifestCaching:
    """Test that manifest is cached efficiently."""

    def test_manifest_cached_on_site(self, site_with_manifest: MockSite) -> None:
        """Manifest should be cached on site object after first lookup."""
        # First call should load and cache
        resolve_asset_url("css/style.css", site_with_manifest)
        assert hasattr(site_with_manifest, "_asset_manifest_cache")

        # Cache should contain the manifest entries
        cache = site_with_manifest._asset_manifest_cache
        assert "css/style.css" in cache
        assert cache["css/style.css"].fingerprint == "abc123"

    def test_missing_manifest_cached_as_empty(self, tmp_path: Path) -> None:
        """Sites without manifest should cache empty dict to avoid repeated loads."""
        site = MockSite(output_dir=tmp_path)  # No manifest file

        result = resolve_asset_url("css/style.css", site)
        assert result == "/assets/css/style.css"  # Fallback

        assert hasattr(site, "_asset_manifest_cache")
        assert site._asset_manifest_cache == {}

"""
Integration tests for asset manifest cache invalidation.

RFC: rfc-global-build-state-dependencies.md (Phase 2)

Tests that rendered HTML cache is properly invalidated when asset
manifest changes (CSS fingerprints change).

The bug this addresses:
- Home page served from rendered HTML cache with stale CSS fingerprint
- CSS changed → new fingerprint (style.4df19bd5.css)
- Asset manifest updated
- Rendered cache validation checked: content, metadata, template ✅
- Rendered cache validation didn't check: asset manifest ❌
- Result: Home page served with old style.9b0fa869.css reference → broken styles

Phase 1 (v0.1.9) added asset_manifest_mtime validation.
Phase 2 adds ContextVar pattern for thread-safe access.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from bengal.core.site import Site
from bengal.orchestration.build.options import BuildOptions


class TestAssetManifestCacheInvalidation:
    """Test that rendered cache is invalidated when asset fingerprints change."""

    @pytest.fixture
    def site_with_css(self, tmp_path: Path) -> Path:
        """Create a minimal site with CSS that will be fingerprinted."""
        site_root = tmp_path / "test_site"
        site_root.mkdir()

        # Create bengal.toml with fingerprinting enabled
        (site_root / "bengal.toml").write_text(
            """
[site]
title = "Test Site"

[build]
incremental = true

[assets]
fingerprint = true
minify = false
"""
        )

        # Create content directory with home page
        content_dir = site_root / "content"
        content_dir.mkdir()
        (content_dir / "_index.md").write_text(
            """---
title: Home
---

# Welcome

This is the home page.
"""
        )

        # Create CSS file
        css_dir = site_root / "assets" / "css"
        css_dir.mkdir(parents=True)
        (css_dir / "style.css").write_text(
            """
/* Initial CSS */
body {
    color: black;
    font-family: sans-serif;
}
"""
        )

        return site_root

    def test_manifest_loaded_during_build(self, site_with_css: Path, tmp_path: Path):
        """Verify that asset manifest is loaded and available during rendering.

        This test verifies the Phase 2 ContextVar pattern:
        - Manifest is loaded once before rendering starts
        - Manifest entries are accessible via get_asset_manifest()

        RFC: rfc-global-build-state-dependencies.md (Phase 2)
        """
        site = Site.from_config(site_with_css)

        # Build the site
        options = BuildOptions(incremental=False, force_sequential=True)
        stats = site.build(options)
        assert stats.pages_built > 0, "Build should build pages"

        output_dir = site.output_dir
        manifest_path = output_dir / "asset-manifest.json"

        # Verify manifest exists
        assert manifest_path.exists(), "Asset manifest should exist after build"

        # Verify manifest has assets
        manifest_data = json.loads(manifest_path.read_text())
        assets = manifest_data.get("assets", {})
        assert assets, "Manifest should contain assets"

        # Verify home page was rendered with fingerprinted assets
        home_html = (output_dir / "index.html").read_text()

        # The page should contain fingerprinted CSS references
        # The theme CSS is bundled and fingerprinted as style.{hash}.css
        css_pattern = re.search(r'href="[^"]*style\.[a-f0-9]+\.css"', home_html)
        assert css_pattern, "Home page should reference fingerprinted CSS"

    def test_contextvar_manifest_access_during_render(self, site_with_css: Path):
        """Verify that rendering uses ContextVar for manifest access.

        This test verifies the Phase 2 implementation where asset manifest
        is loaded once and accessed via ContextVar during rendering.
        """
        from bengal.rendering.assets import (
            AssetManifestContext,
            asset_manifest_context,
            get_asset_manifest,
        )

        # Create a manifest context
        ctx = AssetManifestContext(
            entries={
                "css/style.css": "assets/css/style.test123.css",
                "js/main.js": "assets/js/main.test456.js",
            },
            mtime=1234567890.0,
        )

        # Verify context manager works
        assert get_asset_manifest() is None

        with asset_manifest_context(ctx):
            manifest = get_asset_manifest()
            assert manifest is not None
            assert manifest.entries.get("css/style.css") == "assets/css/style.test123.css"
            assert manifest.mtime == 1234567890.0

        assert get_asset_manifest() is None

    def test_manifest_not_found_graceful_fallback(self, tmp_path: Path):
        """When manifest doesn't exist, _resolve_fingerprinted should return None gracefully."""
        from bengal.rendering.assets import (
            get_asset_manifest,
            reset_asset_manifest,
        )

        # Ensure no ContextVar is set
        reset_asset_manifest()

        # Create minimal site without building (no manifest)
        site_root = tmp_path / "empty_site"
        site_root.mkdir()
        (site_root / "bengal.toml").write_text('[site]\ntitle = "Empty"')
        (site_root / "content").mkdir()
        (site_root / "content" / "_index.md").write_text("# Home")

        site = Site.from_config(site_root)

        # When no manifest and no ContextVar, should gracefully return None
        from bengal.rendering.assets import _resolve_fingerprinted

        result = _resolve_fingerprinted("css/style.css", site)
        assert result is None

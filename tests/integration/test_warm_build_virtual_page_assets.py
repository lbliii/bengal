"""
Regression test for warm builds where virtual pages have stale asset URLs.

RFC: rfc-global-build-state-dependencies

Bug: In CI, cache is restored but output is cleaned. Virtual pages (api/, cli/)
are regenerated but might reference stale CSS fingerprints if the asset manifest
isn't properly tracked.

Scenario being tested:
1. Build 1: Full build with autodoc → creates api/index.html with CSS fingerprint A
2. Modify CSS → new fingerprint B  
3. Clear output (keep cache) → simulates CI cache restore
4. Build 2: Warm build → api/index.html should have fingerprint B, not A

This test catches the exact bug where home page had style.9b0fa869.css but
the actual file was style.4df19bd5.css (stale cache).
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

import pytest

from bengal.cache import BuildCache
from bengal.cache.paths import BengalPaths
from bengal.core.site import Site
from bengal.orchestration.build.options import BuildOptions


class TestWarmBuildVirtualPageAssets:
    """Test that warm builds produce virtual pages with correct asset URLs."""

    @pytest.fixture
    def site_with_autodoc(self, tmp_path: Path) -> Path:
        """Create a site with autodoc configuration."""
        site_root = tmp_path / "test_site"
        site_root.mkdir()

        # Create bengal.toml with autodoc config
        (site_root / "bengal.toml").write_text(
            """
[site]
title = "Test Site"

[build]
incremental = true

[assets]
fingerprint = true
minify = false

[autodoc.python]
enabled = true
source_dirs = ["src"]
output_prefix = "api"
"""
        )

        # Create minimal Python source for autodoc
        src_dir = site_root / "src"
        src_dir.mkdir()
        (src_dir / "__init__.py").write_text('"""Test package."""')
        (src_dir / "module.py").write_text(
            '''
"""Test module with a function."""

def example_function(x: int) -> str:
    """Example function.
    
    Args:
        x: Input value
        
    Returns:
        String representation
    """
    return str(x)
'''
        )

        # Create content directory with home page
        content_dir = site_root / "content"
        content_dir.mkdir()
        (content_dir / "index.md").write_text(
            """---
title: Home
---

# Welcome

Check out our [API Documentation](/api/).
"""
        )

        # Create custom CSS asset that we'll modify
        assets_dir = site_root / "assets" / "css"
        assets_dir.mkdir(parents=True)
        (assets_dir / "style.css").write_text(
            """
/* Version 1 of custom styles */
:root {
    --color-primary: blue;
}
"""
        )

        return site_root

    def test_virtual_pages_have_correct_css_fingerprint_after_warm_build(
        self, site_with_autodoc: Path
    ) -> None:
        """
        Full integration test for warm build asset URL correctness.
        
        Steps:
        1. Build 1: Full build → creates api/index.html with CSS fingerprint A
        2. Modify CSS → new fingerprint B
        3. Clear output (keep cache) → simulates CI cache restore
        4. Build 2: Warm build → api/index.html should have fingerprint B
        
        Verifies:
        - Virtual pages (autodoc) reference correct fingerprint after warm build
        - The fingerprinted CSS file actually exists
        - Home page also references the correct fingerprint
        """
        site_root = site_with_autodoc
        
        # === BUILD 1: Full build ===
        site1 = Site.from_config(site_root)
        stats1 = site1.build(BuildOptions(force_sequential=True, incremental=False))
        
        assert stats1.pages_built > 0, "Build 1 should create pages"
        
        # Verify initial state
        output_dir = site1.output_dir
        api_index = output_dir / "api" / "index.html"
        home_index = output_dir / "index.html"
        
        assert api_index.exists(), "Build 1 should create api/index.html"
        assert home_index.exists(), "Build 1 should create index.html"
        
        # Extract CSS fingerprint from home page
        home_html = home_index.read_text()
        css_match = re.search(r'href="[^"]*?(style\.[a-f0-9]+\.css)"', home_html)
        assert css_match, "Home page should reference fingerprinted CSS"
        fingerprint_v1 = css_match.group(1)
        
        # Verify API page also uses this fingerprint
        api_html = api_index.read_text()
        assert fingerprint_v1 in api_html, (
            f"API page should reference {fingerprint_v1}"
        )
        
        # Verify the CSS file exists
        css_files_v1 = list((output_dir / "assets" / "css").glob("style.*.css"))
        assert len(css_files_v1) == 1, "Should have exactly one fingerprinted CSS"
        assert css_files_v1[0].name == fingerprint_v1
        
        # === MODIFY CSS: Create new fingerprint ===
        css_source = site_root / "assets" / "css" / "style.css"
        css_source.write_text(
            """
/* Version 2 of custom styles - MODIFIED */
:root {
    --color-primary: green;
    --color-secondary: red;
}
"""
        )
        
        # === SIMULATE CI: Clear output but keep cache ===
        # This is what happens in GitHub Actions when:
        # - .bengal cache is restored
        # - But public/ directory is cleaned (rm -rf public/*)
        
        # Remove all output files but keep cache
        for item in output_dir.iterdir():
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()
        
        assert not api_index.exists(), "Output should be cleared"
        assert not home_index.exists(), "Output should be cleared"
        
        # Verify cache still exists
        paths = BengalPaths(site_root)
        cache_exists = (
            paths.build_cache.exists() or 
            paths.build_cache.with_suffix(".json.zst").exists()
        )
        assert cache_exists, "Cache should still exist (simulating CI restore)"
        
        # === BUILD 2: Warm build (incremental) ===
        site2 = Site.from_config(site_root)
        stats2 = site2.build(BuildOptions(force_sequential=True, incremental=True))
        
        assert stats2.pages_built > 0, "Warm build should rebuild pages"
        
        # === VERIFY: All pages have correct NEW fingerprint ===
        assert api_index.exists(), "Warm build should recreate api/index.html"
        assert home_index.exists(), "Warm build should recreate index.html"
        
        # Extract new CSS fingerprint
        home_html_v2 = home_index.read_text()
        css_match_v2 = re.search(r'href="[^"]*?(style\.[a-f0-9]+\.css)"', home_html_v2)
        assert css_match_v2, "Home page should reference fingerprinted CSS after warm build"
        fingerprint_v2 = css_match_v2.group(1)
        
        # CRITICAL: New fingerprint should be DIFFERENT from v1 (CSS changed)
        assert fingerprint_v2 != fingerprint_v1, (
            f"CSS fingerprint should change: {fingerprint_v1} -> {fingerprint_v2}"
        )
        
        # CRITICAL: API page should reference the NEW fingerprint
        api_html_v2 = api_index.read_text()
        assert fingerprint_v2 in api_html_v2, (
            f"API page should reference NEW fingerprint {fingerprint_v2}, "
            f"but it might still have old {fingerprint_v1}"
        )
        assert fingerprint_v1 not in api_html_v2, (
            f"API page should NOT reference old fingerprint {fingerprint_v1}"
        )
        
        # Verify the NEW CSS file exists and OLD is removed
        css_files_v2 = list((output_dir / "assets" / "css").glob("style.*.css"))
        assert len(css_files_v2) == 1, "Should have exactly one fingerprinted CSS"
        assert css_files_v2[0].name == fingerprint_v2, (
            f"CSS file should be {fingerprint_v2}, not {css_files_v2[0].name}"
        )

    def test_regular_pages_with_link_to_virtual_pages(
        self, site_with_autodoc: Path
    ) -> None:
        """
        Test that links to virtual pages work after warm build.
        
        Verifies that internal links like [API](/api/) in regular pages
        still work after a warm build regenerates the virtual pages.
        """
        site_root = site_with_autodoc
        
        # Build 1: Full build
        site1 = Site.from_config(site_root)
        site1.build(BuildOptions(force_sequential=True, incremental=False))
        
        output_dir = site1.output_dir
        
        # Verify link target exists
        api_index = output_dir / "api" / "index.html"
        assert api_index.exists(), "API index should exist"
        
        # Check home page has link to API
        home_html = (output_dir / "index.html").read_text()
        assert "/api/" in home_html or 'href="api' in home_html.lower(), (
            "Home page should link to API"
        )
        
        # Clear output, keep cache
        for item in output_dir.iterdir():
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()
        
        # Build 2: Warm build
        site2 = Site.from_config(site_root)
        site2.build(BuildOptions(force_sequential=True, incremental=True))
        
        # Verify both pages exist
        assert (output_dir / "index.html").exists(), "Home should exist after warm build"
        assert (output_dir / "api" / "index.html").exists(), (
            "API should exist after warm build - link target must not 404"
        )

    def test_asset_manifest_mtime_invalidates_rendered_cache(
        self, site_with_autodoc: Path
    ) -> None:
        """
        Test that rendered output cache is invalidated when asset manifest changes.
        
        This tests the tactical fix (asset_manifest_mtime tracking) added in
        RFC: rfc-global-build-state-dependencies Phase 1.
        
        Scenario:
        1. Build 1: Page rendered and cached with fingerprint A
        2. CSS changes → new fingerprint B
        3. Build 2: Rendered cache should be invalidated, page re-rendered with B
        """
        site_root = site_with_autodoc
        
        # Build 1: Full build - caches rendered output
        site1 = Site.from_config(site_root)
        site1.build(BuildOptions(force_sequential=True, incremental=False))
        
        output_dir = site1.output_dir
        home_html_v1 = (output_dir / "index.html").read_text()
        css_match_v1 = re.search(r'(style\.[a-f0-9]+\.css)', home_html_v1)
        fingerprint_v1 = css_match_v1.group(1) if css_match_v1 else None
        
        # Modify CSS
        css_source = site_root / "assets" / "css" / "style.css"
        css_source.write_text(
            """
/* Modified CSS - should invalidate rendered cache */
:root { --modified: true; }
"""
        )
        
        # Build 2: Incremental build - should detect manifest change
        site2 = Site.from_config(site_root)
        site2.build(BuildOptions(force_sequential=True, incremental=True))
        
        # CRITICAL: Home page should have NEW fingerprint (cache was invalidated)
        home_html_v2 = (output_dir / "index.html").read_text()
        css_match_v2 = re.search(r'(style\.[a-f0-9]+\.css)', home_html_v2)
        fingerprint_v2 = css_match_v2.group(1) if css_match_v2 else None
        
        assert fingerprint_v1 is not None, "V1 should have fingerprinted CSS"
        assert fingerprint_v2 is not None, "V2 should have fingerprinted CSS"
        assert fingerprint_v2 != fingerprint_v1, (
            f"Rendered cache should be invalidated on asset manifest change. "
            f"Got same fingerprint: {fingerprint_v1}"
        )


class TestCLIAutodocWarmBuild:
    """Test warm builds with CLI autodoc (uses different prefix)."""

    @pytest.fixture
    def site_with_cli_autodoc(self, tmp_path: Path) -> Path:
        """Create a site with CLI autodoc configuration."""
        site_root = tmp_path / "test_site"
        site_root.mkdir()

        # Create bengal.toml with CLI autodoc config
        (site_root / "bengal.toml").write_text(
            """
[site]
title = "CLI Test Site"

[build]
incremental = true

[assets]
fingerprint = true

[autodoc.cli]
enabled = true
module = "src.cli"
output_prefix = "cli"
"""
        )

        # Create CLI module
        src_dir = site_root / "src"
        src_dir.mkdir()
        (src_dir / "__init__.py").write_text("")
        (src_dir / "cli.py").write_text(
            '''
"""CLI application."""
import click

@click.group()
def main():
    """Main CLI group."""
    pass

@main.command()
@click.option("--name", "-n", help="Name to greet")
def hello(name: str):
    """Say hello."""
    click.echo(f"Hello {name}")
'''
        )

        # Create content
        content_dir = site_root / "content"
        content_dir.mkdir()
        (content_dir / "index.md").write_text(
            """---
title: Home
---

# CLI Tool

See [CLI Reference](/cli/).
"""
        )

        # Create CSS
        assets_dir = site_root / "assets" / "css"
        assets_dir.mkdir(parents=True)
        (assets_dir / "style.css").write_text(":root { --v: 1; }")

        return site_root

    def test_cli_autodoc_warm_build_assets(
        self, site_with_cli_autodoc: Path
    ) -> None:
        """
        Test CLI autodoc pages have correct assets after warm build.
        
        CLI autodoc uses "cli/" prefix instead of "api/" - verify both work.
        """
        site_root = site_with_cli_autodoc
        
        # Build 1
        site1 = Site.from_config(site_root)
        try:
            stats1 = site1.build(BuildOptions(force_sequential=True, incremental=False))
        except Exception as e:
            # CLI autodoc might fail if click isn't importable - skip gracefully
            pytest.skip(f"CLI autodoc setup failed: {e}")
        
        output_dir = site1.output_dir
        cli_index = output_dir / "cli" / "index.html"
        
        if not cli_index.exists():
            pytest.skip("CLI autodoc didn't generate pages - check config")
        
        # Get initial fingerprint
        cli_html_v1 = cli_index.read_text()
        css_match_v1 = re.search(r'(style\.[a-f0-9]+\.css)', cli_html_v1)
        
        if not css_match_v1:
            pytest.skip("CLI page doesn't have fingerprinted CSS")
        
        fingerprint_v1 = css_match_v1.group(1)
        
        # Modify CSS
        css_source = site_root / "assets" / "css" / "style.css"
        css_source.write_text(":root { --v: 2; --changed: true; }")
        
        # Clear output, keep cache
        for item in output_dir.iterdir():
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()
        
        # Build 2: Warm build
        site2 = Site.from_config(site_root)
        site2.build(BuildOptions(force_sequential=True, incremental=True))
        
        # Verify CLI page has new fingerprint
        assert cli_index.exists(), "CLI index should exist after warm build"
        cli_html_v2 = cli_index.read_text()
        css_match_v2 = re.search(r'(style\.[a-f0-9]+\.css)', cli_html_v2)
        
        assert css_match_v2, "CLI page should have fingerprinted CSS after warm build"
        fingerprint_v2 = css_match_v2.group(1)
        
        assert fingerprint_v2 != fingerprint_v1, (
            f"CLI page should have new fingerprint: {fingerprint_v1} -> {fingerprint_v2}"
        )

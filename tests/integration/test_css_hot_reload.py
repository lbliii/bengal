"""
Regression test for CSS styling during hot reload (incremental builds).

GitHub Issue: #130 - CSS styling breaks during hot reload (incremental builds)

Bug: CSS styling intermittently stops loading during hot reload in the dev server.
When only content files change, asset discovery is skipped and CSS processing
can be incorrectly bypassed, resulting in missing/stale CSS in output.

The fix ensures:
1. Asset change detection receives file watcher changes (changed_sources param)
2. CSS entry points are validated in output before skipping asset processing
3. Arbitrary file count thresholds are replaced with specific CSS checks
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from bengal.core.site import Site
from bengal.orchestration.build.options import BuildOptions


class TestCSSHotReload:
    """Test that CSS survives incremental builds when only content changes."""

    @pytest.fixture
    def site_with_css_and_content(self, tmp_path: Path) -> Path:
        """Create a minimal site with CSS and multiple content pages."""
        site_root = tmp_path / "test_site"
        site_root.mkdir()

        # Create bengal.toml with incremental builds enabled
        (site_root / "bengal.toml").write_text(
            """
[site]
title = "Hot Reload Test Site"

[build]
incremental = true

[assets]
fingerprint = true
minify = false
"""
        )

        # Create content directory with multiple pages
        content_dir = site_root / "content"
        content_dir.mkdir()
        
        (content_dir / "index.md").write_text(
            """---
title: Home
---

# Welcome

This is the home page.
"""
        )
        
        (content_dir / "about.md").write_text(
            """---
title: About
---

# About Us

This is the about page.
"""
        )

        # Create CSS asset (entry point)
        assets_dir = site_root / "assets" / "css"
        assets_dir.mkdir(parents=True)
        (assets_dir / "style.css").write_text(
            """
/* Site styles */
:root {
    --color-primary: blue;
    --font-size-base: 16px;
}

body {
    font-family: system-ui, sans-serif;
    color: var(--color-primary);
}
"""
        )

        return site_root

    def test_css_survives_content_only_incremental_build(
        self, site_with_css_and_content: Path
    ) -> None:
        """
        Test that CSS remains intact when only content changes.
        
        This is the core regression test for Issue #130 where CSS would
        intermittently break during hot reload when editing markdown files.
        
        Scenario:
        1. Full build creates CSS in output
        2. User edits markdown (content only, no CSS changes)
        3. Incremental build runs
        4. CSS should still exist and be referenced correctly
        """
        site_root = site_with_css_and_content
        about_file = site_root / "content" / "about.md"

        # Build 1: Full build
        site1 = Site.from_config(site_root)
        stats1 = site1.build(BuildOptions(force_sequential=True, incremental=False))

        assert stats1.pages_built >= 2, "Build 1 should create at least 2 pages"

        output_dir = site1.output_dir
        home_index = output_dir / "index.html"
        about_index = output_dir / "about" / "index.html"
        
        assert home_index.exists(), "Build 1 should create index.html"
        assert about_index.exists(), "Build 1 should create about/index.html"

        # Verify CSS exists in output
        css_dir = output_dir / "assets" / "css"
        assert css_dir.exists(), "CSS directory should exist after full build"
        
        css_files_v1 = list(css_dir.glob("style*.css"))
        assert len(css_files_v1) >= 1, "Should have CSS file after full build"

        # Extract CSS reference from home page
        html1 = home_index.read_text()
        css_match1 = re.search(r'href="[^"]*?(style[^"]*\.css)"', html1)
        assert css_match1, "Home page should reference CSS"
        css_ref_v1 = css_match1.group(1)

        # Modify ONLY content (no CSS changes)
        about_file.write_text(
            """---
title: About Us
---

# About Our Company

This page has been updated with new content.
More information about what we do.
"""
        )

        # Build 2: Incremental build (content changed, CSS didn't)
        site2 = Site.from_config(site_root)
        site2.build(
            BuildOptions(
                force_sequential=True,
                incremental=True,
                changed_sources={about_file},  # Simulate file watcher
            )
        )

        # CRITICAL: CSS should still exist in output after incremental build
        assert css_dir.exists(), "CSS directory should exist after incremental build"
        
        css_files_v2 = list(css_dir.glob("style*.css"))
        assert len(css_files_v2) >= 1, (
            "CSS file should exist after incremental build. "
            "This is the core Issue #130 regression - CSS was disappearing."
        )

        # Verify home page still references CSS correctly
        html2 = home_index.read_text()
        css_match2 = re.search(r'href="[^"]*?(style[^"]*\.css)"', html2)
        assert css_match2, (
            "Home page should still reference CSS after incremental build. "
            "Missing CSS reference indicates Issue #130 regression."
        )

        # CSS reference should be unchanged (we didn't modify CSS)
        css_ref_v2 = css_match2.group(1)
        assert css_ref_v2 == css_ref_v1, (
            f"CSS reference should remain stable: {css_ref_v1}. "
            "Changed reference indicates unnecessary CSS reprocessing."
        )

    def test_css_revalidated_when_output_cleaned(
        self, site_with_css_and_content: Path
    ) -> None:
        """
        Test that CSS is re-created if output is cleaned during incremental build.
        
        This tests the defensive check that validates CSS output exists
        before skipping asset processing.
        """
        site_root = site_with_css_and_content
        about_file = site_root / "content" / "about.md"

        # Build 1: Full build
        site1 = Site.from_config(site_root)
        site1.build(BuildOptions(force_sequential=True, incremental=False))

        output_dir = site1.output_dir
        css_dir = output_dir / "assets" / "css"
        
        assert css_dir.exists(), "CSS directory should exist after full build"

        # Simulate partial output cleanup (CSS deleted but other files remain)
        for css_file in css_dir.glob("style*.css"):
            css_file.unlink()

        # Modify content to trigger incremental build
        about_file.write_text(
            """---
title: About
---

# About Page Updated

Content was modified.
"""
        )

        # Build 2: Incremental build with CSS missing
        site2 = Site.from_config(site_root)
        site2.build(
            BuildOptions(
                force_sequential=True,
                incremental=True,
                changed_sources={about_file},
            )
        )

        # CSS should be regenerated
        css_files = list(css_dir.glob("style*.css"))
        assert len(css_files) >= 1, (
            "CSS should be regenerated when missing from output. "
            "This tests the defensive CSS validation check."
        )

    def test_multiple_content_changes_preserve_css(
        self, site_with_css_and_content: Path
    ) -> None:
        """
        Test that multiple sequential content changes preserve CSS.
        
        This simulates rapid editing during development where the user
        makes multiple changes without CSS ever being touched.
        """
        site_root = site_with_css_and_content
        about_file = site_root / "content" / "about.md"
        index_file = site_root / "content" / "index.md"

        # Build 1: Full build
        site1 = Site.from_config(site_root)
        site1.build(BuildOptions(force_sequential=True, incremental=False))

        output_dir = site1.output_dir
        css_dir = output_dir / "assets" / "css"

        # Get initial CSS state
        css_files_initial = {f.name for f in css_dir.glob("style*.css")}
        assert css_files_initial, "Should have CSS files after initial build"

        # Simulate 3 rapid content edits
        for i in range(3):
            # Alternate between files
            target_file = about_file if i % 2 == 0 else index_file
            target_file.write_text(
                f"""---
title: {"About" if i % 2 == 0 else "Home"}
---

# Content Update {i + 1}

This is edit number {i + 1}.
"""
            )

            site_n = Site.from_config(site_root)
            site_n.build(
                BuildOptions(
                    force_sequential=True,
                    incremental=True,
                    changed_sources={target_file},
                )
            )

            # Verify CSS still exists after each build
            css_files_current = {f.name for f in css_dir.glob("style*.css")}
            assert css_files_current, (
                f"CSS should exist after incremental build {i + 1}. "
                "This tests that rapid content changes don't break CSS."
            )


class TestCSSHotReloadEdgeCases:
    """Edge case tests for CSS hot reload scenarios."""

    @pytest.fixture
    def site_without_theme(self, tmp_path: Path) -> Path:
        """Create a minimal site without a theme (no CSS)."""
        site_root = tmp_path / "bare_site"
        site_root.mkdir()

        (site_root / "bengal.toml").write_text(
            """
[site]
title = "Bare Site"

[build]
incremental = true
"""
        )

        content_dir = site_root / "content"
        content_dir.mkdir()
        (content_dir / "index.md").write_text(
            """---
title: Home
---

# Bare Site

No CSS expected here.
"""
        )

        return site_root

    @pytest.fixture
    def site_without_fingerprinting(self, tmp_path: Path) -> Path:
        """Create a site with CSS but fingerprinting disabled."""
        site_root = tmp_path / "no_fingerprint_site"
        site_root.mkdir()

        (site_root / "bengal.toml").write_text(
            """
[site]
title = "No Fingerprint Site"

[build]
incremental = true

[assets]
fingerprint = false
minify = false
"""
        )

        content_dir = site_root / "content"
        content_dir.mkdir()
        (content_dir / "index.md").write_text(
            """---
title: Home
---

# Welcome
"""
        )
        (content_dir / "about.md").write_text(
            """---
title: About
---

# About
"""
        )

        assets_dir = site_root / "assets" / "css"
        assets_dir.mkdir(parents=True)
        (assets_dir / "style.css").write_text(
            """
body { color: black; }
"""
        )

        return site_root

    def test_no_theme_site_builds_without_error(
        self, site_without_theme: Path
    ) -> None:
        """
        Test that sites without themes (no CSS) build correctly.
        
        The CSS validation should not cause errors when there's no theme
        and no CSS is expected.
        """
        site_root = site_without_theme
        index_file = site_root / "content" / "index.md"

        # Build 1: Full build
        site1 = Site.from_config(site_root)
        stats1 = site1.build(BuildOptions(force_sequential=True, incremental=False))

        assert stats1.pages_built >= 1, "Should build at least one page"

        # Modify content
        index_file.write_text(
            """---
title: Home Updated
---

# Updated Bare Site

Content was changed.
"""
        )

        # Build 2: Incremental build should work without CSS validation errors
        site2 = Site.from_config(site_root)
        stats2 = site2.build(
            BuildOptions(
                force_sequential=True,
                incremental=True,
                changed_sources={index_file},
            )
        )

        # Should complete without errors
        assert stats2.pages_built >= 1, "Should rebuild modified page"

    def test_css_with_fingerprinting_disabled_survives_incremental_build(
        self, site_without_fingerprinting: Path
    ) -> None:
        """
        Test that CSS survives incremental builds with fingerprinting config disabled.
        
        The CSS validation uses glob("style*.css") which should match
        both "style.css" and "style.abc123.css" patterns.
        
        Note: The default theme may still have fingerprinted CSS even with
        fingerprinting disabled in config, because theme assets have their
        own processing. This test verifies CSS survives regardless.
        """
        site_root = site_without_fingerprinting
        about_file = site_root / "content" / "about.md"

        # Build 1: Full build
        site1 = Site.from_config(site_root)
        site1.build(BuildOptions(force_sequential=True, incremental=False))

        output_dir = site1.output_dir
        css_dir = output_dir / "assets" / "css"

        # Verify CSS exists (may or may not be fingerprinted depending on theme)
        css_files = list(css_dir.glob("style*.css"))
        assert len(css_files) >= 1, "Should have style CSS file(s)"
        initial_css_names = {f.name for f in css_files}

        # Modify content only
        about_file.write_text(
            """---
title: About Updated
---

# About Us Updated

New content here.
"""
        )

        # Build 2: Incremental build
        site2 = Site.from_config(site_root)
        site2.build(
            BuildOptions(
                force_sequential=True,
                incremental=True,
                changed_sources={about_file},
            )
        )

        # CSS should still exist
        css_files_after = list(css_dir.glob("style*.css"))
        assert len(css_files_after) >= 1, (
            "CSS should survive incremental build with fingerprinting config"
        )
        
        # CSS names should be unchanged (no CSS was modified)
        after_css_names = {f.name for f in css_files_after}
        assert initial_css_names == after_css_names, (
            "CSS filenames should remain stable when only content changes"
        )

    def test_output_cleaned_triggers_css_regeneration(
        self, site_without_fingerprinting: Path
    ) -> None:
        """
        Test that CSS is regenerated when output directory is cleaned.
        
        This tests the provenance filter's CSS entry check that forces
        a full rebuild when CSS is missing from output.
        """
        site_root = site_without_fingerprinting
        about_file = site_root / "content" / "about.md"

        # Build 1: Full build
        site1 = Site.from_config(site_root)
        site1.build(BuildOptions(force_sequential=True, incremental=False))

        output_dir = site1.output_dir
        css_dir = output_dir / "assets" / "css"

        assert css_dir.exists(), "CSS dir should exist after build"

        # Delete entire CSS directory (simulates clean)
        import shutil
        shutil.rmtree(css_dir)

        assert not css_dir.exists(), "CSS dir should be deleted"

        # Modify content to trigger incremental build
        about_file.write_text(
            """---
title: About
---

# About After Clean

Content modified after CSS directory was cleaned.
"""
        )

        # Build 2: Incremental build should detect missing CSS and regenerate
        site2 = Site.from_config(site_root)
        site2.build(
            BuildOptions(
                force_sequential=True,
                incremental=True,
                changed_sources={about_file},
            )
        )

        # CSS should be regenerated
        assert css_dir.exists(), "CSS dir should be regenerated"
        css_files = list(css_dir.glob("style*.css"))
        assert len(css_files) >= 1, (
            "CSS should be regenerated when output was cleaned. "
            "This tests the provenance filter's CSS entry check."
        )

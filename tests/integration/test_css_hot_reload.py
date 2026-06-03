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
from typing import TYPE_CHECKING

import pytest

from bengal.core.site import Site
from bengal.orchestration.build.options import BuildOptions

if TYPE_CHECKING:
    from pathlib import Path


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

    def test_css_revalidated_when_output_cleaned(self, site_with_css_and_content: Path) -> None:
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

    def test_multiple_content_changes_preserve_css(self, site_with_css_and_content: Path) -> None:
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

    def test_no_theme_site_builds_without_error(self, site_without_theme: Path) -> None:
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


class TestCSSHotReloadThemeProvidedCSS:
    """Hot-reload CSS coverage for the dogfood case: CSS comes from the *theme*.

    The other tests in this module put a ``style.css`` in the site's own
    ``assets/css/`` (in-root). The real dogfood site (and most users) have no
    own CSS — the entry point is the bundled theme's ``style.css``, which lives
    inside the installed package, *outside* the site root.

    That distinction matters for Issue #130: the incremental asset-discovery
    cache keys discovered assets by ``source_path.relative_to(root_path)``, so
    theme assets (outside root) are handled on a different path than in-root
    assets. These tests assert the theme CSS survives and recovers across
    content-only incremental rebuilds.
    """

    @pytest.fixture
    def theme_site(self, tmp_path: Path) -> Path:
        """A site that uses the default theme and has NO own CSS."""
        site_root = tmp_path / "theme_site"
        site_root.mkdir()
        (site_root / "bengal.toml").write_text(
            """
title = "Theme CSS Hot Reload"
baseurl = "https://example.com"

[build]
theme = "default"
parallel = false
minify_assets = false
optimize_assets = false
fingerprint_assets = false
incremental = true
"""
        )
        content_dir = site_root / "content"
        content_dir.mkdir()
        (content_dir / "index.md").write_text("---\ntitle: Home\n---\n\n# Home\n\nHello.\n")
        (content_dir / "about.md").write_text("---\ntitle: About\n---\n\n# About\n\nAbout.\n")
        return site_root

    @staticmethod
    def _theme_css(output_dir: Path) -> list[Path]:
        css_dir = output_dir / "assets" / "css"
        return list(css_dir.glob("style*.css")) if css_dir.exists() else []

    @staticmethod
    def _manifest_entry_count(output_dir: Path) -> int:
        import json

        manifest = output_dir / "asset-manifest.json"
        if not manifest.exists():
            return 0
        data = json.loads(manifest.read_text())
        entries = data.get("entries", data) if isinstance(data, dict) else data
        return len(entries)

    def test_theme_css_survives_content_only_incremental(self, theme_site: Path) -> None:
        """Theme CSS and the asset manifest survive a content-only incremental.

        Regression guard for Issue #130: a content-only edit must not drop the
        theme's ``style.css`` from the output, nor empty the asset manifest
        (an empty manifest would make the output-integrity check vacuously
        "complete" and blind the reprocess safety net on later rebuilds).
        """
        about_file = theme_site / "content" / "about.md"

        site1 = Site.from_config(theme_site)
        output_dir = site1.output_dir
        site1.build(BuildOptions(force_sequential=True, incremental=False))

        assert self._theme_css(output_dir), "full build should emit the theme style.css"
        entries_full = self._manifest_entry_count(output_dir)
        assert entries_full >= 1, "full build should record asset-manifest entries"

        # Content-only edit (no CSS touched).
        about_file.write_text("---\ntitle: About\n---\n\n# About (edited)\n\nEdited.\n")
        site2 = Site.from_config(theme_site)
        site2.build(
            BuildOptions(
                force_sequential=True,
                incremental=True,
                changed_sources={about_file},
            )
        )

        assert self._theme_css(output_dir), (
            "theme style.css must survive a content-only incremental build (Issue #130)"
        )
        assert self._manifest_entry_count(output_dir) == entries_full, (
            "content-only incremental must not empty/shrink the asset manifest (Issue #130)"
        )

    def test_theme_css_recovered_when_output_cleaned(self, theme_site: Path) -> None:
        """If the theme CSS goes missing from output, an incremental recovers it.

        This is the dogfood form of Issue #130's "fixed by restart" symptom:
        when the served output loses ``style.css``, the next incremental build
        must detect the gap (via the asset-manifest output-integrity check) and
        regenerate it, rather than serving an unstyled page until a full rebuild.
        """
        about_file = theme_site / "content" / "about.md"

        site1 = Site.from_config(theme_site)
        output_dir = site1.output_dir
        site1.build(BuildOptions(force_sequential=True, incremental=False))

        css_v1 = self._theme_css(output_dir)
        assert css_v1, "full build should emit the theme style.css"

        # Simulate the served output losing its CSS.
        for css in css_v1:
            css.unlink()
        assert not self._theme_css(output_dir)

        # Content-only incremental should detect the missing CSS and regenerate.
        about_file.write_text("---\ntitle: About\n---\n\n# About (edited)\n\nEdited.\n")
        site2 = Site.from_config(theme_site)
        site2.build(
            BuildOptions(
                force_sequential=True,
                incremental=True,
                changed_sources={about_file},
            )
        )

        assert self._theme_css(output_dir), (
            "theme style.css must be regenerated when missing from output (Issue #130)"
        )

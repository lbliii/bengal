"""
Integration tests for incremental build cache stability.

RFC: rfc-cache-invalidation-fixes

These tests verify that incremental builds are stable and don't trigger
false full rebuilds due to cache invalidation bugs.
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest


class TestIncrementalBuildStability:
    """
    Tests for incremental build stability.

    Verifies that:
    1. Consecutive incremental builds with no changes don't rebuild pages
    2. Touching templates without content changes doesn't trigger rebuilds
    3. Cache is consistent across builds
    """

    @pytest.fixture
    def minimal_site(self, tmp_path: Path) -> Path:
        """Create a minimal site for testing."""
        # Create bengal.toml
        config = tmp_path / "bengal.toml"
        config.write_text(
            """
[site]
title = "Test Site"
theme = "terminal"

[build]
incremental = true
"""
        )

        # Create content directory
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        # Create index page
        index = content_dir / "index.md"
        index.write_text(
            """---
title: Home
---

# Welcome

This is the home page.
"""
        )

        # Create another page
        about = content_dir / "about.md"
        about.write_text(
            """---
title: About
---

# About Us

About content here.
"""
        )

        return tmp_path

    def test_consecutive_builds_no_changes(self, minimal_site: Path) -> None:
        """
        Three consecutive incremental builds with no changes should be instant.

        This is the main test case from the RFC to verify cache stability.
        """
        from bengal.cache import BuildCache
        from bengal.cache.paths import BengalPaths

        paths = BengalPaths(minimal_site)
        paths.ensure_dirs()

        cache = BuildCache()

        # Track all content files
        content_dir = minimal_site / "content"
        for md_file in content_dir.glob("*.md"):
            cache.update_file(md_file)

        # Save cache
        cache.save(paths.build_cache)

        # Build 2: Load cache and verify no changes detected
        cache2 = BuildCache.load(paths.build_cache)

        changed_files = []
        for md_file in content_dir.glob("*.md"):
            if cache2.is_changed(md_file):
                changed_files.append(md_file)

        assert len(changed_files) == 0, f"Build 2 detected changes: {changed_files}"

        # Build 3: Same check (should also be stable)
        cache3 = BuildCache.load(paths.build_cache)

        changed_files = []
        for md_file in content_dir.glob("*.md"):
            if cache3.is_changed(md_file):
                changed_files.append(md_file)

        assert len(changed_files) == 0, f"Build 3 detected changes: {changed_files}"

    def test_template_touch_no_rebuild(self, minimal_site: Path) -> None:
        """
        Touching template without content change should not rebuild.

        Verifies Fix 4: Don't update unchanged template fingerprints.
        """
        from bengal.cache import BuildCache
        from bengal.cache.paths import BengalPaths

        paths = BengalPaths(minimal_site)
        paths.ensure_dirs()

        # Create a template file
        templates_dir = minimal_site / "templates"
        templates_dir.mkdir(exist_ok=True)
        template = templates_dir / "base.html"
        template.write_text("{{ content }}")

        # Track template
        cache = BuildCache()
        cache.update_file(template)
        cache.save(paths.build_cache)

        # Touch template (mtime changes, content unchanged)
        time.sleep(0.01)
        template.touch()

        # Load cache and check if template is considered changed
        cache2 = BuildCache.load(paths.build_cache)

        # Template should NOT be considered changed (content hash matches)
        assert not cache2.is_changed(template), "Touch without change triggered rebuild"

    def test_config_hash_stability_across_loads(self, minimal_site: Path) -> None:
        """
        Config hash should be identical when loaded multiple times.

        Verifies Fix 1: Config hash stability.
        """
        from bengal.config import ConfigLoader
        from bengal.config.hash import compute_config_hash

        # Load config twice
        loader1 = ConfigLoader(minimal_site)
        loader2 = ConfigLoader(minimal_site)
        config1 = loader1.load()
        config2 = loader2.load()

        hash1 = compute_config_hash(config1)
        hash2 = compute_config_hash(config2)

        assert hash1 == hash2, f"Config hash differs: {hash1} vs {hash2}"

    def test_dependency_tracking_stable(self, minimal_site: Path) -> None:
        """
        Dependency tracking should be stable across builds.

        Verifies Fix 3: Deferred fingerprint updates.
        """
        from bengal.cache import BuildCache
        from bengal.cache.dependency_tracker import DependencyTracker
        from bengal.cache.paths import BengalPaths

        paths = BengalPaths(minimal_site)
        paths.ensure_dirs()

        # Create template and page
        templates_dir = minimal_site / "templates"
        templates_dir.mkdir(exist_ok=True)
        template = templates_dir / "single.html"
        template.write_text("<html>{{ content }}</html>")

        content_dir = minimal_site / "content"
        page = content_dir / "index.md"

        # Build 1: Track dependencies
        cache = BuildCache()
        tracker = DependencyTracker(cache)

        tracker.start_page(page)
        tracker.track_template(template)
        tracker.end_page()

        # Flush pending updates
        tracker.flush_pending_updates()

        # Update page fingerprint
        cache.update_file(page)
        cache.save(paths.build_cache)

        # Build 2: Verify dependencies are intact
        cache2 = BuildCache.load(paths.build_cache)

        # Page should still depend on template
        page_deps = cache2.dependencies.get(str(page), set())
        assert str(template) in page_deps, "Dependency not preserved"

        # Template fingerprint should exist
        assert str(template) in cache2.file_fingerprints, "Template fingerprint missing"

    def test_content_change_detected_correctly(self, minimal_site: Path) -> None:
        """
        Actual content changes should be detected.

        Ensures fixes don't break legitimate change detection.
        """
        from bengal.cache import BuildCache
        from bengal.cache.paths import BengalPaths

        paths = BengalPaths(minimal_site)
        paths.ensure_dirs()

        content_dir = minimal_site / "content"
        page = content_dir / "index.md"

        # Track page
        cache = BuildCache()
        cache.update_file(page)
        cache.save(paths.build_cache)

        # Modify page content
        time.sleep(0.01)
        page.write_text(
            """---
title: Home (Updated)
---

# Welcome

This is the updated home page.
"""
        )

        # Load cache and verify change detected
        cache2 = BuildCache.load(paths.build_cache)
        assert cache2.is_changed(page), "Content change not detected"

    def test_new_file_detected(self, minimal_site: Path) -> None:
        """
        New files should be detected as changed.

        Ensures fixes don't break new file detection.
        """
        from bengal.cache import BuildCache
        from bengal.cache.paths import BengalPaths

        paths = BengalPaths(minimal_site)
        paths.ensure_dirs()

        content_dir = minimal_site / "content"

        # Track existing files
        cache = BuildCache()
        for md_file in content_dir.glob("*.md"):
            cache.update_file(md_file)
        cache.save(paths.build_cache)

        # Add new file
        new_page = content_dir / "new-page.md"
        new_page.write_text(
            """---
title: New Page
---

# New Page

New content here.
"""
        )

        # Load cache and verify new file detected
        cache2 = BuildCache.load(paths.build_cache)
        assert cache2.is_changed(new_page), "New file not detected as changed"

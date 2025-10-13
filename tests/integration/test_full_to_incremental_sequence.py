"""
Integration test for full → incremental build sequence.

This test validates the critical bug we found: that cache is properly
saved after full builds, enabling true incremental builds on the next run.

Bug History:
- Original bug: Cache was only saved if incremental=True, so first full build
  didn't save cache, causing all subsequent incremental builds to rebuild everything
- Fix: Always save cache after successful builds
"""

import time

import pytest

from bengal.core.site import Site


class TestFullToIncrementalSequence:
    """Test the full → incremental build sequence."""

    @pytest.fixture
    def test_site(self, tmp_path):
        """Create a test site with config and content."""
        site_root = tmp_path / "test_site"
        site_root.mkdir()

        # Config
        config_file = site_root / "bengal.toml"
        config_file.write_text("""
[site]
title = "Test Site"
baseurl = "https://example.com"

[build]
output_dir = "public"
""")

        # Content
        content_dir = site_root / "content"
        content_dir.mkdir()

        # Create 50 pages for realistic test
        for i in range(50):
            page_file = content_dir / f"page-{i:02d}.md"
            page_file.write_text(f"""---
title: "Page {i}"
date: 2025-01-{(i % 28) + 1:02d}
tags: ["tag-{i % 5}"]
---

# Page {i}

Content for page {i}.

## Section

More content here.
""")

        yield site_root

        # Cleanup handled by tmp_path fixture

    def test_full_build_saves_cache(self, test_site):
        """Test that full builds save cache for future incremental builds."""
        # Build 1: Full build
        site = Site.from_config(test_site)
        _ = site.build(parallel=True, incremental=False)

        # Verify cache was created (new location: .bengal/cache.json since v0.1.2)
        cache_file = test_site / ".bengal" / "cache.json"
        assert cache_file.exists(), "Cache should be saved after full build"

        # Read cache to verify it has content
        import json

        with open(cache_file) as f:
            cache_data = json.load(f)

        assert "file_hashes" in cache_data
        assert len(cache_data["file_hashes"]) > 0, "Cache should have file hashes"

        # Verify config is in cache
        config_path = str(test_site / "bengal.toml")
        assert any(
            config_path in key for key in cache_data["file_hashes"]
        ), "Config file should be in cache"

    def test_incremental_after_full_build(self, test_site):
        """Test that incremental builds work after a full build."""
        # Build 1: Full build (baseline)
        site = Site.from_config(test_site)
        _ = site.build(parallel=True, incremental=False)

        # Wait to ensure file mtime changes are detectable
        time.sleep(0.15)

        # Build 2: Incremental with no changes (should use cache)
        stats2 = site.build(parallel=True, incremental=True)

        # Should use cache (50 cache hits, 0 misses)
        assert stats2.cache_hits == 50, f"Should have 50 cache hits, got {stats2.cache_hits}"
        assert stats2.cache_misses == 0, f"Should have 0 cache misses, got {stats2.cache_misses}"

        # Note: skipped may be False if we have taxonomies that need regeneration
        # The important thing is that pages are cached (not rebuilt)

    def test_incremental_single_page_change(self, test_site):
        """Test that incremental builds only rebuild changed pages."""
        # Build 1: Full build
        site = Site.from_config(test_site)
        stats1 = site.build(parallel=True, incremental=False)
        full_time = stats1.build_time_ms / 1000

        # Record output file mtimes
        output_dir = test_site / "public"
        files_before = {f: f.stat().st_mtime for f in output_dir.rglob("*.html")}

        # Wait and change one page
        time.sleep(0.15)
        test_page = test_site / "content" / "page-00.md"
        original = test_page.read_text()
        test_page.write_text(original + "\n\n## New Section\n\nNew content added.\n")

        # Build 2: Incremental with one change
        time.sleep(0.15)
        stats2 = site.build(parallel=True, incremental=True)
        incr_time = stats2.build_time_ms / 1000

        # Check which files were actually modified
        files_after = {f: f.stat().st_mtime for f in output_dir.rglob("*.html")}
        modified_files = [f for f in files_before if files_after.get(f, 0) != files_before[f]]

        # Assertions
        assert stats2.skipped is not True, "Build should not be skipped"
        assert (
            len(modified_files) < 15
        ), f"Should rebuild <15 files, but rebuilt {len(modified_files)}"
        assert (
            incr_time < full_time
        ), f"Incremental ({incr_time:.2f}s) should be faster than full ({full_time:.2f}s)"

        # Calculate speedup
        speedup = full_time / incr_time
        assert speedup >= 2.0, f"Incremental should be at least 2x faster (got {speedup:.1f}x)"

    def test_config_change_triggers_full_rebuild(self, test_site):
        """Test that config changes trigger full rebuild."""
        # Build 1: Full build
        site = Site.from_config(test_site)
        site.build(parallel=True, incremental=False)

        # Wait and modify config
        time.sleep(0.15)
        config_file = test_site / "bengal.toml"
        config_content = config_file.read_text()
        config_file.write_text(
            config_content.replace('title = "Test Site"', 'title = "Modified Site"')
        )

        # Build 2: Incremental (should detect config change)
        time.sleep(0.15)
        site = Site.from_config(test_site)  # Reload config
        stats = site.build(parallel=True, incremental=True)

        # Should do full rebuild (skipped=False)
        assert stats.skipped is not True, "Build should not be skipped when config changes"

    def test_first_incremental_build_no_cache(self, test_site):
        """Test that first incremental build without cache does full rebuild."""
        # Skip initial full build - go straight to incremental
        site = Site.from_config(test_site)

        # Verify no cache exists (new location since v0.1.2)
        cache_file = test_site / ".bengal" / "cache.json"
        assert not cache_file.exists(), "Cache should not exist yet"

        # Build with incremental=True but no cache
        stats = site.build(parallel=True, incremental=True)

        # Should do full build (no cache to compare against)
        assert stats.skipped is not True

        # Cache should now exist
        assert cache_file.exists(), "Cache should be created"

    def test_multiple_incremental_builds(self, test_site):
        """Test that multiple incremental builds in sequence work correctly."""
        # Build 1: Full build
        site = Site.from_config(test_site)
        site.build(parallel=True, incremental=False)

        # Build 2: Incremental, no changes (should use cache)
        time.sleep(0.15)
        stats2 = site.build(parallel=True, incremental=True)
        assert stats2.cache_hits == 50, "Should use cache for all pages"
        assert stats2.cache_misses == 0, "Should have no cache misses"

        # Build 3: Change one file
        time.sleep(0.15)
        (test_site / "content" / "page-00.md").write_text("---\ntitle: Changed\n---\nNew content")
        time.sleep(0.15)
        stats3 = site.build(parallel=True, incremental=True)
        assert stats3.cache_misses > 0, "Should have cache miss for changed file"
        assert stats3.cache_hits > 40, "Should still use cache for unchanged files"

        # Build 4: No changes again
        time.sleep(0.15)
        stats4 = site.build(parallel=True, incremental=True)
        assert stats4.cache_hits == 50, "Should use cache for all pages again"
        assert stats4.cache_misses == 0, "Should have no cache misses again"

    def test_cache_survives_site_reload(self, test_site):
        """Test that cache persists across Site object recreation."""
        # Build 1: Full build with first site instance
        site1 = Site.from_config(test_site)
        site1.build(parallel=True, incremental=False)

        # Create NEW Site instance (simulates restart)
        time.sleep(0.15)
        site2 = Site.from_config(test_site)

        # Build 2: Incremental with new instance, no changes
        stats = site2.build(parallel=True, incremental=True)

        # Should use cache from previous build (50 hits, 0 misses)
        assert (
            stats.cache_hits == 50
        ), f"New site instance should use persisted cache (got {stats.cache_hits} hits)"
        assert (
            stats.cache_misses == 0
        ), f"New site instance should have no cache misses (got {stats.cache_misses})"


class TestIncrementalBuildRegression:
    """Regression tests for specific incremental build bugs."""

    def test_bug_cache_not_saved_after_full_build(self, tmp_path):
        """
        Regression test for bug where cache wasn't saved after full builds.

        Bug: Cache was only saved if incremental=True, causing first incremental
        build after a full build to think everything changed.

        Fix: Always save cache after successful builds.
        """
        site_root = tmp_path / "bug_test"
        site_root.mkdir()
        (site_root / "bengal.toml").write_text('[site]\ntitle="Test"\n')
        content_dir = site_root / "content"
        content_dir.mkdir()
        (content_dir / "test.md").write_text("---\ntitle: Test\n---\nContent")

        # The bug sequence: full build followed by incremental
        site = Site.from_config(site_root)

        # Step 1: Full build with incremental=False
        stats1 = site.build(parallel=False, incremental=False)
        assert stats1.cache_hits == 0, "First build should have no cache hits"

        # Step 2: Check cache exists (this would fail with the bug) - new location since v0.1.2
        cache_file = site_root / ".bengal" / "cache.json"
        assert cache_file.exists(), "BUG: Cache not saved after full build with incremental=False"

        # Step 3: Incremental build should use cache
        time.sleep(0.15)
        stats2 = site.build(parallel=False, incremental=True)

        # Should use cache (1 page, 1 cache hit, 0 misses)
        assert stats2.cache_hits == 1, f"BUG: Should have 1 cache hit, got {stats2.cache_hits}"
        assert (
            stats2.cache_misses == 0
        ), f"BUG: Should have 0 cache misses, got {stats2.cache_misses}"

    def test_bug_config_hash_not_populated(self, tmp_path):
        """
        Regression test for bug where config hash wasn't populated on full builds.

        Bug: check_config_changed() only called when incremental=True, so
        config hash never added to cache during full builds.

        Fix: Always call check_config_changed() to populate cache.
        """
        site_root = tmp_path / "config_bug"
        site_root.mkdir()
        config_file = site_root / "bengal.toml"
        config_file.write_text('[site]\ntitle="Test"\n')
        content_dir = site_root / "content"
        content_dir.mkdir()
        (content_dir / "test.md").write_text("---\ntitle: Test\n---\nContent")

        # Full build
        site = Site.from_config(site_root)
        site.build(parallel=False, incremental=False)

        # Check that config is in cache (new location since v0.1.2)
        import json

        cache_file = site_root / ".bengal" / "cache.json"
        with open(cache_file) as f:
            cache_data = json.load(f)

        config_path = str(config_file)
        assert any(
            config_path in key for key in cache_data["file_hashes"]
        ), "BUG: Config file hash not in cache after full build"

        # Incremental build should not think config changed
        time.sleep(0.15)
        stats = site.build(parallel=False, incremental=True)

        # Should use cache (indicating config was NOT detected as changed)
        assert (
            stats.cache_hits == 1
        ), f"BUG: Should use cache (config unchanged), got {stats.cache_hits} hits"
        assert (
            stats.cache_misses == 0
        ), f"BUG: Incremental build thought config changed when it didn't (got {stats.cache_misses} misses)"

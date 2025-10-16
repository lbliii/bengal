"""
Integration test for full → incremental build sequence.

This test validates the critical bug we found: that cache is properly
saved after full builds, enabling true incremental builds on the next run.

Bug History:
- Original bug: Cache was only saved if incremental=True, so first full build
  didn't save cache, causing all subsequent incremental builds to rebuild everything
- Fix: Always save cache after successful builds
"""

import glob
import shutil
import time

import hypothesis.strategies as st
import pytest
from hypothesis import given, settings

from bengal.core.orchestrator import IncrementalOrchestrator
from bengal.core.site import Site


@pytest.mark.slow
class TestIncrementalSequence:
    """
    Integration tests for full-to-incremental build sequences.
    Marked slow due to multiple full builds and file watching simulation.
    """

    @pytest.fixture(autouse=True)
    def setup_teardown(self, tmp_path):
        """Ensure clean state between tests."""
        yield
        # Clean any lingering output
        public_dir = tmp_path / "public"
        if public_dir.exists():
            shutil.rmtree(public_dir)

    # Fixture fix for assets
    @pytest.fixture
    def site_with_assets(self, tmp_path):
        assets_dir = tmp_path / "assets"
        assets_dir.mkdir()
        (assets_dir / "style.css").touch()
        return tmp_path

    @pytest.mark.parametrize(
        "change_type",
        [
            "content",  # Modify page content
            "template",  # Modify template
            "config",  # Modify bengal.toml
        ],
    )
    def test_change_detection(self, tmp_site, change_type):
        """
        Test that incremental builds detect and rebuild only affected files.

        Parametrized to reduce redundant site creation across change types.
        """
        site_dir = tmp_site

        # Setup basic site
        config_path = site_dir / "bengal.toml"
        config_content = """
[site]
title = "Test Incremental"
baseurl = "/"

[build]
output_dir = "public"
incremental = true
parallel = false  # Sequential for predictable timing
"""
        with open(config_path, "w") as f:
            f.write(config_content)

        # Create content
        content_dir = site_dir / "content"
        content_dir.mkdir()
        page1 = content_dir / "page1.md"
        with open(page1, "w") as f:
            f.write("""---
title: "Page 1"
---
Original content.""")

        # Create simple template
        templates_dir = site_dir / "templates"
        templates_dir.mkdir()
        base_html = templates_dir / "base.html"
        with open(base_html, "w") as f:
            f.write("""
<!DOCTYPE html>
<html>
<head><title>{{ page.title }}</title></head>
<body>
<h1>{{ page.title }}</h1>
{{ content }}
</body>
</html>
""")

        # Initial full build
        site = Site.from_config(site_dir, config_path=config_path)
        site.discover_content()
        site.discover_assets()
        full_stats = site.build()
        assert full_stats.total_pages > 0
        assert len(list((site_dir / "public").rglob("*.html"))) > 0

        # Wait for file system
        time.sleep(0.05)  # Reduced from 0.15

        # Make change based on type
        if change_type == "content":
            with open(page1, "w") as f:
                f.write("""---
title: "Page 1"
---
Modified content.""")
        elif change_type == "template":
            with open(base_html, "w") as f:
                f.write("""
<!DOCTYPE html>
<html>
<head><title>{{ page.title }} - Updated</title></head>
<body>
<h1>{{ page.title }}</h1>
{{ content }}
<footer>Modified template</footer>
</body>
</html>
""")
        elif change_type == "config":
            with open(config_path, "w") as f:
                f.write(
                    config_content.replace('title = "Test Incremental"', 'title = "Updated Title"')
                )

        time.sleep(0.05)  # Reduced

        # Incremental build
        incremental_stats = site.build(incremental=True)
        assert incremental_stats.total_pages > 0

        # Verify change applied
        output_html = site_dir / "public" / "page1.html"
        with open(output_html) as f:
            content = f.read()
            if change_type == "content":
                assert "Modified content" in content
            elif change_type == "template":
                assert "Updated" in content or "footer>Modified template" in content
            elif change_type == "config":
                assert "Updated Title" in content  # Via page title update

        # Additional incremental (no change) should be very fast
        time.sleep(0.05)
        no_change_stats = site.build(incremental=True)
        assert no_change_stats.total_pages > 0


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


@settings(max_examples=50)
@given(st.data())
def test_incremental_change_invariant(self, data, site_with_assets):
    # This test is a work-in-progress and not fully implemented
    pytest.skip("Test not yet fully implemented - fixture needs proper site setup")
    # Stateful: Simulate changes
    change_type = data.draw(st.one_of(st.just("content"), st.just("template"), st.just("config")))
    changed_paths = data.draw(st.sets(st.text(min_size=1)))

    # Use updated orchestrator
    orch = IncrementalOrchestrator(site_with_assets)
    orch.initialize(enabled=True)
    orch.process(change_type, set(changed_paths))

    # Invariant: If changed, total_pages > 0 and outputs exist
    assert orch.tracker.is_stale() == (len(changed_paths) > 0)
    if orch.tracker.is_stale():
        assert len(glob.glob("public/*.html")) > 0

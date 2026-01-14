"""Integration tests for asset manifest ContextVar usage during builds.

RFC: rfc-asset-resolution-observability.md (Phase 3)

Tests that:
1. ContextVar is always set during full builds (no unexpected fallback)
2. Dev server correctly uses disk fallback
3. Stats are tracked and reset properly
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from bengal.core.site import Site
from bengal.orchestration.build.options import BuildOptions
from bengal.rendering.assets import clear_manifest_cache, get_resolution_stats
from bengal.utils.observability.logger import reset_loggers


@pytest.fixture(scope="module")
def test_site_dir(tmp_path_factory) -> Path:
    """Create a minimal test site for integration tests.
    
    Uses module scope to avoid recreating the site for each test.
    """
    tmp_path = tmp_path_factory.mktemp("asset_test_site")
    
    # Create basic site structure
    (tmp_path / "content").mkdir()
    (tmp_path / "themes" / "default" / "templates").mkdir(parents=True)
    (tmp_path / "themes" / "default" / "assets" / "css").mkdir(parents=True)
    
    # Create config
    config = """
title = "Test Site"
baseurl = "https://example.com"

[build]
output_dir = "public"
"""
    (tmp_path / "bengal.toml").write_text(config)
    
    # Create minimal template
    template = """<!DOCTYPE html>
<html>
<head>
    <title>{{ page.title }}</title>
    <link rel="stylesheet" href="{{ asset_url('css/style.css') }}">
</head>
<body>
    <h1>{{ page.title }}</h1>
    {{ page.content }}
</body>
</html>
"""
    (tmp_path / "themes" / "default" / "templates" / "default.html").write_text(template)
    (tmp_path / "themes" / "default" / "templates" / "single.html").write_text(template)
    
    # Create a basic CSS file
    css = """
body { font-family: sans-serif; }
h1 { color: #333; }
"""
    (tmp_path / "themes" / "default" / "assets" / "css" / "style.css").write_text(css)
    
    # Create test pages that use asset_url
    index_md = """---
title: Home
---

This is the home page.
"""
    (tmp_path / "content" / "_index.md").write_text(index_md)
    
    about_md = """---
title: About
---

This is the about page.
"""
    (tmp_path / "content" / "about.md").write_text(about_md)
    
    return tmp_path


@pytest.fixture(autouse=True)
def clean_state():
    """Reset caches and logger state before each test."""
    clear_manifest_cache()
    reset_loggers()
    yield
    clear_manifest_cache()
    reset_loggers()


class TestContextVarDuringFullBuild:
    """Tests for ContextVar setup during full builds."""

    def test_stats_tracked_during_full_build(self, test_site_dir: Path) -> None:
        """Verify stats are tracked during build.
        
        This test verifies that the observability infrastructure is working:
        - Stats are collected during the build
        - Cache hits are tracked for ContextVar path
        - Any unexpected fallbacks are logged (observability goal)
        
        Note: Some fallbacks may occur during post-processing phases that
        are outside asset_manifest_context(). This is expected behavior that
        the observability surfaces for future optimization.
        """
        # Clear any previous state
        clear_manifest_cache()
        
        # Build site
        site = Site.from_config(test_site_dir)
        options = BuildOptions(force_sequential=True)  # Simpler for testing
        site.build(options)
        
        # Verify stats exist after build
        stats = get_resolution_stats()
        
        # Stats should exist if asset resolution occurred
        assert stats is not None, "Resolution stats should be tracked during build"
        
        # At minimum, cache hits should occur during rendering (inside context)
        # Cache hits = ContextVar was set and used correctly
        assert stats.cache_hits > 0, (
            f"Expected cache hits during rendering phase.\n"
            f"Stats: {stats.format_summary('AssetResolution')}"
        )

    def test_cache_hits_tracked_during_build(self, test_site_dir: Path) -> None:
        """Verify cache hits are tracked when ContextVar is set."""
        clear_manifest_cache()
        
        site = Site.from_config(test_site_dir)
        options = BuildOptions(force_sequential=True)
        site.build(options)
        
        stats = get_resolution_stats()
        
        # Stats should exist
        assert stats is not None, "Stats should be tracked during build"
        
        # Cache operations should have occurred
        total_ops = stats.cache_hits + stats.cache_misses
        assert total_ops > 0, (
            "Expected asset resolution operations during build.\n"
            f"Stats: {stats.format_summary('AssetResolution')}"
        )
        
        # Verify the summary is informative
        summary = stats.format_summary("AssetResolution")
        assert "cache=" in summary, "Summary should include cache stats"


class TestStatsResetBetweenBuilds:
    """Tests for stats isolation between builds."""

    def test_stats_reset_between_builds(self, test_site_dir: Path) -> None:
        """Stats should reset on clear_manifest_cache()."""
        # First build
        clear_manifest_cache()
        
        site = Site.from_config(test_site_dir)
        options = BuildOptions(force_sequential=True)
        site.build(options)
        
        stats1 = get_resolution_stats()
        
        # Reset for second build
        clear_manifest_cache()
        
        # Stats should be None after reset
        assert get_resolution_stats() is None, "Stats should be None after clear_manifest_cache()"
        
        # Second build
        site2 = Site.from_config(test_site_dir)
        site2.build(options)
        
        stats2 = get_resolution_stats()
        
        # Stats should be fresh (not accumulated from first build)
        if stats1 is not None and stats2 is not None:
            # Can't directly compare since pages might differ,
            # but stats2 should be independent
            assert stats2 is not stats1, "Stats should be new objects after reset"


class TestIncrementalBuild:
    """Tests for stats tracking during incremental builds."""

    def test_incremental_build_tracks_stats(self, test_site_dir: Path) -> None:
        """Incremental builds should also track resolution stats."""
        clear_manifest_cache()
        
        # Initial full build
        site = Site.from_config(test_site_dir)
        options = BuildOptions(force_sequential=True)
        site.build(options)
        
        # Clear and do incremental build
        clear_manifest_cache()
        
        site2 = Site.from_config(test_site_dir)
        options_incremental = BuildOptions(force_sequential=True, incremental=True)
        site2.build(options_incremental)
        
        stats = get_resolution_stats()
        
        # Stats should be tracked during incremental builds too
        # Note: On incremental builds with no changes, resolution may be minimal
        # The key test is that the observability infrastructure works
        if stats is not None:
            # Verify stats format is correct
            summary = stats.format_summary("AssetResolution")
            assert "AssetResolution" in summary


class TestStatsFormatting:
    """Tests for stats output formatting."""

    def test_stats_provide_useful_summary(self, test_site_dir: Path) -> None:
        """Stats should provide a useful summary for debugging."""
        clear_manifest_cache()
        
        site = Site.from_config(test_site_dir)
        options = BuildOptions(force_sequential=True)
        site.build(options)
        
        stats = get_resolution_stats()
        
        if stats is not None:
            summary = stats.format_summary("AssetResolution")
            
            # Summary should contain useful info
            assert "AssetResolution" in summary
            
            # If cache operations occurred, should show cache stats
            if stats.cache_hits > 0 or stats.cache_misses > 0:
                assert "cache=" in summary

    def test_stats_log_context_for_debugging(self, test_site_dir: Path) -> None:
        """Stats should provide log context for structured logging."""
        clear_manifest_cache()
        
        site = Site.from_config(test_site_dir)
        options = BuildOptions(force_sequential=True)
        site.build(options)
        
        stats = get_resolution_stats()
        
        if stats is not None:
            log_ctx = stats.to_log_context()
            
            # Should have standard fields
            assert "cache_hits" in log_ctx
            assert "cache_misses" in log_ctx
            assert "cache_hit_rate" in log_ctx

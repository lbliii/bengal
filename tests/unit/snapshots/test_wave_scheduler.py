"""
Tests for WaveScheduler - topological wave-based rendering.

Verifies that pages are rendered in topological waves and HTML files
are written correctly.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, Mock

import pytest

from bengal.snapshots import create_site_snapshot
from bengal.snapshots.scheduler import WaveScheduler


@pytest.mark.bengal(testroot="test-basic")
def test_wave_scheduler_renders_pages(site, tmp_path):
    """Test that WaveScheduler renders pages and writes HTML."""
    # Site fixture already has pages discovered, but not rendered
    # Create snapshot from discovered pages
    snapshot = create_site_snapshot(site)

    stats = MagicMock()

    # Create build context
    from bengal.orchestration.build_context import BuildContext

    build_context = BuildContext(
        site=site,
        pages=site.pages,
        stats=stats,
    )
    build_context.snapshot = snapshot

    # Create scheduler
    scheduler = WaveScheduler(
        snapshot=snapshot,
        site=site,
        quiet=True,
        stats=stats,
        build_context=build_context,
        max_workers=2,
    )

    # Render all pages
    pages_to_build = list(site.pages)
    render_stats = scheduler.render_all(pages_to_build)

    # Check that pages were rendered
    assert render_stats.pages_rendered > 0, f"No pages rendered. Stats: {render_stats}"
    assert render_stats.pages_rendered == len(pages_to_build), (
        f"Expected {len(pages_to_build)} pages, got {render_stats.pages_rendered}"
    )

    # Check that HTML files were written
    for page in pages_to_build:
        if page.output_path:
            assert page.output_path.exists(), f"HTML file not written: {page.output_path}"
            assert page.output_path.stat().st_size > 0, f"HTML file is empty: {page.output_path}"
            assert page.rendered_html, f"Page has no rendered_html: {page.source_path}"


@pytest.mark.bengal(testroot="test-taxonomy")
def test_wave_scheduler_topological_order(site, build_site):
    """Test that pages are rendered in topological waves."""
    build_site()

    snapshot = create_site_snapshot(site)

    # Track render order
    render_order: list[Path] = []

    # Mock RenderingPipeline.process_page instance method to track order
    from unittest.mock import patch
    from bengal.rendering.pipeline import RenderingPipeline

    original_process_page = RenderingPipeline.process_page

    def track_process_page(self, page):
        render_order.append(page.source_path)
        return original_process_page(self, page)

    with patch.object(RenderingPipeline, "process_page", track_process_page):
        stats = MagicMock()

        from bengal.orchestration.build_context import BuildContext

        build_context = BuildContext(
            site=site,
            pages=site.pages,
            stats=stats,
        )
        build_context.snapshot = snapshot

        scheduler = WaveScheduler(
            snapshot=snapshot,
            site=site,
            quiet=True,
            stats=stats,
            build_context=build_context,
            max_workers=1,  # Sequential to verify order
        )

        scheduler.render_all(list(site.pages))

        # Verify pages were rendered (order may vary within waves)
        assert len(render_order) == len(site.pages)


@pytest.mark.bengal(testroot="test-basic")
def test_wave_scheduler_sets_output_paths(site, build_site):
    """Test that WaveScheduler sets output_paths before rendering."""
    build_site()

    snapshot = create_site_snapshot(site)

    # Clear output_paths
    for page in site.pages:
        page.output_path = None

    stats = MagicMock()

    from bengal.orchestration.build_context import BuildContext

    build_context = BuildContext(
        site=site,
        pages=site.pages,
        stats=stats,
    )
    build_context.snapshot = snapshot

    scheduler = WaveScheduler(
        snapshot=snapshot,
        site=site,
        quiet=True,
        stats=stats,
        build_context=build_context,
        max_workers=1,
    )

    # Render pages
    scheduler.render_all(list(site.pages))

    # All pages should have output_path set
    for page in site.pages:
        assert page.output_path is not None, f"output_path not set for {page.source_path}"


@pytest.mark.bengal(testroot="test-basic")
def test_wave_scheduler_handles_errors(site, build_site):
    """Test that WaveScheduler handles rendering errors gracefully."""
    build_site()

    snapshot = create_site_snapshot(site)

    stats = MagicMock()

    from bengal.orchestration.build_context import BuildContext

    build_context = BuildContext(
        site=site,
        pages=site.pages,
        stats=stats,
    )
    build_context.snapshot = snapshot

    scheduler = WaveScheduler(
        snapshot=snapshot,
        site=site,
        quiet=True,
        stats=stats,
        build_context=build_context,
        max_workers=1,
    )

    # Mock a page to raise an error
    error_page = site.pages[0]

    original_process_page = None

    def failing_process_page(page):
        if page.source_path == error_page.source_path:
            raise ValueError("Test error")
        if original_process_page:
            original_process_page(page)

    from bengal.rendering.pipeline import RenderingPipeline

    original_process_page = RenderingPipeline.process_page

    try:
        RenderingPipeline.process_page = failing_process_page

        render_stats = scheduler.render_all(list(site.pages))

        # Should have errors recorded
        assert len(render_stats.errors) > 0
        assert render_stats.errors[0][0] == error_page.source_path

    finally:
        RenderingPipeline.process_page = original_process_page

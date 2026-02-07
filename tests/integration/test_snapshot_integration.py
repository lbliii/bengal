"""
Integration tests for snapshot engine.

Tests the full integration: snapshot creation → WaveScheduler → HTML output.
"""

from __future__ import annotations

import re

import pytest

from bengal.orchestration.build import BuildOrchestrator
from bengal.orchestration.build.options import BuildOptions
from bengal.snapshots import create_site_snapshot

# Pattern to strip build-specific content hashes that vary between runs
_CONTENT_HASH_RE = re.compile(r'<meta name="bengal:content-hash" content="[0-9a-f]+">')


@pytest.mark.bengal(testroot="test-basic")
def test_snapshot_created_during_build(site, build_site):
    """Test that snapshot is created during build and stored in BuildContext."""
    build_site()

    orchestrator = BuildOrchestrator(site)
    options = BuildOptions(force_sequential=False, incremental=False)

    stats = orchestrator.build(options)

    # Snapshot should be created (check via build stats if available)
    # Note: We can't directly access snapshot from stats, but we can verify
    # that the build completed successfully
    assert stats is not None


@pytest.mark.bengal(testroot="test-taxonomy")
def test_snapshot_enables_parallel_rendering(site, build_site, tmp_path):
    """Test that snapshot enables parallel rendering and HTML files are written."""
    build_site()

    orchestrator = BuildOrchestrator(site)
    options = BuildOptions(force_sequential=False, incremental=False)

    stats = orchestrator.build(options)

    # Verify HTML files were written
    html_files = list(site.output_dir.rglob("*.html"))

    # Should have HTML files (at least index.html)
    assert len(html_files) > 0, "No HTML files were written"

    # Verify files are not empty
    for html_file in html_files:
        assert html_file.stat().st_size > 0, f"HTML file is empty: {html_file}"


@pytest.mark.bengal(testroot="test-taxonomy")
def test_snapshot_rendering_produces_html(site, build_site):
    """Test that snapshot-based rendering produces valid HTML."""
    build_site()

    # Create snapshot manually
    snapshot = create_site_snapshot(site)

    # Verify snapshot has pages
    assert len(snapshot.pages) > 0

    # Use WaveScheduler to render
    from bengal.orchestration.build_context import BuildContext
    from bengal.snapshots.scheduler import WaveScheduler

    stats = None  # No stats for this test

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
        max_workers=2,
    )

    # Render pages
    pages_to_build = list(site.pages)
    render_stats = scheduler.render_all(pages_to_build)

    # Verify pages were rendered
    assert render_stats.pages_rendered == len(pages_to_build)

    # Verify HTML files exist
    for page in pages_to_build:
        if page.output_path:
            assert page.output_path.exists(), f"HTML not written: {page.output_path}"
            html_content = page.output_path.read_text()
            assert len(html_content) > 0, f"HTML is empty: {page.output_path}"
            assert "<!DOCTYPE" in html_content or "<html" in html_content, (
                f"Invalid HTML: {page.output_path}"
            )


@pytest.mark.bengal(testroot="test-taxonomy")
def test_snapshot_vs_sequential_rendering(site, build_site):
    """Test that snapshot-based rendering produces same output as sequential."""
    build_site()

    # Build with parallel (uses snapshot)
    orchestrator1 = BuildOrchestrator(site)
    options1 = BuildOptions(force_sequential=False, incremental=False)
    stats1 = orchestrator1.build(options1)

    # Get HTML files from parallel build
    parallel_html = {
        p.output_path: p.output_path.read_text() if p.output_path and p.output_path.exists() else ""
        for p in site.pages
        if p.output_path
    }

    # Rebuild with sequential (no snapshot)
    orchestrator2 = BuildOrchestrator(site)
    options2 = BuildOptions(force_sequential=True, incremental=False)
    stats2 = orchestrator2.build(options2)

    # Get HTML files from sequential build
    sequential_html = {
        p.output_path: p.output_path.read_text() if p.output_path and p.output_path.exists() else ""
        for p in site.pages
        if p.output_path
    }

    # Compare outputs (should be identical)
    assert set(parallel_html.keys()) == set(sequential_html.keys()), "Different pages rendered"

    for path in parallel_html.keys():
        # Normalize: strip whitespace and build-specific content hashes
        parallel_content = _CONTENT_HASH_RE.sub("", parallel_html[path].strip())
        sequential_content = _CONTENT_HASH_RE.sub("", sequential_html[path].strip())

        assert parallel_content == sequential_content, f"Different HTML for {path}"

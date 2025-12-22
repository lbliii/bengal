"""Integration tests for template scaffolding and building.

Tests that all 7 site templates scaffold correctly and build without errors.
Validates the end-to-end user workflow: scaffold → build → validate output.

Phase 1 of RFC: User Scenario Coverage & Validation Matrix
"""

from __future__ import annotations

import pytest

from tests._testing.cli import run_cli

AVAILABLE_TEMPLATES = [
    "default",
    "docs",
    "blog",
    "portfolio",
    "resume",
    "landing",
    "changelog",
]


@pytest.mark.integration
@pytest.mark.parametrize("template", AVAILABLE_TEMPLATES)
def test_template_scaffolds_and_builds(template: str, tmp_path) -> None:
    """Each template should scaffold and build without errors.

    This test validates the complete user workflow:
    1. Scaffold a new site from template
    2. Build the site
    3. Verify essential output files exist

    Args:
        template: Template name to test
        tmp_path: Pytest temporary directory fixture
    """
    site_name = f"site-{template}"
    site_dir = tmp_path / site_name

    # Scaffold - run from tmp_path so site is created there
    result = run_cli(
        ["new", "site", site_name, "--template", template, "--no-init"],
        cwd=str(tmp_path),
        timeout=60,
    )
    assert result.returncode == 0, f"Scaffold failed for {template}: {result.stderr}"

    # Verify site directory was created
    assert site_dir.exists(), f"Site directory not created for {template}"

    # Build
    result = run_cli(
        ["site", "build"],
        cwd=str(site_dir),
        timeout=120,
    )
    assert result.returncode == 0, f"Build failed for {template}: {result.stderr}"

    # Basic validation - output directory exists with index.html
    output_dir = site_dir / "public"
    assert output_dir.exists(), f"Output directory not created for {template}"
    assert (output_dir / "index.html").exists(), f"index.html not created for {template}"

    # Sitemap should exist for all templates
    assert (output_dir / "sitemap.xml").exists(), f"sitemap.xml not created for {template}"


@pytest.mark.integration
@pytest.mark.parametrize("template", AVAILABLE_TEMPLATES)
def test_template_has_valid_structure(template: str, tmp_path) -> None:
    """Each template should scaffold with expected directory structure.

    Args:
        template: Template name to test
        tmp_path: Pytest temporary directory fixture
    """
    site_name = f"site-{template}"
    site_dir = tmp_path / site_name

    # Scaffold - run from tmp_path so site is created there
    result = run_cli(
        ["new", "site", site_name, "--template", template, "--no-init"],
        cwd=str(tmp_path),
        timeout=60,
    )
    assert result.returncode == 0, f"Scaffold failed for {template}: {result.stderr}"

    # Verify site directory was created
    assert site_dir.exists(), f"Site directory not created for {template}"

    # Check required structure
    assert (site_dir / "config").exists(), f"config/ not created for {template}"
    assert (site_dir / "content").exists(), f"content/ not created for {template}"
    assert (site_dir / ".gitignore").exists(), f".gitignore not created for {template}"

    # Check config structure
    assert (site_dir / "config" / "_default").exists(), (
        f"config/_default/ not created for {template}"
    )
    assert (site_dir / "config" / "_default" / "site.yaml").exists(), (
        f"site.yaml not created for {template}"
    )


@pytest.mark.integration
def test_blog_template_generates_rss(tmp_path) -> None:
    """Blog template should generate RSS feed."""
    site_name = "site-blog-rss"
    site_dir = tmp_path / site_name

    # Scaffold blog - run from tmp_path
    result = run_cli(
        ["new", "site", site_name, "--template", "blog", "--no-init"],
        cwd=str(tmp_path),
        timeout=60,
    )
    assert result.returncode == 0, f"Scaffold failed: {result.stderr}"

    # Build
    result = run_cli(
        ["site", "build"],
        cwd=str(site_dir),
        timeout=120,
    )
    assert result.returncode == 0, f"Build failed: {result.stderr}"

    output_dir = site_dir / "public"

    # RSS feed should exist (either feed.xml or rss.xml or index.xml)
    rss_exists = (
        (output_dir / "feed.xml").exists()
        or (output_dir / "rss.xml").exists()
        or (output_dir / "index.xml").exists()
        or (output_dir / "posts" / "index.xml").exists()
    )
    assert rss_exists, "Blog template should generate RSS feed"


@pytest.mark.integration
def test_docs_template_generates_search_index(tmp_path) -> None:
    """Docs template should generate search index."""
    site_name = "site-docs-search"
    site_dir = tmp_path / site_name

    # Scaffold docs - run from tmp_path
    result = run_cli(
        ["new", "site", site_name, "--template", "docs", "--no-init"],
        cwd=str(tmp_path),
        timeout=60,
    )
    assert result.returncode == 0, f"Scaffold failed: {result.stderr}"

    # Build
    result = run_cli(
        ["site", "build"],
        cwd=str(site_dir),
        timeout=120,
    )
    assert result.returncode == 0, f"Build failed: {result.stderr}"

    output_dir = site_dir / "public"

    # Search index should exist
    search_index_exists = (
        (output_dir / "search-index.json").exists()
        or (output_dir / "index.json").exists()
        or (output_dir / "search" / "index.json").exists()
    )
    assert search_index_exists, "Docs template should generate search index"


@pytest.mark.integration
@pytest.mark.slow
def test_template_dev_server_starts(tmp_path) -> None:
    """Verify dev server can start for default template.

    This is a smoke test to ensure dev server infrastructure works.
    Only tests default template to keep CI fast.
    """
    import subprocess
    import sys
    import time
    import signal

    site_name = "site-dev-server"
    site_dir = tmp_path / site_name

    # Scaffold - run from tmp_path
    result = run_cli(
        ["new", "site", site_name, "--template", "default", "--no-init"],
        cwd=str(tmp_path),
        timeout=60,
    )
    assert result.returncode == 0, f"Scaffold failed: {result.stderr}"

    # Verify site directory was created
    assert site_dir.exists(), "Site directory not created"

    # Start dev server as subprocess
    proc = subprocess.Popen(
        [sys.executable, "-m", "bengal.cli", "site", "serve", "--port", "8765"],
        cwd=str(site_dir),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,  # Create new process group for clean termination
    )

    try:
        # Give server time to start
        time.sleep(3)

        # Check if process is still running (no immediate crash)
        assert proc.poll() is None, "Dev server crashed on startup"

    finally:
        # Clean up - use SIGKILL for reliable termination in tests
        try:
            proc.kill()
            proc.wait(timeout=5)
        except (ProcessLookupError, subprocess.TimeoutExpired, PermissionError, OSError):
            pass  # Process already exited, timed out, or permission denied - OK in cleanup

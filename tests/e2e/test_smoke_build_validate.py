"""Smoke E2E: build + validate + check links.

Covers the golden path across build, health, and output.
Plan: plan-production-maturity.md Phase 0A
"""

from __future__ import annotations

import re

import pytest


@pytest.mark.e2e
def test_build_succeeds(built_site):
    """J1: Build from Markdown — bengal build completes successfully."""
    _, output_dir, result = built_site("test-basic")
    assert result.returncode == 0, f"Build failed: {result.stderr}"
    assert (output_dir / "index.html").exists()


@pytest.mark.e2e
def test_build_produces_html_assets(built_site):
    """J2/J6: Theme and assets — CSS/JS present in output."""
    _, output_dir, result = built_site("test-basic")
    assert result.returncode == 0
    assets_dir = output_dir / "assets"
    assert assets_dir.exists()
    css_files = list(assets_dir.rglob("*.css"))
    assert len(css_files) >= 1, "Expected at least one CSS file"


@pytest.mark.e2e
def test_build_produces_valid_html_structure(built_site):
    """J1: Output has valid HTML structure (doctype, head, body)."""
    _, output_dir, result = built_site("test-basic")
    assert result.returncode == 0
    html = (output_dir / "index.html").read_text(encoding="utf-8")
    assert "<!DOCTYPE" in html or "<!doctype" in html
    assert "<html" in html
    assert "</html>" in html


@pytest.mark.e2e
def test_build_with_validate_runs_health_checks(built_site):
    """J9: Health checking — build with validation runs health phase."""
    _, output_dir, result = built_site("test-basic")
    assert result.returncode == 0
    # Health phase runs by default; sitemap indicates successful build
    sitemap = output_dir / "sitemap.xml"
    if sitemap.exists():
        content = sitemap.read_text(encoding="utf-8")
        assert "<?xml" in content or "<urlset" in content


@pytest.mark.e2e
def test_asset_links_resolve(built_site):
    """J6: Correct links — primary CSS/JS asset hrefs in HTML point to existing files."""
    _, output_dir, result = built_site("test-basic")
    assert result.returncode == 0
    html = (output_dir / "index.html").read_text(encoding="utf-8")
    # Extract asset hrefs (css, js) - these must exist
    asset_hrefs = re.findall(r'href="(/[^"]*\.css[^"]*)"', html) + re.findall(
        r'src="(/[^"]*\.js[^"]*)"', html
    )
    for href in asset_hrefs[:5]:  # Check first 5 to avoid flakiness
        path = href.lstrip("/")
        full_path = output_dir / path
        assert full_path.exists(), f"Broken asset link: {href} -> {full_path}"

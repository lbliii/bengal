"""Integration tests for baseurl handling during builds.

Validates that baseurl configuration (via config and BENGAL_BASEURL env var)
correctly affects asset links, page URLs, and index.json output.

Uses Phase 1 infrastructure: @pytest.mark.bengal with test-baseurl root.
"""

import json

import pytest


@pytest.mark.bengal(testroot="test-baseurl", confoverrides={"site.baseurl": "/bengal"})
def test_build_with_path_baseurl(site, build_site):
    """Test that path-based baseurl is applied to assets and URLs."""
    # Build the site with baseurl="/bengal"
    build_site()

    # Assert assets and index.json present
    assert (site.output_dir / "assets").exists()
    index_path = site.output_dir / "index.json"
    assert index_path.exists()

    # Validate HTML contains baseurl-prefixed CSS
    html = (site.output_dir / "index.html").read_text(encoding="utf-8")
    assert 'href="/bengal/assets/css/style' in html

    # Validate index.json shape and baseurl
    data = json.loads(index_path.read_text(encoding="utf-8"))
    assert data.get("site", {}).get("baseurl") == "/bengal"
    assert isinstance(data.get("pages"), list)
    if data["pages"]:
        sample = data["pages"][0]
        assert "url" in sample and "uri" in sample


def test_build_with_env_absolute_baseurl(site_factory, monkeypatch):
    """Test that BENGAL_BASEURL env var overrides config baseurl."""
    # Override baseurl via environment variable BEFORE creating site
    monkeypatch.setenv("BENGAL_BASEURL", "https://example.com/sub")

    # Create site with empty baseurl (env var will override)
    site = site_factory("test-baseurl", confoverrides={"site.baseurl": ""})

    # Build the site
    site.build()

    # Validate HTML contains absolute baseurl-prefixed CSS
    html = (site.output_dir / "index.html").read_text(encoding="utf-8")
    assert 'href="https://example.com/sub/assets/css/style' in html

    # Validate index.json uses absolute baseurl
    index_path = site.output_dir / "index.json"
    assert index_path.exists()
    data = json.loads(index_path.read_text(encoding="utf-8"))
    assert data.get("site", {}).get("baseurl") == "https://example.com/sub"
    assert isinstance(data.get("pages"), list)
    if data["pages"]:
        sample = data["pages"][0]
        assert sample["url"].startswith("https://example.com/sub/")

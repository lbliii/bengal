from __future__ import annotations

from pathlib import Path

import pytest

from bengal.core.site import Site
from bengal.rendering.template_engine import TemplateEngine
from tests._testing.mocks import MockPage


def test_baseurl_meta_and_nav_links(tmp_path: Path):
    # Arrange: minimal site with config
    site_dir = tmp_path / "site"
    (site_dir / "content").mkdir(parents=True)
    (site_dir / "public").mkdir(parents=True)

    cfg = site_dir / "bengal.toml"
    cfg.write_text(
        """
[site]
title = "Test"
baseurl = "/bengal"

[build]
output_dir = "public"
        """,
        encoding="utf-8",
    )

    (site_dir / "content" / "index.md").write_text(
        """---\ntitle: Home\n---\n# Home\n""", encoding="utf-8"
    )

    site = Site.from_config(site_dir)
    engine = TemplateEngine(site)

    html = engine.render("base.html", {"page": None})

    assert '<meta name="bengal:baseurl" content="/bengal">' in html
    # Logo link uses absolute_url
    assert 'href="/bengal/"' in html


def test_url_for_with_baseurl_path_only(tmp_path: Path):
    """Test that url_for applies path-only base URLs correctly."""
    # Arrange: site with path-only base URL
    site_dir = tmp_path / "site"
    (site_dir / "content").mkdir(parents=True)
    (site_dir / "public").mkdir(parents=True)

    cfg = site_dir / "bengal.toml"
    cfg.write_text(
        """
[site]
title = "Test"
baseurl = "/bengal"

[build]
output_dir = "public"
        """,
        encoding="utf-8",
    )

    (site_dir / "content" / "api").mkdir(parents=True)
    (site_dir / "content" / "api" / "module.md").write_text(
        """---\ntitle: Module\n---\n# Module\n""", encoding="utf-8"
    )

    site = Site.from_config(site_dir)
    engine = TemplateEngine(site)

    page = MockPage(title="Module", url="/api/module/", slug="module")
    result = engine._url_for(page)

    # Assert: url_for should prepend the base URL
    assert result == "/bengal/api/module/"


def test_url_for_with_baseurl_absolute(tmp_path: Path):
    """Test that url_for applies absolute base URLs correctly."""
    # Arrange: site with absolute base URL
    site_dir = tmp_path / "site"
    (site_dir / "content").mkdir(parents=True)
    (site_dir / "public").mkdir(parents=True)

    cfg = site_dir / "bengal.toml"
    cfg.write_text(
        """
[site]
title = "Test"
baseurl = "https://example.com"

[build]
output_dir = "public"
        """,
        encoding="utf-8",
    )

    (site_dir / "content" / "api").mkdir(parents=True)
    (site_dir / "content" / "api" / "module.md").write_text(
        """---\ntitle: Module\n---\n# Module\n""", encoding="utf-8"
    )

    site = Site.from_config(site_dir)
    engine = TemplateEngine(site)

    page = MockPage(title="Module", url="/api/module/", slug="module")
    result = engine._url_for(page)

    # Assert: url_for should prepend the absolute base URL
    assert result == "https://example.com/api/module/"


def test_url_for_without_baseurl(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Test that url_for works correctly without a base URL."""
    # Ensure BENGAL_BASEURL isn't set from test matrix
    monkeypatch.delenv("BENGAL_BASEURL", raising=False)
    monkeypatch.delenv("BENGAL_BASE_URL", raising=False)
    # Ensure CI environment variables don't auto-detect baseurl
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    monkeypatch.delenv("NETLIFY", raising=False)
    monkeypatch.delenv("VERCEL", raising=False)

    # Arrange: site without base URL
    site_dir = tmp_path / "site"
    (site_dir / "content").mkdir(parents=True)
    (site_dir / "public").mkdir(parents=True)

    cfg = site_dir / "bengal.toml"
    cfg.write_text(
        """
[site]
title = "Test"

[build]
output_dir = "public"
        """,
        encoding="utf-8",
    )

    (site_dir / "content" / "api").mkdir(parents=True)
    (site_dir / "content" / "api" / "module.md").write_text(
        """---\ntitle: Module\n---\n# Module\n""", encoding="utf-8"
    )

    site = Site.from_config(site_dir)
    engine = TemplateEngine(site)

    page = MockPage(title="Module", url="/api/module/", slug="module")
    result = engine._url_for(page)

    # Assert: url_for should return the URL as-is
    assert result == "/api/module/"

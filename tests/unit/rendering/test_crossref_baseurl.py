"""
Tests for cross-reference functions with base URL support.

Tests that ref(), anchor(), and relref() properly handle base URLs
in various scenarios (path-only, absolute, none).
"""

from __future__ import annotations

from pathlib import Path

from bengal.core.site import Site
from bengal.rendering.template_functions import crossref
from tests._testing.page_records import make_test_page


def _page(source_path: str, title: str | None, output_path: Path, site: Site):
    metadata = {"title": title} if title is not None else {}
    page = make_test_page(source_path=Path(source_path), metadata=metadata)
    page.output_path = output_path
    page._site = site
    return page


class TestRefWithBaseUrl:
    """Test ref() function with base URL configurations."""

    def test_ref_with_path_baseurl(self, tmp_path):
        """Test ref() with path-only base URL like /bengal."""
        site = Site(root_path=tmp_path, config={}, theme="default")
        site.output_dir = tmp_path / "public"

        page = _page(
            "docs/install.md",
            "Installation",
            tmp_path / "public" / "docs" / "installation" / "index.html",
            site,
        )

        index = {
            "by_path": {"docs/installation": page},
            "by_slug": {},
            "by_id": {},
            "by_heading": {},
        }

        # Test with path-only base URL
        result = crossref.ref("docs/installation", index, baseurl="/bengal")
        assert '<a href="/bengal/docs/installation/">Installation</a>' in result

        # Test with custom text
        result = crossref.ref("docs/installation", index, baseurl="/bengal", text="Install")
        assert '<a href="/bengal/docs/installation/">Install</a>' in result

    def test_ref_with_absolute_baseurl(self, tmp_path):
        """Test ref() with absolute base URL like https://example.com."""
        site = Site(root_path=tmp_path, config={}, theme="default")
        site.output_dir = tmp_path / "public"

        page = _page(
            "api/module.md",
            "Module API",
            tmp_path / "public" / "api" / "module" / "index.html",
            site,
        )

        index = {
            "by_path": {"api/module": page},
            "by_slug": {},
            "by_id": {},
            "by_heading": {},
        }

        result = crossref.ref("api/module", index, baseurl="https://example.com")
        assert '<a href="https://example.com/api/module/">Module API</a>' in result

    def test_ref_without_baseurl(self, tmp_path):
        """Test ref() without base URL (default behavior)."""
        site = Site(root_path=tmp_path, config={}, theme="default")
        site.output_dir = tmp_path / "public"

        page = _page(
            "docs/about.md",
            "About",
            tmp_path / "public" / "docs" / "about" / "index.html",
            site,
        )

        # Use path-based lookup (same pattern as existing tests)
        index = {
            "by_path": {"docs/about": page},
            "by_slug": {},
            "by_id": {},
            "by_heading": {},
        }

        result = crossref.ref("docs/about", index, baseurl="")
        assert '<a href="/docs/about/">About</a>' in result


class TestAnchorWithBaseUrl:
    """Test anchor() function with base URL configurations."""

    def test_anchor_with_path_baseurl(self, tmp_path):
        """Test anchor() with path-only base URL."""
        site = Site(root_path=tmp_path, config={}, theme="default")
        site.output_dir = tmp_path / "public"

        page = _page(
            "docs/guide.md",
            "Guide",
            tmp_path / "public" / "docs" / "guide" / "index.html",
            site,
        )

        index = {
            "by_path": {},
            "by_slug": {},
            "by_id": {},
            "by_heading": {"installation": [(page, "installation")]},
        }

        result = crossref.anchor("Installation", index, baseurl="/bengal")
        assert '<a href="/bengal/docs/guide/#installation">Installation</a>' in result

    def test_anchor_with_absolute_baseurl(self, tmp_path):
        """Test anchor() with absolute base URL."""
        site = Site(root_path=tmp_path, config={}, theme="default")
        site.output_dir = tmp_path / "public"

        page = _page(
            "tutorial.md", "Tutorial", tmp_path / "public" / "tutorial" / "index.html", site
        )

        index = {
            "by_path": {},
            "by_slug": {},
            "by_id": {},
            "by_heading": {"getting started": [(page, "getting-started")]},
        }

        result = crossref.anchor("Getting Started", index, baseurl="https://docs.example.com")
        assert (
            '<a href="https://docs.example.com/tutorial/#getting-started">Getting Started</a>'
            in result
        )

    def test_anchor_without_baseurl(self, tmp_path):
        """Test anchor() without base URL."""
        site = Site(root_path=tmp_path, config={}, theme="default")
        site.output_dir = tmp_path / "public"

        page = _page("faq.md", "FAQ", tmp_path / "public" / "faq" / "index.html", site)

        index = {
            "by_path": {},
            "by_slug": {},
            "by_id": {},
            "by_heading": {"how to": [(page, "how-to")]},
        }

        result = crossref.anchor("How to", index, baseurl="")
        assert '<a href="/faq/#how-to">How to</a>' in result


class TestRelrefWithBaseUrl:
    """Test relref() function with base URL configurations."""

    def test_relref_with_path_baseurl(self, tmp_path):
        """Test relref() with path-only base URL."""
        site = Site(root_path=tmp_path, config={}, theme="default")
        site.output_dir = tmp_path / "public"

        page = _page(
            "docs/api.md",
            None,
            tmp_path / "public" / "docs" / "api" / "index.html",
            site,
        )

        index = {
            "by_path": {"docs/api": page},
            "by_slug": {},
            "by_id": {},
            "by_heading": {},
        }

        result = crossref.relref("docs/api", index, baseurl="/bengal")
        assert result == "/bengal/docs/api/"

    def test_relref_with_absolute_baseurl(self, tmp_path):
        """Test relref() with absolute base URL."""
        site = Site(root_path=tmp_path, config={}, theme="default")
        site.output_dir = tmp_path / "public"

        page = _page(
            "cli/commands.md",
            None,
            tmp_path / "public" / "cli" / "commands" / "index.html",
            site,
        )

        index = {
            "by_path": {"cli/commands": page},
            "by_slug": {},
            "by_id": {},
            "by_heading": {},
        }

        result = crossref.relref("cli/commands", index, baseurl="https://example.com")
        assert result == "https://example.com/cli/commands/"

    def test_relref_without_baseurl(self, tmp_path):
        """Test relref() without base URL."""
        site = Site(root_path=tmp_path, config={}, theme="default")
        site.output_dir = tmp_path / "public"

        page = _page(
            "blog/post.md",
            None,
            tmp_path / "public" / "blog" / "post" / "index.html",
            site,
        )

        index = {
            "by_path": {"blog/post": page},
            "by_slug": {},
            "by_id": {},
            "by_heading": {},
        }

        result = crossref.relref("blog/post", index, baseurl="")
        assert result == "/blog/post/"

    def test_relref_not_found(self):
        """Test relref() returns empty string for non-existent pages."""
        index = {
            "by_path": {},
            "by_slug": {},
            "by_id": {},
            "by_heading": {},
        }

        result = crossref.relref("nonexistent", index, baseurl="/bengal")
        assert result == ""


class TestCrossReferenceIntegrationWithBaseUrl:
    """Integration tests with full Site and base URL configuration."""

    def test_ref_via_template_engine(self, tmp_path):
        """Test ref() function via template engine with base URL in config."""
        from bengal.rendering.template_engine import TemplateEngine

        # Create site with base URL
        site_dir = tmp_path / "site"
        (site_dir / "content").mkdir(parents=True)
        (site_dir / "public").mkdir(parents=True)

        cfg = site_dir / "bengal.toml"
        cfg.write_text(
            """
[site]
title = "Test"
baseurl = "/docs"

[build]
output_dir = "public"
            """,
            encoding="utf-8",
        )

        (site_dir / "content" / "api").mkdir()
        (site_dir / "content" / "api" / "reference.md").write_text(
            """---\ntitle: API Reference\n---\n# API\n""", encoding="utf-8"
        )

        site = Site.from_config(site_dir)

        # Create a page and add to index
        page = _page(
            "api/reference.md",
            "API Reference",
            site_dir / "public" / "api" / "reference" / "index.html",
            site,
        )

        # Build xref index
        site.xref_index = {
            "by_path": {"api/reference": page},
            "by_slug": {},
            "by_id": {},
            "by_heading": {},
        }

        # Create template engine and render template with ref() function
        engine = TemplateEngine(site)

        # Test ref function in template
        template_str = "{{ ref('api/reference') }}"
        result = engine.render_string(template_str, {})

        assert "/docs/api/reference/" in result
        assert "API Reference" in result

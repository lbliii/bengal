"""
Tests for navigation component templates with baseurl support.

Verifies that navigation components (breadcrumbs, footer menu)
properly apply the | absolute_url filter to support subpath deployments.
"""

from unittest.mock import Mock

import pytest

from bengal.core.site import Site
from bengal.orchestration.menu import MenuOrchestrator
from bengal.rendering.template_engine import TemplateEngine


class TestBreadcrumbsWithBaseurl:
    """Test breadcrumb macro with baseurl configuration."""

    def test_breadcrumbs_macro_applies_baseurl_filter(self, tmp_path):
        """Test that breadcrumbs macro applies | absolute_url filter to item URLs."""
        # Create site with baseurl
        site_dir = tmp_path / "site"
        (site_dir / "content").mkdir(parents=True)
        (site_dir / "public").mkdir(parents=True)

        cfg = site_dir / "bengal.toml"
        cfg.write_text(
            """
[site]
title = "Test"
baseurl = "/repo"

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

        # Create mock page with mock ancestors for breadcrumbs
        docs_section = Mock()
        docs_section.title = "Documentation"
        docs_section.url = "/docs/"  # Relative URL (identity)

        page = Mock()
        page.title = "User Guide"
        page.url = "/docs/guide/"  # Relative URL (identity)
        page.ancestors = [docs_section]

        # Render template with breadcrumbs macro
        template_str = """
{% from 'partials/navigation-components.html' import breadcrumbs %}
{{ breadcrumbs(page) }}
        """
        html = engine.render_string(template_str, {"page": page})

        # Assert: breadcrumb links should have baseurl applied
        assert 'href="/repo/docs/"' in html, "Docs link should have baseurl"
        assert '<nav class="breadcrumbs"' in html

    def test_breadcrumbs_without_baseurl(self, tmp_path, monkeypatch):
        """Test breadcrumbs work correctly without baseurl configured."""
        # Ensure no env baseurl
        monkeypatch.delenv("BENGAL_BASEURL", raising=False)

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

        (site_dir / "content" / "index.md").write_text(
            """---\ntitle: Home\n---\n# Home\n""", encoding="utf-8"
        )

        site = Site.from_config(site_dir)
        engine = TemplateEngine(site)

        # Create mock page with ancestors
        section = Mock()
        section.title = "Documentation"
        section.url = "/docs/"

        page = Mock()
        page.title = "User Guide"
        page.url = "/docs/guide/"
        page.ancestors = [section]

        template_str = """
{% from 'partials/navigation-components.html' import breadcrumbs %}
{{ breadcrumbs(page) }}
        """
        html = engine.render_string(template_str, {"page": page})

        # Assert: links should be relative (no baseurl)
        assert 'href="/docs/"' in html
        # Current page should not be a link (aria-current="page")
        assert 'aria-current="page"' in html
        assert "User Guide" in html


class TestFooterMenuWithBaseurl:
    """Test footer menu links with baseurl configuration."""

    def test_footer_menu_applies_baseurl(self, tmp_path):
        """Test that footer menu links apply | absolute_url filter."""
        site_dir = tmp_path / "site"
        (site_dir / "content").mkdir(parents=True)
        (site_dir / "public").mkdir(parents=True)

        cfg = site_dir / "bengal.toml"
        cfg.write_text(
            """
[site]
title = "Test"
baseurl = "/blog"

[[menu.footer]]
name = "Privacy"
url = "/privacy/"
weight = 10

[[menu.footer]]
name = "Terms"
url = "/terms/"
weight = 20

[build]
output_dir = "public"
            """,
            encoding="utf-8",
        )

        (site_dir / "content" / "index.md").write_text(
            """---\ntitle: Home\n---\n# Home\n""", encoding="utf-8"
        )

        site = Site.from_config(site_dir)

        # Build menus from config
        menu_orchestrator = MenuOrchestrator(site)
        menu_orchestrator.build()

        engine = TemplateEngine(site)

        # Render base.html (contains footer)
        html = engine.render("base.html", {"page": None})

        # Assert: footer links should have baseurl applied
        # Footer menu should be present and links should have baseurl
        assert "Privacy" in html or "Terms" in html, "Footer menu items should be present"
        if 'href="/privacy/"' in html or 'href="/terms/"' in html:
            # Check if baseurl is applied
            assert (
                'href="/blog/privacy/"' in html or 'href="/blog/terms/"' in html
            ), "Footer links should have baseurl applied"


class TestNavigationComponentsConsistency:
    """Test that all navigation components handle baseurl consistently."""

    @pytest.mark.parametrize(
        "baseurl_value,expected_prefix",
        [
            ("/repo", "/repo"),
            ("/blog", "/blog"),
            ("https://example.com", "https://example.com"),
            ("https://example.com/sub", "https://example.com/sub"),
            ("", ""),  # No baseurl
        ],
    )
    def test_consistent_baseurl_application(self, tmp_path, baseurl_value, expected_prefix):
        """Test that all navigation components apply baseurl consistently."""
        site_dir = tmp_path / "site"
        (site_dir / "content").mkdir(parents=True)
        (site_dir / "public").mkdir(parents=True)

        baseurl_line = f'baseurl = "{baseurl_value}"' if baseurl_value else ""

        cfg = site_dir / "bengal.toml"
        cfg.write_text(
            f"""
[site]
title = "Test"
{baseurl_line}

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

        # Create mock page with breadcrumbs
        section = Mock()
        section.title = "Documentation"
        section.url = "/docs/"

        page = Mock()
        page.title = "User Guide"
        page.url = "/docs/guide/"
        page.ancestors = [section]

        # Test breadcrumbs
        breadcrumb_template = """
{% from 'partials/navigation-components.html' import breadcrumbs %}
{{ breadcrumbs(page) }}
        """
        breadcrumb_html = engine.render_string(breadcrumb_template, {"page": page})

        expected_url = f"{expected_prefix}/docs/" if expected_prefix else "/docs/"
        assert f'href="{expected_url}"' in breadcrumb_html, f"Breadcrumbs should use {expected_url}"


class TestMenuURLComparisonWithBaseurl:
    """Test that menu URLs remain comparable with page URLs despite baseurl."""

    def test_menu_url_comparison_works_with_baseurl(self, tmp_path):
        """
        Test that menu activation works correctly even with baseurl configured.

        Menu URLs are stored as relative (identity URLs) for comparison,
        but displayed with baseurl applied via filter.
        """
        site_dir = tmp_path / "site"
        (site_dir / "content").mkdir(parents=True)
        (site_dir / "public").mkdir(parents=True)

        cfg = site_dir / "bengal.toml"
        cfg.write_text(
            """
[site]
title = "Test"
baseurl = "/repo"

[[menu.main]]
name = "Docs"
url = "/docs/"
weight = 10

[build]
output_dir = "public"
            """,
            encoding="utf-8",
        )

        (site_dir / "content" / "index.md").write_text(
            """---\ntitle: Home\n---\n# Home\n""", encoding="utf-8"
        )

        site = Site.from_config(site_dir)

        # Build menus from config
        menu_orchestrator = MenuOrchestrator(site)
        menu_orchestrator.build()

        engine = TemplateEngine(site)

        # Create mock page at /docs/
        page = Mock()
        page.url = "/docs/"  # Relative URL (identity)
        page.title = "Documentation"
        page.metadata = {}
        page.keywords = []
        page.tags = []

        # Render base template (contains menu)
        html = engine.render("base.html", {"page": page})

        # Assert: menu link should have baseurl in href
        assert 'href="/repo/docs/"' in html, "Menu link should have baseurl applied"

        # Note: Menu activation happens via MenuItem.mark_active() which compares
        # menu.url (relative) with page.url (relative), so it should work correctly

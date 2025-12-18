"""
Tests for taxonomy functions with base URL support.

Tests that tag_url() properly handles base URLs in various scenarios,
including i18n prefix strategy combined with base URLs.
"""

from pathlib import Path

from bengal.core.site import Site


class TestTagUrlWithBaseUrl:
    """Test tag_url function with base URL configurations."""

    def test_tag_url_with_path_baseurl(self, tmp_path):
        """Test tag_url with path-only base URL like /bengal."""
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

        # Test tag_url in template
        template_str = "{{ tag_url('python') }}"
        result = engine.render_string(template_str, {})

        assert result == "/bengal/tags/python/"

    def test_tag_url_with_absolute_baseurl(self, tmp_path):
        """Test tag_url with absolute base URL like https://example.com."""
        from bengal.rendering.template_engine import TemplateEngine

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

        (site_dir / "content" / "index.md").write_text(
            """---\ntitle: Home\n---\n# Home\n""", encoding="utf-8"
        )

        site = Site.from_config(site_dir)
        engine = TemplateEngine(site)

        # Test tag_url in template
        template_str = "{{ tag_url('web-dev') }}"
        result = engine.render_string(template_str, {})

        assert result == "https://example.com/tags/web-dev/"

    def test_tag_url_without_baseurl(self, tmp_path, monkeypatch):
        """Test tag_url without base URL (default behavior)."""
        from bengal.rendering.template_engine import TemplateEngine

        # Clear CI env vars to prevent auto-detection
        monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
        monkeypatch.delenv("NETLIFY", raising=False)
        monkeypatch.delenv("VERCEL", raising=False)
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

        # Test tag_url in template
        template_str = "{{ tag_url('javascript') }}"
        result = engine.render_string(template_str, {})

        assert result == "/tags/javascript/"

    def test_tag_url_with_baseurl_and_i18n_prefix(self, tmp_path):
        """Test tag_url with both base URL and i18n prefix strategy."""
        from bengal.core.page import Page
        from bengal.rendering.template_engine import TemplateEngine

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

[i18n]
enabled = true
strategy = "prefix"
default_language = "en"
default_in_subdir = true
languages = ["en", "fr"]
            """,
            encoding="utf-8",
        )

        (site_dir / "content" / "index.md").write_text(
            """---\ntitle: Home\n---\n# Home\n""", encoding="utf-8"
        )

        site = Site.from_config(site_dir)
        engine = TemplateEngine(site)

        # Create a French page to provide language context
        page = Page(source_path=Path("content/fr/post.md"))
        page.metadata = {"title": "Post", "lang": "fr"}
        page.output_path = site_dir / "public" / "fr" / "post" / "index.html"
        page._site = site
        # Set lang as a direct attribute (used by tag_url_with_site)
        page.lang = "fr"

        # Test tag_url with French page context (should have /fr prefix AND base URL)
        template_str = "{{ tag_url('python') }}"
        result = engine.render_string(template_str, {"page": page})

        # Should have base URL /docs + language prefix /fr + tag path /tags/python/
        assert result == "/docs/fr/tags/python/"

    def test_tag_url_with_baseurl_no_i18n_for_default_lang(self, tmp_path):
        """Test tag_url with base URL but no i18n prefix for default language."""
        from bengal.core.page import Page
        from bengal.rendering.template_engine import TemplateEngine

        site_dir = tmp_path / "site"
        (site_dir / "content").mkdir(parents=True)
        (site_dir / "public").mkdir(parents=True)

        cfg = site_dir / "bengal.toml"
        cfg.write_text(
            """
[site]
title = "Test"
baseurl = "/site"

[build]
output_dir = "public"

[i18n]
enabled = true
strategy = "prefix"
default_language = "en"
default_in_subdir = false
languages = ["en", "es"]
            """,
            encoding="utf-8",
        )

        (site_dir / "content" / "index.md").write_text(
            """---\ntitle: Home\n---\n# Home\n""", encoding="utf-8"
        )

        site = Site.from_config(site_dir)
        engine = TemplateEngine(site)

        # Create an English page (default language, no subdir)
        page = Page(source_path=Path("content/post.md"))
        page.metadata = {"title": "Post", "lang": "en"}
        page.output_path = site_dir / "public" / "post" / "index.html"
        page._site = site
        # Set lang as a direct attribute (used by tag_url_with_site)
        page.lang = "en"

        # Test tag_url with English page (should NOT have /en prefix, but should have base URL)
        template_str = "{{ tag_url('django') }}"
        result = engine.render_string(template_str, {"page": page})

        # Should have base URL /site + tag path /tags/django/ (no /en)
        assert result == "/site/tags/django/"

    def test_tag_url_with_spaces_and_baseurl(self, tmp_path):
        """Test tag_url with spaces in tag name and base URL."""
        from bengal.rendering.template_engine import TemplateEngine

        site_dir = tmp_path / "site"
        (site_dir / "content").mkdir(parents=True)
        (site_dir / "public").mkdir(parents=True)

        cfg = site_dir / "bengal.toml"
        cfg.write_text(
            """
[site]
title = "Test"
baseurl = "/blog"

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

        # Test tag_url with spaces (should be slugified)
        template_str = "{{ tag_url('web development') }}"
        result = engine.render_string(template_str, {})

        assert result == "/blog/tags/web-development/"


class TestTagUrlInAutodocContext:
    """Test tag_url behavior specifically in autodoc page contexts."""

    def test_tag_url_in_api_reference_page(self, tmp_path):
        """Test tag_url works correctly when called from API reference pages."""
        from bengal.core.page import Page
        from bengal.rendering.template_engine import TemplateEngine

        site_dir = tmp_path / "site"
        (site_dir / "content").mkdir(parents=True)
        (site_dir / "content" / "api").mkdir()
        (site_dir / "public").mkdir(parents=True)

        cfg = site_dir / "bengal.toml"
        cfg.write_text(
            """
[site]
title = "API Docs"
baseurl = "https://docs.myproject.org"

[build]
output_dir = "public"
            """,
            encoding="utf-8",
        )

        # Create an autodoc API page
        (site_dir / "content" / "api" / "module.md").write_text(
            """---
title: module
type: python-module
tags: ["api", "core"]
---
# Module Documentation
""",
            encoding="utf-8",
        )

        site = Site.from_config(site_dir)
        engine = TemplateEngine(site)

        # Create page object for API reference
        page = Page(source_path=Path("content/api/module.md"))
        page.metadata = {"title": "module", "type": "python-module", "tags": ["api", "core"]}
        page.output_path = site_dir / "public" / "api" / "module" / "index.html"
        page._site = site

        # Test tag_url in API page context
        template_str = "{{ tag_url('api') }}"
        result = engine.render_string(template_str, {"page": page})

        # Should have absolute base URL + tag path
        assert result == "https://docs.myproject.org/tags/api/"

    def test_tag_url_in_cli_reference_page(self, tmp_path):
        """Test tag_url works correctly when called from CLI reference pages."""
        from bengal.core.page import Page
        from bengal.rendering.template_engine import TemplateEngine

        site_dir = tmp_path / "site"
        (site_dir / "content").mkdir(parents=True)
        (site_dir / "content" / "cli").mkdir()
        (site_dir / "public").mkdir(parents=True)

        cfg = site_dir / "bengal.toml"
        cfg.write_text(
            """
[site]
title = "CLI Docs"
baseurl = "/myapp"

[build]
output_dir = "public"
            """,
            encoding="utf-8",
        )

        # Create a CLI reference page
        (site_dir / "content" / "cli" / "build.md").write_text(
            """---
title: build
type: autodoc/cli
tags: ["cli", "build"]
---
# Build Command
""",
            encoding="utf-8",
        )

        site = Site.from_config(site_dir)
        engine = TemplateEngine(site)

        # Create page object for CLI reference
        page = Page(source_path=Path("content/cli/build.md"))
        page.metadata = {"title": "build", "type": "autodoc/cli", "tags": ["cli", "build"]}
        page.output_path = site_dir / "public" / "cli" / "build" / "index.html"
        page._site = site

        # Test tag_url in CLI page context
        template_str = "{{ tag_url('cli') }}"
        result = engine.render_string(template_str, {"page": page})

        # Should have path base URL + tag path
        assert result == "/myapp/tags/cli/"

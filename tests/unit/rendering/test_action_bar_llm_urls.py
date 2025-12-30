"""
Tests for action-bar template LLM.txt URL generation.

Verifies that the action-bar partial correctly generates LLM.txt URLs
for the "Copy LLM text" and "Open LLM text" functionality.
"""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from bengal.rendering.engines import create_engine


class TestActionBarLLMUrls:
    """Test LLM.txt URL generation in action-bar template."""

    @pytest.fixture
    def template_engine(self, tmp_path):
        """Create a TemplateEngine with real action-bar template."""
        # Create minimal site structure
        (tmp_path / "content").mkdir()
        config_content = """
[site]
title = "Test Site"
baseurl = "https://example.com"
"""
        (tmp_path / "bengal.toml").write_text(config_content)

        # Create site
        from bengal.core.site import Site

        site = Site.from_config(tmp_path)

        # Create template engine (defaults to Kida which supports {% def %} syntax)
        engine = create_engine(site)
        return engine

    def _create_mock_page(self, title, url, _raw_content="Content"):
        """Create a mock page with all required attributes."""
        page = Mock()
        page.title = title
        page.href = url
        page._path = url  # _path doesn't include baseurl
        page.metadata = {}
        page.date = None
        page.content = _raw_content
        page.ancestors = []  # Required for breadcrumbs
        return page

    def test_action_bar_generates_index_txt_url(self, template_engine):
        """Test that action-bar generates correct index.txt URL for pages."""
        page = self._create_mock_page("Getting Started", "/docs/getting-started/", "Page content")

        # Render the action-bar partial
        rendered = template_engine.render_template("partials/action-bar.html", {"page": page})

        # Check that the LLM.txt URL is correct
        # canonical_url() returns full URL with baseurl, so we check for index.txt in path
        assert "docs/getting-started/index.txt" in rendered, (
            "Action bar should include index.txt URL"
        )

    def test_action_bar_llm_url_for_root_page(self, template_engine):
        """Test LLM.txt URL for root-level pages."""
        page = self._create_mock_page("Home", "/", "Home content")

        rendered = template_engine.render_template("partials/action-bar.html", {"page": page})

        # Root page should have /index.txt
        assert "/index.txt" in rendered

    def test_action_bar_llm_url_for_nested_page(self, template_engine):
        """Test LLM.txt URL for deeply nested pages."""
        page = self._create_mock_page(
            "Advanced Topics", "/docs/guides/advanced/topics/", "Advanced content"
        )

        rendered = template_engine.render_template("partials/action-bar.html", {"page": page})

        # Should generate correct nested path (canonical_url includes baseurl scheme)
        assert "docs/guides/advanced/topics/index.txt" in rendered

    def test_action_bar_has_copy_llm_txt_button(self, template_engine):
        """Test that action-bar includes 'Copy LLM text' button."""
        page = self._create_mock_page("Test Page", "/test/")

        rendered = template_engine.render_template("partials/action-bar.html", {"page": page})

        # Check for Copy LLM text button
        assert "Copy LLM text" in rendered
        assert 'data-action="copy-llm-txt"' in rendered

    def test_action_bar_has_open_llm_txt_link(self, template_engine):
        """Test that action-bar includes 'Open LLM text' link."""
        page = self._create_mock_page("Test Page", "/test/")

        rendered = template_engine.render_template("partials/action-bar.html", {"page": page})

        # Check for Open LLM text link
        assert "Open LLM text" in rendered
        # The URL should contain index.txt - it might be absolute or with baseurl
        assert "index.txt" in rendered
        assert "/test/" in rendered or "test/index.txt" in rendered

    def test_action_bar_ai_share_links_use_llm_url(self, template_engine):
        """Test that AI assistant share links use correct LLM.txt URL."""
        page = self._create_mock_page("Documentation", "/docs/", "Docs content")

        rendered = template_engine.render_template("partials/action-bar.html", {"page": page})

        # Check that AI share links include the LLM.txt URL
        # The share prompt should reference index.txt (may be URL-encoded in share links)
        assert "index.txt" in rendered

        # Should have share links to AI assistants
        assert "Ask Claude" in rendered
        assert "Ask ChatGPT" in rendered
        assert "Ask Gemini" in rendered
        assert "Ask Copilot" in rendered

    def test_action_bar_url_encoding_in_share_links(self, template_engine):
        """Test that URLs are properly encoded in share links."""
        page = self._create_mock_page("Test Page", "/test/")

        rendered = template_engine.render_template("partials/action-bar.html", {"page": page})

        # Share links should have URL-encoded parameters
        assert "claude.ai/new?q=" in rendered
        assert "chatgpt.com/?q=" in rendered

        # The prompt text should be URL-encoded (spaces as %20)
        assert "%20" in rendered  # Encoded spaces

    def test_action_bar_without_page_renders_nothing(self, template_engine):
        """Test that action-bar renders nothing when page is None."""
        template = template_engine.env.get_template("partials/action-bar.html")
        rendered = template.render(page=None)

        # Should render empty or minimal output
        assert rendered.strip() == "" or "action-bar" not in rendered


class TestLLMUrlTemplateHelpers:
    """Test template helper functions used for LLM.txt URLs."""

    @pytest.fixture
    def template_engine(self, tmp_path):
        """Create a TemplateEngine for testing helpers."""
        (tmp_path / "content").mkdir()
        config = """
[site]
title = "Test Site"
baseurl = "https://example.com"
"""
        (tmp_path / "bengal.toml").write_text(config)

        from bengal.core.site import Site

        site = Site.from_config(tmp_path)
        engine = create_engine(site)
        return engine

    def test_ensure_trailing_slash_function(self, template_engine):
        """Test that ensure_trailing_slash helper works correctly."""
        # This function is used in action-bar.html to construct LLM.txt URLs
        result = template_engine.render_string("{{ ensure_trailing_slash('/test') }}", {})
        assert result == "/test/"

    def test_ensure_trailing_slash_idempotent(self, template_engine):
        """Test that ensure_trailing_slash is idempotent."""
        result = template_engine.render_string("{{ ensure_trailing_slash('/test/') }}", {})
        assert result == "/test/"

    def test_canonical_url_function(self, template_engine):
        """Test that canonical_url helper works correctly."""
        # Used in action-bar to get the canonical URL for a page
        result = template_engine.render_string("{{ canonical_url('/docs/') }}", {})
        # Should return absolute URL with baseurl
        assert result == "https://example.com/docs/"

    def test_urlencode_filter(self, template_engine):
        """Test that urlencode filter works for share links."""
        result = template_engine.render_string(
            "{{ 'Please help: /test/index.txt' | urlencode }}", {}
        )
        # Should encode spaces and special chars
        assert "%20" in result or "+" in result
        assert "index.txt" in result


class TestActionBarIntegration:
    """Integration tests for action-bar in full page rendering."""

    def test_action_bar_in_full_page_render(self, tmp_path):
        """Test that action-bar with LLM URLs works in full page context."""
        # Create a minimal site
        site_dir = tmp_path / "site"
        site_dir.mkdir()
        (site_dir / "content").mkdir()

        # Config
        config = """
[site]
title = "Test Site"
baseurl = "https://example.com"
"""
        (site_dir / "bengal.toml").write_text(config)

        # Create a page
        page_content = """---
title: "Test Page"
---

# Test Page

This is test content.
"""
        (site_dir / "content" / "test.md").write_text(page_content)

        # Build the site
        from bengal.core.site import Site
        from bengal.orchestration.build.options import BuildOptions

        site = Site.from_config(site_dir)
        site.build(BuildOptions())

        # Read the generated HTML
        html_path = site.output_dir / "test" / "index.html"
        html_content = html_path.read_text()

        # Check that action-bar is present with LLM URLs
        assert "action-bar" in html_content.lower()
        # LLM.txt URL should be present
        assert "/test/index.txt" in html_content or "index.txt" in html_content
        # Share functionality should be present
        assert "Copy LLM text" in html_content or "copy-llm-txt" in html_content

"""
Tests for type-based template selection.

Verifies that content types correctly map to template families.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock

import pytest

from bengal.core.page import Page
from bengal.core.section import Section
from bengal.rendering.renderer import Renderer


class TestTypeMappings:
    """Test that content types map to correct templates."""

    def test_python_module_maps_to_api_reference(self):
        """Test that type: python-module uses autodoc/python templates."""
        # Setup
        site = Mock()
        renderer = Renderer(site)

        page = Mock(spec=Page)
        page.metadata = {"type": "python-module"}
        page.source_path = Path("content/api/module.md")
        page._section = None
        page.is_home = False
        page.url = "/api/module/"

        # Mock template_exists to return True for autodoc/python
        def template_exists(name):
            return name == "autodoc/python/single.html"

        renderer._template_exists = template_exists

        # Execute
        template = renderer._get_template_name(page)

        # Verify
        assert template == "autodoc/python/single.html"

    def test_cli_command_maps_to_cli_reference(self):
        """Test that type: cli-command uses autodoc/cli templates."""
        site = Mock()
        renderer = Renderer(site)

        page = Mock(spec=Page)
        page.metadata = {"type": "cli-command"}
        page.source_path = Path("content/cli/build.md")
        page._section = None
        page.is_home = False
        page.url = "/cli/build/"

        def template_exists(name):
            return name == "autodoc/cli/single.html"

        renderer._template_exists = template_exists

        template = renderer._get_template_name(page)

        assert template == "autodoc/cli/single.html"

    def test_doc_type_maps_to_doc_templates(self):
        """Test that type: doc uses doc templates."""
        site = Mock()
        renderer = Renderer(site)

        page = Mock(spec=Page)
        page.metadata = {"type": "doc"}
        page.source_path = Path("content/docs/guide.md")
        page._section = None
        page.is_home = False
        page.url = "/docs/guide/"

        def template_exists(name):
            return name == "doc/single.html"

        renderer._template_exists = template_exists

        template = renderer._get_template_name(page)

        assert template == "doc/single.html"

    def test_tutorial_type_maps_to_tutorial_templates(self):
        """Test that type: tutorial uses tutorial templates."""
        site = Mock()
        renderer = Renderer(site)

        page = Mock(spec=Page)
        page.metadata = {"type": "tutorial"}
        page.source_path = Path("content/tutorials/intro.md")
        page._section = None
        page.is_home = False
        page.url = "/tutorials/intro/"

        def template_exists(name):
            return name == "tutorial/single.html"

        renderer._template_exists = template_exists

        template = renderer._get_template_name(page)

        assert template == "tutorial/single.html"

    def test_blog_type_maps_to_blog_templates(self):
        """Test that type: blog uses blog templates."""
        site = Mock()
        renderer = Renderer(site)

        page = Mock(spec=Page)
        page.metadata = {"type": "blog"}
        page.source_path = Path("content/blog/post.md")
        page._section = None
        page.is_home = False
        page.url = "/blog/post/"

        def template_exists(name):
            return name == "blog/single.html"

        renderer._template_exists = template_exists

        template = renderer._get_template_name(page)

        assert template == "blog/single.html"


class TestTypeForIndexPages:
    """Test that types work for index pages (list templates)."""

    def test_doc_index_uses_list_template(self):
        """Test that _index.md with type: doc uses doc/list.html."""
        site = Mock()
        renderer = Renderer(site)

        page = Mock(spec=Page)
        page.metadata = {"type": "doc"}
        page.source_path = Path("content/docs/_index.md")
        page._section = None
        page.is_home = False
        page.url = "/docs/"

        def template_exists(name):
            return name == "doc/list.html"

        renderer._template_exists = template_exists

        template = renderer._get_template_name(page)

        assert template == "doc/list.html"

    def test_tutorial_index_uses_list_template(self):
        """Test that _index.md with type: tutorial uses tutorial/list.html."""
        site = Mock()
        renderer = Renderer(site)

        page = Mock(spec=Page)
        page.metadata = {"type": "tutorial"}
        page.source_path = Path("content/tutorials/_index.md")
        page._section = None
        page.is_home = False
        page.url = "/tutorials/"

        def template_exists(name):
            return name == "tutorial/list.html"

        renderer._template_exists = template_exists

        template = renderer._get_template_name(page)

        assert template == "tutorial/list.html"


class TestTemplatePriority:
    """Test template selection priority order."""

    def test_explicit_template_beats_type(self):
        """Test that explicit template: overrides type:."""
        site = Mock()
        renderer = Renderer(site)

        page = Mock(spec=Page)
        page.metadata = {"template": "custom.html", "type": "doc"}
        page.source_path = Path("content/page.md")
        page._section = None

        template = renderer._get_template_name(page)

        # Should use explicit template, not type
        assert template == "custom.html"

    def test_type_beats_section_name(self):
        """Test that type: beats section name patterns."""
        site = Mock()
        renderer = Renderer(site)

        section = Mock(spec=Section)
        section.name = "guides"  # Section name
        section.metadata = {}

        page = Mock(spec=Page)
        page.metadata = {"type": "tutorial"}  # Different type
        page.source_path = Path("content/guides/intro.md")
        page._section = section
        page.is_home = False
        page.url = "/guides/intro/"

        def template_exists(name):
            # tutorial template exists, guides template doesn't
            return name == "tutorial/single.html"

        renderer._template_exists = template_exists

        template = renderer._get_template_name(page)

        # Should use type-based template
        assert template == "tutorial/single.html"

    def test_fallback_to_section_name_if_type_template_missing(self):
        """Test fallback to section name if type template doesn't exist."""
        site = Mock()
        renderer = Renderer(site)

        section = Mock(spec=Section)
        section.name = "docs"
        section.metadata = {}

        page = Mock(spec=Page)
        page.metadata = {"type": "custom-type"}  # Custom type with no template
        page.source_path = Path("content/docs/page.md")
        page._section = section

        def template_exists(name):
            # custom-type templates don't exist, but docs template does
            if "custom-type" in name:
                return False
            return name == "docs/single.html"

        renderer._template_exists = template_exists

        template = renderer._get_template_name(page)

        # Should fallback to section name
        assert template == "docs/single.html"

    def test_ultimate_fallback_to_page_html(self):
        """Test ultimate fallback to page.html."""
        site = Mock()
        renderer = Renderer(site)

        page = Mock(spec=Page)
        page.metadata = {}
        page.source_path = Path("content/page.md")
        page._section = None

        def template_exists(name):
            return False  # No templates exist

        renderer._template_exists = template_exists

        template = renderer._get_template_name(page)

        # Should fallback to page.html
        assert template == "page.html"


class TestContentTypeCascade:
    """Test content_type from section metadata."""

    def test_section_content_type_used(self):
        """Test that section's content_type is used for template selection."""
        site = Mock()
        renderer = Renderer(site)

        section = Mock(spec=Section)
        section.name = "api"
        section.metadata = {"content_type": "autodoc/python"}

        page = Mock(spec=Page)
        page.metadata = {}  # No type set on page
        page.source_path = Path("content/api/module.md")
        page._section = section
        page.is_home = False
        page.url = "/api/module/"

        def template_exists(name):
            return name == "autodoc/python/single.html"

        renderer._template_exists = template_exists

        template = renderer._get_template_name(page)

        # Should use section's content_type
        assert template == "autodoc/python/single.html"

    def test_page_type_overrides_section_content_type(self):
        """Test that page's type overrides section's content_type."""
        site = Mock()
        renderer = Renderer(site)

        section = Mock(spec=Section)
        section.name = "docs"
        section.metadata = {"content_type": "doc"}

        page = Mock(spec=Page)
        page.metadata = {"type": "tutorial"}  # Override
        page.source_path = Path("content/docs/tutorial-page.md")
        page._section = section
        page.is_home = False
        page.url = "/docs/tutorial-page/"

        def template_exists(name):
            return name in ["tutorial/single.html", "doc/single.html"]

        renderer._template_exists = template_exists

        template = renderer._get_template_name(page)

        # Should use page's type, not section's content_type
        assert template == "tutorial/single.html"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

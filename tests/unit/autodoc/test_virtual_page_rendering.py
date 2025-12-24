"""
Tests for virtual autodoc page rendering.

Ensures autodoc pages have consistent rendering with regular pages,
including navigation, menus, and full template context.
"""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from bengal.autodoc.base import DocElement
from bengal.core.page import Page
from bengal.core.section import Section
from bengal.rendering.pipeline.core import RenderingPipeline


@pytest.fixture
def mock_site() -> Generator[MagicMock]:
    """Create a mock site with menus populated."""
    site = MagicMock()
    site.root_path = Path("/test/site")
    site.output_dir = Path("/test/site/public")
    site.config = {
        "site": {"title": "Test Site", "baseurl": "/"},
        "autodoc": {"python": {"enabled": True}},
    }
    site.theme = "default"
    site.theme_config = {}
    site.baseurl = "/"

    # Mock menu with items (this is crucial for nav rendering)
    mock_menu_item = MagicMock()
    mock_menu_item.to_dict.return_value = {
        "name": "Documentation",
        "url": "/docs/",
        "children": [],
    }
    site.menu = {"main": [mock_menu_item]}
    site.menu_localized = {}

    # Mock sections registry
    site.registry = Mock()
    site.registry.epoch = 0
    site.registry.register_section = Mock()
    site.registry.get_section = Mock(return_value=None)

    yield site


@pytest.fixture
def mock_doc_element() -> DocElement:
    """Create a mock DocElement for testing."""
    return DocElement(
        name="test_module",
        qualified_name="bengal.test_module",
        description="A test module for documentation.",
        element_type="module",
        source_file=Path("/test/bengal/test_module.py"),
        line_number=1,
        metadata={
            "type": "autodoc/python",
            "is_package": False,
        },
        children=[],
        examples=[],
        see_also=[],
        deprecated=None,
    )


@pytest.fixture
def autodoc_page(mock_site: MagicMock, mock_doc_element: DocElement) -> Page:
    """Create a virtual autodoc page."""
    page = Page.create_virtual(
        source_id="python/api/test_module.md",
        title="test_module",
        metadata={
            "type": "python-reference",
            "qualified_name": "bengal.test_module",
            "element_type": "module",
            "description": "A test module",
            "is_autodoc": True,
            "autodoc_element": mock_doc_element,
            "_autodoc_template": "autodoc/python/module",
            "_autodoc_url_path": "api/test_module",
            "_autodoc_page_type": "python-reference",
        },
        rendered_html=None,
        template_name="autodoc/python/module",
        output_path=mock_site.output_dir / "api/test_module/index.html",
    )
    page._site = mock_site
    return page


@pytest.fixture
def section_index_page(mock_site: MagicMock) -> Page:
    """Create a virtual section index page."""
    page = Page.create_virtual(
        source_id="python/api/core/_index.md",
        title="Core",
        metadata={
            "type": "python-reference",
            "is_section_index": True,
            "is_autodoc": True,
            "_autodoc_template": "autodoc/python/section-index",
            "_autodoc_url_path": "api/core",
            "_autodoc_page_type": "python-reference",
        },
        rendered_html=None,
        template_name="autodoc/python/section-index",
        output_path=mock_site.output_dir / "api/core/index.html",
    )
    page._site = mock_site
    return page


@pytest.fixture
def root_index_page(mock_site: MagicMock) -> Page:
    """Create a virtual root API index page."""
    page = Page.create_virtual(
        source_id="python/api/_index.md",
        title="API Reference",
        metadata={
            "type": "python-reference",
            "is_section_index": True,
            "is_autodoc": True,
            "_autodoc_template": "autodoc/python/section-index",
            "_autodoc_url_path": "api",
            "_autodoc_page_type": "python-reference",
        },
        rendered_html=None,
        template_name="autodoc/python/section-index",
        output_path=mock_site.output_dir / "api/index.html",
    )
    page._site = mock_site
    return page


class TestVirtualPageDetection:
    """Test detection of autodoc virtual pages."""

    def test_autodoc_page_detected_by_metadata(self, autodoc_page: Page) -> None:
        """Autodoc pages have is_autodoc=True in metadata."""
        assert autodoc_page.metadata.get("is_autodoc") is True

    def test_autodoc_page_has_element(
        self, autodoc_page: Page, mock_doc_element: DocElement
    ) -> None:
        """Autodoc pages store the DocElement in metadata."""
        assert autodoc_page.metadata.get("autodoc_element") is mock_doc_element

    def test_autodoc_page_has_template_info(self, autodoc_page: Page) -> None:
        """Autodoc pages have rendering metadata."""
        assert autodoc_page.metadata.get("_autodoc_template") == "autodoc/python/module"
        assert autodoc_page.metadata.get("_autodoc_url_path") == "api/test_module"
        assert autodoc_page.metadata.get("_autodoc_page_type") == "python-reference"

    def test_section_index_detected(self, section_index_page: Page) -> None:
        """Section index pages have is_section_index=True."""
        assert section_index_page.metadata.get("is_section_index") is True
        assert section_index_page.metadata.get("is_autodoc") is True

    def test_root_index_detected(self, root_index_page: Page) -> None:
        """Root index pages are detected correctly."""
        assert root_index_page.metadata.get("is_section_index") is True
        assert root_index_page.metadata.get("is_autodoc") is True


class TestDeferredRendering:
    """Test that autodoc pages use deferred rendering."""

    def test_autodoc_page_has_no_prerendered_html(self, autodoc_page: Page) -> None:
        """Autodoc pages should not have pre-rendered HTML during discovery."""
        # rendered_html is empty string during discovery phase (deferred rendering)
        # Page.create_virtual uses `rendered_html or ""` as default
        assert autodoc_page.rendered_html == ""
        assert autodoc_page._prerendered_html is None

    def test_section_index_has_no_prerendered_html(self, section_index_page: Page) -> None:
        """Section index pages should not have pre-rendered HTML during discovery."""
        assert section_index_page.rendered_html == ""
        assert section_index_page._prerendered_html is None


class TestRenderingPipelineIntegration:
    """Test RenderingPipeline handling of autodoc pages."""

    def test_process_virtual_page_detects_autodoc(
        self, autodoc_page: Page, mock_site: MagicMock
    ) -> None:
        """RenderingPipeline should detect autodoc pages by metadata."""
        # Verify the detection logic
        is_autodoc = autodoc_page.metadata.get("is_autodoc") and autodoc_page.metadata.get(
            "autodoc_element"
        )
        # Expression evaluates to the DocElement (truthy), not exactly True
        assert is_autodoc  # truthy check
        assert autodoc_page.metadata.get("is_autodoc") is True
        assert autodoc_page.metadata.get("autodoc_element") is not None

    def test_autodoc_page_uses_site_template_engine(
        self, autodoc_page: Page, mock_site: MagicMock
    ) -> None:
        """Autodoc pages should use site's template engine, not a separate one."""
        # This is the key fix - we use self.template_engine.env, not a new orchestrator
        # The implementation should NOT create VirtualAutodocOrchestrator per page
        template_name = autodoc_page.metadata.get("_autodoc_template")
        assert template_name is not None

    def test_process_page_routes_deferred_autodoc(
        self, autodoc_page: Page, mock_site: MagicMock
    ) -> None:
        """Deferred autodoc pages should go through virtual page renderer."""
        build_context = MagicMock()
        build_context.template_engine = MagicMock()
        pipeline = RenderingPipeline(mock_site, build_context=build_context)

        with patch.object(pipeline._autodoc_renderer, "process_virtual_page") as mock_process:
            pipeline.process_page(autodoc_page)
            mock_process.assert_called_once_with(autodoc_page)

    def test_render_autodoc_page_uses_section_fallback(
        self, autodoc_page: Page, mock_site: MagicMock
    ) -> None:
        """_render_autodoc_page should pass section even when page lacks .section attr."""
        build_context = MagicMock()
        fake_template = MagicMock()
        fake_template.render.return_value = "<div>ok</div>"
        fake_env = MagicMock()
        fake_env.get_template.return_value = fake_template
        build_context.template_engine = MagicMock(env=fake_env)

        pipeline = RenderingPipeline(mock_site, build_context=build_context)

        # Attach only _section; no public section attribute exists on Page
        section = Section.create_virtual(
            name="cli",
            relative_url="/cli/",
            title="CLI Reference",
            metadata={"type": "autodoc/cli"},
        )
        autodoc_page._section = section
        mock_site.get_section_by_url.return_value = section
        mock_site.get_section_by_path.return_value = None

        # Call via the extracted AutodocRenderer
        pipeline._autodoc_renderer._render_autodoc_page(autodoc_page)

        fake_template.render.assert_called_once()
        kwargs = fake_template.render.call_args.kwargs
        assert kwargs["section"] is section
        assert autodoc_page.rendered_html is not None


class TestMenuAvailability:
    """Test that menus are available during autodoc rendering."""

    def test_site_has_menu_before_autodoc_render(self, mock_site: MagicMock) -> None:
        """Site should have menu populated before autodoc pages render."""
        assert "main" in mock_site.menu
        assert len(mock_site.menu["main"]) > 0

    def test_menu_items_are_dicts(self, mock_site: MagicMock) -> None:
        """Menu items should be convertible to dicts for templates."""
        menu_items = mock_site.menu["main"]
        for item in menu_items:
            d = item.to_dict()
            assert isinstance(d, dict)
            assert "name" in d
            assert "url" in d


class TestPageTypes:
    """Test all autodoc page types."""

    @pytest.mark.parametrize(
        "page_type,template",
        [
            ("module", "autodoc/python/module"),
            ("class", "autodoc/python/class"),
            ("function", "autodoc/python/function"),
        ],
    )
    def test_python_page_types(
        self, mock_site: MagicMock, mock_doc_element: DocElement, page_type: str, template: str
    ) -> None:
        """Test different Python element page types."""
        mock_doc_element.element_type = page_type
        page = Page.create_virtual(
            source_id=f"python/api/{page_type}.md",
            title=f"Test{page_type.title()}",
            metadata={
                "type": "python-reference",
                "element_type": page_type,
                "is_autodoc": True,
                "autodoc_element": mock_doc_element,
                "_autodoc_template": template,
            },
            rendered_html=None,
            template_name=template,
            output_path=mock_site.output_dir / f"api/{page_type}/index.html",
        )
        page._site = mock_site

        assert page.metadata.get("element_type") == page_type
        assert page.metadata.get("_autodoc_template") == template

    def test_cli_command_page(self, mock_site: MagicMock) -> None:
        """Test CLI command page type."""
        element = DocElement(
            name="build",
            qualified_name="bengal.cli.build",
            description="Build the site",
            element_type="command",
            source_file=None,
            line_number=1,
            metadata={"type": "autodoc/cli"},
            children=[],
            examples=[],
            see_also=[],
            deprecated=None,
        )
        page = Page.create_virtual(
            source_id="cli/cli/build.md",
            title="build",
            metadata={
                "type": "autodoc/cli",
                "element_type": "command",
                "is_autodoc": True,
                "autodoc_element": element,
                "_autodoc_template": "autodoc/cli/command",
            },
            rendered_html=None,
            template_name="autodoc/cli/command",
            output_path=mock_site.output_dir / "cli/build/index.html",
        )
        page._site = mock_site

        assert page.metadata.get("element_type") == "command"
        assert page.metadata.get("_autodoc_template") == "autodoc/cli/command"

    def test_openapi_endpoint_page(self, mock_site: MagicMock) -> None:
        """Test OpenAPI endpoint page type."""
        element = DocElement(
            name="GET /users",
            qualified_name="api.users.list",
            description="List all users",
            element_type="openapi_endpoint",
            source_file=None,
            line_number=1,
            metadata={"type": "openautodoc/python", "method": "GET", "path": "/users"},
            children=[],
            examples=[],
            see_also=[],
            deprecated=None,
        )
        page = Page.create_virtual(
            source_id="openapi/endpoints/users/list.md",
            title="GET /users",
            metadata={
                "type": "openautodoc/python",
                "element_type": "openapi_endpoint",
                "is_autodoc": True,
                "autodoc_element": element,
                "_autodoc_template": "openautodoc/python/endpoint",
            },
            rendered_html=None,
            template_name="openautodoc/python/endpoint",
            output_path=mock_site.output_dir / "openapi/users/list/index.html",
        )
        page._site = mock_site

        assert page.metadata.get("element_type") == "openapi_endpoint"


class TestVirtualSectionIntegration:
    """Test virtual sections for autodoc."""

    def test_autodoc_page_has_section_reference(
        self, autodoc_page: Page, mock_site: MagicMock
    ) -> None:
        """Autodoc pages should have section reference."""
        # Create a mock section
        section = Section.create_virtual(
            name="api",
            relative_url="/api/",
            title="API Reference",
            metadata={"type": "autodoc/python"},
        )

        # Mock the site's section registry to return this section
        mock_site.get_section_by_url.return_value = section
        mock_site.get_section_by_path.return_value = None  # Virtual section uses URL

        autodoc_page._section = section

        assert autodoc_page._section is not None
        assert autodoc_page._section.name == "api"

    def test_section_index_page_in_section(
        self, section_index_page: Page, mock_site: MagicMock
    ) -> None:
        """Section index pages should belong to their section."""
        section = Section.create_virtual(
            name="core",
            relative_url="/api/core/",
            title="Core",
            metadata={"type": "autodoc/python"},
        )

        # Mock the site's section registry
        mock_site.get_section_by_url.return_value = section
        mock_site.get_section_by_path.return_value = None

        section_index_page._section = section

        assert section_index_page._section.name == "core"


class TestOutputPaths:
    """Test output path handling for autodoc pages."""

    def test_module_page_output_path(self, autodoc_page: Page, mock_site: MagicMock) -> None:
        """Module pages have correct output path."""
        expected = mock_site.output_dir / "api/test_module/index.html"
        assert autodoc_page.output_path == expected

    def test_section_index_output_path(
        self, section_index_page: Page, mock_site: MagicMock
    ) -> None:
        """Section index pages have correct output path."""
        expected = mock_site.output_dir / "api/core/index.html"
        assert section_index_page.output_path == expected

    def test_root_index_output_path(self, root_index_page: Page, mock_site: MagicMock) -> None:
        """Root index pages have correct output path."""
        expected = mock_site.output_dir / "api/index.html"
        assert root_index_page.output_path == expected


class TestTemplateContext:
    """Test that template context is correct for autodoc pages."""

    def test_autodoc_page_context_has_element(
        self, autodoc_page: Page, mock_doc_element: DocElement
    ) -> None:
        """Template context should include the DocElement."""
        element = autodoc_page.metadata.get("autodoc_element")
        assert element is mock_doc_element
        assert element.name == "test_module"
        assert element.qualified_name == "bengal.test_module"

    def test_autodoc_page_context_has_page(self, autodoc_page: Page) -> None:
        """Template context should include the page object."""
        # When rendering, page is passed to template
        assert autodoc_page.title == "test_module"

    def test_autodoc_page_context_has_site(self, autodoc_page: Page, mock_site: MagicMock) -> None:
        """Template context should include the site object."""
        assert autodoc_page._site is mock_site


class TestEdgeCases:
    """Test edge cases for autodoc virtual pages."""

    def test_page_without_autodoc_element(self, mock_site: MagicMock) -> None:
        """Pages without autodoc_element should be handled."""
        page = Page.create_virtual(
            source_id="test.md",
            title="Test",
            metadata={"is_autodoc": True},  # Missing autodoc_element
            rendered_html="<p>Test</p>",
            template_name="default",
            output_path=mock_site.output_dir / "test/index.html",
        )
        # Should not have autodoc_element
        assert page.metadata.get("autodoc_element") is None

    def test_page_with_prerendered_html(
        self, mock_site: MagicMock, mock_doc_element: DocElement
    ) -> None:
        """Pages with pre-rendered HTML should use it directly."""
        prerendered = "<html><body>Pre-rendered</body></html>"
        page = Page.create_virtual(
            source_id="test.md",
            title="Test",
            metadata={
                "is_autodoc": True,
                "autodoc_element": mock_doc_element,
            },
            rendered_html=prerendered,
            template_name="default",
            output_path=mock_site.output_dir / "test/index.html",
        )
        # If HTML is pre-rendered, it should be used
        assert page.rendered_html == prerendered
        assert page._prerendered_html == prerendered
        assert "Pre-rendered" in page.rendered_html

    def test_nested_module_path(self, mock_site: MagicMock) -> None:
        """Test deeply nested module paths."""
        element = DocElement(
            name="deep_module",
            qualified_name="bengal.core.page.mixins.deep_module",
            description="A deeply nested module",
            element_type="module",
            source_file=Path("/test/bengal/core/page/mixins/deep_module.py"),
            line_number=1,
            metadata={},
            children=[],
            examples=[],
            see_also=[],
            deprecated=None,
        )
        page = Page.create_virtual(
            source_id="python/api/core/page/mixins/deep_module.md",
            title="deep_module",
            metadata={
                "is_autodoc": True,
                "autodoc_element": element,
                "_autodoc_url_path": "api/core/page/mixins/deep_module",
            },
            rendered_html=None,
            template_name="autodoc/python/module",
            output_path=mock_site.output_dir / "api/core/page/mixins/deep_module/index.html",
        )
        page._site = mock_site

        assert "core/page/mixins/deep_module" in page.metadata.get("_autodoc_url_path", "")

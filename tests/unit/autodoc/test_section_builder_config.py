"""
Tests for autodoc section builder configuration.

Covers display_name and other configurable section properties.
"""

from pathlib import Path
from unittest.mock import MagicMock, Mock

import pytest

from bengal.autodoc.base import DocElement
from bengal.autodoc.orchestration.section_builders import (
    create_cli_sections,
    create_openapi_sections,
    create_python_sections,
)


@pytest.fixture
def mock_site():
    """Create a mock site with autodoc config."""
    site = MagicMock()
    site.root_path = Path("/test/site")
    site.output_dir = Path("/test/site/public")
    site.config = {
        "site": {"title": "Test Site", "baseurl": "/"},
        "autodoc": {
            "python": {"enabled": True, "source_dirs": ["."]},
            "cli": {"enabled": True},
            "openapi": {"enabled": False},
        },
    }
    site.theme = "default"
    site.theme_config = {}
    site.baseurl = "/"
    site.registry = Mock()
    site.registry.epoch = 0
    return site


@pytest.fixture
def mock_elements():
    """Create mock DocElements for testing."""
    return [
        DocElement(
            name="module",
            qualified_name="mypackage.module",
            description="A test module",
            element_type="module",
            source_file=Path("/test/mypackage/module.py"),
            line_number=1,
            metadata={},
            children=[],
            examples=[],
            see_also=[],
            deprecated=None,
        )
    ]


@pytest.fixture
def mock_cli_elements():
    """Create mock CLI DocElements for testing."""
    return [
        DocElement(
            name="build",
            qualified_name="myapp.build",
            description="Build command",
            element_type="command",
            source_file=None,
            line_number=1,
            metadata={},
            children=[],
            examples=[],
            see_also=[],
            deprecated=None,
        )
    ]


class TestDisplayNameConfig:
    """Test display_name configuration for section titles."""

    def test_python_section_uses_display_name(self, mock_site, mock_elements):
        """Python sections should use display_name from config."""
        mock_site.config["autodoc"]["python"]["display_name"] = "MyApp API Reference"

        def resolve_prefix(doc_type):
            return "api/mypackage"

        sections = create_python_sections(mock_elements, mock_site, resolve_prefix)

        # Root section should use custom display_name
        root_section = sections.get("api/mypackage")
        assert root_section is not None
        assert root_section.title == "MyApp API Reference"

    def test_python_section_uses_default_when_no_display_name(self, mock_site, mock_elements):
        """Python sections should fall back to 'Python API Reference' when no display_name."""
        # Ensure display_name is not set
        mock_site.config["autodoc"]["python"].pop("display_name", None)

        def resolve_prefix(doc_type):
            return "api/mypackage"

        sections = create_python_sections(mock_elements, mock_site, resolve_prefix)

        root_section = sections.get("api/mypackage")
        assert root_section is not None
        assert root_section.title == "Python API Reference"

    def test_python_section_uses_default_when_empty_display_name(self, mock_site, mock_elements):
        """Python sections should fall back to default when display_name is empty string."""
        mock_site.config["autodoc"]["python"]["display_name"] = ""

        def resolve_prefix(doc_type):
            return "api/mypackage"

        sections = create_python_sections(mock_elements, mock_site, resolve_prefix)

        root_section = sections.get("api/mypackage")
        assert root_section is not None
        assert root_section.title == "Python API Reference"

    def test_cli_section_uses_display_name(self, mock_site, mock_cli_elements):
        """CLI sections should use display_name from config."""
        mock_site.config["autodoc"]["cli"]["display_name"] = "MyApp CLI"

        def resolve_prefix(doc_type):
            return "cli"

        sections = create_cli_sections(mock_cli_elements, mock_site, resolve_prefix)

        root_section = sections.get("cli")
        assert root_section is not None
        assert root_section.title == "MyApp CLI"

    def test_cli_section_uses_default_when_no_display_name(self, mock_site, mock_cli_elements):
        """CLI sections should fall back to 'CLI Reference' when no display_name."""
        mock_site.config["autodoc"]["cli"].pop("display_name", None)

        def resolve_prefix(doc_type):
            return "cli"

        sections = create_cli_sections(mock_cli_elements, mock_site, resolve_prefix)

        root_section = sections.get("cli")
        assert root_section is not None
        assert root_section.title == "CLI Reference"

    def test_openapi_section_uses_display_name(self, mock_site):
        """OpenAPI sections should use display_name from config."""
        mock_site.config["autodoc"]["openapi"] = {
            "enabled": True,
            "display_name": "MyApp REST API",
        }

        openapi_elements = [
            DocElement(
                name="API Overview",
                qualified_name="openapi.overview",
                description="API overview",
                element_type="openapi_overview",
                source_file=None,
                line_number=1,
                metadata={},
                children=[],
                examples=[],
                see_also=[],
                deprecated=None,
            )
        ]

        def resolve_prefix(doc_type):
            return "api/rest"

        sections = create_openapi_sections(openapi_elements, mock_site, resolve_prefix)

        root_section = sections.get("api/rest")
        assert root_section is not None
        assert root_section.title == "MyApp REST API"

    def test_openapi_section_uses_default_when_no_display_name(self, mock_site):
        """OpenAPI sections should fall back to 'REST API Reference' when no display_name."""
        mock_site.config["autodoc"]["openapi"] = {"enabled": True}

        openapi_elements = [
            DocElement(
                name="API Overview",
                qualified_name="openapi.overview",
                description="API overview",
                element_type="openapi_overview",
                source_file=None,
                line_number=1,
                metadata={},
                children=[],
                examples=[],
                see_also=[],
                deprecated=None,
            )
        ]

        def resolve_prefix(doc_type):
            return "api/rest"

        sections = create_openapi_sections(openapi_elements, mock_site, resolve_prefix)

        root_section = sections.get("api/rest")
        assert root_section is not None
        assert root_section.title == "REST API Reference"



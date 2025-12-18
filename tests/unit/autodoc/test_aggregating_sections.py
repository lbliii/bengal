"""
Unit tests for autodoc aggregating sections.

Tests the create_aggregating_parent_sections() function and the api-hub type
used for landing pages that aggregate multiple API documentation types.
"""

from __future__ import annotations

from bengal.autodoc.orchestration.section_builders import create_aggregating_parent_sections
from bengal.autodoc.orchestration.utils import get_template_dir_for_type
from bengal.core.section import Section


class TestAggregatingParentSections:
    """Tests for create_aggregating_parent_sections()."""

    def test_creates_api_hub_type_for_aggregating_section(self) -> None:
        """Aggregating section should use 'api-hub' type for agnostic landing page."""
        # Create child sections with different types
        python_section = Section.create_virtual(
            name="python",
            relative_url="/api/python/",
            title="Python API Reference",
            metadata={"type": "python-reference"},
        )
        openapi_section = Section.create_virtual(
            name="rest",
            relative_url="/api/rest/",
            title="REST API Reference",
            metadata={"type": "openautodoc/python"},
        )

        sections = {
            "api/python": python_section,
            "api/rest": openapi_section,
        }

        # Create aggregating parent
        parent_sections = create_aggregating_parent_sections(sections)

        # Should create an 'api' parent section
        assert "api" in parent_sections
        api_section = parent_sections["api"]

        # Should use 'api-hub' type, not inherit from children
        assert api_section.metadata.get("type") == "api-hub"

    def test_aggregating_section_tracks_child_types(self) -> None:
        """Aggregating section should track child types in metadata."""
        python_section = Section.create_virtual(
            name="python",
            relative_url="/api/python/",
            title="Python API Reference",
            metadata={"type": "python-reference"},
        )
        openapi_section = Section.create_virtual(
            name="rest",
            relative_url="/api/rest/",
            title="REST API Reference",
            metadata={"type": "openautodoc/python"},
        )

        sections = {
            "api/python": python_section,
            "api/rest": openapi_section,
        }

        parent_sections = create_aggregating_parent_sections(sections)
        api_section = parent_sections["api"]

        # Should track child types
        child_types = api_section.metadata.get("child_types", [])
        assert "python-reference" in child_types
        assert "openautodoc/python" in child_types

    def test_aggregating_section_has_is_aggregating_flag(self) -> None:
        """Aggregating section should have is_aggregating_section flag."""
        python_section = Section.create_virtual(
            name="python",
            relative_url="/api/python/",
            title="Python API Reference",
            metadata={"type": "python-reference"},
        )

        sections = {"api/python": python_section}

        parent_sections = create_aggregating_parent_sections(sections)
        api_section = parent_sections["api"]

        assert api_section.metadata.get("is_aggregating_section") is True

    def test_aggregating_section_links_children(self) -> None:
        """Aggregating section should have children as subsections."""
        python_section = Section.create_virtual(
            name="python",
            relative_url="/api/python/",
            title="Python API Reference",
            metadata={"type": "python-reference"},
        )
        openapi_section = Section.create_virtual(
            name="rest",
            relative_url="/api/rest/",
            title="REST API Reference",
            metadata={"type": "openautodoc/python"},
        )

        sections = {
            "api/python": python_section,
            "api/rest": openapi_section,
        }

        parent_sections = create_aggregating_parent_sections(sections)
        api_section = parent_sections["api"]

        # Should have both children as subsections
        assert len(api_section.subsections) == 2
        subsection_names = {s.name for s in api_section.subsections}
        assert "python" in subsection_names
        assert "rest" in subsection_names

    def test_no_aggregating_section_when_parent_exists(self) -> None:
        """Should not create aggregating section if parent already exists."""
        existing_api_section = Section.create_virtual(
            name="api",
            relative_url="/api/",
            title="API Reference",
            metadata={"type": "python-reference"},
        )
        python_section = Section.create_virtual(
            name="python",
            relative_url="/api/python/",
            title="Python API Reference",
            metadata={"type": "python-reference"},
        )

        sections = {
            "api": existing_api_section,
            "api/python": python_section,
        }

        parent_sections = create_aggregating_parent_sections(sections)

        # Should not create new parent since 'api' already exists
        assert "api" not in parent_sections

    def test_single_child_still_creates_aggregating_section(self) -> None:
        """Single child should still get aggregating parent for menu detection."""
        python_section = Section.create_virtual(
            name="python",
            relative_url="/api/python/",
            title="Python API Reference",
            metadata={"type": "python-reference"},
        )

        sections = {"api/python": python_section}

        parent_sections = create_aggregating_parent_sections(sections)

        # Should still create 'api' parent for Dev dropdown detection
        assert "api" in parent_sections
        assert parent_sections["api"].metadata.get("type") == "api-hub"


class TestApiHubTemplateMapping:
    """Tests for api-hub template directory mapping."""

    def test_api_hub_maps_to_api_hub_template_dir(self) -> None:
        """api-hub type should map to api-hub template directory."""
        template_dir = get_template_dir_for_type("api-hub")
        assert template_dir == "api-hub"

    def test_python_reference_maps_to_api_reference(self) -> None:
        """python-reference type should still map to autodoc/python."""
        template_dir = get_template_dir_for_type("python-reference")
        assert template_dir == "autodoc/python"

    def test_openapi_reference_maps_to_itself(self) -> None:
        """openautodoc/python type should map to openautodoc/python."""
        template_dir = get_template_dir_for_type("openautodoc/python")
        assert template_dir == "openautodoc/python"

    def test_cli_reference_maps_to_itself(self) -> None:
        """autodoc/cli type should map to autodoc/cli."""
        template_dir = get_template_dir_for_type("autodoc/cli")
        assert template_dir == "autodoc/cli"

"""
Tests for OpenAPI template filter functions (endpoints, schemas).

These filters normalize access to endpoint and schema data in templates,
providing a consistent API regardless of consolidation mode.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from bengal.rendering.template_functions.openapi import (
    EndpointView,
    SchemaView,
    _generate_anchor_id,
    endpoints_filter,
    schemas_filter,
)

# =============================================================================
# Mock Classes
# =============================================================================


@dataclass
class MockOpenAPIEndpointMetadata:
    """Mock OpenAPIEndpointMetadata for testing."""

    method: str = "GET"
    path: str = "/users"
    operation_id: str | None = None
    summary: str | None = None
    tags: tuple[str, ...] = ()
    deprecated: bool = False


@dataclass
class MockOpenAPISchemaMetadata:
    """Mock OpenAPISchemaMetadata for testing."""

    schema_type: str | None = "object"
    properties: dict[str, Any] = field(default_factory=dict)
    required: tuple[str, ...] = ()
    enum: tuple[Any, ...] | None = None
    example: Any = None


@dataclass
class MockDocElement:
    """Mock DocElement for testing."""

    name: str
    description: str = ""
    typed_metadata: Any = None
    href: str | None = None


@dataclass
class MockPage:
    """Mock Page for testing."""

    metadata: dict[str, Any] = field(default_factory=dict)
    href: str | None = None


@dataclass
class MockSection:
    """Mock Section for testing."""

    metadata: dict[str, Any] = field(default_factory=dict)
    pages: list[Any] = field(default_factory=list)
    index_page: Any = None


# =============================================================================
# Tests for _generate_anchor_id
# =============================================================================


class TestGenerateAnchorId:
    """Tests for anchor ID generation."""

    def test_simple_path(self) -> None:
        """Generates anchor from simple path."""
        result = _generate_anchor_id("GET", "/users")
        assert result == "get-users"

    def test_path_with_params(self) -> None:
        """Removes braces from path parameters."""
        result = _generate_anchor_id("DELETE", "/users/{id}")
        assert result == "delete-users-id"

    def test_nested_path(self) -> None:
        """Handles nested paths with multiple segments."""
        result = _generate_anchor_id("POST", "/users/{user_id}/posts/{post_id}")
        assert result == "post-users-user_id-posts-post_id"

    def test_root_path(self) -> None:
        """Handles root path."""
        result = _generate_anchor_id("GET", "/")
        assert result == "get"

    def test_method_lowercased(self) -> None:
        """Method is lowercased in anchor."""
        result = _generate_anchor_id("POST", "/items")
        assert result == "post-items"


# =============================================================================
# Tests for EndpointView
# =============================================================================


class TestEndpointViewFromDocElement:
    """Tests for EndpointView.from_doc_element()."""

    def test_consolidated_mode_generates_anchor_href(self) -> None:
        """In consolidated mode, href is an anchor link."""
        meta = MockOpenAPIEndpointMetadata(
            method="GET",
            path="/users/{id}",
            operation_id="getUser",
        )
        element = MockDocElement(
            name="getUser",
            description="Get a user by ID",
            typed_metadata=meta,
            href="/api/users/get-user/",  # This would be wrong in consolidated mode
        )

        view = EndpointView.from_doc_element(element, consolidated=True)

        assert view.href == "#getUser"  # Uses operation_id as anchor
        assert view.has_page is False

    def test_consolidated_mode_generates_path_based_anchor(self) -> None:
        """Uses path-based anchor when no operation_id."""
        meta = MockOpenAPIEndpointMetadata(
            method="POST",
            path="/users/{user_id}/posts",
            operation_id=None,
        )
        element = MockDocElement(
            name="createPost",
            typed_metadata=meta,
        )

        view = EndpointView.from_doc_element(element, consolidated=True)

        assert view.href == "#post-users-user_id-posts"
        assert view.has_page is False

    def test_individual_mode_uses_element_href(self) -> None:
        """In individual mode, href is the page URL."""
        meta = MockOpenAPIEndpointMetadata(
            method="GET",
            path="/users",
        )
        element = MockDocElement(
            name="listUsers",
            typed_metadata=meta,
            href="/api/users/list/",
        )

        view = EndpointView.from_doc_element(element, consolidated=False)

        assert view.href == "/api/users/list/"
        assert view.has_page is True

    def test_extracts_all_metadata_fields(self) -> None:
        """All metadata fields are correctly extracted."""
        meta = MockOpenAPIEndpointMetadata(
            method="DELETE",
            path="/items/{id}",
            operation_id="deleteItem",
            summary="Delete an item",
            tags=("items", "admin"),
            deprecated=True,
        )
        element = MockDocElement(
            name="deleteItem",
            description="Full description here",
            typed_metadata=meta,
        )

        view = EndpointView.from_doc_element(element, consolidated=True)

        assert view.method == "DELETE"
        assert view.path == "/items/{id}"
        assert view.summary == "Delete an item"
        assert view.description == "Full description here"
        assert view.deprecated is True
        assert view.operation_id == "deleteItem"
        assert view.tags == ("items", "admin")
        assert view.typed_metadata is meta


class TestEndpointViewFromPage:
    """Tests for EndpointView.from_page()."""

    def test_extracts_from_page_metadata(self) -> None:
        """Extracts endpoint data from page metadata dict."""
        page = MockPage(
            metadata={
                "method": "PUT",
                "path": "/items/{id}",
                "summary": "Update an item",
                "description": "Updates item properties",
                "deprecated": True,
                "operation_id": "updateItem",
                "tags": ["items"],
            },
            href="/api/items/update/",
        )

        view = EndpointView.from_page(page)

        assert view.method == "PUT"
        assert view.path == "/items/{id}"
        assert view.summary == "Update an item"
        assert view.description == "Updates item properties"
        assert view.deprecated is True
        assert view.href == "/api/items/update/"
        assert view.has_page is True
        assert view.operation_id == "updateItem"
        assert view.tags == ("items",)

    def test_uses_defaults_for_missing_fields(self) -> None:
        """Uses sensible defaults when fields are missing."""
        page = MockPage(
            metadata={"path": "/simple"},
            href="/api/simple/",
        )

        view = EndpointView.from_page(page)

        assert view.method == "GET"  # Default
        assert view.path == "/simple"
        assert view.summary == ""
        assert view.deprecated is False
        assert view.operation_id is None
        assert view.tags == ()

    def test_href_fallback_to_hash(self) -> None:
        """Falls back to # when page has no href."""
        page = MockPage(
            metadata={"method": "GET", "path": "/test"},
            href=None,
        )

        view = EndpointView.from_page(page)

        assert view.href == "#"


# =============================================================================
# Tests for SchemaView
# =============================================================================


class TestSchemaViewFromDocElement:
    """Tests for SchemaView.from_doc_element()."""

    def test_extracts_schema_data(self) -> None:
        """Extracts all schema data from DocElement."""
        meta = MockOpenAPISchemaMetadata(
            schema_type="object",
            properties={"id": {"type": "integer"}, "name": {"type": "string"}},
            required=("id",),
            example={"id": 1, "name": "Test"},
        )
        element = MockDocElement(
            name="User",
            description="A user in the system",
            typed_metadata=meta,
            href="/api/schemas/user/",
        )

        view = SchemaView.from_doc_element(element, consolidated=False)

        assert view.name == "User"
        assert view.schema_type == "object"
        assert view.description == "A user in the system"
        assert view.href == "/api/schemas/user/"
        assert view.has_page is True
        assert view.properties == {"id": {"type": "integer"}, "name": {"type": "string"}}
        assert view.required == ("id",)
        assert view.example == {"id": 1, "name": "Test"}

    def test_consolidated_mode_generates_anchor(self) -> None:
        """In consolidated mode, generates anchor link."""
        meta = MockOpenAPISchemaMetadata(schema_type="object")
        element = MockDocElement(
            name="Order",
            typed_metadata=meta,
            href=None,
        )

        view = SchemaView.from_doc_element(element, consolidated=True)

        assert view.href == "#schema-Order"
        assert view.has_page is False

    def test_no_href_generates_anchor(self) -> None:
        """When element has no href, generates anchor."""
        meta = MockOpenAPISchemaMetadata(schema_type="array")
        element = MockDocElement(
            name="Items",
            typed_metadata=meta,
            href=None,
        )

        view = SchemaView.from_doc_element(element, consolidated=False)

        assert view.href == "#schema-Items"
        assert view.has_page is False

    def test_enum_type(self) -> None:
        """Handles enum schemas."""
        meta = MockOpenAPISchemaMetadata(
            schema_type="string",
            enum=("pending", "active", "completed"),
        )
        element = MockDocElement(
            name="Status",
            typed_metadata=meta,
        )

        view = SchemaView.from_doc_element(element, consolidated=False)

        assert view.schema_type == "string"
        assert view.enum == ("pending", "active", "completed")

    def test_defaults_schema_type_to_object(self) -> None:
        """Defaults to 'object' when schema_type is None."""
        meta = MockOpenAPISchemaMetadata(schema_type=None)
        element = MockDocElement(
            name="Unknown",
            typed_metadata=meta,
        )

        view = SchemaView.from_doc_element(element, consolidated=False)

        assert view.schema_type == "object"


# =============================================================================
# Tests for endpoints_filter
# =============================================================================


class TestEndpointsFilter:
    """Tests for endpoints_filter()."""

    def test_returns_empty_for_none(self) -> None:
        """Returns empty list for None section."""
        result = endpoints_filter(None)
        assert result == []

    def test_returns_empty_for_empty_section(self) -> None:
        """Returns empty list for section without endpoints."""
        section = MockSection()
        result = endpoints_filter(section)
        assert result == []

    def test_consolidated_mode_from_metadata_endpoints(self) -> None:
        """Returns EndpointViews from metadata.endpoints (consolidated mode)."""
        meta1 = MockOpenAPIEndpointMetadata(method="GET", path="/users")
        meta2 = MockOpenAPIEndpointMetadata(method="POST", path="/users")

        section = MockSection(
            metadata={
                "endpoints": [
                    MockDocElement(name="listUsers", typed_metadata=meta1),
                    MockDocElement(name="createUser", typed_metadata=meta2),
                ]
            }
        )

        result = endpoints_filter(section)

        assert len(result) == 2
        assert all(isinstance(ep, EndpointView) for ep in result)
        assert result[0].method == "GET"
        assert result[0].path == "/users"
        assert result[0].has_page is False  # Consolidated mode
        assert result[1].method == "POST"

    def test_individual_mode_from_pages(self) -> None:
        """Returns EndpointViews from section.pages (individual mode)."""
        section = MockSection(
            metadata={},  # No endpoints in metadata
            pages=[
                MockPage(
                    metadata={"method": "GET", "path": "/items", "type": "openapi_endpoint"},
                    href="/api/items/list/",
                ),
                MockPage(
                    metadata={"method": "DELETE", "path": "/items/{id}"},
                    href="/api/items/delete/",
                ),
            ],
        )

        result = endpoints_filter(section)

        assert len(result) == 2
        assert result[0].method == "GET"
        assert result[0].href == "/api/items/list/"
        assert result[0].has_page is True  # Individual mode
        assert result[1].method == "DELETE"

    def test_filters_out_non_endpoint_pages(self) -> None:
        """Only includes pages that look like endpoints."""
        section = MockSection(
            metadata={},
            pages=[
                MockPage(
                    metadata={"method": "GET", "path": "/items"},
                    href="/api/items/",
                ),
                MockPage(
                    metadata={"title": "Overview"},  # Not an endpoint
                    href="/api/overview/",
                ),
            ],
        )

        result = endpoints_filter(section)

        assert len(result) == 1
        assert result[0].path == "/items"

    def test_skips_elements_without_typed_metadata(self) -> None:
        """Skips DocElements without typed_metadata."""
        section = MockSection(
            metadata={
                "endpoints": [
                    MockDocElement(name="valid", typed_metadata=MockOpenAPIEndpointMetadata()),
                    MockDocElement(name="invalid", typed_metadata=None),
                ]
            }
        )

        result = endpoints_filter(section)

        assert len(result) == 1
        assert result[0].path == "/users"  # From default MockOpenAPIEndpointMetadata


class TestSchemasFilter:
    """Tests for schemas_filter()."""

    def test_returns_empty_for_none(self) -> None:
        """Returns empty list for None section."""
        result = schemas_filter(None)
        assert result == []

    def test_returns_empty_for_empty_section(self) -> None:
        """Returns empty list for section without schemas."""
        section = MockSection()
        result = schemas_filter(section)
        assert result == []

    def test_returns_schema_views(self) -> None:
        """Returns SchemaViews from metadata.schemas."""
        meta1 = MockOpenAPISchemaMetadata(schema_type="object")
        meta2 = MockOpenAPISchemaMetadata(schema_type="array")

        section = MockSection(
            metadata={
                "schemas": [
                    MockDocElement(
                        name="User",
                        description="A user",
                        typed_metadata=meta1,
                        href="/schemas/user/",
                    ),
                    MockDocElement(name="Items", typed_metadata=meta2),
                ]
            }
        )

        result = schemas_filter(section)

        assert len(result) == 2
        assert all(isinstance(s, SchemaView) for s in result)
        assert result[0].name == "User"
        assert result[0].schema_type == "object"
        assert result[0].description == "A user"
        assert result[1].name == "Items"
        assert result[1].schema_type == "array"

    def test_skips_elements_without_typed_metadata(self) -> None:
        """Skips DocElements without typed_metadata."""
        section = MockSection(
            metadata={
                "schemas": [
                    MockDocElement(name="Valid", typed_metadata=MockOpenAPISchemaMetadata()),
                    MockDocElement(name="Invalid", typed_metadata=None),
                ]
            }
        )

        result = schemas_filter(section)

        assert len(result) == 1
        assert result[0].name == "Valid"


# =============================================================================
# Integration Tests
# =============================================================================


class TestFilterIntegration:
    """Integration tests for filter usage patterns."""

    def test_endpoints_with_deprecated_filtering(self) -> None:
        """Can filter endpoints by deprecated status."""
        section = MockSection(
            metadata={
                "endpoints": [
                    MockDocElement(
                        name="active",
                        typed_metadata=MockOpenAPIEndpointMetadata(
                            method="GET", path="/v2/users", deprecated=False
                        ),
                    ),
                    MockDocElement(
                        name="deprecated",
                        typed_metadata=MockOpenAPIEndpointMetadata(
                            method="GET", path="/v1/users", deprecated=True
                        ),
                    ),
                ]
            }
        )

        endpoints = endpoints_filter(section)
        active = [ep for ep in endpoints if not ep.deprecated]
        deprecated = [ep for ep in endpoints if ep.deprecated]

        assert len(active) == 1
        assert len(deprecated) == 1
        assert active[0].path == "/v2/users"
        assert deprecated[0].path == "/v1/users"

    def test_endpoints_grouped_by_tag(self) -> None:
        """Can group endpoints by tag."""
        section = MockSection(
            metadata={
                "endpoints": [
                    MockDocElement(
                        name="listUsers",
                        typed_metadata=MockOpenAPIEndpointMetadata(
                            method="GET", path="/users", tags=("users",)
                        ),
                    ),
                    MockDocElement(
                        name="listItems",
                        typed_metadata=MockOpenAPIEndpointMetadata(
                            method="GET", path="/items", tags=("items",)
                        ),
                    ),
                    MockDocElement(
                        name="createUser",
                        typed_metadata=MockOpenAPIEndpointMetadata(
                            method="POST", path="/users", tags=("users",)
                        ),
                    ),
                ]
            }
        )

        endpoints = endpoints_filter(section)
        users = [ep for ep in endpoints if "users" in ep.tags]
        items = [ep for ep in endpoints if "items" in ep.tags]

        assert len(users) == 2
        assert len(items) == 1

    def test_schemas_by_type(self) -> None:
        """Can filter schemas by type."""
        section = MockSection(
            metadata={
                "schemas": [
                    MockDocElement(
                        name="User",
                        typed_metadata=MockOpenAPISchemaMetadata(schema_type="object"),
                    ),
                    MockDocElement(
                        name="Status",
                        typed_metadata=MockOpenAPISchemaMetadata(
                            schema_type="string", enum=("a", "b")
                        ),
                    ),
                    MockDocElement(
                        name="Items",
                        typed_metadata=MockOpenAPISchemaMetadata(schema_type="array"),
                    ),
                ]
            }
        )

        schemas = schemas_filter(section)
        objects = [s for s in schemas if s.schema_type == "object"]
        enums = [s for s in schemas if s.enum is not None]

        assert len(objects) == 1
        assert objects[0].name == "User"
        assert len(enums) == 1
        assert enums[0].name == "Status"

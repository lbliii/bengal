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
    _build_example_body,
    _generate_anchor_id,
    _schema_to_example,
    endpoints_filter,
    generate_code_sample,
    get_response_example,
    schema_additional_properties,
    schema_composition,
    schema_constraints,
    schema_examples,
    schema_flags,
    schema_ref,
    schema_view_filter,
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
    parameters: tuple[Any, ...] = ()
    request_body: Any = None
    responses: tuple[Any, ...] = ()
    security: tuple[str, ...] = ()


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
    metadata: dict[str, Any] = field(default_factory=dict)
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
        assert view.anchor_id == "getUser"
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
        assert view.anchor_id == "post-users-user_id-posts"
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
        assert view.primary_tag == "items"
        assert view.typed_metadata is meta

    def test_preserves_operation_details_for_consolidated_templates(self) -> None:
        """Endpoint views keep details needed by consolidated reference pages."""
        params = ({"name": "user_id", "in": "path", "schema": {"type": "string"}},)
        raw_responses = {
            "201": {
                "description": "Created",
                "content": {"application/json": {"example": {"id": "user_123"}}},
            }
        }
        meta = MockOpenAPIEndpointMetadata(
            method="POST",
            path="/users/{user_id}",
            tags=("users",),
            parameters=params,
            responses=({"status_code": "201", "description": "Created"},),
            security=("BearerAuth",),
        )
        element = MockDocElement(
            name="createUser",
            typed_metadata=meta,
            metadata={"request_body": {"content": {}}, "responses": raw_responses},
        )

        view = EndpointView.from_doc_element(element, consolidated=True)

        assert view.parameters == (
            {
                "name": "user_id",
                "location": "path",
                "in": "path",
                "required": False,
                "schema_type": "string",
                "schema": {"type": "string"},
                "description": "",
                "default": None,
                "enum": None,
                "example": None,
            },
        )
        assert view.raw_request_body == {"content": {}}
        assert view.responses == (
            {
                "status_code": "201",
                "description": "Created",
                "content_type": "application/json",
                "schema_ref": None,
                "schema": {},
                "example": {"id": "user_123"},
            },
        )
        assert view.success_status == "201"
        assert view.response_example == {"id": "user_123"}
        assert view.security == ("BearerAuth",)


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
        assert view.anchor_id == "updateItem"
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

    def test_flattens_all_of_schema_properties(self) -> None:
        """Flattens allOf branches for schema detail rendering."""
        meta = MockOpenAPISchemaMetadata(schema_type=None)
        element = MockDocElement(
            name="Order",
            typed_metadata=meta,
            metadata={
                "raw_schema": {
                    "allOf": [
                        {
                            "type": "object",
                            "required": ["id"],
                            "properties": {"id": {"type": "string"}},
                        },
                        {
                            "type": "object",
                            "required": ["number"],
                            "properties": {"number": {"type": "string"}},
                        },
                    ]
                }
            },
        )

        view = SchemaView.from_doc_element(element)

        assert view.schema_type == "object"
        assert view.properties == {
            "id": {"type": "string"},
            "number": {"type": "string"},
        }
        assert view.required == ("id", "number")
        assert view.display_schema["properties"] == view.properties

    def test_schema_view_filter_handles_single_schema(self) -> None:
        """schema_view filter returns a normalized view for detail templates."""
        element = MockDocElement(
            name="Status",
            typed_metadata=MockOpenAPISchemaMetadata(schema_type="string", enum=("open", "closed")),
        )

        view = schema_view_filter(element)

        assert view is not None
        assert view.name == "Status"
        assert view.enum == ("open", "closed")


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


class TestOpenAPICodeSamples:
    """Tests for request sample generation."""

    def test_replaces_path_params_and_required_query_params(self) -> None:
        """Samples use concrete request URLs instead of raw placeholders."""
        sample = generate_code_sample(
            "curl",
            "GET",
            "/users/{user_id}/invoices",
            base_url="https://api.example.test",
            parameters=[
                {
                    "name": "user_id",
                    "in": "path",
                    "schema": {"type": "string"},
                    "required": True,
                },
                {
                    "name": "limit",
                    "in": "query",
                    "schema": {"type": "integer", "default": 25},
                    "required": True,
                },
            ],
        )

        assert "https://api.example.test/users/id_123/invoices?limit=25" in sample
        assert "{user_id}" not in sample

    def test_builds_body_from_raw_openapi_request_body(self) -> None:
        """Request bodies can be generated from raw OpenAPI content maps."""
        sample = generate_code_sample(
            "python",
            "POST",
            "/users",
            request_body={
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "properties": {
                                "email": {"type": "string", "format": "email"},
                                "active": {"type": "boolean"},
                            },
                        }
                    }
                }
            },
        )

        assert '"email": "user@example.com"' in sample
        assert '"active": true' in sample

    def test_response_example_supports_raw_response_maps(self) -> None:
        """Response examples are extracted from raw OpenAPI response maps."""
        example = get_response_example(
            {
                "201": {
                    "content": {
                        "application/json": {
                            "examples": {
                                "created": {"value": {"id": "user_123"}},
                            }
                        }
                    }
                }
            },
            "201",
        )

        assert example == {"id": "user_123"}


# =============================================================================
# Tests for advanced schema normalization (#285)
# =============================================================================


class TestSchemaComposition:
    """Tests for schema_composition() (oneOf/anyOf/allOf + discriminator)."""

    def test_one_of_with_discriminator(self) -> None:
        """oneOf polymorphism exposes branches and a normalized discriminator."""
        raw = {
            "type": "object",
            "discriminator": {
                "propertyName": "type",
                "mapping": {
                    "credit_card": "#/components/schemas/CreditCard",
                    "bank_account": "#/components/schemas/BankAccount",
                    "paypal": "#/components/schemas/PayPal",
                },
            },
            "oneOf": [
                {"type": "object", "properties": {"type": {"enum": ["credit_card"]}}},
                {"type": "object", "properties": {"type": {"enum": ["bank_account"]}}},
                {"type": "object", "title": "PayPal"},
            ],
        }

        composition = schema_composition(raw)

        assert composition is not None
        assert composition["kind"] == "oneOf"
        assert len(composition["branches"]) == 3
        # Branch labels derive from a single-value type enum, else title.
        assert [b["label"] for b in composition["branches"]] == [
            "credit_card",
            "bank_account",
            "PayPal",
        ]
        disc = composition["discriminator"]
        assert disc is not None
        assert disc["property_name"] == "type"
        assert {row["value"] for row in disc["mapping"]} == {
            "credit_card",
            "bank_account",
            "paypal",
        }
        # The ref string is shortened to its schema name for display.
        assert {row["target"] for row in disc["mapping"]} == {
            "CreditCard",
            "BankAccount",
            "PayPal",
        }

    def test_any_of_without_discriminator(self) -> None:
        """anyOf is recognized and reports no discriminator when absent."""
        composition = schema_composition({"anyOf": [{"type": "string"}, {"type": "integer"}]})
        assert composition is not None
        assert composition["kind"] == "anyOf"
        assert composition["discriminator"] is None
        assert composition["branches"][0]["schema_type"] == "string"

    def test_all_of_is_recognized_as_composition(self) -> None:
        """allOf is exposed as composition even though properties stay flattened."""
        composition = schema_composition({"allOf": [{"type": "object"}, {"type": "object"}]})
        assert composition is not None
        assert composition["kind"] == "allOf"

    def test_plain_schema_has_no_composition(self) -> None:
        """A non-composed schema returns None (discriminating, not vacuous)."""
        assert schema_composition({"type": "object", "properties": {}}) is None
        assert schema_composition(None) is None


class TestSchemaConstraints:
    """Tests for schema_constraints() validation-constraint extraction."""

    def test_extracts_present_constraints_only(self) -> None:
        """Only set constraint keys are returned, with their values."""
        constraints = schema_constraints(
            {
                "type": "string",
                "pattern": "^[a-z]+$",
                "minLength": 3,
                "maxLength": 64,
                "format": "email",
            }
        )
        assert constraints == {
            "format": "email",
            "pattern": "^[a-z]+$",
            "min length": "3",
            "max length": "64",
        }

    def test_unique_items_renders_as_label_only(self) -> None:
        """Boolean uniqueItems maps to an empty value (label-only chip)."""
        assert schema_constraints({"type": "array", "uniqueItems": True}) == {"unique items": ""}
        # False boolean constraints are omitted entirely.
        assert schema_constraints({"type": "array", "uniqueItems": False}) == {}

    def test_exclusive_bounds(self) -> None:
        """exclusiveMinimum/exclusiveMaximum (3.1 numeric form) are surfaced."""
        assert schema_constraints(
            {"type": "number", "exclusiveMinimum": 0, "exclusiveMaximum": 100}
        ) == {"exclusive min": "0", "exclusive max": "100"}

    def test_no_constraints_yields_empty_dict(self) -> None:
        """A property with no constraints yields an empty dict, not noise."""
        assert schema_constraints({"type": "string"}) == {}
        assert schema_constraints(None) == {}


class TestSchemaFlags:
    """Tests for schema_flags() (nullable/readOnly/writeOnly/deprecated)."""

    def test_surfaces_true_flags_only(self) -> None:
        """Only flags set to true are returned."""
        assert schema_flags({"type": "string", "writeOnly": True}) == {"writeOnly": True}
        assert schema_flags({"type": "string", "readOnly": True, "deprecated": True}) == {
            "readOnly": True,
            "deprecated": True,
        }

    def test_normal_field_has_no_flags(self) -> None:
        """A plain field reports no flags (the discriminating negative case)."""
        assert schema_flags({"type": "string"}) == {}

    def test_nullable_via_openapi_30_and_31_forms(self) -> None:
        """nullable is recognized from 3.0 `nullable` and 3.1 type-array null."""
        assert schema_flags({"type": "string", "nullable": True}) == {"nullable": True}
        assert schema_flags({"type": ["string", "null"]}) == {"nullable": True}


class TestSchemaAdditionalProperties:
    """Tests for schema_additional_properties() normalization."""

    def test_boolean_form(self) -> None:
        assert schema_additional_properties({"type": "object", "additionalProperties": True}) == {
            "allowed": True
        }

    def test_schema_form_is_typed_map(self) -> None:
        result = schema_additional_properties(
            {"type": "object", "additionalProperties": {"type": "string"}}
        )
        assert result is not None
        assert result["schema_type"] == "string"
        assert result["value_schema"] == {"type": "string"}

    def test_absent_returns_none(self) -> None:
        assert schema_additional_properties({"type": "object"}) is None


class TestSchemaExamples:
    """Tests for schema_examples() example normalization."""

    def test_singular_example(self) -> None:
        examples = schema_examples({"type": "string", "example": "hello"})
        assert examples == ({"name": "", "summary": "", "value": "hello"},)

    def test_examples_map_with_summary_and_value(self) -> None:
        examples = schema_examples(
            {
                "examples": {
                    "ok": {"summary": "A success", "value": {"id": 1}},
                    "bare": "plain",
                }
            }
        )
        assert examples[0] == {"name": "ok", "summary": "A success", "value": {"id": 1}}
        assert examples[1] == {"name": "bare", "summary": "", "value": "plain"}

    def test_no_examples_yields_empty_tuple(self) -> None:
        assert schema_examples({"type": "string"}) == ()


class TestSchemaRef:
    """Tests for schema_ref() (cyclic $ref leaf detection)."""

    def test_bare_ref_returns_schema_name(self) -> None:
        assert schema_ref({"$ref": "#/components/schemas/TreeNode"}) == "TreeNode"

    def test_resolved_schema_returns_none(self) -> None:
        assert schema_ref({"type": "object", "properties": {}}) is None
        assert schema_ref(None) is None


class TestSchemaViewExposesAdvancedConstructs:
    """display_schema must carry advanced keys for advanced schemas only."""

    def test_advanced_keys_surface_for_composed_schema(self) -> None:
        """A composed schema's display_schema exposes the raw construct keys."""
        element = MockDocElement(
            name="PaymentMethod",
            typed_metadata=MockOpenAPISchemaMetadata(schema_type="object"),
            metadata={
                "raw_schema": {
                    "type": "object",
                    "discriminator": {"propertyName": "type"},
                    "oneOf": [{"type": "object"}, {"type": "object"}],
                }
            },
        )

        view = SchemaView.from_doc_element(element)

        assert schema_composition(view.display_schema) is not None
        assert "oneOf" in view.display_schema
        assert "discriminator" in view.display_schema

    def test_simple_schema_display_schema_stays_minimal(self) -> None:
        """A simple schema gains no advanced keys (byte-stable output guard)."""
        element = MockDocElement(
            name="Tag",
            typed_metadata=MockOpenAPISchemaMetadata(schema_type="string"),
            metadata={"raw_schema": {"type": "string"}},
        )

        view = SchemaView.from_doc_element(element)

        advanced = {
            "oneOf",
            "anyOf",
            "allOf",
            "discriminator",
            "additionalProperties",
            "examples",
            "nullable",
            "readOnly",
            "writeOnly",
            "deprecated",
            "pattern",
            "format",
        }
        assert advanced.isdisjoint(view.display_schema.keys())


class TestSchemaExampleBounding:
    """_schema_to_example / _build_example_body must bound recursion + handle oneOf."""

    def test_self_referential_schema_is_bounded(self) -> None:
        """A directly circular schema returns within the depth bound, no hang.

        This assertion would stack-overflow / hang forever if the depth guard
        regressed — that is the point of the test.
        """
        node: dict[str, Any] = {"type": "object", "properties": {}}
        node["properties"]["self"] = node  # direct cycle

        result = _schema_to_example(node)

        # Bounded: the recursion terminates and yields a finite nested dict.
        assert isinstance(result, dict)

    def test_indirect_cycle_is_bounded(self) -> None:
        """An A -> B -> A cycle also terminates."""
        a: dict[str, Any] = {"type": "object", "properties": {}}
        b: dict[str, Any] = {"type": "object", "properties": {}}
        a["properties"]["b"] = b
        b["properties"]["a"] = a

        result = _schema_to_example(a)
        assert isinstance(result, dict)

    def test_one_of_request_body_uses_first_branch(self) -> None:
        """A polymorphic (oneOf) request body yields the first branch example."""
        body = _build_example_body(
            {
                "content": {
                    "application/json": {
                        "schema": {
                            "oneOf": [
                                {
                                    "type": "object",
                                    "properties": {"kind": {"enum": ["card"]}},
                                },
                                {"type": "object", "properties": {"kind": {"enum": ["cash"]}}},
                            ]
                        }
                    }
                }
            }
        )
        assert body == {"kind": "card"}

    def test_media_type_examples_take_precedence(self) -> None:
        """An explicit media-type examples map is preferred over schema synthesis."""
        body = _build_example_body(
            {
                "content": {
                    "application/json": {
                        "examples": {"sample": {"value": {"id": "abc"}}},
                        "schema": {"type": "object", "properties": {"id": {"type": "string"}}},
                    }
                }
            }
        )
        assert body == {"id": "abc"}

    def test_list_form_examples_do_not_crash(self) -> None:
        """A JSON-Schema list-form `examples` must not raise (it is not a map).

        Regression for an AttributeError when `examples.values()` was called on
        a list — at both the top-level and the media-type example sites.
        """
        assert _build_example_body({"examples": [{"value": "first"}, {"value": "second"}]}) == (
            "first"
        )
        assert _build_example_body({"examples": ["plain", "other"]}) == "plain"
        media_body = _build_example_body(
            {"content": {"application/json": {"examples": [{"value": {"id": 1}}]}}}
        )
        assert media_body == {"id": 1}

    def test_malformed_properties_do_not_crash(self) -> None:
        """A non-Mapping `properties` (malformed spec) degrades, never crashes."""
        # allOf merge path.
        assert isinstance(
            _schema_to_example({"allOf": [{"type": "object"}], "properties": ["a", "b"]}),
            dict,
        )
        # object branch path.
        assert _schema_to_example({"type": "object", "properties": ["a", "b"]}) == {}

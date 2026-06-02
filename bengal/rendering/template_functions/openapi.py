"""
OpenAPI template functions for REST API documentation.

Provides code sample generation and utility functions for OpenAPI templates.

Functions:
- generate_code_sample: Generate code samples in multiple languages
- highlight_path_params: Highlight {param} placeholders in paths
- method_color_class: Get CSS class for HTTP method
- status_code_class: Get CSS class for HTTP status code
- get_response_example: Extract example from OpenAPI response
- endpoints: Filter to normalize endpoint access from sections
- schemas: Filter to normalize schema access from sections

Engine-Agnostic:
These functions work with any template engine that provides a globals/filters
interface (Jinja2, Kida, or custom engines via the adapter layer).

"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol, cast

from bengal.utils.observability.logger import get_logger

logger = get_logger(__name__)

if TYPE_CHECKING:
    from bengal.autodoc.base import DocElement
    from bengal.autodoc.models.openapi import OpenAPIEndpointMetadata, OpenAPISchemaMetadata
    from bengal.protocols import PageLike, SectionLike, SiteLike, TemplateEnvironment


class DocElementLike(Protocol):
    """Protocol for objects with DocElement-like interface."""

    @property
    def typed_metadata(self) -> Any:
        """Typed metadata object."""
        ...

    @property
    def description(self) -> str:
        """Element description."""
        ...

    @property
    def metadata(self) -> Any:
        """Untyped metadata object."""
        ...

    @property
    def href(self) -> str | None:
        """URL to the element."""
        ...


# =============================================================================
# View Dataclasses for Template Normalization
# =============================================================================


@dataclass(frozen=True, slots=True)
class EndpointView:
    """
    Normalized endpoint view for templates.

    Provides consistent access to endpoint data regardless of
    whether the source is a DocElement (consolidated mode) or
    Page (individual mode).

    Attributes:
        method: HTTP method (GET, POST, etc.)
        path: URL path with parameters (/users/{id})
        summary: Short description
        description: Full description
        deprecated: Whether endpoint is deprecated
        href: Always valid - anchor in consolidated mode, page URL otherwise
        anchor_id: Stable in-page anchor ID
        has_page: Whether an individual page exists
        operation_id: OpenAPI operationId (for advanced use)
        tags: Endpoint tags
        parameters: Request parameters
        request_body: Typed request body metadata
        raw_request_body: Raw OpenAPI requestBody object, when available
        responses: Typed response metadata
        raw_responses: Raw OpenAPI responses object, when available
        security: Security requirements
        primary_tag: First tag or "Default"
        success_status: First 2xx response code
        response_example: Example object for the success response, when available
        typed_metadata: Full OpenAPIEndpointMetadata (for advanced use)

    """

    method: str
    path: str
    summary: str
    description: str
    deprecated: bool
    href: str  # Always valid - never None
    anchor_id: str
    has_page: bool
    operation_id: str | None
    tags: tuple[str, ...]
    parameters: tuple[Any, ...] = ()
    request_body: Any = None
    raw_request_body: Any = None
    responses: tuple[Any, ...] = ()
    raw_responses: Any = None
    security: tuple[Any, ...] = ()
    primary_tag: str = "Default"
    success_status: str | None = None
    response_example: Any = None
    typed_metadata: Any = None  # OpenAPIEndpointMetadata or None

    @classmethod
    def from_doc_element(cls, el: DocElementLike, consolidated: bool) -> EndpointView:
        """Create from DocElement (consolidated or individual mode)."""
        meta: OpenAPIEndpointMetadata = el.typed_metadata
        raw_meta = getattr(el, "metadata", {}) or {}
        raw_parameters = _get_value(raw_meta, "parameters") or meta.parameters
        raw_responses = _get_value(raw_meta, "responses") or meta.responses
        success_status = _first_success_status(raw_responses)

        # Generate anchor ID from operationId or path
        anchor_id = meta.operation_id or _generate_anchor_id(meta.method, meta.path)

        # Smart href: anchor if consolidated, page URL otherwise
        href = f"#{anchor_id}" if consolidated else el.href or "#"

        return cls(
            method=meta.method,
            path=meta.path,
            summary=meta.summary or "",
            description=el.description,
            deprecated=meta.deprecated,
            href=href,
            anchor_id=anchor_id,
            has_page=not consolidated,
            operation_id=meta.operation_id,
            tags=meta.tags or (),
            parameters=_parameter_views(raw_parameters),
            request_body=_request_body_view(
                _get_value(raw_meta, "request_body") or meta.request_body
            ),
            raw_request_body=_get_value(raw_meta, "request_body") or meta.request_body,
            responses=_response_views(raw_responses),
            raw_responses=raw_responses,
            security=meta.security or (),
            primary_tag=(meta.tags[0] if meta.tags else "Default"),
            success_status=success_status,
            response_example=get_response_example(raw_responses, success_status or "200"),
            typed_metadata=meta,
        )

    @classmethod
    def from_page(cls, page: PageLike) -> EndpointView:
        """Create from Page (individual mode)."""
        meta = page.metadata
        # Autodoc endpoint pages carry the source DocElement (with typed
        # metadata and the resolved page href) rather than flattened
        # method/path/parameter keys. Build the view from that element so the
        # listing matches the detail page exactly, including ``el.href``.
        element = meta.get("autodoc_element")
        if element is not None and getattr(element, "typed_metadata", None) is not None:
            return cls.from_doc_element(element, consolidated=False)
        raw_parameters = meta.get("parameters", ())
        raw_responses = meta.get("responses", ())
        success_status = _first_success_status(raw_responses)
        tags = tuple(meta.get("tags", ()))
        return cls(
            method=meta.get("method", "GET"),
            path=meta.get("path", ""),
            summary=meta.get("summary", ""),
            description=meta.get("description", ""),
            deprecated=meta.get("deprecated", False),
            href=page.href or "#",
            anchor_id=meta.get("operation_id")
            or _generate_anchor_id(meta.get("method", "GET"), meta.get("path", "")),
            has_page=True,
            operation_id=meta.get("operation_id"),
            tags=tags,
            parameters=_parameter_views(raw_parameters),
            request_body=_request_body_view(meta.get("request_body")),
            raw_request_body=meta.get("request_body"),
            responses=_response_views(raw_responses),
            raw_responses=raw_responses,
            security=tuple(meta.get("security") or ()),
            primary_tag=(tags[0] if tags else "Default"),
            success_status=success_status,
            response_example=get_response_example(raw_responses, success_status or "200"),
            typed_metadata=None,
        )


@dataclass(frozen=True, slots=True)
class SchemaView:
    """
    Normalized schema view for templates.

    Provides consistent access to schema data for listing and linking.

    Attributes:
        name: Schema name (e.g., "User", "OrderRequest")
        schema_type: Type (object, array, string, etc.)
        description: Schema description
        href: Link to schema page (or anchor if inline)
        has_page: Whether individual page exists
        properties: Property definitions (for quick access)
        required: Required property names
        enum: Enum values (if applicable)
        example: Example value (if provided)
        raw_schema: Raw OpenAPI schema object
        display_schema: Flattened schema object for template rendering
        typed_metadata: Full OpenAPISchemaMetadata

    """

    name: str
    schema_type: str
    description: str
    href: str
    has_page: bool
    properties: dict[str, Any]
    required: tuple[str, ...]
    enum: tuple[Any, ...] | None
    example: Any
    raw_schema: Any
    display_schema: dict[str, Any]
    typed_metadata: Any  # OpenAPISchemaMetadata or None

    @classmethod
    def from_doc_element(cls, el: DocElement, consolidated: bool = False) -> SchemaView:
        """Create from DocElement."""
        meta = cast("OpenAPISchemaMetadata", el.typed_metadata)
        raw_meta = getattr(el, "metadata", {}) or {}
        raw_schema = _get_value(raw_meta, "raw_schema") or raw_meta
        properties = _schema_properties(raw_schema) or dict(meta.properties or {})
        required = _schema_required(raw_schema) or tuple(meta.required or ())
        schema_type = _schema_type(raw_schema, meta.schema_type)
        enum = _schema_enum(raw_schema)
        if enum is None:
            enum = meta.enum
        example = _get_value(raw_schema, "example", meta.example)
        display_schema = {
            "type": schema_type,
            "schema_type": schema_type,
            "properties": properties,
            "required": required,
            "enum": enum,
            "example": example,
            "description": el.description,
        }

        # Smart href: anchor if no page, page URL otherwise
        if consolidated or not el.href:
            href = f"#schema-{el.name}"
            has_page = False
        else:
            href = el.href
            has_page = True

        return cls(
            name=el.name,
            schema_type=schema_type,
            description=el.description,
            href=href,
            has_page=has_page,
            properties=properties,
            required=required,
            enum=enum,
            example=example,
            raw_schema=raw_schema,
            display_schema=display_schema,
            typed_metadata=meta,
        )


def _schema_type(raw_schema: Any, fallback: str | None = None) -> str:
    """Return a display type for raw or normalized OpenAPI schemas."""
    schema_type = _get_value(raw_schema, "type")
    if schema_type:
        return str(schema_type)
    if _get_value(raw_schema, "allOf"):
        return "object"
    if _get_value(raw_schema, "oneOf"):
        return "oneOf"
    if _get_value(raw_schema, "anyOf"):
        return "anyOf"
    return fallback or "object"


def _schema_properties(raw_schema: Any) -> dict[str, Any]:
    """Flatten displayable properties from direct and allOf schema objects."""
    properties: dict[str, Any] = {}
    direct = _get_value(raw_schema, "properties") or {}
    if isinstance(direct, Mapping):
        properties.update(dict(direct))

    all_of = _get_value(raw_schema, "allOf") or ()
    if isinstance(all_of, Sequence) and not isinstance(all_of, str):
        for child in all_of:
            child_props = _schema_properties(child)
            properties.update(child_props)

    return properties


def _schema_required(raw_schema: Any) -> tuple[str, ...]:
    """Flatten required property names from direct and allOf schema objects."""
    required: list[str] = []

    direct = _get_value(raw_schema, "required") or ()
    if isinstance(direct, Sequence) and not isinstance(direct, str):
        required.extend(str(item) for item in direct)

    all_of = _get_value(raw_schema, "allOf") or ()
    if isinstance(all_of, Sequence) and not isinstance(all_of, str):
        for child in all_of:
            required.extend(_schema_required(child))

    return tuple(dict.fromkeys(required))


def _schema_enum(raw_schema: Any) -> tuple[Any, ...] | None:
    """Return enum values from direct, allOf, oneOf, or anyOf schemas."""
    direct = _get_value(raw_schema, "enum")
    if direct:
        return tuple(direct)

    for key in ("allOf", "oneOf", "anyOf"):
        children = _get_value(raw_schema, key) or ()
        if isinstance(children, Sequence) and not isinstance(children, str):
            for child in children:
                child_enum = _schema_enum(child)
                if child_enum:
                    return child_enum
    return None


def _generate_anchor_id(method: str, path: str) -> str:
    """Generate a URL-safe anchor ID from method and path."""
    # Remove leading/trailing slashes, replace path separators and braces
    sanitized = path.strip("/").replace("/", "-").replace("{", "").replace("}", "")
    return f"{method.lower()}-{sanitized}" if sanitized else method.lower()


def _get_value(obj: Any, key: str, default: Any = None) -> Any:
    """Get a value from a mapping or object attribute."""
    if isinstance(obj, Mapping):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _parameter_views(parameters: Sequence[Any] | None) -> tuple[dict[str, Any], ...]:
    """Normalize typed and raw OpenAPI parameters for strict templates."""
    if not parameters:
        return ()

    views: list[dict[str, Any]] = []
    for param in parameters:
        schema = _get_value(param, "schema") or {}
        schema_type = _get_value(param, "schema_type") or _get_value(schema, "type", "string")
        location = _get_value(param, "location") or _get_value(param, "in", "query")

        views.append(
            {
                "name": _get_value(param, "name", "unnamed"),
                "location": location,
                "in": location,
                "required": _get_value(param, "required", False),
                "schema_type": schema_type,
                "schema": schema,
                "description": _get_value(param, "description", ""),
                "default": _get_value(param, "default", _get_value(schema, "default")),
                "enum": _get_value(param, "enum", _get_value(schema, "enum")),
                "example": _get_value(param, "example", _get_value(schema, "example")),
            }
        )

    return tuple(views)


def _request_body_view(request_body: Any) -> dict[str, Any] | None:
    """Normalize typed and raw OpenAPI request body metadata."""
    if not request_body:
        return None

    content_type = _get_value(request_body, "content_type", "application/json")
    schema: Any = {}
    if isinstance(request_body, Mapping):
        content_type, media = _select_json_media_item(request_body.get("content", {}))
        schema = _get_value(media, "schema") or {}

    return {
        "content_type": content_type,
        "required": _get_value(request_body, "required", False),
        "description": _get_value(request_body, "description", ""),
        "schema_ref": _get_value(request_body, "schema_ref") or _get_value(schema, "$ref"),
        "schema": schema,
    }


def _response_views(responses: Any) -> tuple[dict[str, Any], ...]:
    """Normalize typed and raw OpenAPI responses for strict templates."""
    if not responses:
        return ()

    views: list[dict[str, Any]] = []
    if isinstance(responses, Mapping):
        for code, response in responses.items():
            content_type: str | None = None
            schema: Any = {}
            if isinstance(response, Mapping):
                content_type, media = _select_json_media_item(response.get("content", {}))
                schema = _get_value(media, "schema") or {}
            views.append(
                {
                    "status_code": str(code),
                    "description": _get_value(response, "description", ""),
                    "content_type": content_type,
                    "schema_ref": _get_value(response, "schema_ref") or _get_value(schema, "$ref"),
                    "schema": schema,
                    "example": get_response_example({str(code): response}, str(code)),
                }
            )
        return tuple(views)

    if not isinstance(responses, Sequence) or isinstance(responses, str | bytes):
        return ()

    for response in responses:
        schema = _get_value(response, "schema") or {}
        views.append(
            {
                "status_code": str(_get_value(response, "status_code", "200")),
                "description": _get_value(response, "description", ""),
                "content_type": _get_value(response, "content_type"),
                "schema_ref": _get_value(response, "schema_ref") or _get_value(schema, "$ref"),
                "schema": schema,
                "example": _get_value(response, "example"),
            }
        )
    return tuple(views)


def _first_success_status(responses: Any) -> str | None:
    """Return the first 2xx response code from raw or typed OpenAPI responses."""
    response_items: Sequence[Any]
    if isinstance(responses, Mapping):
        for code in responses:
            if str(code).startswith("2"):
                return str(code)
        return next((str(code) for code in responses), None)

    if isinstance(responses, Sequence) and not isinstance(responses, str | bytes):
        response_items = responses
    else:
        response_items = ()

    for response in response_items:
        code = _get_value(response, "status_code")
        if str(code).startswith("2"):
            return str(code)
    for response in response_items:
        code = _get_value(response, "status_code")
        if code:
            return str(code)
    return None


# =============================================================================
# Filter Functions
# =============================================================================


def endpoints_filter(section: SectionLike | None) -> list[EndpointView]:
    """
    Normalize section endpoints for templates.

    Detects consolidation mode automatically and returns a list of
    EndpointView objects with consistent properties.

    Usage:
        {% for ep in section | endpoints %}
          <a href="{{ ep.href }}">{{ ep.method }} {{ ep.path }}</a>
        {% end %}

    Args:
        section: Section containing endpoints

    Returns:
        List of EndpointView objects

    """
    if section is None:
        return []

    # Detect mode from data structure.
    #
    # Tag sections always carry their endpoint DocElements in
    # ``metadata["endpoints"]`` (set by section_builders.py), but when endpoints
    # are generated as individual pages they ALSO appear in ``section.pages``.
    # Prefer the page-backed view in that case so ``ep.href`` is a real page URL
    # rather than an in-page ``#anchor``. Fall back to the consolidated anchor
    # view only when no endpoint pages exist (``consolidate: true``).
    metadata = getattr(section, "metadata", None)
    if metadata is None:
        metadata = {}

    # Multi-tag note: secondary tag sections also carry an endpoint in their
    # metadata["endpoints"] even though each endpoint has a SINGLE canonical page
    # under its first tag. list.html renders the page URL from
    # EndpointView.from_page(), which is always that first-tag canonical URL, so
    # cross-listing an endpoint under multiple tags never duplicates the page.

    # Individual mode - Pages in section.pages (consolidate=false)
    pages = getattr(section, "pages", None) or []
    endpoint_pages = [
        p
        for p in pages
        if hasattr(p, "metadata")
        and (
            p.metadata.get("element_type") == "openapi_endpoint"
            or p.metadata.get("type") == "openapi_endpoint"
            or "method" in p.metadata
        )
    ]
    raw_endpoints = metadata.get("endpoints", [])

    if endpoint_pages:
        # Individual mode: start with this tag's canonical (first-tag) pages, then
        # UNION in endpoints whose first tag is elsewhere but that are cross-listed
        # under this tag (present only in metadata["endpoints"]). Without this, a
        # secondary tag that also owns its own endpoint would silently drop the
        # cross-listed ones, since page-backed and metadata views were previously
        # mutually exclusive. Dedupe by (method, path); cross-listed views link to
        # their canonical first-tag page via ``el.href``.
        views = [EndpointView.from_page(p) for p in endpoint_pages]
        seen = {(v.method, v.path) for v in views}
        for el in raw_endpoints:
            if getattr(el, "typed_metadata", None) is None:
                continue
            view = EndpointView.from_doc_element(el, consolidated=False)
            if (view.method, view.path) not in seen:
                seen.add((view.method, view.path))
                views.append(view)
        return views

    if raw_endpoints:
        # Consolidated mode - DocElements stored in metadata.endpoints
        return [
            EndpointView.from_doc_element(el, consolidated=True)
            for el in raw_endpoints
            if hasattr(el, "typed_metadata") and el.typed_metadata is not None
        ]

    return []


def schemas_filter(section: SectionLike | None) -> list[SchemaView]:
    """
    Normalize section schemas for templates.

    Returns a list of SchemaView objects with consistent properties.

    Usage:
        {% for schema in section | schemas %}
          <a href="{{ schema.href }}">{{ schema.name }}</a>
          <span>{{ schema.schema_type }}</span>
        {% end %}

    Args:
        section: Section containing schemas (usually root API section)

    Returns:
        List of SchemaView objects

    """
    if section is None:
        return []

    metadata = getattr(section, "metadata", None)
    if metadata is None:
        metadata = {}

    raw_schemas = metadata.get("schemas", [])

    return [
        SchemaView.from_doc_element(el, consolidated=False)
        for el in raw_schemas
        if hasattr(el, "typed_metadata") and el.typed_metadata is not None
    ]


def schema_view_filter(element: DocElement | None) -> SchemaView | None:
    """Normalize a single OpenAPI schema element for templates."""
    if element is None:
        return None
    if not hasattr(element, "typed_metadata") or element.typed_metadata is None:
        return None
    return SchemaView.from_doc_element(element, consolidated=False)


def register(env: TemplateEnvironment, site: SiteLike) -> None:
    """Register OpenAPI functions with template environment.

    Args:
        env: Template environment (Jinja2, Kida, or any engine with globals/filters)
        site: Site instance

    """
    env.globals.update(
        {
            "generate_code_sample": generate_code_sample,
            "highlight_path_params": highlight_path_params,
            "method_color_class": method_color_class,
            "status_code_class": status_code_class,
            "get_response_example": get_response_example,
            "schema_view": schema_view_filter,
        }
    )
    env.filters.update(
        {
            "highlight_path_params": highlight_path_params,
            "method_color_class": method_color_class,
            "status_code_class": status_code_class,
            "endpoints": endpoints_filter,
            "schemas": schemas_filter,
            "schema_view": schema_view_filter,
        }
    )


# =============================================================================
# Code Sample Generation
# =============================================================================


def generate_code_sample(
    language: str,
    method: str,
    path: str,
    *,
    base_url: str = "https://api.example.com",
    request_body: Any = None,
    parameters: Sequence[Any] | None = None,
    headers: dict[str, str] | None = None,
    auth_scheme: str = "Bearer",
) -> str:
    """
    Generate a code sample for an API endpoint in the specified language.

    Args:
        language: Target language (curl, python, javascript, go, ruby, php)
        method: HTTP method (GET, POST, PUT, PATCH, DELETE, etc.)
        path: Endpoint path (e.g., "/users/{id}")
        base_url: Base API URL
        request_body: Request body schema/example
        parameters: List of parameter definitions
        headers: Additional headers
        auth_scheme: Authentication scheme name

    Returns:
        Formatted code sample string

    Example:
        {{ generate_code_sample('curl', 'GET', '/users/{id}') }}

    """
    method = method.upper()
    generators = {
        "curl": _generate_curl_sample,
        "python": _generate_python_sample,
        "javascript": _generate_javascript_sample,
        "go": _generate_go_sample,
        "ruby": _generate_ruby_sample,
        "php": _generate_php_sample,
    }

    generator = generators.get(language.lower())
    if not generator:
        return f"# Code sample not available for {language}"

    return generator(
        method=method,
        path=path,
        base_url=base_url,
        request_body=request_body,
        parameters=parameters,
        headers=headers or {},
        auth_scheme=auth_scheme,
    )


def _build_example_body(request_body: Any) -> Any:
    """Build an example request body from schema."""
    if not request_body:
        return {}

    if not isinstance(request_body, Mapping):
        example = _get_value(request_body, "example")
        if example is not None:
            return example
        return {}

    # If there's an explicit example, use it
    if "example" in request_body:
        return request_body["example"]
    examples = request_body.get("examples")
    if examples:
        first_example = next(iter(examples.values()), {})
        if isinstance(first_example, Mapping):
            return first_example.get("value", {})
        return first_example

    if "content" in request_body and isinstance(request_body["content"], Mapping):
        media = _select_json_media(request_body["content"])
        if media:
            if "example" in media:
                return media["example"]
            examples = media.get("examples")
            if examples:
                first_example = next(iter(examples.values()), {})
                if isinstance(first_example, Mapping):
                    return first_example.get("value", {})
                return first_example
            schema = media.get("schema", {})
            return _schema_to_example(schema) if isinstance(schema, Mapping) else {}

    # Try to build from schema
    schema = request_body.get("schema", request_body)
    return _schema_to_example(schema)


def _schema_to_example(schema: Any) -> Any:
    """Convert a JSON schema to an example value."""
    if not isinstance(schema, Mapping):
        return None

    schema_type = schema.get("type", schema.get("schema_type", "object"))

    if "example" in schema:
        return schema["example"]

    if schema_type == "object":
        properties = schema.get("properties", {})
        result = {}
        for name, prop in properties.items():
            result[name] = _schema_to_example(prop)
        return result

    if schema_type == "array":
        items = schema.get("items", {})
        return [_schema_to_example(items)]

    if schema_type == "string":
        if schema.get("enum"):
            return schema["enum"][0]
        if schema.get("format") == "email":
            return "user@example.com"
        if schema.get("format") == "date":
            return "2025-01-01"
        if schema.get("format") == "date-time":
            return "2025-01-01T00:00:00Z"
        if schema.get("format") == "uuid":
            return "550e8400-e29b-41d4-a716-446655440000"
        return "string"

    if schema_type == "integer":
        return schema.get("default", 1)

    if schema_type == "number":
        return schema.get("default", 1.0)

    if schema_type == "boolean":
        return schema.get("default", True)

    return None


def _generate_curl_sample(
    method: str,
    path: str,
    base_url: str,
    request_body: Any,
    parameters: Sequence[Any] | None,
    headers: dict[str, str],
    auth_scheme: str,
) -> str:
    """Generate cURL code sample."""
    url = f"{base_url}{_path_with_parameter_examples(path, parameters)}"
    lines = [f'curl -X {method} "{url}"']

    # Authorization header
    lines.append(f'  -H "Authorization: {auth_scheme} $API_KEY"')

    # Content-Type for methods with body
    if method in ("POST", "PUT", "PATCH"):
        lines.append('  -H "Content-Type: application/json"')

    # Additional headers
    for key, value in headers.items():
        lines.append(f'  -H "{key}: {value}"')

    # Request body
    if request_body and method in ("POST", "PUT", "PATCH"):
        body = _build_example_body(request_body)
        body_json = json.dumps(body, indent=2)
        # Escape for shell
        body_escaped = body_json.replace("'", "'\\''")
        lines.append(f"  -d '{body_escaped}'")

    return " \\\n".join(lines)


def _generate_python_sample(
    method: str,
    path: str,
    base_url: str,
    request_body: Any,
    parameters: Sequence[Any] | None,
    headers: dict[str, str],
    auth_scheme: str,
) -> str:
    """Generate Python (requests) code sample."""
    lines = ["import requests", ""]
    lines.append(f'url = "{base_url}{_path_with_parameter_examples(path, parameters)}"')
    lines.append("headers = {")
    lines.append(f'    "Authorization": "{auth_scheme} " + API_KEY,')

    if method in ("POST", "PUT", "PATCH"):
        lines.append('    "Content-Type": "application/json",')

    for key, value in headers.items():
        lines.append(f'    "{key}": "{value}",')

    lines.append("}")
    lines.append("")

    # Request body
    if request_body and method in ("POST", "PUT", "PATCH"):
        body = _build_example_body(request_body)
        lines.append("payload = " + _format_python_dict(body))
        lines.append("")
        lines.append(f"response = requests.{method.lower()}(url, headers=headers, json=payload)")
    else:
        lines.append(f"response = requests.{method.lower()}(url, headers=headers)")

    lines.append("")
    lines.append("print(response.json())")

    return "\n".join(lines)


def _format_python_dict(obj: Any, indent: int = 0) -> str:
    """Format a Python dict/list for code display."""
    return json.dumps(obj, indent=4)


def _generate_javascript_sample(
    method: str,
    path: str,
    base_url: str,
    request_body: Any,
    parameters: Sequence[Any] | None,
    headers: dict[str, str],
    auth_scheme: str,
) -> str:
    """Generate JavaScript (fetch) code sample."""
    lines = []
    lines.append(f'const url = "{base_url}{_path_with_parameter_examples(path, parameters)}";')
    lines.append("")
    lines.append("const options = {")
    lines.append(f'  method: "{method}",')
    lines.append("  headers: {")
    lines.append(f'    "Authorization": `{auth_scheme} ${{API_KEY}}`,')

    if method in ("POST", "PUT", "PATCH"):
        lines.append('    "Content-Type": "application/json",')

    for key, value in headers.items():
        lines.append(f'    "{key}": "{value}",')

    lines.append("  },")

    # Request body
    if request_body and method in ("POST", "PUT", "PATCH"):
        body = _build_example_body(request_body)
        body_json = json.dumps(body, indent=4)
        lines.append(f"  body: JSON.stringify({body_json}),")

    lines.append("};")
    lines.append("")
    lines.append("const response = await fetch(url, options);")
    lines.append("const data = await response.json();")
    lines.append("console.log(data);")

    return "\n".join(lines)


def _generate_go_sample(
    method: str,
    path: str,
    base_url: str,
    request_body: Any,
    parameters: Sequence[Any] | None,
    headers: dict[str, str],
    auth_scheme: str,
) -> str:
    """Generate Go (net/http) code sample."""
    lines = ["package main", "", "import ("]
    if request_body and method in ("POST", "PUT", "PATCH"):
        lines.append('\t"bytes"')
    lines.append('\t"fmt"')
    lines.append('\t"io"')
    lines.append('\t"net/http"')
    lines.append('\t"os"')
    lines.append(")")
    lines.append("")
    lines.append("func main() {")
    lines.append(f'\turl := "{base_url}{_path_with_parameter_examples(path, parameters)}"')
    lines.append("")

    if request_body and method in ("POST", "PUT", "PATCH"):
        body = _build_example_body(request_body)
        body_json = json.dumps(body)
        lines.append(f"\tbody := []byte(`{body_json}`)")
        lines.append(f'\treq, err := http.NewRequest("{method}", url, bytes.NewBuffer(body))')
    else:
        lines.append(f'\treq, err := http.NewRequest("{method}", url, nil)')

    lines.append("\tif err != nil {")
    lines.append("\t\tpanic(err)")
    lines.append("\t}")
    lines.append("")
    lines.append(f'\treq.Header.Set("Authorization", "{auth_scheme} " + os.Getenv("API_KEY"))')

    if method in ("POST", "PUT", "PATCH"):
        lines.append('\treq.Header.Set("Content-Type", "application/json")')

    for key, value in headers.items():
        lines.append(f'\treq.Header.Set("{key}", "{value}")')

    lines.append("")
    lines.append("\tclient := &http.Client{}")
    lines.append("\tresp, err := client.Do(req)")
    lines.append("\tif err != nil {")
    lines.append("\t\tpanic(err)")
    lines.append("\t}")
    lines.append("\tdefer resp.Body.Close()")
    lines.append("")
    lines.append("\tbody, _ := io.ReadAll(resp.Body)")
    lines.append("\tfmt.Println(string(body))")
    lines.append("}")

    return "\n".join(lines)


def _generate_ruby_sample(
    method: str,
    path: str,
    base_url: str,
    request_body: Any,
    parameters: Sequence[Any] | None,
    headers: dict[str, str],
    auth_scheme: str,
) -> str:
    """Generate Ruby (Net::HTTP) code sample."""
    lines = [
        "require 'net/http'",
        "require 'json'",
        "require 'uri'",
        "",
        f'uri = URI("{base_url}{_path_with_parameter_examples(path, parameters)}")',
        "",
        "http = Net::HTTP.new(uri.host, uri.port)",
        "http.use_ssl = true",
        "",
    ]

    # Request class based on method
    method_class = {
        "GET": "Get",
        "POST": "Post",
        "PUT": "Put",
        "PATCH": "Patch",
        "DELETE": "Delete",
    }.get(method, "Get")

    lines.append(f"request = Net::HTTP::{method_class}.new(uri)")
    lines.append(f'request["Authorization"] = "{auth_scheme} #{{ENV[\'API_KEY\']}}"')

    if method in ("POST", "PUT", "PATCH"):
        lines.append('request["Content-Type"] = "application/json"')

    for key, value in headers.items():
        lines.append(f'request["{key}"] = "{value}"')

    if request_body and method in ("POST", "PUT", "PATCH"):
        body = _build_example_body(request_body)
        body_json = json.dumps(body, indent=2)
        lines.append("")
        lines.append(f"request.body = {body_json!r}")

    lines.append("")
    lines.append("response = http.request(request)")
    lines.append("puts JSON.parse(response.body)")

    return "\n".join(lines)


def _generate_php_sample(
    method: str,
    path: str,
    base_url: str,
    request_body: Any,
    parameters: Sequence[Any] | None,
    headers: dict[str, str],
    auth_scheme: str,
) -> str:
    """Generate PHP (Guzzle) code sample."""
    lines = [
        "<?php",
        "require 'vendor/autoload.php';",
        "",
        "use GuzzleHttp\\Client;",
        "",
        "$client = new Client();",
        "",
        f'$url = "{base_url}{_path_with_parameter_examples(path, parameters)}";',
        "",
        "$options = [",
        "    'headers' => [",
        f"        'Authorization' => '{auth_scheme} ' . getenv('API_KEY'),",
    ]

    if method in ("POST", "PUT", "PATCH"):
        lines.append("        'Content-Type' => 'application/json',")

    for key, value in headers.items():
        lines.append(f"        '{key}' => '{value}',")

    lines.append("    ],")

    if request_body and method in ("POST", "PUT", "PATCH"):
        body = _build_example_body(request_body)
        # Convert to PHP array syntax
        lines.append("    'json' => " + _dict_to_php_array(body) + ",")

    lines.append("];")
    lines.append("")
    lines.append(f"$response = $client->request('{method}', $url, $options);")
    lines.append("")
    lines.append("echo $response->getBody();")

    return "\n".join(lines)


def _dict_to_php_array(obj: Any, indent: int = 2) -> str:
    """Convert a Python dict to PHP array syntax."""
    if obj is None:
        return "null"
    if isinstance(obj, bool):
        return "true" if obj else "false"
    if isinstance(obj, str):
        return f"'{obj}'"
    if isinstance(obj, (int, float)):
        return str(obj)
    if isinstance(obj, list):
        items = [_dict_to_php_array(item, indent + 1) for item in obj]
        return "[" + ", ".join(items) + "]"
    if isinstance(obj, dict):
        items = [f"'{k}' => {_dict_to_php_array(v, indent + 1)}" for k, v in obj.items()]
        return "[" + ", ".join(items) + "]"
    return str(obj)


def _select_json_media(content: Mapping[str, Any]) -> Mapping[str, Any] | None:
    """Pick the most useful media object from an OpenAPI content map."""
    for content_type in ("application/json", "application/problem+json"):
        media = content.get(content_type)
        if isinstance(media, Mapping):
            return media
    for media in content.values():
        if isinstance(media, Mapping):
            return media
    return None


def _select_json_media_item(content: Any) -> tuple[str, Mapping[str, Any] | None]:
    """Pick the best media type and object from an OpenAPI content map."""
    if not isinstance(content, Mapping):
        return "application/json", None

    for content_type in ("application/json", "application/problem+json"):
        media = content.get(content_type)
        if isinstance(media, Mapping):
            return content_type, media
    for content_type, media in content.items():
        if isinstance(media, Mapping):
            return str(content_type), media
    return "application/json", None


def _parameter_example(param: Any) -> str:
    """Return a compact example value for an OpenAPI parameter."""
    explicit = _get_value(param, "example")
    if explicit is not None:
        return str(explicit)

    schema = _get_value(param, "schema", {}) or {}
    default = _get_value(schema, "default")
    if default is not None:
        return str(default)

    enum = _get_value(schema, "enum")
    if enum:
        return str(enum[0])

    schema_type = _get_value(param, "schema_type") or _get_value(schema, "type", "string")
    param_name = _get_value(param, "name", "value")
    if schema_type in ("integer", "number"):
        return "1"
    if schema_type == "boolean":
        return "true"
    if _get_value(schema, "format") == "email":
        return "user@example.com"
    if "id" in str(param_name).lower():
        return "id_123"
    return str(param_name)


def _path_with_parameter_examples(path: str, parameters: Sequence[Any] | None) -> str:
    """Substitute path params and append required query params for request samples."""
    if not parameters:
        return path

    rendered_path = path
    query_parts: list[str] = []
    for param in parameters:
        name = _get_value(param, "name")
        if not name:
            continue
        value = _parameter_example(param)
        location = _get_value(param, "location") or _get_value(param, "in")
        if location == "path":
            rendered_path = rendered_path.replace("{" + str(name) + "}", value)
        elif location == "query" and bool(_get_value(param, "required", False)):
            query_parts.append(f"{name}={value}")

    if not query_parts:
        return rendered_path

    separator = "&" if "?" in rendered_path else "?"
    return rendered_path + separator + "&".join(query_parts)


# =============================================================================
# Utility Functions
# =============================================================================


def highlight_path_params(path: str) -> str:
    """
    Highlight path parameters like {id} with HTML markup.

    Args:
        path: Endpoint path with {param} placeholders

    Returns:
        Path with highlighted parameters

    Example:
        {{ "/users/{id}/posts/{post_id}" | highlight_path_params }}
        # Returns: /users/<span class="api-path-param">{id}</span>/posts/<span class="api-path-param">{post_id}</span>

    """
    if not path:
        return ""

    def replace_param(match: re.Match) -> str:
        param = match.group(0)
        return f'<span class="api-path-param">{param}</span>'

    return re.sub(r"\{[^}]+\}", replace_param, path)


def method_color_class(method: str) -> str:
    """
    Get CSS class for HTTP method styling.

    Args:
        method: HTTP method (GET, POST, PUT, PATCH, DELETE, etc.)

    Returns:
        CSS class name

    Example:
        {{ "POST" | method_color_class }}  # "api-method--post"

    """
    method = (method or "GET").upper()
    return f"api-method--{method.lower()}"


def status_code_class(code: str | int) -> str:
    """
    Get CSS class for HTTP status code styling.

    Args:
        code: HTTP status code (200, 404, etc.)

    Returns:
        CSS class based on status category

    Example:
        {{ 200 | status_code_class }}  # "status--success"
        {{ 404 | status_code_class }}  # "status--client-error"

    """
    code_str = str(code)
    if not code_str:
        return "status--info"

    first_digit = code_str[0]
    categories = {
        "2": "status--success",
        "3": "status--redirect",
        "4": "status--client-error",
        "5": "status--server-error",
    }
    return categories.get(first_digit, "status--info")


def get_response_example(
    responses: Any,
    status_code: str = "200",
) -> Any:
    """
    Extract example response from OpenAPI responses.

    Args:
        responses: List or dict of response definitions
        status_code: Target status code (default "200")

    Returns:
        Example response object or None

    Example:
        {{ get_response_example(element.metadata.responses, "200") | tojson }}

    """
    if not responses:
        return None

    # Handle both raw OpenAPI response maps and typed response sequences.
    if isinstance(responses, Mapping):
        response = responses.get(status_code) or responses.get("200")
        if response is None:
            response = next(iter(responses.values()), None)
    elif isinstance(responses, Sequence) and not isinstance(responses, str | bytes):
        response = next(
            (r for r in responses if str(_get_value(r, "status_code")) == str(status_code)),
            None,
        )
        if response is None:
            response = next(iter(responses), None)
    else:
        response = None

    if not response:
        return None

    # Try to get example from content
    content = _get_value(response, "content", {})
    if isinstance(content, Mapping):
        for media_def in content.values():
            if not isinstance(media_def, Mapping):
                continue
            if "example" in media_def:
                return media_def["example"]
            if "examples" in media_def:
                examples = media_def["examples"]
                if examples:
                    first_example = next(iter(examples.values()), {})
                    if isinstance(first_example, Mapping):
                        return first_example.get("value")
                    return first_example

    # Try direct example
    example = _get_value(response, "example")
    if example is not None:
        return example

    return None

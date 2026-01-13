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
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from bengal.utils.logger import get_logger

logger = get_logger(__name__)

if TYPE_CHECKING:
    from bengal.autodoc.base import DocElement
    from bengal.autodoc.models.openapi import OpenAPIEndpointMetadata, OpenAPISchemaMetadata
    from bengal.core.page import Page
    from bengal.core.section import Section
    from bengal.core.site import Site
    from bengal.rendering.engines.protocol import TemplateEnvironment


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
        has_page: Whether an individual page exists
        operation_id: OpenAPI operationId (for advanced use)
        tags: Endpoint tags
        typed_metadata: Full OpenAPIEndpointMetadata (for advanced use)
        
    """

    method: str
    path: str
    summary: str
    description: str
    deprecated: bool
    href: str  # Always valid - never None
    has_page: bool
    operation_id: str | None
    tags: tuple[str, ...]
    typed_metadata: Any  # OpenAPIEndpointMetadata or None

    @classmethod
    def from_doc_element(cls, el: DocElement, consolidated: bool) -> EndpointView:
        """Create from DocElement (consolidated or individual mode)."""
        meta: OpenAPIEndpointMetadata = el.typed_metadata  # type: ignore[assignment]

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
            has_page=not consolidated,
            operation_id=meta.operation_id,
            tags=meta.tags or (),
            typed_metadata=meta,
        )

    @classmethod
    def from_page(cls, page: Page) -> EndpointView:
        """Create from Page (individual mode)."""
        meta = page.metadata
        return cls(
            method=meta.get("method", "GET"),
            path=meta.get("path", ""),
            summary=meta.get("summary", ""),
            description=meta.get("description", ""),
            deprecated=meta.get("deprecated", False),
            href=page.href or "#",
            has_page=True,
            operation_id=meta.get("operation_id"),
            tags=tuple(meta.get("tags", ())),
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
    typed_metadata: Any  # OpenAPISchemaMetadata or None

    @classmethod
    def from_doc_element(cls, el: DocElement, consolidated: bool = False) -> SchemaView:
        """Create from DocElement."""
        meta: OpenAPISchemaMetadata = el.typed_metadata  # type: ignore[assignment]

        # Smart href: anchor if no page, page URL otherwise
        if consolidated or not el.href:
            href = f"#schema-{el.name}"
            has_page = False
        else:
            href = el.href
            has_page = True

        return cls(
            name=el.name,
            schema_type=meta.schema_type or "object",
            description=el.description,
            href=href,
            has_page=has_page,
            properties=dict(meta.properties) if meta.properties else {},
            required=meta.required or (),
            enum=meta.enum,
            example=meta.example,
            typed_metadata=meta,
        )


def _generate_anchor_id(method: str, path: str) -> str:
    """Generate a URL-safe anchor ID from method and path."""
    # Remove leading/trailing slashes, replace path separators and braces
    sanitized = path.strip("/").replace("/", "-").replace("{", "").replace("}", "")
    return f"{method.lower()}-{sanitized}" if sanitized else method.lower()


# =============================================================================
# Filter Functions
# =============================================================================


def endpoints_filter(section: Section | None) -> list[EndpointView]:
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

    # Detect mode from data structure
    metadata = getattr(section, "metadata", None)
    if metadata is None:
        metadata = {}

    raw_endpoints = metadata.get("endpoints", [])

    if raw_endpoints:
        # Consolidated mode - DocElements stored in metadata.endpoints
        return [
            EndpointView.from_doc_element(el, consolidated=True)
            for el in raw_endpoints
            if hasattr(el, "typed_metadata") and el.typed_metadata is not None
        ]

    # Individual mode - Pages in section.pages
    pages = getattr(section, "pages", None) or []
    return [
        EndpointView.from_page(p)
        for p in pages
        if hasattr(p, "metadata")
        and (p.metadata.get("type") == "openapi_endpoint" or "method" in p.metadata)
    ]


def schemas_filter(section: Section | None) -> list[SchemaView]:
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


def register(env: TemplateEnvironment, site: Site) -> None:
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
        }
    )
    env.filters.update(
        {
            "highlight_path_params": highlight_path_params,
            "method_color_class": method_color_class,
            "status_code_class": status_code_class,
            "endpoints": endpoints_filter,
            "schemas": schemas_filter,
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
    request_body: dict[str, Any] | None = None,
    parameters: list[dict[str, Any]] | None = None,
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


def _build_example_body(request_body: dict[str, Any] | None) -> dict[str, Any]:
    """Build an example request body from schema."""
    if not request_body:
        return {}

    # If there's an explicit example, use it
    if "example" in request_body:
        return request_body["example"]

    # Try to build from schema
    schema = request_body.get("schema", request_body)
    return _schema_to_example(schema)


def _schema_to_example(schema: dict[str, Any]) -> Any:
    """Convert a JSON schema to an example value."""
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
    request_body: dict[str, Any] | None,
    parameters: list[dict[str, Any]] | None,
    headers: dict[str, str],
    auth_scheme: str,
) -> str:
    """Generate cURL code sample."""
    url = f"{base_url}{path}"
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
    request_body: dict[str, Any] | None,
    parameters: list[dict[str, Any]] | None,
    headers: dict[str, str],
    auth_scheme: str,
) -> str:
    """Generate Python (requests) code sample."""
    lines = ["import requests", ""]
    lines.append(f'url = "{base_url}{path}"')
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
    request_body: dict[str, Any] | None,
    parameters: list[dict[str, Any]] | None,
    headers: dict[str, str],
    auth_scheme: str,
) -> str:
    """Generate JavaScript (fetch) code sample."""
    lines = []
    lines.append(f'const url = "{base_url}{path}";')
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
    request_body: dict[str, Any] | None,
    parameters: list[dict[str, Any]] | None,
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
    lines.append(f'\turl := "{base_url}{path}"')
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
    request_body: dict[str, Any] | None,
    parameters: list[dict[str, Any]] | None,
    headers: dict[str, str],
    auth_scheme: str,
) -> str:
    """Generate Ruby (Net::HTTP) code sample."""
    lines = [
        "require 'net/http'",
        "require 'json'",
        "require 'uri'",
        "",
        f'uri = URI("{base_url}{path}")',
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
    request_body: dict[str, Any] | None,
    parameters: list[dict[str, Any]] | None,
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
        f'$url = "{base_url}{path}";',
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
    responses: list[dict[str, Any]] | dict[str, Any] | None,
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

    # Handle both list and dict formats
    if isinstance(responses, dict):
        response = responses.get(status_code, responses.get("200"))
    else:
        # List format
        response = next(
            (r for r in responses if str(r.get("status_code")) == str(status_code)),
            None,
        )

    if not response:
        return None

    # Try to get example from content
    content = response.get("content", {})
    if isinstance(content, dict):
        for _media_type, media_def in content.items():
            if "example" in media_def:
                return media_def["example"]
            if "examples" in media_def:
                examples = media_def["examples"]
                if examples:
                    first_example = next(iter(examples.values()), {})
                    return first_example.get("value")

    # Try direct example
    if "example" in response:
        return response["example"]

    return None

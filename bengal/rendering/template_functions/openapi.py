"""
OpenAPI template functions for REST API documentation.

Provides code sample generation, path highlighting, and status code utilities
for OpenAPI autodoc templates.

Functions:
    - generate_code_sample: Generate executable code samples in multiple languages
    - highlight_path_params: Highlight {param} placeholders in paths
    - method_color_class: Get CSS class for HTTP method
    - status_code_class: Get CSS class for status code
    - get_response_example: Extract example from response schema

Language Generators:
    - generate_curl_sample: cURL command
    - generate_python_sample: Python requests
    - generate_javascript_sample: JavaScript fetch
    - generate_go_sample: Go net/http
    - generate_ruby_sample: Ruby Net::HTTP
    - generate_php_sample: PHP Guzzle
"""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from jinja2 import Environment

    from bengal.autodoc.base import DocElement
    from bengal.autodoc.models.openapi import OpenAPIEndpointMetadata
    from bengal.core.site import Site


def register(env: Environment, site: Site) -> None:
    """Register OpenAPI template functions with Jinja2 environment."""
    env.filters.update(
        {
            "highlight_path_params": highlight_path_params,
            "method_color_class": method_color_class,
            "status_code_class": status_code_class,
        }
    )

    env.globals.update(
        {
            "generate_code_sample": generate_code_sample,
            "highlight_path_params": highlight_path_params,
            "method_color_class": method_color_class,
            "status_code_class": status_code_class,
            "get_response_example": get_response_example,
        }
    )


# =============================================================================
# PATH UTILITIES
# =============================================================================


def highlight_path_params(path: str) -> str:
    """
    Highlight path parameters in an API path.

    Converts {param} to <span class="api-path-param">{param}</span>.

    Args:
        path: API path like /users/{user_id}/posts/{post_id}

    Returns:
        HTML string with highlighted parameters

    Example:
        >>> highlight_path_params('/users/{id}')
        '/users/<span class="api-path-param">{id}</span>'
    """
    if not path:
        return path

    def replace_param(match: re.Match[str]) -> str:
        param = match.group(0)
        return f'<span class="api-path-param">{param}</span>'

    return re.sub(r"\{[^}]+\}", replace_param, path)


# =============================================================================
# CSS CLASS UTILITIES
# =============================================================================


def method_color_class(method: str) -> str:
    """
    Get CSS class for HTTP method color.

    Args:
        method: HTTP method (GET, POST, PUT, PATCH, DELETE, etc.)

    Returns:
        CSS class name like 'api-method--get'

    Example:
        >>> method_color_class('POST')
        'api-method--post'
    """
    method_lower = (method or "get").lower()
    valid_methods = {"get", "post", "put", "patch", "delete", "head", "options"}

    if method_lower in valid_methods:
        return f"api-method--{method_lower}"
    return "api-method"


def status_code_class(status_code: str | int) -> str:
    """
    Get CSS class for HTTP status code.

    Maps status codes to semantic colors:
        - 2xx: success (green)
        - 3xx: info (blue)
        - 4xx: warning (orange)
        - 5xx: danger (red)
        - default: outline

    Args:
        status_code: HTTP status code (200, '404', 'default', etc.)

    Returns:
        CSS class name like 'api-status--success'

    Example:
        >>> status_code_class(200)
        'api-status--success'
        >>> status_code_class('404')
        'api-status--warning'
    """
    code_str = str(status_code)

    if code_str == "default":
        return "api-status--default"

    status_map = {
        2: "api-status--success",
        3: "api-status--info",
        4: "api-status--warning",
        5: "api-status--danger",
    }

    try:
        code_int = int(code_str)
        category = code_int // 100
        return status_map.get(category, "api-status--default")
    except ValueError:
        return "api-status--default"


# =============================================================================
# CODE SAMPLE GENERATION
# =============================================================================


def generate_code_sample(
    element: DocElement,
    language: str,
    base_url: str = "https://api.example.com",
) -> str:
    """
    Generate an executable code sample for an API endpoint.

    Supports: curl, python, javascript, go, ruby, php

    Args:
        element: DocElement with OpenAPIEndpointMetadata
        language: Target language (curl, python, javascript, go, ruby, php)
        base_url: API base URL

    Returns:
        Formatted code sample string

    Example:
        >>> sample = generate_code_sample(endpoint_element, 'curl', 'https://api.example.com')
        >>> print(sample)
        curl -X GET "https://api.example.com/users" \\
          -H "Authorization: Bearer $API_KEY"
    """
    meta = getattr(element, "typed_metadata", None)
    if meta is None:
        return f"# No metadata available for {language} sample"

    generators = {
        "curl": _generate_curl,
        "python": _generate_python,
        "javascript": _generate_javascript,
        "go": _generate_go,
        "ruby": _generate_ruby,
        "php": _generate_php,
    }

    generator = generators.get(language.lower())
    if generator is None:
        return f"# Unsupported language: {language}"

    return generator(meta, base_url)


def _generate_curl(meta: OpenAPIEndpointMetadata, base_url: str) -> str:
    """Generate cURL command."""
    method = meta.method or "GET"
    path = meta.path or "/"
    url = f"{base_url.rstrip('/')}{path}"

    lines = [f'curl -X {method} "{url}"']

    # Add authorization header if security is required
    if meta.security:
        lines.append('  -H "Authorization: Bearer $API_KEY"')

    # Add content-type for methods with body
    if meta.request_body and method in ("POST", "PUT", "PATCH"):
        content_type = meta.request_body.content_type or "application/json"
        lines.append(f'  -H "Content-Type: {content_type}"')
        lines.append("  -d '$REQUEST_BODY'")

    return " \\\n".join(lines)


def _generate_python(meta: OpenAPIEndpointMetadata, base_url: str) -> str:
    """Generate Python requests code."""
    method = (meta.method or "GET").lower()
    path = meta.path or "/"
    url = f"{base_url.rstrip('/')}{path}"

    lines = [
        "import requests",
        "",
        f'url = "{url}"',
    ]

    # Headers
    headers = {}
    if meta.security:
        headers["Authorization"] = "Bearer $API_KEY"
    if meta.request_body and method in ("post", "put", "patch"):
        headers["Content-Type"] = meta.request_body.content_type or "application/json"

    if headers:
        lines.append(f"headers = {json.dumps(headers, indent=2)}")
    else:
        lines.append("headers = {}")

    # Request body
    if meta.request_body and method in ("post", "put", "patch"):
        lines.append("")
        lines.append("data = {")
        lines.append("    # Add your request data here")
        lines.append("}")
        lines.append("")
        lines.append(f"response = requests.{method}(url, headers=headers, json=data)")
    else:
        lines.append("")
        lines.append(f"response = requests.{method}(url, headers=headers)")

    lines.append("print(response.json())")

    return "\n".join(lines)


def _generate_javascript(meta: OpenAPIEndpointMetadata, base_url: str) -> str:
    """Generate JavaScript fetch code."""
    method = meta.method or "GET"
    path = meta.path or "/"
    url = f"{base_url.rstrip('/')}{path}"

    lines = [
        f'const response = await fetch("{url}", {{',
        f'  method: "{method}",',
        "  headers: {",
    ]

    # Headers
    if meta.security:
        lines.append('    "Authorization": "Bearer $API_KEY",')
    if meta.request_body and method in ("POST", "PUT", "PATCH"):
        content_type = meta.request_body.content_type or "application/json"
        lines.append(f'    "Content-Type": "{content_type}",')

    lines.append("  },")

    # Request body
    if meta.request_body and method in ("POST", "PUT", "PATCH"):
        lines.append("  body: JSON.stringify({")
        lines.append("    // Add your request data here")
        lines.append("  }),")

    lines.append("});")
    lines.append("")
    lines.append("const data = await response.json();")
    lines.append("console.log(data);")

    return "\n".join(lines)


def _generate_go(meta: OpenAPIEndpointMetadata, base_url: str) -> str:
    """Generate Go net/http code."""
    method = meta.method or "GET"
    path = meta.path or "/"
    url = f"{base_url.rstrip('/')}{path}"

    lines = [
        "package main",
        "",
        "import (",
        '    "fmt"',
        '    "io"',
        '    "net/http"',
    ]

    if meta.request_body and method in ("POST", "PUT", "PATCH"):
        lines.append('    "strings"')

    lines.extend(
        [
            ")",
            "",
            "func main() {",
        ]
    )

    # Request body
    if meta.request_body and method in ("POST", "PUT", "PATCH"):
        lines.append('    body := strings.NewReader(`{"key": "value"}`)')
        lines.append(f'    req, err := http.NewRequest("{method}", "{url}", body)')
    else:
        lines.append(f'    req, err := http.NewRequest("{method}", "{url}", nil)')

    lines.extend(
        [
            "    if err != nil {",
            "        panic(err)",
            "    }",
            "",
        ]
    )

    # Headers
    if meta.security:
        lines.append('    req.Header.Set("Authorization", "Bearer $API_KEY")')
    if meta.request_body and method in ("POST", "PUT", "PATCH"):
        content_type = meta.request_body.content_type or "application/json"
        lines.append(f'    req.Header.Set("Content-Type", "{content_type}")')

    lines.extend(
        [
            "",
            "    client := &http.Client{}",
            "    resp, err := client.Do(req)",
            "    if err != nil {",
            "        panic(err)",
            "    }",
            "    defer resp.Body.Close()",
            "",
            "    respBody, _ := io.ReadAll(resp.Body)",
            "    fmt.Println(string(respBody))",
            "}",
        ]
    )

    return "\n".join(lines)


def _generate_ruby(meta: OpenAPIEndpointMetadata, base_url: str) -> str:
    """Generate Ruby Net::HTTP code."""
    method = meta.method or "GET"
    path = meta.path or "/"
    url = f"{base_url.rstrip('/')}{path}"

    lines = [
        "require 'net/http'",
        "require 'json'",
        "",
        f'uri = URI("{url}")',
        "",
    ]

    # Request type
    if method == "GET":
        lines.append("request = Net::HTTP::Get.new(uri)")
    elif method == "POST":
        lines.append("request = Net::HTTP::Post.new(uri)")
    elif method == "PUT":
        lines.append("request = Net::HTTP::Put.new(uri)")
    elif method == "PATCH":
        lines.append("request = Net::HTTP::Patch.new(uri)")
    elif method == "DELETE":
        lines.append("request = Net::HTTP::Delete.new(uri)")
    else:
        lines.append(f"request = Net::HTTP::Get.new(uri)  # {method}")

    # Headers
    if meta.security:
        lines.append('request["Authorization"] = "Bearer $API_KEY"')
    if meta.request_body and method in ("POST", "PUT", "PATCH"):
        content_type = meta.request_body.content_type or "application/json"
        lines.append(f'request["Content-Type"] = "{content_type}"')
        lines.append('request.body = { key: "value" }.to_json')

    lines.extend(
        [
            "",
            "response = Net::HTTP.start(uri.hostname, uri.port, use_ssl: true) do |http|",
            "  http.request(request)",
            "end",
            "",
            "puts JSON.parse(response.body)",
        ]
    )

    return "\n".join(lines)


def _generate_php(meta: OpenAPIEndpointMetadata, base_url: str) -> str:
    """Generate PHP Guzzle code."""
    method = (meta.method or "GET").lower()
    path = meta.path or "/"
    url = f"{base_url.rstrip('/')}{path}"

    lines = [
        "<?php",
        "require 'vendor/autoload.php';",
        "",
        "use GuzzleHttp\\Client;",
        "",
        "$client = new Client();",
        "",
        f"$response = $client->{method}('{url}', [",
        "    'headers' => [",
    ]

    # Headers
    if meta.security:
        lines.append("        'Authorization' => 'Bearer $API_KEY',")
    if meta.request_body and method in ("post", "put", "patch"):
        content_type = meta.request_body.content_type or "application/json"
        lines.append(f"        'Content-Type' => '{content_type}',")

    lines.append("    ],")

    # Request body
    if meta.request_body and method in ("post", "put", "patch"):
        lines.extend(
            [
                "    'json' => [",
                "        // Add your request data here",
                "    ],",
            ]
        )

    lines.extend(
        [
            "]);",
            "",
            "$data = json_decode($response->getBody(), true);",
            "print_r($data);",
        ]
    )

    return "\n".join(lines)


# =============================================================================
# RESPONSE UTILITIES
# =============================================================================


def get_response_example(response: Any, schemas: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    Extract example from response schema.

    Args:
        response: OpenAPIResponseMetadata or dict
        schemas: Resolved schemas dict (optional)

    Returns:
        Example object or placeholder dict

    Example:
        >>> example = get_response_example(response_200)
        >>> print(json.dumps(example, indent=2))
    """
    if response is None:
        return {"message": "Response example not available"}

    # Check for direct example
    if hasattr(response, "example") and response.example:
        return response.example

    # Check for schema_ref and try to get schema example
    schema_ref = getattr(response, "schema_ref", None)
    if schema_ref and schemas:
        schema_name = schema_ref.split("/")[-1]
        schema = schemas.get(schema_name, {})
        if "example" in schema:
            return schema["example"]
        # Generate placeholder from properties
        if "properties" in schema:
            return _generate_example_from_properties(schema["properties"])

    return {"message": "Success", "data": {}}


def _generate_example_from_properties(properties: dict[str, Any]) -> dict[str, Any]:
    """Generate example values from schema properties."""
    example = {}
    type_examples = {
        "string": "string",
        "integer": 0,
        "number": 0.0,
        "boolean": True,
        "array": [],
        "object": {},
    }

    for name, prop in properties.items():
        prop_type = prop.get("type", "string")
        if "example" in prop:
            example[name] = prop["example"]
        elif "default" in prop:
            example[name] = prop["default"]
        else:
            example[name] = type_examples.get(prop_type)

    return example

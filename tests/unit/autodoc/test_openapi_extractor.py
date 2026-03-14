"""
Tests for OpenAPI documentation extractor.

Covers OpenAPI 3.0/3.1 specs, $ref resolution, allOf merging, and error paths.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from bengal.autodoc.extractors.openapi import OpenAPIExtractor
from bengal.errors import BengalContentError, BengalDiscoveryError

# --- Fixtures ---

OPENAPI_30_MINIMAL = """
openapi: 3.0.0
info:
  title: Minimal API
  version: "1.0.0"
paths:
  /health:
    get:
      summary: Health check
      responses:
        "200":
          description: OK
"""

OPENAPI_31_MINIMAL = """
openapi: 3.1.0
info:
  title: Minimal API 3.1
  version: "2.0.0"
paths:
  /status:
    get:
      summary: Status check
      responses:
        "200":
          description: OK
"""

OPENAPI_WITH_REF = """
openapi: 3.1.0
info:
  title: API with $ref
  version: "1.0.0"
paths:
  /users:
    get:
      tags: [users]
      summary: List users
      responses:
        "200":
          description: ok
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/User"
components:
  schemas:
    User:
      type: object
      properties:
        id:
          type: string
        email:
          type: string
      required: [id]
"""

OPENAPI_WITH_ALLOF = """
openapi: 3.1.0
info:
  title: API with allOf
  version: "1.0.0"
components:
  schemas:
    Base:
      type: object
      properties:
        id:
          type: string
    Extended:
      allOf:
        - $ref: "#/components/schemas/Base"
        - type: object
          properties:
            name:
              type: string
      required: [id, name]
"""

OPENAPI_WITH_PARAM_REF = """
openapi: 3.1.0
info:
  title: API with parameter $ref
  version: "1.0.0"
paths:
  /users/{id}:
    parameters:
      - $ref: "#/components/parameters/UserId"
    get:
      summary: Get user
      responses:
        "200":
          description: OK
components:
  parameters:
    UserId:
      name: id
      in: path
      required: true
      schema:
        type: string
"""


# --- Basic extraction ---


def test_extract_openapi_30_minimal(tmp_path: Path) -> None:
    """Extract from OpenAPI 3.0 minimal spec."""
    spec_path = tmp_path / "openapi.yaml"
    spec_path.write_text(OPENAPI_30_MINIMAL, encoding="utf-8")

    extractor = OpenAPIExtractor()
    elements = extractor.extract(spec_path)

    overview = next(e for e in elements if e.element_type == "openapi_overview")
    assert overview.name == "Minimal API"
    assert overview.metadata.get("version") == "1.0.0"

    endpoints = [e for e in elements if e.element_type == "openapi_endpoint"]
    assert len(endpoints) == 1
    assert "GET /health" in endpoints[0].name
    assert endpoints[0].metadata.get("summary") == "Health check"


def test_extract_openapi_31_minimal(tmp_path: Path) -> None:
    """Extract from OpenAPI 3.1 minimal spec."""
    spec_path = tmp_path / "openapi.yaml"
    spec_path.write_text(OPENAPI_31_MINIMAL, encoding="utf-8")

    extractor = OpenAPIExtractor()
    elements = extractor.extract(spec_path)

    overview = next(e for e in elements if e.element_type == "openapi_overview")
    assert overview.name == "Minimal API 3.1"

    endpoints = [e for e in elements if e.element_type == "openapi_endpoint"]
    assert len(endpoints) == 1
    assert "GET /status" in endpoints[0].name


def test_extract_json_spec(tmp_path: Path) -> None:
    """Extract from JSON OpenAPI spec."""
    import json

    spec_path = tmp_path / "openapi.json"
    spec = {
        "openapi": "3.1.0",
        "info": {"title": "JSON API", "version": "1.0.0"},
        "paths": {
            "/items": {
                "get": {
                    "summary": "List items",
                    "responses": {"200": {"description": "OK"}},
                }
            }
        },
    }
    spec_path.write_text(json.dumps(spec), encoding="utf-8")

    extractor = OpenAPIExtractor()
    elements = extractor.extract(spec_path)

    overview = next(e for e in elements if e.element_type == "openapi_overview")
    assert overview.name == "JSON API"

    endpoints = [e for e in elements if e.element_type == "openapi_endpoint"]
    assert len(endpoints) == 1
    assert "GET /items" in endpoints[0].name


# --- $ref resolution ---


def test_extract_schemas_with_ref(tmp_path: Path) -> None:
    """Schemas with $ref in response are resolved."""
    spec_path = tmp_path / "openapi.yaml"
    spec_path.write_text(OPENAPI_WITH_REF, encoding="utf-8")

    extractor = OpenAPIExtractor()
    elements = extractor.extract(spec_path)

    schemas = [e for e in elements if e.element_type == "openapi_schema"]
    assert len(schemas) == 1
    assert schemas[0].name == "User"
    props = schemas[0].metadata.get("properties", {})
    assert "id" in props
    assert "email" in props
    assert "id" in schemas[0].metadata.get("required", [])


def test_extract_schemas_with_allof(tmp_path: Path) -> None:
    """allOf schemas merge properties from subschemas."""
    spec_path = tmp_path / "openapi.yaml"
    spec_path.write_text(OPENAPI_WITH_ALLOF, encoding="utf-8")

    extractor = OpenAPIExtractor()
    elements = extractor.extract(spec_path)

    schemas = [e for e in elements if e.element_type == "openapi_schema"]
    assert len(schemas) == 2  # Base and Extended

    extended = next(s for s in schemas if s.name == "Extended")
    props = extended.metadata.get("properties", {})
    assert "id" in props
    assert "name" in props
    # allOf merges properties; required may come from raw_schema or merged result
    assert extended.metadata.get("raw_schema", {}).get("required") == ["id", "name"]


def test_extract_endpoint_with_request_body_ref(tmp_path: Path) -> None:
    """Request body with $ref schema is extracted."""
    spec_path = tmp_path / "openapi.yaml"
    spec_path.write_text(
        """
openapi: 3.1.0
info:
  title: API
  version: "1.0.0"
paths:
  /users:
    post:
      summary: Create user
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: "#/components/schemas/User"
      responses:
        "201":
          description: Created
components:
  schemas:
    User:
      type: object
      required: [email]
      properties:
        email:
          type: string
""",
        encoding="utf-8",
    )

    extractor = OpenAPIExtractor()
    elements = extractor.extract(spec_path)
    endpoint = next(e for e in elements if e.element_type == "openapi_endpoint")
    req_body = endpoint.metadata.get("request_body")
    assert req_body is not None
    assert req_body.get("required") is True


def test_extract_endpoints_with_param_ref(tmp_path: Path) -> None:
    """Path-level parameter $ref is resolved."""
    spec_path = tmp_path / "openapi.yaml"
    spec_path.write_text(OPENAPI_WITH_PARAM_REF, encoding="utf-8")

    extractor = OpenAPIExtractor()
    elements = extractor.extract(spec_path)

    endpoints = [e for e in elements if e.element_type == "openapi_endpoint"]
    assert len(endpoints) == 1
    params = endpoints[0].metadata.get("parameters", [])
    assert len(params) >= 1
    param_names = [p.get("name") for p in params if isinstance(p, dict)]
    assert "id" in param_names


# --- get_output_path ---


def test_get_output_path_overview(tmp_path: Path) -> None:
    """Overview element returns index.md."""
    spec_path = tmp_path / "openapi.yaml"
    spec_path.write_text(OPENAPI_30_MINIMAL, encoding="utf-8")

    extractor = OpenAPIExtractor()
    elements = extractor.extract(spec_path)
    overview = next(e for e in elements if e.element_type == "openapi_overview")

    path = extractor.get_output_path(overview)
    assert path == Path("index.md")


def test_get_output_path_endpoint(tmp_path: Path) -> None:
    """Endpoint element returns endpoints/{tag}/{name}.md."""
    spec_path = tmp_path / "openapi.yaml"
    spec_path.write_text(OPENAPI_WITH_REF, encoding="utf-8")

    extractor = OpenAPIExtractor()
    elements = extractor.extract(spec_path)
    endpoint = next(e for e in elements if e.element_type == "openapi_endpoint")

    path = extractor.get_output_path(endpoint)
    assert path is not None
    assert "endpoints" in str(path)
    assert path.suffix == ".md"


def test_get_output_path_schema(tmp_path: Path) -> None:
    """Schema element returns schemas/{name}.md."""
    spec_path = tmp_path / "openapi.yaml"
    spec_path.write_text(OPENAPI_WITH_REF, encoding="utf-8")

    extractor = OpenAPIExtractor()
    elements = extractor.extract(spec_path)
    schema = next(e for e in elements if e.element_type == "openapi_schema")

    path = extractor.get_output_path(schema)
    assert path == Path("schemas/User.md")


# --- Error paths ---


def test_extract_missing_file_raises(tmp_path: Path) -> None:
    """Missing spec file raises BengalDiscoveryError."""
    missing_path = tmp_path / "nonexistent.yaml"
    assert not missing_path.exists()

    extractor = OpenAPIExtractor()
    with pytest.raises(BengalDiscoveryError) as exc_info:
        extractor.extract(missing_path)

    assert "not found" in str(exc_info.value).lower()
    assert exc_info.value.file_path == missing_path


def test_extract_malformed_yaml_raises(tmp_path: Path) -> None:
    """Malformed YAML raises BengalContentError."""
    spec_path = tmp_path / "openapi.yaml"
    spec_path.write_text("invalid: yaml: [unclosed", encoding="utf-8")

    extractor = OpenAPIExtractor()
    with pytest.raises(BengalContentError) as exc_info:
        extractor.extract(spec_path)

    assert "YAML" in str(exc_info.value) or "parse" in str(exc_info.value).lower()
    assert exc_info.value.file_path == spec_path


def test_extract_malformed_json_raises(tmp_path: Path) -> None:
    """Malformed JSON raises BengalContentError."""
    spec_path = tmp_path / "openapi.json"
    spec_path.write_text("{ invalid json }", encoding="utf-8")

    extractor = OpenAPIExtractor()
    with pytest.raises(BengalContentError) as exc_info:
        extractor.extract(spec_path)

    assert "JSON" in str(exc_info.value) or "parse" in str(exc_info.value).lower()
    assert exc_info.value.file_path == spec_path


# --- Overview metadata ---


def test_extract_overview_with_servers(tmp_path: Path) -> None:
    """Overview extracts server URLs."""
    spec_path = tmp_path / "openapi.yaml"
    spec_path.write_text(
        """
openapi: 3.1.0
info:
  title: API
  version: "1.0.0"
servers:
  - url: https://api.example.com
  - url: https://staging.example.com
paths: {}
""",
        encoding="utf-8",
    )

    extractor = OpenAPIExtractor()
    elements = extractor.extract(spec_path)
    overview = next(e for e in elements if e.element_type == "openapi_overview")

    servers = overview.metadata.get("servers", [])
    assert len(servers) == 2
    urls = [s.get("url") for s in servers if isinstance(s, dict)]
    assert "https://api.example.com" in urls
    assert "https://staging.example.com" in urls


def test_extract_overview_with_tags(tmp_path: Path) -> None:
    """Overview extracts tags."""
    spec_path = tmp_path / "openapi.yaml"
    spec_path.write_text(
        """
openapi: 3.1.0
info:
  title: API
  version: "1.0.0"
tags:
  - name: users
    description: User operations
  - name: items
paths: {}
""",
        encoding="utf-8",
    )

    extractor = OpenAPIExtractor()
    elements = extractor.extract(spec_path)
    overview = next(e for e in elements if e.element_type == "openapi_overview")

    tags = overview.metadata.get("tags", [])
    assert len(tags) >= 1
    tag_names = [t.get("name") for t in tags if isinstance(t, dict)]
    assert "users" in tag_names


# --- External $ref (graceful fallback) ---


def test_external_ref_returns_unresolved(tmp_path: Path) -> None:
    """External $ref in parameters logs warning and returns ref as-is (no crash)."""
    spec_path = tmp_path / "openapi.yaml"
    spec_path.write_text(
        """
openapi: 3.1.0
info:
  title: API
  version: "1.0.0"
paths:
  /items:
    get:
      summary: List
      parameters:
        - $ref: "https://example.com/params/Limit.json"
      responses:
        "200":
          description: OK
components:
  parameters:
    Limit:
      name: limit
      in: query
      schema:
        type: integer
""",
        encoding="utf-8",
    )

    extractor = OpenAPIExtractor()
    elements = extractor.extract(spec_path)
    # Should not crash; external ref is logged and left unresolved
    assert len(elements) >= 1
    overview = next(e for e in elements if e.element_type == "openapi_overview")
    assert overview.name == "API"


# --- Deprecated operations ---


def test_extract_deprecated_endpoint(tmp_path: Path) -> None:
    """Deprecated operations have deprecated metadata."""
    spec_path = tmp_path / "openapi.yaml"
    spec_path.write_text(
        """
openapi: 3.1.0
info:
  title: API
  version: "1.0.0"
paths:
  /legacy:
    get:
      deprecated: true
      summary: Deprecated endpoint
      responses:
        "200":
          description: OK
""",
        encoding="utf-8",
    )

    extractor = OpenAPIExtractor()
    elements = extractor.extract(spec_path)
    endpoint = next(e for e in elements if e.element_type == "openapi_endpoint")

    assert endpoint.deprecated is not None
    assert "deprecated" in endpoint.deprecated.lower()
    assert endpoint.metadata.get("deprecated") is True

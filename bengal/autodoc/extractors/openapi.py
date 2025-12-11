"""
OpenAPI documentation extractor.

Extracts documentation from OpenAPI 3.0/3.1 specifications.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import yaml

from bengal.autodoc.base import DocElement, Extractor
from bengal.autodoc.models import (
    OpenAPIEndpointMetadata,
    OpenAPIOverviewMetadata,
    OpenAPISchemaMetadata,
)
from bengal.autodoc.models.openapi import (
    OpenAPIParameterMetadata,
    OpenAPIRequestBodyMetadata,
    OpenAPIResponseMetadata,
)
from bengal.autodoc.utils import (
    get_openapi_method,
    get_openapi_operation_id,
    get_openapi_path,
    get_openapi_tags,
)

logger = logging.getLogger(__name__)


class OpenAPIExtractor(Extractor):
    """
    Extracts documentation from OpenAPI specifications.

    Supports OpenAPI 3.0 and 3.1 (YAML or JSON).
    """

    def __init__(self) -> None:
        """Initialize the extractor."""
        self._spec: dict[str, Any] = {}

    def _resolve_ref(self, ref_or_obj: dict[str, Any]) -> dict[str, Any]:
        """
        Resolve a $ref reference to its actual definition.

        Args:
            ref_or_obj: Either a dict with $ref key, or a regular object

        Returns:
            Resolved object with actual properties
        """
        if not isinstance(ref_or_obj, dict):
            return ref_or_obj

        if "$ref" not in ref_or_obj:
            return ref_or_obj

        ref_path = ref_or_obj["$ref"]
        if not ref_path.startswith("#/"):
            # External references not supported
            logger.warning(f"External $ref not supported: {ref_path}")
            return ref_or_obj

        # Parse the JSON pointer (e.g., "#/components/parameters/UserId")
        parts = ref_path[2:].split("/")  # Remove "#/" and split
        result = self._spec
        for part in parts:
            if isinstance(result, dict) and part in result:
                result = result[part]
            else:
                logger.warning(f"Could not resolve $ref: {ref_path}")
                return ref_or_obj

        return result if isinstance(result, dict) else ref_or_obj

    def extract(self, source: Path) -> list[DocElement]:
        """
        Extract documentation elements from OpenAPI spec file.

        Args:
            source: Path to openapi.yaml or openapi.json

        Returns:
            List of DocElement objects
        """
        if not source.exists():
            logger.warning(f"OpenAPI spec not found: {source}")
            return []

        try:
            content = source.read_text(encoding="utf-8")
            if source.suffix in (".yaml", ".yml"):
                spec = yaml.safe_load(content)
            else:
                spec = json.loads(content)
        except Exception as e:
            logger.error(f"Failed to parse OpenAPI spec {source}: {e}")
            return []

        # Store spec for $ref resolution
        self._spec = spec

        elements: list[DocElement] = []

        # 1. Create API Overview Element
        # This serves as the entry point and contains info object
        overview = self._extract_overview(spec, source)
        elements.append(overview)

        # 2. Extract Endpoints (Paths)
        endpoints = self._extract_endpoints(spec)
        elements.extend(endpoints)

        # 3. Extract Schemas (Components)
        schemas = self._extract_schemas(spec)
        elements.extend(schemas)

        return elements

    def get_output_path(self, element: DocElement) -> Path | None:
        """
        Determine output path for OpenAPI elements.

        Structure:
        - Overview: index.md
        - Endpoints: endpoints/{tag}/{operation_id}.md
        - Schemas: schemas/{name}.md
        """
        if element.element_type == "openapi_overview":
            return Path("index.md")

        elif element.element_type == "openapi_endpoint":
            # Group by first tag if available, else 'default'
            tags = get_openapi_tags(element)
            tag = tags[0] if tags else "default"

            # Use operationId if available, else sanitized path
            name = element.name.replace(" ", "_").lower()
            operation_id = get_openapi_operation_id(element)
            if operation_id:
                name = operation_id
            else:
                # Fallback: GET /users -> get_users
                method = get_openapi_method(element) or "op"
                path = get_openapi_path(element).strip("/") or "path"
                name = f"{method}_{path}".replace("/", "_").replace("{", "").replace("}", "")

            return Path(f"endpoints/{tag}/{name}.md")

        elif element.element_type == "openapi_schema":
            return Path(f"schemas/{element.name}.md")

        return None

    def _extract_overview(self, spec: dict[str, Any], source: Path) -> DocElement:
        """Extract API overview information."""
        info = spec.get("info", {})

        # Extract server URLs as strings
        servers = spec.get("servers", [])
        server_urls = tuple(s.get("url", "") for s in servers if isinstance(s, dict))

        # Build typed metadata
        typed_meta = OpenAPIOverviewMetadata(
            version=info.get("version"),
            servers=server_urls,
            security_schemes=spec.get("components", {}).get("securitySchemes", {}),
            tags=tuple(spec.get("tags", [])),
        )

        return DocElement(
            name=info.get("title", "API Documentation"),
            qualified_name="openapi.overview",
            description=info.get("description", ""),
            element_type="openapi_overview",
            source_file=source,
            metadata={
                "version": info.get("version"),
                "servers": spec.get("servers", []),
                "security_schemes": spec.get("components", {}).get("securitySchemes", {}),
                "tags": spec.get("tags", []),
            },
            typed_metadata=typed_meta,
        )

    def _extract_endpoints(self, spec: dict[str, Any]) -> list[DocElement]:
        """Extract all path operations."""
        elements = []
        paths = spec.get("paths", {})

        for path, path_item in paths.items():
            # Handle common parameters at path level (resolve $refs)
            path_params = [self._resolve_ref(p) for p in path_item.get("parameters", [])]

            for method in ["get", "post", "put", "delete", "patch", "head", "options"]:
                if method not in path_item:
                    continue

                operation = path_item[method]

                # Merge path-level parameters with operation-level parameters (resolve $refs)
                op_params = [self._resolve_ref(p) for p in operation.get("parameters", [])]
                all_params = path_params + op_params

                # Construct name like "GET /users"
                name = f"{method.upper()} {path}"

                # Build typed parameters
                typed_params = tuple(
                    OpenAPIParameterMetadata(
                        name=p.get("name", ""),
                        location=p.get("in", "query"),
                        required=p.get("required", False),
                        schema_type=p.get("schema", {}).get("type", "string"),
                        description=p.get("description", ""),
                    )
                    for p in all_params
                )

                # Build typed request body (resolve $ref if present)
                typed_request_body = None
                req_body = operation.get("requestBody")
                if req_body:
                    req_body = self._resolve_ref(req_body)
                    content = req_body.get("content", {})
                    content_type = next(iter(content.keys()), "application/json")
                    schema_ref = content.get(content_type, {}).get("schema", {}).get("$ref")
                    typed_request_body = OpenAPIRequestBodyMetadata(
                        content_type=content_type,
                        schema_ref=schema_ref,
                        required=req_body.get("required", False),
                        description=req_body.get("description", ""),
                    )

                # Build typed responses (resolve $refs)
                raw_responses = operation.get("responses") or {}
                resolved_responses = {
                    status: self._resolve_ref(resp) for status, resp in raw_responses.items()
                }
                typed_responses = tuple(
                    OpenAPIResponseMetadata(
                        status_code=str(status),
                        description=resp.get("description", "") if isinstance(resp, dict) else "",
                        content_type=next(iter(resp.get("content", {}).keys()), None)
                        if isinstance(resp, dict)
                        else None,
                        schema_ref=(
                            resp.get("content", {})
                            .get(next(iter(resp.get("content", {}).keys()), ""), {})
                            .get("schema", {})
                            .get("$ref")
                            if isinstance(resp, dict)
                            else None
                        ),
                    )
                    for status, resp in resolved_responses.items()
                )

                # Build typed metadata
                typed_meta = OpenAPIEndpointMetadata(
                    method=method.upper(),  # type: ignore[arg-type]
                    path=path,
                    operation_id=operation.get("operationId"),
                    summary=operation.get("summary"),
                    tags=tuple(operation.get("tags", [])),
                    parameters=typed_params,
                    request_body=typed_request_body,
                    responses=typed_responses,
                    security=tuple(
                        next(iter(s.keys()), "") for s in (operation.get("security") or [])
                    ),
                    deprecated=operation.get("deprecated", False),
                )

                element = DocElement(
                    name=name,
                    qualified_name=f"openapi.paths.{path}.{method}",
                    description=operation.get("description") or operation.get("summary", ""),
                    element_type="openapi_endpoint",
                    metadata={
                        "method": method,
                        "path": path,
                        "summary": operation.get("summary"),
                        "operation_id": operation.get("operationId"),
                        "tags": operation.get("tags", []),
                        "parameters": all_params,  # Already resolved above
                        "request_body": req_body if req_body else None,  # Use resolved request body
                        "responses": resolved_responses,  # Use resolved responses
                        "security": operation.get("security"),
                        "deprecated": operation.get("deprecated", False),
                    },
                    typed_metadata=typed_meta,
                    examples=[],  # Could extract examples from openapi spec
                    deprecated="Deprecated in API spec" if operation.get("deprecated") else None,
                )
                elements.append(element)

        return elements

    def _extract_schemas(self, spec: dict[str, Any]) -> list[DocElement]:
        """Extract component schemas."""
        elements = []
        components = spec.get("components", {})
        schemas = components.get("schemas", {})

        for name, schema in schemas.items():
            # Build typed metadata
            typed_meta = OpenAPISchemaMetadata(
                schema_type=schema.get("type"),
                properties=schema.get("properties", {}),
                required=tuple(schema.get("required", [])),
                enum=tuple(schema.get("enum", [])) if schema.get("enum") else None,
                example=schema.get("example"),
            )

            element = DocElement(
                name=name,
                qualified_name=f"openapi.components.schemas.{name}",
                description=schema.get("description", ""),
                element_type="openapi_schema",
                metadata={
                    "type": schema.get("type"),
                    "properties": schema.get("properties", {}),
                    "required": schema.get("required", []),
                    "enum": schema.get("enum"),
                    "example": schema.get("example"),
                    "raw_schema": schema,  # Keep full schema for complex rendering
                },
                typed_metadata=typed_meta,
            )
            elements.append(element)

        return elements

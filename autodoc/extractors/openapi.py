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

logger = logging.getLogger(__name__)


class OpenAPIExtractor(Extractor):
    """
    Extracts documentation from OpenAPI specifications.
    
    Supports OpenAPI 3.0 and 3.1 (YAML or JSON).
    """

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
        if element.element_type == "api_overview":
            return Path("index.md")
        
        elif element.element_type == "endpoint":
            # Group by first tag if available, else 'default'
            tag = "default"
            if element.metadata.get("tags"):
                tag = element.metadata["tags"][0]
            
            # Use operationId if available, else sanitized path
            name = element.name.replace(" ", "_").lower()
            if element.metadata.get("operation_id"):
                name = element.metadata["operation_id"]
            else:
                # Fallback: GET /users -> get_users
                method = element.metadata.get("method", "op")
                path = element.metadata.get("path", "path").strip("/")
                name = f"{method}_{path}".replace("/", "_").replace("{", "").replace("}", "")
            
            return Path(f"endpoints/{tag}/{name}.md")
            
        elif element.element_type == "schema":
            return Path(f"schemas/{element.name}.md")
            
        return None

    def _extract_overview(self, spec: dict[str, Any], source: Path) -> DocElement:
        """Extract API overview information."""
        info = spec.get("info", {})
        
        return DocElement(
            name=info.get("title", "API Documentation"),
            qualified_name="openapi.overview",
            description=info.get("description", ""),
            element_type="api_overview",
            source_file=source,
            metadata={
                "version": info.get("version"),
                "servers": spec.get("servers", []),
                "security_schemes": spec.get("components", {}).get("securitySchemes", {}),
                "tags": spec.get("tags", [])
            }
        )

    def _extract_endpoints(self, spec: dict[str, Any]) -> list[DocElement]:
        """Extract all path operations."""
        elements = []
        paths = spec.get("paths", {})
        
        for path, path_item in paths.items():
            # Handle common parameters at path level
            path_params = path_item.get("parameters", [])
            
            for method in ["get", "post", "put", "delete", "patch", "head", "options"]:
                if method not in path_item:
                    continue
                    
                operation = path_item[method]
                
                # Merge path-level parameters with operation-level parameters
                op_params = operation.get("parameters", [])
                all_params = path_params + op_params
                
                # Construct name like "GET /users"
                name = f"{method.upper()} {path}"
                
                element = DocElement(
                    name=name,
                    qualified_name=f"openapi.paths.{path}.{method}",
                    description=operation.get("description") or operation.get("summary", ""),
                    element_type="endpoint",
                    metadata={
                        "method": method,
                        "path": path,
                        "summary": operation.get("summary"),
                        "operation_id": operation.get("operationId"),
                        "tags": operation.get("tags", []),
                        "parameters": all_params,
                        "request_body": operation.get("requestBody"),
                        "responses": operation.get("responses"),
                        "security": operation.get("security"),
                        "deprecated": operation.get("deprecated", False)
                    },
                    examples=[],  # Could extract examples from openapi spec
                    deprecated="Deprecated in API spec" if operation.get("deprecated") else None
                )
                elements.append(element)
                
        return elements

    def _extract_schemas(self, spec: dict[str, Any]) -> list[DocElement]:
        """Extract component schemas."""
        elements = []
        components = spec.get("components", {})
        print(f"DEBUG: Components type: {type(components)}")
        print(f"DEBUG: Components keys: {components.keys() if isinstance(components, dict) else 'Not a dict'}")
        schemas = components.get("schemas", {})
        print(f"DEBUG: Schemas type: {type(schemas)}")
        print(f"DEBUG: Schemas keys: {schemas.keys() if isinstance(schemas, dict) else 'Not a dict'}")
        
        for name, schema in schemas.items():
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
                    "raw_schema": schema  # Keep full schema for complex rendering
                }
            )
            elements.append(element)
            
        return elements

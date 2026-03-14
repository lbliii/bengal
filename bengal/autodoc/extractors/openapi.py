"""
OpenAPI documentation extractor.

Extracts documentation from OpenAPI 3.0/3.1 specifications.
Supports internal (#/), file-relative (./), and URL ($ref) resolution.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

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
from bengal.utils.observability.logger import get_logger

logger = get_logger(__name__)


class OpenAPIExtractor(Extractor):
    """
    Extracts documentation from OpenAPI specifications.

    Supports OpenAPI 3.0 and 3.1 (YAML or JSON).

    """

    def __init__(self) -> None:
        """Initialize the extractor."""
        self._spec: dict[str, Any] = {}
        self._spec_dir: Path = Path(".")
        self._ref_cache: dict[str, Any] = {}
        self._ref_chain: list[str] = []

    def _apply_json_pointer(self, doc: dict[str, Any], pointer: str) -> Any:
        """Apply JSON pointer to document. pointer is the path after #/ (unescaped)."""
        if not pointer or not pointer.strip("/"):
            return doc
        parts = pointer.replace("~1", "/").replace("~0", "~").strip("/").split("/")
        result: Any = doc
        for part in parts:
            if isinstance(result, dict) and part in result:
                result = result[part]
            elif isinstance(result, list):
                idx = int(part)
                result = result[idx] if 0 <= idx < len(result) else None
            else:
                return None
        return result

    def _load_external_doc(self, ref_path: str) -> tuple[Any, Path | None]:
        """
        Load external document from file-relative or URL $ref.

        Returns:
            (loaded_content, base_dir_for_subsequent_refs or None)
        """
        base, _, fragment = ref_path.partition("#")
        fragment = fragment.strip("/") if fragment else ""

        if ref_path in self._ref_cache:
            cached = self._ref_cache[ref_path]
            if fragment:
                result = self._apply_json_pointer(cached, fragment)
                return (result if isinstance(result, dict) else cached), None
            return cached, None

        if base.startswith(("http://", "https://")):
            try:
                req = Request(base, headers={"User-Agent": "Bengal-OpenAPI-Extractor/1.0"})
                with urlopen(req, timeout=10) as resp:
                    content = resp.read().decode("utf-8")
            except Exception as e:
                logger.warning("openapi_url_ref_failed", url=base, error=str(e))
                return {"$ref": ref_path}, None

            if base.endswith((".json", ".json5")):
                doc = json.loads(content)
            else:
                doc = yaml.safe_load(content) or {}

            self._ref_cache[ref_path] = doc
            if fragment:
                result = self._apply_json_pointer(doc, fragment)
                return (result if isinstance(result, dict) else doc), None
            return doc, None

        # File-relative
        if not self._spec_dir:
            logger.warning("openapi_file_ref_no_base", ref=ref_path)
            return {"$ref": ref_path}, None

        resolved = (self._spec_dir / base).resolve()
        if not resolved.exists():
            logger.warning("openapi_file_ref_not_found", path=str(resolved), ref=ref_path)
            return {"$ref": ref_path}, None

        try:
            content = resolved.read_text(encoding="utf-8")
            if resolved.suffix in (".yaml", ".yml"):
                doc = yaml.safe_load(content)
            else:
                doc = json.loads(content)
        except (yaml.YAMLError, json.JSONDecodeError) as e:
            logger.warning("openapi_file_ref_parse_failed", path=str(resolved), error=str(e))
            return {"$ref": ref_path}, None

        doc = doc or {}
        self._ref_cache[ref_path] = doc
        new_base = resolved.parent

        if fragment:
            result = self._apply_json_pointer(doc, fragment)
            return (result if isinstance(result, dict) else doc), new_base
        return doc, new_base

    def _resolve_ref(
        self, ref_or_obj: dict[str, Any], base_dir: Path | None = None
    ) -> dict[str, Any]:
        """
        Resolve a $ref reference to its actual definition.

        Supports:
        - Internal: #/components/schemas/User
        - File-relative: ./schemas/User.yaml
        - URL: https://example.com/schemas/Pet.yaml

        Args:
            ref_or_obj: Either a dict with $ref key, or a regular object
            base_dir: Base directory for file-relative refs (default: _spec_dir)

        Returns:
            Resolved object with actual properties
        """
        if not isinstance(ref_or_obj, dict):
            return ref_or_obj

        if "$ref" not in ref_or_obj:
            return ref_or_obj

        ref_path = ref_or_obj["$ref"]
        if ref_path.startswith("#/"):
            parts = ref_path[2:].replace("~1", "/").replace("~0", "~").split("/")
            result = self._spec
            for part in parts:
                if isinstance(result, dict) and part in result:
                    result = result[part]
                else:
                    logger.warning("openapi_ref_unresolved", ref=ref_path)
                    return ref_or_obj
            return result if isinstance(result, dict) else ref_or_obj

        # External ref
        if ref_path in self._ref_chain:
            logger.warning(
                "openapi_circular_ref",
                ref=ref_path,
                chain=" -> ".join([*self._ref_chain, ref_path]),
            )
            return ref_or_obj

        base_dir = base_dir or self._spec_dir
        prev_dir = self._spec_dir
        if base_dir:
            self._spec_dir = base_dir
        self._ref_chain.append(ref_path)

        try:
            loaded, new_base = self._load_external_doc(ref_path)
            if isinstance(loaded, dict) and loaded.get("_circular"):
                return ref_or_obj
            if isinstance(loaded, dict) and "$ref" in loaded and "_circular" not in loaded:
                # Resolve nested $ref with new base
                nested = self._resolve_ref(loaded, new_base or base_dir)
                return nested if isinstance(nested, dict) else ref_or_obj
            return loaded if isinstance(loaded, dict) else ref_or_obj
        finally:
            self._ref_chain.pop()
            self._spec_dir = prev_dir

    def extract(self, source: Path) -> list[DocElement]:
        """
        Extract documentation elements from OpenAPI spec file.

        Args:
            source: Path to openapi.yaml or openapi.json

        Returns:
            List of DocElement objects
        """
        if not source.exists():
            from bengal.errors import BengalDiscoveryError, ErrorCode

            raise BengalDiscoveryError(
                f"OpenAPI spec not found: {source}",
                file_path=source,
                suggestion="Ensure the OpenAPI spec file exists at the configured path",
                code=ErrorCode.D002,
            )

        try:
            content = source.read_text(encoding="utf-8")
            if source.suffix in (".yaml", ".yml"):
                spec = yaml.safe_load(content)
            else:
                spec = json.loads(content)
        except yaml.YAMLError as e:
            from bengal.errors import BengalContentError, ErrorCode

            raise BengalContentError(
                f"Failed to parse OpenAPI YAML spec: {e}",
                file_path=source,
                suggestion="Check YAML syntax in your OpenAPI specification",
                code=ErrorCode.O003,
            ) from e
        except json.JSONDecodeError as e:
            from bengal.errors import BengalContentError, ErrorCode

            raise BengalContentError(
                f"Failed to parse OpenAPI JSON spec: {e}",
                file_path=source,
                suggestion="Check JSON syntax in your OpenAPI specification",
                code=ErrorCode.O003,
            ) from e

        # Store spec and resolution context for $ref
        self._spec = spec
        self._spec_dir = source.parent.resolve()
        self._ref_cache.clear()
        self._ref_chain.clear()

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

    def _resolve_schema(self, schema: dict[str, Any]) -> dict[str, Any]:
        """
        Resolve $ref and allOf to produce a flattened schema with merged properties.

        Handles:
        - $ref: Resolve to referenced schema
        - allOf: Merge properties, required, enum, example from all subschemas
        """
        if not isinstance(schema, dict):
            return {}
        if "$ref" in schema:
            resolved = self._resolve_ref(schema)
            if not isinstance(resolved, dict):
                return {}
            if "$ref" in resolved:
                return {}  # Unresolved or circular: break to avoid infinite recursion
            return self._resolve_schema(resolved)
        if "allOf" in schema:
            merged: dict[str, Any] = {
                "type": schema.get("type"),
                "properties": {},
                "required": [],
                "enum": schema.get("enum"),
                "example": schema.get("example"),
                "description": schema.get("description", ""),
            }
            for sub in schema.get("allOf", []):
                resolved = self._resolve_schema(sub) if isinstance(sub, dict) else {}
                if not resolved:
                    ref = self._resolve_ref(sub) if isinstance(sub, dict) else sub
                    resolved = self._resolve_schema(ref) if isinstance(ref, dict) else {}
                if resolved:
                    merged["properties"].update(resolved.get("properties", {}))
                    merged["required"] = list(
                        dict.fromkeys(merged.get("required", []) + resolved.get("required", []))
                    )
                    if resolved.get("enum") and not merged.get("enum"):
                        merged["enum"] = resolved["enum"]
                    if resolved.get("example") and not merged.get("example"):
                        merged["example"] = resolved["example"]
                    if resolved.get("description") and not merged.get("description"):
                        merged["description"] = resolved["description"]
                    if resolved.get("type") and not merged.get("type"):
                        merged["type"] = resolved["type"]
            return merged
        # Base case: return schema with resolved nested $ref in properties
        result: dict[str, Any] = {
            "type": schema.get("type"),
            "properties": dict(schema.get("properties", {})),
            "required": list(schema.get("required", [])),
            "enum": schema.get("enum"),
            "example": schema.get("example"),
            "description": schema.get("description", ""),
            "items": schema.get("items"),
        }
        # Resolve $ref in property values
        for prop_name, prop_val in list(result["properties"].items()):
            if isinstance(prop_val, dict) and "$ref" in prop_val:
                result["properties"][prop_name] = self._resolve_schema(prop_val)
            elif isinstance(prop_val, dict) and "items" in prop_val:
                items = prop_val.get("items")
                if isinstance(items, dict) and "$ref" in items:
                    result["properties"][prop_name] = dict(prop_val)
                    result["properties"][prop_name]["items"] = self._resolve_schema(items)
        return result

    def _extract_schemas(self, spec: dict[str, Any]) -> list[DocElement]:
        """Extract component schemas with $ref and allOf resolution."""
        elements = []
        components = spec.get("components", {})
        schemas = components.get("schemas", {})

        for name, schema in schemas.items():
            resolved = self._resolve_schema(dict(schema))
            schema_type = resolved.get("type", "object")
            properties = resolved.get("properties", {})
            required = tuple(resolved.get("required", []))
            enum = tuple(resolved["enum"]) if resolved.get("enum") else None
            example = resolved.get("example")

            typed_meta = OpenAPISchemaMetadata(
                schema_type=schema_type,
                properties=properties,
                required=required,
                enum=enum,
                example=example,
            )

            element = DocElement(
                name=name,
                qualified_name=f"openapi.components.schemas.{name}",
                description=resolved.get("description", schema.get("description", "")),
                element_type="openapi_schema",
                metadata={
                    "type": schema_type,
                    "properties": properties,
                    "required": list(required),
                    "enum": list(enum) if enum else None,
                    "example": example,
                    "raw_schema": schema,
                },
                typed_metadata=typed_meta,
            )
            elements.append(element)

        return elements

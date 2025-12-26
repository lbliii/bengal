"""
Base classes for the autodoc documentation extraction system.

This module defines the core abstractions used by all documentation extractors:

Core Classes:
    - DocElement: Unified data model representing any documented element
      (function, class, endpoint, command, etc.)
    - Extractor: Abstract base class that all extractors must implement

Architecture:
    DocElement serves as the lingua franca between extractors and the
    rendering system. Each extractor (Python, OpenAPI, CLI) produces
    DocElement trees that can be serialized, cached, and rendered
    uniformly regardless of source type.

Serialization:
    DocElement supports JSON serialization via `to_dict()` and `from_dict()`
    for caching extracted documentation between builds.

Related:
    - bengal/autodoc/extractors/: Concrete extractor implementations
    - bengal/autodoc/models/: Typed metadata dataclasses for DocElement.typed_metadata
    - bengal/autodoc/orchestration/: Converts DocElements to virtual pages
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field, is_dataclass
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bengal.autodoc.models import DocMetadata


@lru_cache(maxsize=1024)
def _cached_param_info(
    name: str,
    type_hint: str | None,
    default: str | None,
    description: str | None,
) -> Any:
    """
    Cache common parameter patterns for deserialization.

    Memoizes ParameterInfo construction to avoid repeated object creation
    for common signatures (e.g., "self", "cls", common type hints).

    Args:
        name: Parameter name
        type_hint: Type annotation string
        default: Default value string
        description: Docstring description

    Returns:
        ParameterInfo dataclass instance
    """
    # Import here to avoid circular imports
    from bengal.autodoc.models.python import ParameterInfo

    return ParameterInfo(
        name=name,
        type_hint=type_hint,
        default=default,
        description=description,
    )


def clear_autodoc_caches() -> None:
    """
    Clear autodoc-related caches.

    Call between builds or when cache invalidation is needed.
    """
    _cached_param_info.cache_clear()


@dataclass
class DocElement:
    """
    Represents a documented element (function, class, endpoint, command, etc.).

    This is the unified data model used by all extractors.
    Each extractor converts its specific domain into this common format.

    Attributes:
        name: Element name (e.g., 'build', 'Site', 'GET /users')
        qualified_name: Full path (e.g., 'bengal.core.site.Site.build')
        description: Main description/docstring
        element_type: Type of element ('function', 'class', 'endpoint', 'command', etc.)
        source_file: Source file path (if applicable)
        line_number: Line number in source (if applicable)
        metadata: Type-specific data (signatures, parameters, etc.)
        children: Nested elements (methods, subcommands, etc.)
        examples: Usage examples
        see_also: Cross-references to related elements
        deprecated: Deprecation notice (if any)
        _path: Site-relative URL path without baseurl (e.g., "/cli/assets/build/").
            Computed during page building. Use for internal comparisons.
        href: Public URL with baseurl (e.g., "/bengal/cli/assets/build/").
            Computed during page building. Use in templates: <a href="{{ child.href }}">
    """

    name: str
    qualified_name: str
    description: str
    element_type: str
    source_file: Path | None = None
    line_number: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    typed_metadata: DocMetadata | None = None
    children: list[DocElement] = field(default_factory=list)
    examples: list[str] = field(default_factory=list)
    see_also: list[str] = field(default_factory=list)
    deprecated: str | None = None
    # URL properties - computed during page building when site context is available
    _path: str | None = None  # Site-relative path without baseurl (e.g., "/cli/assets/build/")
    href: str | None = None  # Public URL with baseurl (e.g., "/bengal/cli/assets/build/")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for caching/serialization."""

        def _to_jsonable(value: Any) -> Any:
            """
            Convert a value to a JSON-serializable form.

            Used to ensure autodoc cache payloads can be persisted in BuildCache
            without failing serialization on domain objects (e.g., ParameterInfo).

            IMPORTANT: DocElement objects should NEVER be passed to this function.
            They must go through to_dict() first. If a DocElement is detected here,
            it indicates a bug that could corrupt cache data.
            """
            if value is None:
                return None
            if isinstance(value, str | int | float | bool):
                return value
            if isinstance(value, Path):
                return str(value)
            # CRITICAL: Check for DocElement BEFORE is_dataclass to prevent corruption
            # If a DocElement somehow gets here, it means it bypassed to_dict()
            # This would cause children to be converted to strings via asdict() -> str()
            if isinstance(value, DocElement):
                from bengal.utils.logger import get_logger

                logger = get_logger(__name__)
                logger.warning(
                    "autodoc_serialization_bug",
                    error="DocElement passed to _to_jsonable() instead of to_dict()",
                    element_name=getattr(value, "name", "unknown"),
                    element_type=getattr(value, "element_type", "unknown"),
                    action="converting_to_dict_to_prevent_corruption",
                    error_code="A001",  # cache_corruption - preventing cache corruption
                )
                # Convert to dict properly instead of letting it fall through
                return value.to_dict()
            if is_dataclass(value):
                return _to_jsonable(asdict(value))
            if isinstance(value, dict):
                return {str(k): _to_jsonable(v) for k, v in value.items()}
            if isinstance(value, list | tuple | set):
                return [_to_jsonable(v) for v in value]
            # Last resort: represent unknown objects as strings (stable enough for caching)
            return str(value)

        # Validate children are DocElement instances before serialization
        # This catches bugs early and prevents corrupted cache data
        invalid_children = [
            (i, type(child).__name__)
            for i, child in enumerate(self.children)
            if not isinstance(child, DocElement)
        ]
        if invalid_children:
            from bengal.utils.logger import get_logger

            logger = get_logger(__name__)
            logger.warning(
                "autodoc_children_validation_failed",
                invalid_indices=[idx for idx, _ in invalid_children],
                invalid_types=[typ for _, typ in invalid_children],
                element_name=self.name,
                element_type=self.element_type,
                action="skipping_invalid_children",
                error_code="A001",  # cache_corruption - preventing cache corruption
            )
            # Filter out invalid children to prevent cache corruption
            valid_children = [child for child in self.children if isinstance(child, DocElement)]
        else:
            valid_children = self.children

        result = {
            "name": self.name,
            "qualified_name": self.qualified_name,
            "description": self.description,
            "element_type": self.element_type,
            "source_file": str(self.source_file) if self.source_file else None,
            "line_number": self.line_number,
            "metadata": _to_jsonable(self.metadata),
            "typed_metadata": None,
            "children": [child.to_dict() for child in valid_children],
            "examples": self.examples,
            "see_also": self.see_also,
            "deprecated": self.deprecated,
            "_path": self._path,
            "href": self.href,
        }
        # Serialize typed_metadata if present
        if self.typed_metadata is not None:
            result["typed_metadata"] = {
                "type": type(self.typed_metadata).__name__,
                "data": asdict(self.typed_metadata),
            }
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DocElement:
        """Create from dictionary (for cache loading)."""
        # Guard against malformed cache data (e.g., strings instead of dicts)
        if not isinstance(data, dict):
            from bengal.utils.logger import get_logger

            logger = get_logger(__name__)
            logger.warning(
                "autodoc_cache_malformed_entry",
                expected_type="dict",
                actual_type=type(data).__name__,
                data_preview=str(data)[:100] if isinstance(data, str) else repr(data)[:100],
                action="skipping_entry",
                error_code="A001",  # cache_corruption - malformed cache entry
            )
            # Return a minimal valid element to prevent crashes
            # This allows the build to continue even with corrupted cache entries
            return cls(
                name="<malformed>",
                qualified_name="<malformed>",
                description="Malformed cache entry (skipped)",
                element_type="unknown",
                children=[],
            )

        # Safely process children, skipping any that aren't dicts
        children = []
        for child in data.get("children", []):
            if isinstance(child, dict):
                try:
                    children.append(cls.from_dict(child))
                except Exception as e:
                    from bengal.utils.logger import get_logger

                    logger = get_logger(__name__)
                    logger.debug(
                        "autodoc_cache_child_deserialization_failed",
                        error=str(e),
                        child_preview=repr(child)[:100],
                        action="skipping_child",
                    )
        source_file = Path(data["source_file"]) if data.get("source_file") else None

        # Deserialize typed_metadata
        typed_metadata = None
        if data.get("typed_metadata"):
            typed_metadata = cls._deserialize_typed_metadata(data["typed_metadata"])

        return cls(
            name=data["name"],
            qualified_name=data["qualified_name"],
            description=data["description"],
            element_type=data["element_type"],
            source_file=source_file,
            line_number=data.get("line_number"),
            metadata=data.get("metadata", {}),
            typed_metadata=typed_metadata,
            children=children,
            examples=data.get("examples", []),
            see_also=data.get("see_also", []),
            deprecated=data.get("deprecated"),
            _path=data.get("_path"),
            href=data.get("href"),
        )

    @staticmethod
    def _deserialize_typed_metadata(data: dict[str, Any]) -> DocMetadata | None:
        """
        Deserialize typed_metadata from dict.

        Args:
            data: Dict with "type" and "data" keys

        Returns:
            Typed metadata instance or None
        """
        # Import here to avoid circular imports
        from bengal.autodoc.models import (
            CLICommandMetadata,
            CLIGroupMetadata,
            CLIOptionMetadata,
            OpenAPIEndpointMetadata,
            OpenAPIOverviewMetadata,
            OpenAPISchemaMetadata,
            PythonAliasMetadata,
            PythonAttributeMetadata,
            PythonClassMetadata,
            PythonFunctionMetadata,
            PythonModuleMetadata,
        )
        from bengal.autodoc.models.openapi import (
            OpenAPIParameterMetadata,
            OpenAPIRequestBodyMetadata,
            OpenAPIResponseMetadata,
        )
        from bengal.autodoc.models.python import (
            ParameterInfo,
            ParsedDocstring,
            RaisesInfo,
        )

        type_map: dict[str, type] = {
            "PythonModuleMetadata": PythonModuleMetadata,
            "PythonClassMetadata": PythonClassMetadata,
            "PythonFunctionMetadata": PythonFunctionMetadata,
            "PythonAttributeMetadata": PythonAttributeMetadata,
            "PythonAliasMetadata": PythonAliasMetadata,
            "CLICommandMetadata": CLICommandMetadata,
            "CLIGroupMetadata": CLIGroupMetadata,
            "CLIOptionMetadata": CLIOptionMetadata,
            "OpenAPIEndpointMetadata": OpenAPIEndpointMetadata,
            "OpenAPIOverviewMetadata": OpenAPIOverviewMetadata,
            "OpenAPISchemaMetadata": OpenAPISchemaMetadata,
        }

        type_name = data.get("type")
        type_data = data.get("data", {})

        if type_name not in type_map:
            return None

        metadata_class = type_map[type_name]

        # Helper to safely convert parameter data to ParameterInfo with clear error on mismatch
        # Uses LRU cache for common parameter patterns (e.g., "self", common types)
        def _to_param_info(p: Any, context: str) -> ParameterInfo:
            """Convert param data to ParameterInfo, failing loudly on format mismatch."""
            if isinstance(p, dict):
                # Use cached version for common patterns
                return _cached_param_info(
                    p.get("name", ""),
                    p.get("type_hint"),
                    p.get("default"),
                    p.get("description"),
                )
            raise TypeError(
                f"Autodoc cache format mismatch in {context}: expected dict, got {type(p).__name__}. "
                f"Value: {p!r}. This usually means the cache was created with an older version. "
                f"Clear the cache with: rm -rf .bengal/cache/"
            )

        def _to_raises_info(r: Any, context: str) -> RaisesInfo:
            """Convert raises data to RaisesInfo, failing loudly on format mismatch."""
            if isinstance(r, dict):
                return RaisesInfo(**r)
            raise TypeError(
                f"Autodoc cache format mismatch in {context}: expected dict, got {type(r).__name__}. "
                f"Value: {r!r}. This usually means the cache was created with an older version. "
                f"Clear the cache with: rm -rf .bengal/cache/"
            )

        # Handle nested dataclasses
        if type_name == "PythonClassMetadata" and type_data.get("parsed_doc"):
            pd = type_data["parsed_doc"]
            if pd:
                params = tuple(
                    _to_param_info(p, "PythonClassMetadata.parsed_doc.params")
                    for p in pd.get("params", ())
                )
                raises = tuple(
                    _to_raises_info(r, "PythonClassMetadata.parsed_doc.raises")
                    for r in pd.get("raises", ())
                )
                type_data["parsed_doc"] = ParsedDocstring(
                    summary=pd.get("summary", ""),
                    description=pd.get("description", ""),
                    params=params,
                    returns=pd.get("returns"),
                    raises=raises,
                    examples=tuple(pd.get("examples", ())),
                )

        if type_name == "PythonFunctionMetadata":
            # Convert parameters list to tuple of ParameterInfo
            if type_data.get("parameters"):
                type_data["parameters"] = tuple(
                    _to_param_info(p, "PythonFunctionMetadata.parameters")
                    for p in type_data["parameters"]
                )
            # Handle parsed_doc
            if type_data.get("parsed_doc"):
                pd = type_data["parsed_doc"]
                if pd:
                    params = tuple(
                        _to_param_info(p, "PythonFunctionMetadata.parsed_doc.params")
                        for p in pd.get("params", ())
                    )
                    raises = tuple(
                        _to_raises_info(r, "PythonFunctionMetadata.parsed_doc.raises")
                        for r in pd.get("raises", ())
                    )
                    type_data["parsed_doc"] = ParsedDocstring(
                        summary=pd.get("summary", ""),
                        description=pd.get("description", ""),
                        params=params,
                        returns=pd.get("returns"),
                        raises=raises,
                        examples=tuple(pd.get("examples", ())),
                    )

        if type_name == "OpenAPIEndpointMetadata":
            # Convert nested types
            if type_data.get("parameters"):
                type_data["parameters"] = tuple(
                    OpenAPIParameterMetadata(**p) for p in type_data["parameters"]
                )
            if type_data.get("request_body"):
                type_data["request_body"] = OpenAPIRequestBodyMetadata(**type_data["request_body"])
            if type_data.get("responses"):
                type_data["responses"] = tuple(
                    OpenAPIResponseMetadata(**r) for r in type_data["responses"]
                )

        # Convert lists to tuples for frozen dataclasses
        for key, value in list(type_data.items()):
            if isinstance(value, list):
                type_data[key] = tuple(value)

        try:
            return metadata_class(**type_data)
        except TypeError:
            # If construction fails (e.g., due to extra fields), return None
            return None


class Extractor(ABC):
    """
    Base class for all documentation extractors.

    Each documentation type (Python, OpenAPI, CLI) implements this interface.
    This enables a unified API for generating documentation from different sources.

    Example:
        class PythonExtractor(Extractor):
            def extract(self, source: Path) -> List[DocElement]:
                # Extract Python API docs via AST
                ...

            # Templates are now unified under bengal/autodoc/templates/
            # with python/, cli/, openapi/ subdirectories
    """

    @abstractmethod
    def extract(self, source: Any) -> list[DocElement]:
        """
        Extract documentation elements from source.

        Args:
            source: Source to extract from (Path for files, dict for specs, etc.)

        Returns:
            List of DocElement objects representing the documentation structure

        Note:
            This should be fast and not have side effects (no imports, no network calls)
        """
        pass

    @abstractmethod
    def get_output_path(self, element: DocElement) -> Path | None:
        """
        Determine output path for an element.

        Args:
            element: Element to generate path for

        Returns:
            Relative path for the generated markdown file, or None if the
            element should be skipped (e.g., stripped prefix packages)

        Example:
            For Python: bengal.core.site.Site → bengal/core/site.md
            For OpenAPI: GET /users → endpoints/get-users.md
            For CLI: bengal build → commands/build.md
        """
        pass

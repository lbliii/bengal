"""
Base classes for autodoc system.

Provides common interfaces for all documentation extractors.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


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
    """

    name: str
    qualified_name: str
    description: str
    element_type: str
    source_file: Path | None = None
    line_number: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    children: list["DocElement"] = field(default_factory=list)
    examples: list[str] = field(default_factory=list)
    see_also: list[str] = field(default_factory=list)
    deprecated: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for caching/serialization."""
        return {
            "name": self.name,
            "qualified_name": self.qualified_name,
            "description": self.description,
            "element_type": self.element_type,
            "source_file": str(self.source_file) if self.source_file else None,
            "line_number": self.line_number,
            "metadata": self.metadata,
            "children": [child.to_dict() for child in self.children],
            "examples": self.examples,
            "see_also": self.see_also,
            "deprecated": self.deprecated,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DocElement":
        """Create from dictionary (for cache loading)."""
        children = [cls.from_dict(child) for child in data.get("children", [])]
        source_file = Path(data["source_file"]) if data.get("source_file") else None

        return cls(
            name=data["name"],
            qualified_name=data["qualified_name"],
            description=data["description"],
            element_type=data["element_type"],
            source_file=source_file,
            line_number=data.get("line_number"),
            metadata=data.get("metadata", {}),
            children=children,
            examples=data.get("examples", []),
            see_also=data.get("see_also", []),
            deprecated=data.get("deprecated"),
        )


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

            def get_template_dir(self) -> str:
                return "python"
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
    def get_template_dir(self) -> str:
        """
        Get template directory name for this extractor.

        Returns:
            Directory name (e.g., 'python', 'openapi', 'cli')

        Example:
            Templates will be loaded from:
            - templates/autodoc/{template_dir}/
            - Built-in: bengal/autodoc/templates/{template_dir}/
        """
        pass

    @abstractmethod
    def get_output_path(self, element: DocElement) -> Path:
        """
        Determine output path for an element.

        Args:
            element: Element to generate path for

        Returns:
            Relative path for the generated markdown file

        Example:
            For Python: bengal.core.site.Site → bengal/core/site.md
            For OpenAPI: GET /users → endpoints/get-users.md
            For CLI: bengal build → commands/build.md
        """
        pass

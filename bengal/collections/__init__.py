"""
Content Collections - Type-safe content schemas for Bengal.

This module provides content collections with schema validation, enabling
type-safe frontmatter and early error detection during content discovery.

Usage:
    # collections.py (project root)
    from dataclasses import dataclass, field
    from datetime import datetime
    from typing import Optional
    from bengal.collections import define_collection

    @dataclass
    class BlogPost:
        title: str
        date: datetime
        author: str = "Anonymous"
        tags: list[str] = field(default_factory=list)
        draft: bool = False

    collections = {
        "blog": define_collection(
            schema=BlogPost,
            directory="content/blog",
        ),
    }

Architecture:
    - Collections are opt-in (backward compatible)
    - Schemas use Python dataclasses or Pydantic models
    - Validation happens during discovery phase (fail fast)
    - Supports both strict and lenient modes

Related:
    - bengal/discovery/content_discovery.py: Integration point
    - bengal/core/page/metadata.py: Frontmatter access
    - plan/active/rfc-content-collections.md: Design document
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Generic, TypeVar

T = TypeVar("T")


@dataclass
class CollectionConfig(Generic[T]):
    """
    Configuration for a content collection.

    Attributes:
        schema: Dataclass or Pydantic model defining frontmatter structure
        directory: Directory containing collection content (relative to content root)
        glob: Glob pattern for matching files
        strict: If True, reject unknown frontmatter fields
        allow_extra: If True, store extra fields in _extra attribute
        transform: Optional function to transform frontmatter before validation
    """

    schema: type[T]
    directory: Path
    glob: str = "**/*.md"
    strict: bool = True
    allow_extra: bool = False
    transform: Callable[[dict[str, Any]], dict[str, Any]] | None = None

    def __post_init__(self) -> None:
        """Ensure directory is a Path object."""
        if isinstance(self.directory, str):
            self.directory = Path(self.directory)


def define_collection(
    schema: type[T],
    directory: str | Path,
    *,
    glob: str = "**/*.md",
    strict: bool = True,
    allow_extra: bool = False,
    transform: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
) -> CollectionConfig[T]:
    """
    Define a content collection with typed schema.

    Collections provide type-safe frontmatter validation during content
    discovery, catching errors early and enabling IDE autocompletion.

    Args:
        schema: Dataclass or Pydantic model defining frontmatter structure.
            Required fields must not have defaults. Optional fields should
            have defaults or use Optional[T] type hints.
        directory: Directory containing collection content (relative to
            content root). All matching files in this directory will be
            validated against the schema.
        glob: Glob pattern for matching files. Default "**/*.md" matches
            all markdown files recursively.
        strict: If True (default), reject unknown frontmatter fields.
            Set to False to allow extra fields without validation.
        allow_extra: If True, store extra fields in a _extra dict on
            the validated instance. Only applies when strict=False.
        transform: Optional function to transform frontmatter before
            validation. Useful for normalizing field names, computing
            derived fields, or handling legacy formats.

    Returns:
        CollectionConfig instance for use in collections dict.

    Example:
        >>> from dataclasses import dataclass, field
        >>> from datetime import datetime
        >>> from typing import Optional
        >>>
        >>> @dataclass
        ... class BlogPost:
        ...     title: str
        ...     date: datetime
        ...     author: str = "Anonymous"
        ...     tags: list[str] = field(default_factory=list)
        ...     draft: bool = False
        ...     description: Optional[str] = None
        ...
        >>> blog = define_collection(
        ...     schema=BlogPost,
        ...     directory="content/blog",
        ... )
        >>> blog.schema.__name__
        'BlogPost'

    Example with transform:
        >>> def normalize_legacy(data: dict) -> dict:
        ...     # Rename old field names
        ...     if 'post_title' in data:
        ...         data['title'] = data.pop('post_title')
        ...     return data
        ...
        >>> blog = define_collection(
        ...     schema=BlogPost,
        ...     directory="content/blog",
        ...     transform=normalize_legacy,
        ... )
    """
    return CollectionConfig(
        schema=schema,
        directory=Path(directory),
        glob=glob,
        strict=strict,
        allow_extra=allow_extra,
        transform=transform,
    )


# Re-export commonly used items
from bengal.collections.errors import ContentValidationError, ValidationError
from bengal.collections.loader import (
    get_collection_for_path,
    load_collections,
    validate_collections_config,
)
from bengal.collections.validator import SchemaValidator, ValidationResult

__all__ = [
    "CollectionConfig",
    "ContentValidationError",
    "SchemaValidator",
    "ValidationError",
    "ValidationResult",
    "define_collection",
    "get_collection_for_path",
    "load_collections",
    "validate_collections_config",
]


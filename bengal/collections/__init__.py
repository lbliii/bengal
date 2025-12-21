"""
Content Collections - Type-safe content schemas for Bengal.

This module provides content collections with schema validation, enabling
type-safe frontmatter and early error detection during content discovery.

Usage (Local Content):

```python
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
```

Usage (Remote Content - Content Layer):

```python
from bengal.collections import define_collection
from bengal.content_layer import github_loader, notion_loader

collections = {
    # Local content (default)
    "docs": define_collection(schema=Doc, directory="content/docs"),

    # Remote content from GitHub
    "api": define_collection(
        schema=APIDoc,
        loader=github_loader(repo="myorg/api-docs", path="docs/"),
    ),

    # Remote content from Notion
    "blog": define_collection(
        schema=BlogPost,
        loader=notion_loader(database_id="abc123"),
    ),
}
```

Architecture:
    - Collections are opt-in (backward compatible)
    - Schemas use Python dataclasses or Pydantic models
    - Validation happens during discovery phase (fail fast)
    - Supports both strict and lenient modes
    - Remote sources via Content Layer (zero-cost if unused)

Related:
    - bengal/discovery/content_discovery.py: Integration point
    - bengal/content_layer/: Remote content sources
    - bengal/core/page/metadata.py: Frontmatter access
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

# Re-export commonly used items (placed here to satisfy E402)
from bengal.collections.errors import ContentValidationError, ValidationError
from bengal.collections.loader import (
    get_collection_for_path,
    load_collections,
    validate_collections_config,
)
from bengal.collections.schemas import (
    API,
    APIReference,
    BlogPost,
    Changelog,
    Doc,
    DocPage,
    Post,
    Tutorial,
)
from bengal.collections.validator import SchemaValidator, ValidationResult

if TYPE_CHECKING:
    from bengal.content_layer.source import ContentSource


@dataclass
class CollectionConfig[T]:
    """
    Configuration for a content collection.

    Attributes:
        schema: Dataclass or Pydantic model defining frontmatter structure
        directory: Directory containing collection content (relative to content root).
            Required for local content, optional when using a remote loader.
        glob: Glob pattern for matching files (local content only)
        strict: If True, reject unknown frontmatter fields
        allow_extra: If True, store extra fields in _extra attribute
        transform: Optional function to transform frontmatter before validation
        loader: Optional ContentSource for remote content (Content Layer).
            When provided, content is fetched from the remote source instead
            of the local directory. Install extras: pip install bengal[github]
    """

    schema: type[T]
    directory: Path | None = None
    glob: str = "**/*.md"
    strict: bool = True
    allow_extra: bool = False
    transform: Callable[[dict[str, Any]], dict[str, Any]] | None = None
    loader: ContentSource | None = None

    def __post_init__(self) -> None:
        """Validate configuration and normalize directory."""
        if isinstance(self.directory, str):
            self.directory = Path(self.directory)

        # Validate: must have either directory or loader
        from bengal.utils.exceptions import BengalConfigError

        if self.directory is None and self.loader is None:
            raise BengalConfigError(
                "CollectionConfig requires either 'directory' (for local content) "
                "or 'loader' (for remote content)",
                suggestion="Set either 'directory' for local content or 'loader' for remote content",
            )

    @property
    def is_remote(self) -> bool:
        """Check if this collection uses a remote loader."""
        return self.loader is not None

    @property
    def source_type(self) -> str:
        """Get the source type for this collection."""
        if self.loader is not None:
            return self.loader.source_type
        return "local"


def define_collection[T](
    schema: type[T],
    directory: str | Path | None = None,
    *,
    glob: str = "**/*.md",
    strict: bool = True,
    allow_extra: bool = False,
    transform: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
    loader: ContentSource | None = None,
) -> CollectionConfig[T]:
    """
    Define a content collection with typed schema.

    Collections provide type-safe frontmatter validation during content
    discovery, catching errors early and enabling IDE autocompletion.

    Supports both local content (via directory) and remote content (via loader).
    Remote loaders are part of the Content Layer - install extras as needed:
        pip install bengal[github]   # GitHub loader
        pip install bengal[notion]   # Notion loader

    Args:
        schema: Dataclass or Pydantic model defining frontmatter structure.
            Required fields must not have defaults. Optional fields should
            have defaults or use Optional[T] type hints.
        directory: Directory containing collection content (relative to
            content root). Required for local content, optional when using
            a remote loader.
        glob: Glob pattern for matching files. Default "**/*.md" matches
            all markdown files recursively. Only used for local content.
        strict: If True (default), reject unknown frontmatter fields.
            Set to False to allow extra fields without validation.
        allow_extra: If True, store extra fields in a _extra dict on
            the validated instance. Only applies when strict=False.
        transform: Optional function to transform frontmatter before
            validation. Useful for normalizing field names, computing
            derived fields, or handling legacy formats.
        loader: Optional ContentSource for remote content (Content Layer).
            When provided, content is fetched from the remote source.

    Returns:
        CollectionConfig instance for use in collections dict.

    Example (Local Content):
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
        ...
        >>> blog = define_collection(
        ...     schema=BlogPost,
        ...     directory="content/blog",
        ... )

    Example (Remote Content - GitHub):
        >>> from bengal.content_layer import github_loader
        >>>
        >>> api_docs = define_collection(
        ...     schema=APIDoc,
        ...     loader=github_loader(repo="myorg/api-docs", path="docs/"),
        ... )

    Example (Remote Content - Notion):
        >>> from bengal.content_layer import notion_loader
        >>>
        >>> blog = define_collection(
        ...     schema=BlogPost,
        ...     loader=notion_loader(database_id="abc123..."),
        ... )

    Example with transform:
        >>> def normalize_legacy(data: dict) -> dict:
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
        directory=Path(directory) if directory else None,
        glob=glob,
        strict=strict,
        allow_extra=allow_extra,
        transform=transform,
        loader=loader,
    )


__all__ = [
    # Core API
    "CollectionConfig",
    "define_collection",
    # Validation
    "ContentValidationError",
    "SchemaValidator",
    "ValidationError",
    "ValidationResult",
    # Loader
    "get_collection_for_path",
    "load_collections",
    "validate_collections_config",
    # Standard schemas
    "API",
    "APIReference",
    "BlogPost",
    "Changelog",
    "Doc",
    "DocPage",
    "Post",
    "Tutorial",
]

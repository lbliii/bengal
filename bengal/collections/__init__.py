"""
Content Collections - Type-safe content schemas for Bengal.

Provides content collections with schema validation, enabling type-safe
frontmatter and early error detection during content discovery. Collections
are opt-in and backward compatible with existing Bengal sites.

Quick Start:
    Create a ``collections.py`` file in your project root:

    >>> from dataclasses import dataclass, field
    >>> from datetime import datetime
    >>> from bengal.collections import define_collection
    >>>
    >>> @dataclass
    ... class BlogPost:
    ...     title: str
    ...     date: datetime
    ...     author: str = "Anonymous"
    ...     tags: list[str] = field(default_factory=list)
    ...
    >>> collections = {
    ...     "blog": define_collection(schema=BlogPost, directory="content/blog"),
    ... }

Key Features:
    - **Type-safe frontmatter**: Validate content against dataclass or Pydantic schemas
    - **Early error detection**: Catch schema violations during discovery, not rendering
    - **IDE support**: Get autocompletion for frontmatter fields
    - **Flexible validation**: Strict mode rejects unknown fields; lenient mode allows them
    - **Remote content**: Fetch content from GitHub, Notion, or custom sources

Public API:
    - :func:`define_collection`: Create a collection configuration
    - :class:`CollectionConfig`: Collection configuration dataclass
    - :class:`SchemaValidator`: Validate data against schemas
    - :class:`ValidationResult`: Result of schema validation
    - :exc:`ContentValidationError`: Raised when content fails validation
    - :exc:`ValidationError`: Single field validation error

Standard Schemas:
    Ready-to-use schemas for common content types:
    - :class:`BlogPost`: Blog posts with title, date, author, tags
    - :class:`DocPage`: Documentation pages with weight, category, toc
    - :class:`APIReference`: API endpoint documentation
    - :class:`Tutorial`: Tutorial/guide pages with difficulty, duration
    - :class:`Changelog`: Release changelog entries

Architecture:
    Collections integrate with Bengal's discovery phase. When content is
    discovered, frontmatter is validated against the collection's schema.
    Invalid content raises :exc:`ContentValidationError` with details.

    Validation supports:
    - Python dataclasses (recommended)
    - Pydantic models (auto-detected)
    - Type coercion for datetime, date, lists
    - Nested dataclass validation

Related Modules:
    - ``bengal.discovery.content_discovery``: Collection integration point
    - ``bengal.content_layer``: Remote content sources (GitHub, Notion)
    - ``bengal.core.page.metadata``: Page frontmatter access
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

    Defines how content in a directory (or remote source) maps to a typed
    schema. Created via :func:`define_collection` rather than direct instantiation.

    Type Parameters:
        T: The schema type (dataclass or Pydantic model)

    Attributes:
        schema: Dataclass or Pydantic model class defining the frontmatter
            structure. Required fields in the schema become required frontmatter.
        directory: Directory containing collection content, relative to content
            root. Required for local content; optional when using ``loader``.
        glob: Glob pattern for matching content files within the directory.
            Defaults to ``**/*.md`` (all markdown files recursively).
        strict: If ``True`` (default), reject content with unknown frontmatter
            fields. Set to ``False`` to allow extra fields.
        allow_extra: If ``True``, store unrecognized fields in a ``_extra``
            dict attribute on the validated instance. Only applies when
            ``strict=False``.
        transform: Optional function to transform frontmatter dict before
            validation. Useful for normalizing legacy field names or computing
            derived values.
        loader: Optional :class:`ContentSource` for fetching remote content.
            When provided, content is fetched from the remote source instead
            of the local filesystem. Requires extras: ``pip install bengal[github]``

    Example:
        >>> config = CollectionConfig(
        ...     schema=BlogPost,
        ...     directory=Path("content/blog"),
        ...     glob="**/*.md",
        ...     strict=True,
        ... )
        >>> config.is_remote
        False
        >>> config.source_type
        'local'

    See Also:
        :func:`define_collection`: Preferred way to create configurations.
    """

    schema: type[T]
    directory: Path | None = None
    glob: str = "**/*.md"
    strict: bool = True
    allow_extra: bool = False
    transform: Callable[[dict[str, Any]], dict[str, Any]] | None = None
    loader: ContentSource | None = None

    def __post_init__(self) -> None:
        """
        Validate configuration and normalize the directory path.

        Raises:
            BengalConfigError: If neither ``directory`` nor ``loader`` is provided.
        """
        if isinstance(self.directory, str):
            self.directory = Path(self.directory)

        # Validate: must have either directory or loader
        from bengal.errors import BengalConfigError

        if self.directory is None and self.loader is None:
            raise BengalConfigError(
                "CollectionConfig requires either 'directory' (for local content) "
                "or 'loader' (for remote content)",
                suggestion="Set either 'directory' for local content or 'loader' for remote content",
            )

    @property
    def is_remote(self) -> bool:
        """
        Whether this collection fetches content from a remote source.

        Returns:
            ``True`` if a loader is configured; ``False`` for local content.
        """
        return self.loader is not None

    @property
    def source_type(self) -> str:
        """
        The content source type identifier.

        Returns:
            Source type string: ``'local'`` for filesystem content, or the
            loader's ``source_type`` (e.g., ``'github'``, ``'notion'``).
        """
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
    Define a content collection with a typed schema.

    Collections provide type-safe frontmatter validation during content
    discovery. Errors are caught early, and IDEs provide autocompletion
    for frontmatter fields.

    Args:
        schema: Dataclass or Pydantic model class defining the frontmatter
            structure. Fields without defaults are required; fields with
            defaults (or ``Optional[T]`` type hints) are optional.
        directory: Directory containing collection content, relative to the
            content root. Required for local content; omit when using ``loader``.
        glob: Glob pattern for matching content files. Defaults to ``**/*.md``
            (all markdown files recursively). Only used for local content.
        strict: If ``True`` (default), reject content with unknown frontmatter
            fields not defined in the schema.
        allow_extra: If ``True``, store unrecognized fields in a ``_extra``
            dict on the validated instance. Only effective when ``strict=False``.
        transform: Optional function to preprocess frontmatter before validation.
            Receives the raw dict, returns the transformed dict. Useful for
            normalizing legacy field names or computing derived values.
        loader: Optional :class:`ContentSource` for fetching remote content.
            Requires extras: ``pip install bengal[github]`` or ``bengal[notion]``.

    Returns:
        A :class:`CollectionConfig` instance for use in the project's
        ``collections`` dictionary.

    Raises:
        BengalConfigError: If neither ``directory`` nor ``loader`` is provided.

    Example:
        Basic local collection:

        >>> from dataclasses import dataclass, field
        >>> from datetime import datetime
        >>>
        >>> @dataclass
        ... class BlogPost:
        ...     title: str
        ...     date: datetime
        ...     author: str = "Anonymous"
        ...     tags: list[str] = field(default_factory=list)
        ...
        >>> blog = define_collection(
        ...     schema=BlogPost,
        ...     directory="content/blog",
        ... )

    Example:
        Remote content from GitHub:

        >>> from bengal.content_layer import github_loader
        >>>
        >>> api_docs = define_collection(
        ...     schema=APIDoc,
        ...     loader=github_loader(repo="myorg/api-docs", path="docs/"),
        ... )

    Example:
        Transform legacy frontmatter:

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

    See Also:
        - :class:`CollectionConfig`: The returned configuration class
        - :class:`SchemaValidator`: How validation is performed
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
    # --- Core API ---
    "CollectionConfig",
    "define_collection",
    # --- Validation ---
    "ContentValidationError",
    "SchemaValidator",
    "ValidationError",
    "ValidationResult",
    # --- Loader Utilities ---
    "get_collection_for_path",
    "load_collections",
    "validate_collections_config",
    # --- Standard Schemas ---
    "API",
    "APIReference",
    "BlogPost",
    "Changelog",
    "Doc",
    "DocPage",
    "Post",
    "Tutorial",
]

"""
Collection loader - loads collection definitions from project files.

Discovers and loads collection schemas from the user's ``collections.py``
file at the project root. This module handles the dynamic import and
validation of user-defined collection configurations.

Functions:
    - :func:`load_collections`: Load collections dict from project file
    - :func:`get_collection_for_path`: Find which collection owns a file
    - :func:`validate_collections_config`: Check collection directories exist

Usage:
    Collections are automatically loaded during site discovery:

    >>> from bengal.collections.loader import load_collections
    >>> collections = load_collections(Path("/path/to/project"))
    >>> for name, config in collections.items():
    ...     print(f"{name}: {config.directory}")
    blog: content/blog
    docs: content/docs

The ``collections.py`` file should define a ``collections`` dictionary:

    >>> # collections.py
    >>> from bengal.collections import define_collection
    >>> from my_schemas import BlogPost, DocPage
    >>>
    >>> collections = {
    ...     "blog": define_collection(schema=BlogPost, directory="content/blog"),
    ...     "docs": define_collection(schema=DocPage, directory="content/docs"),
    ... }
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from bengal.collections import CollectionConfig

logger = get_logger(__name__)


def load_collections(
    project_root: Path,
    collection_file: str = "collections.py",
) -> dict[str, CollectionConfig[Any]]:
    """
    Load collection definitions from the project's collections file.

    Dynamically imports the ``collections.py`` file from the project root
    and extracts the ``collections`` dictionary. If no file exists or the
    file doesn't define ``collections``, returns an empty dict.

    Args:
        project_root: Path to the project root directory.
        collection_file: Name of the collections file. Defaults to
            ``collections.py``.

    Returns:
        Dictionary mapping collection names to :class:`CollectionConfig`
        instances. Returns an empty dict if:
        - The collections file doesn't exist
        - The file doesn't define a ``collections`` variable
        - The ``collections`` variable isn't a dict

    Example:
        >>> collections = load_collections(Path("/path/to/project"))
        >>> for name, config in collections.items():
        ...     print(f"{name}: {config.directory}")
        blog: content/blog
        docs: content/docs

    Note:
        The collections file must export a ``collections`` dictionary:

        >>> # collections.py
        >>> from dataclasses import dataclass
        >>> from bengal.collections import define_collection
        >>>
        >>> @dataclass
        ... class BlogPost:
        ...     title: str
        ...
        >>> collections = {
        ...     "blog": define_collection(schema=BlogPost, directory="content/blog"),
        ... }

    Warning:
        This function executes user code via ``importlib``. The collections
        file runs at import time, so side effects in module-level code will
        execute. Keep collections.py focused on schema and collection definitions.
    """
    collections_path = project_root / collection_file

    if not collections_path.exists():
        logger.debug(
            "No collections.py found, skipping schema validation",
            event="no_collections_file",
            path=str(collections_path),
        )
        return {}

    try:
        # Load the collections module dynamically
        spec = importlib.util.spec_from_file_location("user_collections", collections_path)
        if spec is None or spec.loader is None:
            logger.warning(
                "collections_load_failed",
                path=str(collections_path),
                error="Could not create module spec",
            )
            return {}

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Extract collections dictionary
        collections = getattr(module, "collections", None)

        if collections is None:
            logger.warning(
                "collections.py found but no 'collections' dict defined",
                event="collections_dict_missing",
                path=str(collections_path),
            )
            return {}

        if not isinstance(collections, dict):
            logger.warning(
                f"'collections' should be dict, got {type(collections).__name__}",
                event="collections_invalid_type",
                path=str(collections_path),
            )
            return {}

        logger.info(
            "collections_loaded",
            path=str(collections_path),
            count=len(collections),
            names=list(collections.keys()),
        )

        # Type assertion: collections dict contains CollectionConfig values
        return cast(dict[str, CollectionConfig[Any]], collections)

    except Exception as e:
        logger.error(
            "collections_load_error",
            path=str(collections_path),
            error=str(e),
            error_type=type(e).__name__,
        )
        return {}


def get_collection_for_path(
    file_path: Path,
    content_root: Path,
    collections: dict[str, CollectionConfig[Any]],
) -> tuple[str | None, CollectionConfig[Any] | None]:
    """
    Determine which collection a content file belongs to.

    Matches the file path against collection directories to find the
    applicable collection. Used during content discovery to apply the
    correct schema validation.

    Args:
        file_path: Absolute or relative path to the content file.
        content_root: Root content directory (e.g., ``site/content/``).
        collections: Dictionary of loaded collections from :func:`load_collections`.

    Returns:
        A tuple of ``(collection_name, config)`` if the file is within a
        collection's directory, or ``(None, None)`` if the file doesn't
        belong to any defined collection.

    Example:
        >>> file_path = Path("content/blog/my-post.md")
        >>> name, config = get_collection_for_path(
        ...     file_path, Path("content"), collections
        ... )
        >>> name
        'blog'
        >>> config.schema
        <class 'BlogPost'>

    Note:
        - Files outside the content root always return ``(None, None)``
        - Remote collections (with ``loader`` but no ``directory``) are skipped
        - First matching collection wins if directories overlap (avoid this)
    """
    try:
        rel_path = file_path.relative_to(content_root)
    except ValueError:
        # File is not under content root
        return None, None

    # Check each collection's directory
    for name, config in collections.items():
        if config.directory is None:
            continue
        try:
            # Check if file is under this collection's directory
            rel_path.relative_to(config.directory)
            return name, config
        except ValueError:
            # Not under this collection's directory
            continue

    return None, None


def validate_collections_config(
    collections: dict[str, CollectionConfig[Any]],
    content_root: Path,
) -> list[str]:
    """
    Validate collection configurations for common issues.

    Checks that local collection directories exist and are valid directories.
    Remote collections (with loaders) are skipped.

    Args:
        collections: Dictionary of loaded collections from :func:`load_collections`.
        content_root: Root content directory to resolve relative paths.

    Returns:
        List of warning messages for invalid configurations. Empty list if
        all configurations are valid.

    Example:
        >>> warnings = validate_collections_config(collections, Path("content"))
        >>> for warning in warnings:
        ...     print(f"Warning: {warning}")
        Warning: Collection 'blog' directory does not exist: content/blog

    Note:
        This performs filesystem checks and should be called during site
        initialization, not during hot-reload. Remote collections with
        ``loader`` but no ``directory`` are automatically skipped.
    """
    warnings: list[str] = []

    for name, config in collections.items():
        if config.directory is None:
            continue
        collection_dir = content_root / config.directory

        if not collection_dir.exists():
            warnings.append(f"Collection '{name}' directory does not exist: {collection_dir}")
        elif not collection_dir.is_dir():
            warnings.append(f"Collection '{name}' path is not a directory: {collection_dir}")

    return warnings

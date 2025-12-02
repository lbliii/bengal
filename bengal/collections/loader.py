"""
Collection loader - loads collection definitions from project files.

Discovers and loads collection schemas from the user's collections.py file
at the project root.
"""

from __future__ import annotations

import importlib.util
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bengal.collections import CollectionConfig

logger = logging.getLogger(__name__)


def load_collections(
    project_root: Path,
    collection_file: str = "collections.py",
) -> dict[str, CollectionConfig]:
    """
    Load collection definitions from project's collections.py file.

    Searches for collections.py in the project root and loads the
    `collections` dictionary containing CollectionConfig instances.

    Args:
        project_root: Path to project root directory
        collection_file: Name of collections file (default: collections.py)

    Returns:
        Dictionary mapping collection names to CollectionConfig instances.
        Returns empty dict if no collections file found.

    Example:
        >>> collections = load_collections(Path("/path/to/project"))
        >>> for name, config in collections.items():
        ...     print(f"{name}: {config.directory}")
        blog: content/blog
        docs: content/docs

    Note:
        The collections file should export a `collections` dict:

        ```python
        # collections.py
        from dataclasses import dataclass
        from bengal.collections import define_collection

        @dataclass
        class BlogPost:
            title: str
            ...

        collections = {
            "blog": define_collection(schema=BlogPost, directory="content/blog"),
        }
        ```
    """
    collections_path = project_root / collection_file

    if not collections_path.exists():
        logger.debug(
            "no_collections_file",
            path=str(collections_path),
            message="No collections.py found, skipping schema validation",
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
                "collections_dict_missing",
                path=str(collections_path),
                message="collections.py found but no 'collections' dict defined",
            )
            return {}

        if not isinstance(collections, dict):
            logger.warning(
                "collections_invalid_type",
                path=str(collections_path),
                message=f"'collections' should be dict, got {type(collections).__name__}",
            )
            return {}

        logger.info(
            "collections_loaded",
            path=str(collections_path),
            count=len(collections),
            names=list(collections.keys()),
        )

        return collections

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
    collections: dict[str, CollectionConfig],
) -> tuple[str | None, CollectionConfig | None]:
    """
    Determine which collection a content file belongs to.

    Matches the file path against collection directories to find
    the applicable collection.

    Args:
        file_path: Path to content file
        content_root: Root content directory
        collections: Dictionary of loaded collections

    Returns:
        Tuple of (collection_name, CollectionConfig) if file is in a collection,
        or (None, None) if file doesn't belong to any collection.

    Example:
        >>> file_path = Path("content/blog/my-post.md")
        >>> name, config = get_collection_for_path(file_path, Path("content"), collections)
        >>> name
        'blog'
    """
    try:
        rel_path = file_path.relative_to(content_root)
    except ValueError:
        # File is not under content root
        return None, None

    # Check each collection's directory
    for name, config in collections.items():
        try:
            # Check if file is under this collection's directory
            rel_path.relative_to(config.directory)
            return name, config
        except ValueError:
            # Not under this collection's directory
            continue

    return None, None


def validate_collections_config(
    collections: dict[str, CollectionConfig],
    content_root: Path,
) -> list[str]:
    """
    Validate collection configurations.

    Checks that collection directories exist and are valid.

    Args:
        collections: Dictionary of loaded collections
        content_root: Root content directory

    Returns:
        List of warning messages for invalid configurations.
    """
    warnings: list[str] = []

    for name, config in collections.items():
        collection_dir = content_root / config.directory

        if not collection_dir.exists():
            warnings.append(
                f"Collection '{name}' directory does not exist: {collection_dir}"
            )
        elif not collection_dir.is_dir():
            warnings.append(
                f"Collection '{name}' path is not a directory: {collection_dir}"
            )

    return warnings


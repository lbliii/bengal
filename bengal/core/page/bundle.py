"""Page bundle detection and resource access shims.

Page bundles keep content and assets together in a directory:
- Leaf bundles: posts/my-post/index.md (page with co-located resources)
- Branch bundles: posts/_index.md (section index, no resources)
- Regular pages: posts/my-post.md (standalone file, no bundle resources)

This module provides:
- BundleType enum for bundle classification
- Free functions for bundle detection
- PageResources collection for matching co-located files
- PageResource for individual resource file references

Functions accept explicit parameters (source_path, url) instead of
accessing them through mixin self-reference.

Example:
    >>> from bengal.core.page.bundle import get_bundle_type, get_resources
    >>> get_bundle_type(Path("posts/my-post/index.md"))
    <BundleType.LEAF: 'leaf'>
    >>> resources = get_resources(Path("posts/my-post/index.md"), "/posts/my-post/")
    >>> hero = resources.get_match("hero.*")

See Also:
- bengal/core/page/__init__.py: Page class that wraps these functions as properties

"""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path


class BundleType(Enum):
    """Type of content bundle.

    Bundle classification based on filename convention:
    - NONE: Regular standalone page (my-post.md)
    - LEAF: Leaf bundle with resources (my-post/index.md)
    - BRANCH: Branch bundle / section index (_index.md)

    """

    NONE = "none"  # Regular page (my-post.md)
    LEAF = "leaf"  # Leaf bundle (my-post/index.md)
    BRANCH = "branch"  # Branch bundle (_index.md)


@dataclass(frozen=True, slots=True)
class PageResource:
    """Single resource co-located with a page bundle.

    Represents a non-content file in a leaf bundle directory
    (images, data files, PDFs, etc.).

    Attributes:
        path: Absolute path to the resource file
        page_url: URL of the parent page (for rel_permalink)

    Example:
            >>> resource = PageResource(path=Path("/site/posts/my-post/hero.jpg"), page_url="/posts/my-post/")
            >>> resource.name
            'hero.jpg'
            >>> resource.rel_permalink
            '/posts/my-post/hero.jpg'

    """

    path: Path
    page_url: str

    @property
    def name(self) -> str:
        """Filename with extension."""
        return self.path.name

    @property
    def stem(self) -> str:
        """Filename without extension."""
        return self.path.stem

    @property
    def suffix(self) -> str:
        """File extension including dot (e.g., '.jpg')."""
        return self.path.suffix

    @property
    def rel_permalink(self) -> str:
        """URL relative to site root.

        Resources are served alongside the page.
        """
        # Ensure page_url ends with /
        page_url = self.page_url.rstrip("/") + "/" if self.page_url else "/"
        return f"{page_url}{self.name}"

    @property
    def size(self) -> int:
        """File size in bytes."""
        from bengal.rendering.page_resources import resource_size

        return resource_size(self)

    @property
    def exists(self) -> bool:
        """Check if the resource file exists."""
        from bengal.rendering.page_resources import resource_exists

        return resource_exists(self)

    @property
    def resource_type(self) -> str | None:
        """Get resource type category based on extension.

        Returns one of: 'image', 'video', 'audio', 'document', 'data', 'code', 'archive'
        or None if unrecognized.
        """
        from bengal.rendering.page_resources import resource_type

        return resource_type(self)

    def as_image(self) -> Any | None:
        """Convert to ImageResource for image processing."""
        from bengal.rendering.page_resources import as_image

        return as_image(self)

    def read_text(self, encoding: str = "utf-8") -> str:
        """Read resource as text (for data files)."""
        from bengal.rendering.page_resources import read_text

        return read_text(self, encoding=encoding)

    def read_bytes(self) -> bytes:
        """Read resource as bytes (for binary files)."""
        from bengal.rendering.page_resources import read_bytes

        return read_bytes(self)

    def read_json(self) -> Any:
        """Read resource as JSON.

        Returns parsed JSON data.
        """
        from bengal.rendering.page_resources import read_json

        return read_json(self)

    def read_yaml(self) -> Any:
        """Read resource as YAML.

        Returns parsed YAML data.
        """
        from bengal.rendering.page_resources import read_yaml

        return read_yaml(self)

    def __str__(self) -> str:
        """Return URL for easy template usage."""
        return self.rel_permalink


@dataclass
class PageResources:
    """Collection of resources co-located with a page bundle.

    Provides resource access methods for leaf bundles including
    pattern matching and type-based filtering.
    Empty collection for non-bundle pages.

    Attributes:
        _resources: Internal list of PageResource objects
        _by_name: Lookup dict keyed by filename

    Example:
            >>> resources = page.resources
            >>> hero = resources.get_match("hero.*")
            >>> images = resources.by_type("image")
            >>> data = resources.get("config.json")

    """

    _resources: list[PageResource] = field(default_factory=list)
    _by_name: dict[str, PageResource] = field(default_factory=dict, init=False, repr=False)

    def __post_init__(self) -> None:
        """Build lookup dict from resources."""
        self._by_name = {r.name: r for r in self._resources}

    def get(self, name: str) -> PageResource | None:
        """Get resource by exact filename.

        Args:
            name: Exact filename to match (e.g., "hero.jpg")

        Returns:
            PageResource if found, None otherwise

        Example:
            >>> page.resources.get("data.json")
        """
        return self._by_name.get(name)

    def get_match(self, pattern: str) -> PageResource | None:
        """Get first resource matching glob pattern.

        Args:
            pattern: Glob pattern (e.g., "hero.*", "*.pdf")

        Returns:
            First matching PageResource, or None

        Example:
            >>> page.resources.get_match("hero.*")  # hero.jpg, hero.png, etc.
            >>> page.resources.get_match("diagram-*.svg")
        """
        for r in self._resources:
            if fnmatch.fnmatch(r.name, pattern):
                return r
        return None

    def match(self, pattern: str) -> list[PageResource]:
        """Get all resources matching glob pattern.

        Args:
            pattern: Glob pattern (e.g., "*.jpg", "gallery-*")

        Returns:
            List of matching PageResource objects

        Example:
            >>> page.resources.match("gallery-*.jpg")
            >>> page.resources.match("*.pdf")
        """
        return [r for r in self._resources if fnmatch.fnmatch(r.name, pattern)]

    def by_type(self, resource_type: str) -> list[PageResource]:
        """Get resources by MIME type category.

        Args:
            resource_type: One of 'image', 'video', 'audio', 'document', 'data', 'code', 'archive'

        Returns:
            List of matching PageResource objects

        Example:
            >>> page.resources.by_type("image")
            >>> page.resources.by_type("data")
        """
        from bengal.rendering.page_resources import by_type

        return by_type(self, resource_type)

    def images(self) -> list[PageResource]:
        """Get all image resources. Convenience alias for by_type("image")."""
        from bengal.rendering.page_resources import images

        return images(self)

    def data(self) -> list[PageResource]:
        """Get all data resources (JSON, YAML, CSV, etc.). Convenience alias for by_type("data")."""
        from bengal.rendering.page_resources import data

        return data(self)

    def __iter__(self) -> Iterator[PageResource]:
        """Iterate over all resources."""
        return iter(self._resources)

    def __len__(self) -> int:
        """Number of resources."""
        return len(self._resources)

    def __bool__(self) -> bool:
        """True if there are any resources."""
        return len(self._resources) > 0

    def __contains__(self, name: str) -> bool:
        """Check if resource exists by name."""
        return name in self._by_name


def get_bundle_type(source_path: Path) -> BundleType:
    """Determine bundle type from file structure.

    - index.md in directory → LEAF (has resources)
    - _index.md in directory → BRANCH (section, no resources)
    - standalone .md file → NONE

    Args:
        source_path: Path to the source markdown file

    Returns:
        BundleType enum value
    """
    name = source_path.name.lower()

    if name == "index.md":
        return BundleType.LEAF
    if name == "_index.md":
        return BundleType.BRANCH
    return BundleType.NONE


def is_leaf_bundle(source_path: Path) -> bool:
    """True if this page is a leaf bundle with resources.

    Only leaf bundles (index.md) have co-located resources.
    Branch bundles (_index.md) are section indexes without resources.

    Args:
        source_path: Path to the source markdown file
    """
    return get_bundle_type(source_path) == BundleType.LEAF


def is_branch_bundle(source_path: Path) -> bool:
    """True if this page is a branch bundle (section index).

    Args:
        source_path: Path to the source markdown file
    """
    return get_bundle_type(source_path) == BundleType.BRANCH


def get_resources(source_path: Path, url: str) -> PageResources:
    """Compatibility wrapper for rendering-owned page bundle resource discovery.

    For leaf bundles (index.md in directory), returns all
    non-markdown files in the same directory.

    Returns empty PageResources for non-bundles (not an error).

    Args:
        source_path: Path to the source markdown file
        url: Page URL (for resource permalinks)

    Returns:
        PageResources collection (empty if not a bundle)

    Example:
        >>> get_resources(Path("posts/my-post/index.md"), "/posts/my-post/")
    """
    from bengal.rendering.page_resources import get_resources as _get_resources

    return _get_resources(source_path, url)
